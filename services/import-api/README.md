# Memory OS Import API — Security Vertical Slice

This Go module is the executable backend security slice for Capture / Import. It is intentionally incomplete and must not be described as a production backend.

## Authority

Production and implementation claims are governed by:

1. [`docs/memory-os-current-authority-order-round-10-operability.md`](../../docs/memory-os-current-authority-order-round-10-operability.md)
2. [`contracts/operations/production-operability-status.json`](../../contracts/operations/production-operability-status.json)
3. [`docs/memory-os-current-authority-order-round-9-security.md`](../../docs/memory-os-current-authority-order-round-9-security.md)

Production remains `NO_GO`.

## Current implementation

The executable HTTP server exists. It includes hardened timeouts, graceful shutdown, bearer-session middleware, strict upload handlers, Preview reads, Apply, account deletion and Apple authentication routes.

Apple code exchange, replay protection, account binding and session issuance exist and are live-tested against a fake Apple boundary plus PostgreSQL. Real-Apple credential evidence remains a deployment gate, not an unimplemented code path.

Implemented foundations include:

- verified-principal and request-context boundaries;
- fixed PostgreSQL runtime roles and transaction-local account/epoch context;
- `FORCE RLS` repositories and restricted authentication functions;
- Apple JWT/JWKS verification, code exchange, nonce/code replay protection and account binding;
- bearer sessions stored only as SHA-256 digests;
- signed quarantine uploads with exact metadata/version verification;
- bounded Generic CSV parsing and canonical parser-option binding;
- Linux Preview spool lifecycle, bounded writer, durable no-replace publication and independent verification;
- startup reconciliation and TTL cleanup;
- canonical adapter record contract and Generic CSV worker;
- digest-pinned, resource-bounded parser supervision;
- version-pinned object fetch and supervised import flow;
- atomic Preview commit under live PostgreSQL;
- executable `importctl` development harness;
- idempotent exact-hash Apply into minimal `memory_item` persistence;
- Preview read API;
- account epoch fencing, stored-object erasure and resumable deletion worker;
- provenance and interpretation invariants with destructive update paths closed fail-closed;
- deterministic Prometheus text exposition with mandatory histogram `+Inf` buckets;
- a fail-closed bearer-authenticated metrics scrape handler with bounded response size;
- an explicit, default-disabled HTTP server mount seam that keeps metrics outside public API rate-limit buckets while retaining privacy-safe request observability.

## Critical boundaries

### Database and identity

- Runtime traffic must use the deployment login principal and `SET LOCAL ROLE`; superuser access is development-only.
- Identity authority is issuer + subject, never email.
- Client account, owner, epoch, bucket, object key and version are never authority.
- Raw bearer tokens never enter logs or request context.

### Upload and object storage

- Presigned upload authorization binds content length, content type and SHA-256 checksum.
- Completion verifies the exact object version and authoritative metadata.
- Production TLS, scoped credentials, independent retention and lifecycle evidence remain deployment work.

### Parser and spool

- Untrusted parsing occurs outside database transactions.
- The parser worker is digest-pinned, secretless, process-group isolated and bounded by CPU, memory, file-descriptor, output and wall-clock limits.
- Network namespace/seccomp/container evidence is still required for production.
- A published spool manifest is untrusted until independent verification reopens, re-decodes, re-counts and re-hashes every binding.
- Unknown filesystem state is quarantined or rejected; it is not deleted merely to clear an alert.

### Preview and Apply

- Preview persistence is one short atomic transaction under `FORCE RLS`.
- Exact retries are idempotent and conflicting retries fail closed.
- Apply is exact-Preview-hash-bound and fully accounted.
- Rejected rows never enter Apply.
- Destructive `update_safe_fields` behavior is disabled; append-only supersession remains future work.

### Deletion

- `DELETE /v1/account` fences the account before asynchronous erasure.
- Leased deletion work resumes after interruption.
- Backup/restore non-resurrection has not yet been proven and remains a P0 gate.

### Metrics scrape

- The Prometheus exporter reads only the closed, bounded-cardinality registry.
- Scrape authentication uses a deployment bearer token hashed before constant-time comparison; the raw token is not logged or labeled.
- The handler is not mounted by default.
- A deployment must explicitly construct and pass the handler, provision its secret, and place the listener behind a private operational network boundary.
- No production listener, network policy, external scraper, dashboard, retention rule or alert route is configured yet.

