# Memory OS Quarantine Object Storage Checkpoint

最終更新: 2026-07-19

## Verdict

```txt
Preview spool package + PostgreSQL domain + commit repository:
PARTIAL IMPLEMENTATION (live-tested)

signed-upload S3-compatible storage adapter:
PARTIAL IMPLEMENTATION CREATED (live-tested against MinIO)

parser supervisor / executable server / clients:
NOT IMPLEMENTED

production:
NO-GO
```

This checkpoint makes the signed-upload boundary real: presigned quarantine PUTs whose bindings are enforced by the storage service itself, and HEAD verification that returns the exact object version.

## Implemented files

```txt
services/import-api/internal/objectstore/sigv4.go
services/import-api/internal/objectstore/client.go
services/import-api/internal/objectstore/sigv4_test.go
services/import-api/internal/objectstore/client_test.go
services/import-api/internal/objectstore/client_live_test.go
.github/workflows/import-api-security-slice.yml (MinIO service)
```

`objectstore.Client` implements `upload.Signer` and `upload.ObjectStore` with **no SDK dependency**: AWS Signature V4 is implemented directly on the standard library and pinned to the documented AWS test vector.

## Binding model

`PresignPut` returns one PUT URL whose signature covers, as signed headers:

```txt
host
content-length
content-type
x-amz-checksum-sha256  (base64 of the authorized full-object SHA-256)
```

so the storage service — not application code — rejects any upload that omits or alters the bound length, type or checksum, or that substitutes different content under the same headers. The adapter additionally enforces:

- exact `quarantine/{job}/{upload}` key shape with dot-segment rejection (the character class alone would admit `..`, which URL normalization could fold into a foreign path);
- content length 1..256 MiB and hex SHA-256 shape;
- presign TTL bounded to 15 minutes;
- endpoint/bucket/credential configuration validation.

`HeadObject` sends a SigV4 header-signed HEAD with `x-amz-checksum-mode: ENABLED` and returns the exact `x-amz-version-id`, ETag, length, content type and the full-object SHA-256 converted back to lowercase hex — feeding the upload service's exact-metadata completion check unchanged.

## Live evidence (MinIO)

10 top-level tests; the 4 live ones are gated on `MEMORY_OS_TEST_S3_ENDPOINT` and provision their own versioned bucket:

- documented AWS SigV4 presign vector reproduced byte-for-byte;
- presigned round trip: upload accepted only with the exact bound headers; HEAD returns non-empty version ID, exact length/type and matching checksum hex;
- re-upload of the same key yields a **different version ID** (bucket versioning proven, not assumed);
- tampered checksum header, missing content type and substituted content are all rejected by the store and leave no object behind;
- expired presigned URLs are rejected;
- missing objects report not-found; traversal keys never reach the network.

## Validation language

```txt
local golang:1.23 + postgres:16-alpine + minio (fresh), exact HEAD 229c0bfa67679e868ee52601da9c411e8faafb63:
gofmt clean + go vet + go test -race ./... (15 packages, live DB and object-store tests included)
+ both 5s fuzz smokes PASS

remote Import API workflow with postgres + MinIO services:
recorded after the push completes
```

## Residual risks

- production must use TLS and non-root scoped credentials; the adapter tolerates http and root credentials only for test containers;
- lifecycle/retention rules (quarantine TTL, abort-incomplete-multipart) remain deployment configuration without runtime evidence;
- MinIO is S3-compatible evidence, not AWS-production evidence;
- the upload service and this adapter are not yet composed into an executable server.

## Immediate next task

```txt
Implement the isolated parser supervisor only:
spawn one parser worker per job with no network, no credentials and bounded resources
→ feed the version-bound quarantine object read-only
→ receive canonical rows over a synchronous pipe into the bounded spool writer
→ seal on success; reconcile on crash
→ prove isolation and resource bounds with targeted tests
```

Do not add executable-server or client wiring in that checkpoint.
