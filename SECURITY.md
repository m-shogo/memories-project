# Security

最終更新: 2026-07-20

Memory OS handles highly sensitive personal context. The repository is in security-foundation and partial backend vertical-slice development.

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

Preview spool:
manifest contract hardened
Linux filesystem attempt lifecycle checkpoint created
bounded stream writer created
stream fsync + no-replace manifest publication created
independent decode / count / re-hash verifier created
startup reconciliation + TTL cleanup created

PostgreSQL:
RLS / upload security foundation migrations and SQL tests created
production Preview domain schema created with live SQL tests
atomic Go Preview commit repository created (live-tested)

object storage adapter:
CREATED (live-tested against MinIO)

parser supervisor:
PROCESS BOUNDARY CREATED (live-tested; network namespace is deployment work)

iOS / Portal:
NOT IMPLEMENTED

GitHub Actions:
workflows created
earlier Import API runs failed on formatting/vet; repaired at the verifier checkpoint
every push since the verifier checkpoint green (latest recorded: Import API run 29691864573 with live DB + MinIO tests, Security Contracts run 29691821341)

production:
NO-GO
```

Do not claim perfectly secure, unhackable, fully private, backend complete, Preview spool complete or production ready.

## Read first

1. [Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)
2. [Current Implementation Status and Roadmap](docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md)
3. [Preview Spool and Atomic Commit Contract](docs/memory-os-preview-spool-commit-contract-round-9.md)
4. [Import API Security Slice](services/import-api/README.md)
5. [Capture / Import Security Architecture](docs/memory-os-capture-import-security-architecture-round-9.md)
6. [Threat Model](docs/memory-os-capture-import-threat-model-round-9.md)
7. [Security Verification Gate](docs/memory-os-security-verification-gate-round-9.md)
8. [Schema Registry](docs/schemas/memory-os-security/schema-registry.v1.json)
9. [Fixture Index](docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json)

Historical progress and handoff documents are not current authority.

## Contract validation

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

## Go validation

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

Historical PASS applies only to its recorded commit. The current repository full suite and remote workflows are not claimed until rerun against the exact HEAD.

## Binding boundaries

- Sign in with Apple is verified server-side; identity is issuer + subject, not email.
- Client account, owner, epoch, bucket, object key and version are never authority.
- PostgreSQL uses fixed roles and transaction-local owner/epoch; user security tables use `FORCE RLS`.
- Existing SQL provides the security foundation plus the production Preview domain (`preview_ready`/`preview_candidate`/`preview_rejection`): worker-only insert, no updates, deterministic commit keys, one ready Preview per job, structurally safe rejections and a completeness gate before COMMIT.
- Signed upload binds one owner/epoch/job/key/size/checksum/type/expiry and verifies real object metadata/version.
- CSV parsing is bounded synchronous pull; no hidden goroutine/channel in iterator or Preview bridge.
- Preview binds source, adapter, options and accepted/rejected evidence.
- Production parsing occurs outside database transactions through a private bounded spool.
- Spool manifests contain no filesystem paths.
- Linux spool attempts use a supervisor-provisioned `0700` root, descriptor-relative create/open, `O_EXCL/O_NOFOLLOW`, fixed `0600` files and inode substitution checks.
- Unknown filesystem entries fail closed; successful cleanup is idempotent; non-Linux fails closed.
- Stream records are exact length-prefixed canonical bytes with aggregate record/byte and per-record limits; writer failures are sticky and terminal.
- Seal publication fsyncs both streams, writes an exclusive `manifest.tmp`, publishes with `linkat` no-replace semantics and fsyncs the attempt directory; existing final names are never overwritten.
- Independent verification re-opens everything descriptor-relative with `O_NOFOLLOW`, strictly decodes exactly one canonical manifest, re-counts and re-hashes exact stream bytes, enforces expiry and rejects every binding mismatch before any database transaction.
- Startup reconciliation runs one exclusive fail-closed pass: it removes only fixed-name crash residue and expired sealed attempts, completes the linkat crash window, quarantines everything unclassifiable in place and never deletes a sealed unexpired attempt.
- The atomic commit repository exists and is live-tested; the composed production flow (fetch → supervised parse → verify → commit) is not yet wired.
- Final Apply is iOS-user-only, exact-hash-bound and idempotent.
- Account deletion fences jobs, workers, URLs, objects, spools, Preview, Apply, caches, exports and backup restoration.
- Private content is forbidden in logs, analytics, notifications and crash reports.

## Current machine evidence

```txt
registered schemas:                         24
positive contract fixtures:                 23
structural schema rejections:               31
semantic rejections:                         8
object authorization cases:                  8
PostgreSQL RLS logic cases:                 14
Sign in with Apple cases:                   16
parser sandbox unsafe mutations:            16
archive / JSON / CSV cases:                 25
Preview spool structural cases:              9
Preview spool semantic cases:                6
Preview spool filesystem top-level tests:    9
Preview spool cancellation stages:           5
Preview spool writer top-level tests:        9
Preview spool seal top-level tests:         10
Preview spool verifier top-level tests:     15
Preview spool reconciliation top-level tests: 8
Preview domain live SQL test blocks:        19
Preview commit repository top-level tests:   9
object storage top-level tests:             10
parser supervision top-level tests:         12
```

Repository-integrated Go evidence:

```txt
code HEAD c09ef41bcf8cacd023ecba6c46086c8d554085c4
(local golang:1.23 Linux container + fresh postgres:16 + MinIO):
gofmt clean + go vet + go test ./... + go test -race ./... (16 packages,
live DB/object-store/supervision tests included) + both 5s fuzz smokes PASS

remote workflows at object-storage HEAD 27b5e33:
Import API Security Slice run 29691864573 SUCCESS (live DB + MinIO tests executed)
Security Contracts run 29691821341 SUCCESS
```

## Production blockers

Production remains blocked until current evidence exists for:

- real cross-user HTTP/PostgreSQL isolation;
- concrete Apple code exchange, replay and session issuance;
- production object-storage TLS, scoped credentials and lifecycle evidence;
- deployment-exclusive reconciliation execution and quarantine alerting;
- supervisor composition wiring verifier and commit repository as one production flow;
- concrete Apply/Memory persistence;
- parser network-namespace/seccomp/container deployment evidence and reviewed adapter artifacts;
- malicious corpus/fuzz evidence;
- deletion race and backup non-resurrection;
- iOS App Group and Portal security evidence;
- sensitive-log canaries and supply-chain gates;
- independent review with zero unresolved Critical/High;
- zero unresolved P0.

## Vulnerability reporting

A private reporting channel is not yet published because the product is not public production. Before beta, publish a security contact, supported versions, acknowledgement/remediation targets and disclosure policy.

Never place private user data, credentials, tokens or live exploit payloads in a public GitHub issue.
