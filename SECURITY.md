# Security

最終更新: 2026-07-20

Memory OS handles highly sensitive personal context. The repository is in security-foundation and partial backend vertical-slice development.

## Current status

<!-- MEMORY_OS_STATUS_BLOCK:BEGIN -->

```txt
product priority:
Capture / Import first

security architecture:
DEFINED

machine-readable contracts:
26 schemas / 23 positive fixtures
31 structural + 8 semantic rejection cases

Go backend:
PARTIAL SECURITY VERTICAL SLICE
not a production backend

Preview spool:
manifest contract hardened
Linux attempt filesystem lifecycle created
bounded accepted/rejected writer created
stream fsync + no-replace manifest publication created
independent decode / count / re-hash verifier created
startup reconciliation + TTL cleanup created

PostgreSQL:
RLS / upload security foundations created
production Preview domain schema created with live SQL tests
atomic Go Preview commit repository created (live-tested)

object storage adapter:
created (live-tested against MinIO)

parser supervisor:
process boundary created (live-tested; network namespace is deployment work)

supervised import flow:
composed and live-tested end to end (fetch → parse → verify → commit)

canonical adapter record contract:
reviewed contract created; real adapter wired through the supervised worker

importctl harness (first visible end-to-end run):
created and executed for real: local CSV → committed Preview printed to the terminal

runtime-role database access:
pgx scoped executor + concrete upload repository proven under FORCE RLS (non-superuser path)

executable HTTP server:
bearer-session auth over the strict upload handlers; exercised for real with curl (Apple exchange remains a later boundary)

Apply / Memory persistence:
idempotent exact-hash apply into memory_item over HTTP; preview read API; rich Memory domain model remains future work

account deletion fencing:
epoch bump fences every surface; authorized sweep erases all owned rows, sessions and stored object versions (live-tested over HTTP + MinIO)

deletion backlog alerting:
stuck deletions alert as counts only; identifiers go to the runtime that must act, never to the alerting surface
the alert is a log line — wiring it to a real alerting system is deployment work

fuzz corpus:
coverage-interesting inputs for both parsers committed as seed corpora and replayed by every test run

background deletion runtime:
DELETE /v1/account returns 202 after fencing only; a leased worker erases and resumes after interruption (live-proven)
no alerting yet on an account whose deletion attempts keep climbing

deployment login principal:
NOINHERIT / NOBYPASSRLS login with no table privileges; the HTTP journey and the RLS proofs now run through it, not through a superuser

iOS / Portal:
not implemented

current full-repository Go suite:
PASS in a local golang:1.23 Linux container at the recorded HEAD

remote Actions:
deployment-login-deletion-runtime-fuzz-corpus HEAD 0f79f5c CONFIRMED green (Import API run 30059874457, Security Contracts run 30059815370)
Security Contracts last ran at b030b66, not at HEAD: Security Contracts does not run at 0f79f5c: that commit touches only fuzz testdata and a script, which its path filters exclude. b030b66 is the newest commit that changed anything it checks.

production:
NO-GO
```

<!-- MEMORY_OS_STATUS_BLOCK:END -->

GitHub Actions: workflows created; earlier Import API runs failed on formatting/vet and were repaired at the verifier checkpoint; every push since has run green (see the remote-Actions line above for the latest confirmed run).

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
- The composed production flow (version-pinned fetch → supervised parse → seal → independent verify → canonical decode → atomic commit) is wired end to end and live-tested with the real Generic CSV adapter under the machine-validated canonical record contract; there is no executable server yet.
- Final Apply is iOS-user-only, exact-hash-bound and idempotent.
- Account deletion fences jobs, workers, URLs, objects, spools, Preview, Apply, caches, exports and backup restoration.
- Private content is forbidden in logs, analytics, notifications and crash reports.

## Current machine evidence

```txt
registered schemas:                         26
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
import flow end-to-end tests:                6
canonical record fixture cases:             22
canonical record Go top-level tests:         5
CSV worker top-level tests:                  2
```

Repository-integrated Go evidence:

```txt
code HEAD 3f9ab51 (docs only; code identical to 5c3dc4b)
(local golang:1.23 Linux container + fresh postgres:16 + MinIO):
gofmt clean + go vet + go test ./... + go test -race ./... (17 packages,
live DB/object-store/supervision/import-flow tests included) + both 5s fuzz smokes PASS

remote workflows at import-flow HEAD 381c514:
Import API Security Slice run 29793196253 SUCCESS (live import-flow tests executed)
Security Contracts run 29793196257 SUCCESS
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
