# Security

最終更新: 2026-07-17

Memory OSは、ユーザーの人生の文脈、画像、URL、視聴・読書・食事・旅行・人間関係など、高感度になり得る情報を扱う。

## Current status

```txt
security architecture / threat model / verification gate:
DEFINED

machine-readable security foundation:
24 registered schemas
23 positive contract fixtures
31 structural rejection cases
8 semantic rejection cases

Go backend:
PARTIAL SECURITY VERTICAL SLICE
not a production backend

Preview spool contract:
HARDENED
runtime not implemented

PostgreSQL:
RLS / upload persistence foundation migration and SQL tests created
production domain schema / repositories incomplete

object storage / parser runtime / iOS / Portal:
NOT IMPLEMENTED

GitHub Actions:
workflows created
remote result for current HEAD unconfirmed

production readiness:
NO-GO
```

This repository is in security-foundation and partial backend vertical-slice development. Do not claim “perfectly safe”, “unhackable”, “complete privacy”, “backend complete” or “production ready”.

## Read first

1. [Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)
2. [Current Implementation Status and Roadmap](docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md)
3. [Preview Spool and Atomic Commit Contract](docs/memory-os-preview-spool-commit-contract-round-9.md)
4. [Import API Security Slice](services/import-api/README.md)
5. [Capture / Import Security Architecture](docs/memory-os-capture-import-security-architecture-round-9.md)
6. [Capture / Import Threat Model](docs/memory-os-capture-import-threat-model-round-9.md)
7. [Security Verification Gate](docs/memory-os-security-verification-gate-round-9.md)
8. [Security Schema Registry](docs/schemas/memory-os-security/schema-registry.v1.json)
9. [Security Fixture Index](docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json)
10. [Signed Upload OpenAPI](contracts/openapi/memory-os-import-security.v1.openapi.json)

Historical progress and next-chat documents are not current authority.

## Re-run contract checks

```bash
python -m pip install -r requirements-security-validation.txt
python scripts/validate-memory-os-security.py
python scripts/validate-memory-os-authorization.py
python scripts/validate-memory-os-postgresql-rls.py
python scripts/validate-memory-os-apple-auth.py
python scripts/validate-memory-os-signed-upload-openapi.py
python scripts/validate-memory-os-parser-security.py
python scripts/validate-memory-os-preview-spool.py
```

## Re-run Go slice checks

```bash
cd services/import-api
test -z "$(gofmt -l .)"
go test ./...
go vet ./...
go test -race ./...

GOMAXPROCS=4 go test -run='^$' \
  -fuzz=FuzzParserNeverPanicsOrExpandsLimits \
  -fuzztime=5s -timeout=30s ./internal/adapters/genericcsv

GOMAXPROCS=4 go test -run='^$' \
  -fuzz=FuzzParseCompactTokenNeverPanics \
  -fuzztime=5s -timeout=30s ./internal/appleauth
```

Do not write `PASS` into current status unless these commands were run against the exact recorded HEAD. Historical PASS statements apply only to the snapshot that recorded them.

## Security priorities

```txt
1. prevent cross-user disclosure
2. prevent unauthorized or silent Memory writes
3. isolate untrusted imports and parsers
4. bind Preview to exact Apply content
5. keep raw and spool files private and short-lived
6. prevent retry and deletion resurrection
7. keep private content out of logs, analytics and notifications
8. preserve export and deletion rights
```

## Binding implementation boundaries

- Sign in with Apple identity is verified server-side; canonical account binding is issuer + subject, not email.
- Client-provided account ID, epoch, owner, bucket, object key and storage version are never authority.
- Verified principal fields are private and enter request handling through dedicated server context.
- PostgreSQL work uses fixed roles and transaction-local account ID / account epoch context.
- Every Import Job, pairing session, upload authorization, quarantine object, Preview, Apply, report and export is object-authorized.
- User-owned PostgreSQL security tables use `FORCE RLS`; runtime roles are `NOLOGIN NOINHERIT NOBYPASSRLS` and do not own tables.
- Existing SQL files are RLS/upload security foundations, not the complete production domain schema.
- Signed upload is bound to one owner, epoch, job, generated key, size, SHA-256, content type and expiry.
- Upload completion checks real server-side object metadata and exact object version.
- Generic CSV parsing is bounded and synchronous one-row pull; its Preview bridge has no hidden goroutine or channel.
- Parser input never triggers URL fetching; URL checks are syntactic only.
- Formula-like CSV content remains literal and receives a warning code rather than execution.
- Preview is bound to source version/size/checksum, adapter artifact, options and both accepted/rejected stream evidence.
- Production Preview parsing occurs outside database transactions through a private bounded spool.
- Spool manifests do not carry filesystem paths; attempts are server-generated, private, no-follow and non-reusable.
- Final Apply is iOS-user-only, exact-hash-bound and idempotent; browser pairing authority is denied.
- Created, updated and skipped counts must account for every accepted Preview candidate or Apply rolls back.
- Parser workers remain outside the public API process, non-root, networkless, read-only and resource-limited.
- App Group data is minimized; secrets remain in Keychain.
- Audit events cannot contain private content, raw filenames, raw URLs, tokens, email addresses or user notes.
- Account deletion fences jobs, workers, signed URLs, objects, spool attempts, Preview, Apply, caches, exports, App Group files and restored backups.

## Current executable evidence

Machine-readable evidence:

```txt
registered schemas:                    24
positive contract fixtures:            23
structural schema rejections:          31
semantic rejections:                    8
object authorization cases:             8
PostgreSQL RLS logic cases:             14
Sign in with Apple cases:               16
parser sandbox unsafe mutations:       16
archive / JSON / CSV cases:             25
Preview spool structural cases:          9
Preview spool semantic cases:            6
```

Executable/reference Go code exists for verified principals, scoped transactions, Apple JWT/JWKS validation, signed-upload boundaries, bounded CSV parsing, synchronous CSV iteration, Preview hashing and idempotent Apply interfaces.

This evidence does not prove production safety. Concrete server composition, repositories, object storage, spool runtime, parser sandbox runtime, deletion fencing, iOS and Portal remain incomplete.

## Production blockers

Production remains blocked until the Security Verification Gate has current evidence for:

- exact-current-HEAD local and remote CI success;
- real cross-user HTTP and PostgreSQL isolation;
- concrete Sign in with Apple code exchange, replay store and session issuance;
- signed upload enforcement against private versioned object storage;
- supervisor-owned spool creation, sealing, independent re-hash and terminal cleanup;
- concrete Preview candidate/rejection/ready schema and atomic `pgx.CopyFrom` repository;
- concrete Apply and Memory persistence;
- parser sandbox runtime inspection and adapter artifact verification;
- malicious archive / JSON / CSV corpus and fuzzing;
- deletion race and backup-restore non-resurrection tests;
- App Group crash recovery and local storage inspection;
- Portal CSP / XSS / browser-token tests;
- sensitive-log canary tests;
- dependency, secret, container, SBOM and provenance gates;
- independent review with zero unresolved Critical / High findings;
- zero unresolved P0 security findings.

## Vulnerability reporting

A private vulnerability-reporting channel has not yet been published because the product is not in public production.

Before public beta, publish:

- private security contact;
- supported versions;
- acknowledgement target;
- severity and remediation targets;
- disclosure coordination policy.

Do not place private user data, credentials, tokens or live exploit payloads in a public GitHub issue.