## Development-only components

- `cmd/importctl` and `scripts/dev-import.sh` are local development harnesses.
- The dev stack may use privileged bootstrap/read-back paths and must never target production.
- Operator-supplied worker pins are not a reviewed production artifact registry.

## Not implemented or not production-proven

- rich Memory domain, shelves, retrieval/search and append-only supersession;
- iOS canonical client and limited Desktop Portal;
- real-Apple credential/key-rotation evidence;
- production object-storage TLS/scoped credentials/lifecycle evidence;
- parser network namespace/seccomp/container evidence;
- privacy-safe structured observability and real alert routing (structured event contract, correlation IDs and redaction tests now exist under `internal/obslog` and `internal/reqid`; retention and real alert routing remain, so OPS-P0-003 stays PARTIAL, not READY);
- production metrics operations (the typed bounded-cardinality registry, deterministic Prometheus exporter, authenticated scrape handler and explicit default-disabled server mount seam exist with machine-readable contracts and fail-closed tests; production secret provisioning, private network policy, runtime mounting, external scraping, dashboards, alert routing, retention and load-calibrated buckets/SLOs remain, so OPS-P0-004 stays PARTIAL, not READY);
- endpoint-specific distributed rate limiting (a fail-closed token-bucket limiter with route-global and keyed per-network guards, explicit trusted-proxy boundary and a stable 429 now exists under `internal/ratelimit`; a distributed shared store, trusted-proxy configuration and load-calibrated limits remain, so OPS-P0-005 stays PARTIAL, not READY);
- production-shaped load/capacity evidence (the committed mock harness and results cover deterministic steady, burst, failure and cardinality scenarios; executable live checkpoints now drive Preview read and concurrent idempotent Apply through bearer sessions, the deployment PostgreSQL principal and `FORCE RLS`, and drive signed authorization, presigned PUT, exact object-version verification and scan enqueue through PostgreSQL 16 plus MinIO. Both live checkpoints have machine-readable contracts, independent fail-closed validators and an automatic push-triggered/daily regeneration workflow. Local PostgreSQL/MinIO evidence does not establish a production capacity boundary, sustained soak, production-equivalent dependencies or production object-storage controls, so OPS-P0-006 stays PARTIAL, not READY);
- PostgreSQL PITR and isolated restore rehearsal;
- production-shaped migration recovery and mixed-version proof;
- incident paging and completed recovery drills;
- critical production system-level failure drills;
- independent review with zero unresolved Critical/High.

## Validation

From the repository root:

```bash
python scripts/validate-memory-os-security.py
python scripts/validate-memory-os-authorization.py
python scripts/validate-memory-os-postgresql-rls.py
python scripts/validate-memory-os-apple-auth.py
python scripts/validate-memory-os-signed-upload-openapi.py
python scripts/validate-memory-os-parser-security.py
python scripts/validate-memory-os-preview-spool.py
python scripts/validate-memory-os-canonical-records.py
python scripts/validate-memory-os-memory-provenance.py
python scripts/validate-memory-os-metrics.py
python scripts/validate-memory-os-metrics-scrape.py
python scripts/validate-memory-os-load.py
python scripts/validate-memory-os-live-load.py
python scripts/validate-memory-os-live-object-load.py
python scripts/validate-memory-os-operability.py
python scripts/validate-memory-os-entry-docs.py
```

The live validators require their generated result documents. Automatic workflows create those documents from the exact source SHA before running the validators. Their absence is a missing-evidence signal, not a reason to fabricate a PASS fixture.

From `services/import-api`:

```bash
test -z "$(gofmt -l .)"
go vet ./...
go build ./cmd/...
go test ./...
go test -race ./...

GOMAXPROCS=4 go test -run='^$' \
  -fuzz=FuzzParserNeverPanicsOrExpandsLimits \
  -fuzztime=5s -timeout=30s ./internal/adapters/genericcsv

GOMAXPROCS=4 go test -run='^$' \
  -fuzz=FuzzParseCompactTokenNeverPanics \
  -fuzztime=5s -timeout=30s ./internal/appleauth
```

Historical PASS applies only to its recorded commit and exact scope. Do not claim that a newer HEAD is green until the relevant workflows and local suites have run against that exact HEAD.
