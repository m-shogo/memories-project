# Security

最終更新: 2026-08-07

Memory OS handles highly sensitive personal context. The repository contains a strong but partial security and operability vertical slice; it is not a production-ready system.

## Current authority

Read in this order:

1. [Round 10 Production Operability Authority](docs/memory-os-current-authority-order-round-10-operability.md)
2. [Machine-readable Production Operability Status](contracts/operations/production-operability-status.json)
3. [Production Operability Audit](docs/memory-os-production-operability-audit-2026-07-24.md)
4. [Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)
5. [Capture / Import Security Architecture](docs/memory-os-capture-import-security-architecture-round-9.md)
6. [Threat Model](docs/memory-os-capture-import-threat-model-round-9.md)
7. [Security Verification Gate](docs/memory-os-security-verification-gate-round-9.md)
8. [Import API Security Slice](services/import-api/README.md)

Historical checkpoints prove only their recorded commit and scope.

## Current security status

Production remains `NO_GO`.

Implemented and tested foundations include:

- server-verified Sign in with Apple identity semantics using issuer + subject;
- Apple code exchange is implemented with single-use nonce/code replay protection, account binding and session issuance, live-proven against a fake Apple boundary;
- bearer sessions stored as digests and resolved through restricted SECURITY DEFINER functions;
- PostgreSQL runtime-role transactions with `FORCE RLS` and non-superuser deployment-principal tests;
- exact owner/epoch/job/upload/object bindings;
- bounded, digest-pinned parser supervision with fail-closed cleanup;
- version-bound object verification and checksum validation;
- durable Preview spool publication and independent decode/count/re-hash verification;
- atomic Preview persistence and idempotent exact-hash Apply;
- account epoch fencing, object deletion and resumable deletion worker behavior;
- provenance and interpretation invariants with destructive update paths closed fail-closed;
- privacy-safe structured event and bounded-cardinality metrics contracts with executable instrumentation;
- fail-closed rate-limit foundations and operator recovery contracts;
- migration, incident, backup/restore, compatibility and failure-drill machine-readable controls;
- exact-source local PostgreSQL load evidence for Preview read and concurrent idempotent Apply;
- exact-source local PostgreSQL + MinIO signed-upload lifecycle evidence;
- post-fence deletion-under-load evidence proving 400/400 former-session Preview requests return 401 while the worker completes erasure and preserves the deletion tombstone.

Not yet production-proven:

- real-Apple credentials and production key/secret rotation;
- production object-storage TLS, scoped credentials, retention and lifecycle configuration;
- parser network namespace/seccomp/container deployment;
- production observability backend retention, external scraping/dashboard wiring, alert routing, paging and access-operation drills;
- production-equivalent distributed rate limiting, trusted-proxy ownership and emergency-control-plane evidence;
- production capacity boundary, repeatable saturation transition and approved operational thresholds;
- 60-minute-or-longer sustained soak and leak/stability proof;
- production-equivalent PostgreSQL/object-storage topology and failure behavior;
- production PITR / coherent cross-domain isolated restore rehearsal;
- production-shaped migration recovery and rollback/forward-fix rehearsal;
- production paging, human-led incident tabletop and independently reviewed recovery drills;
- approved-release rolling mixed-version, downgrade and rollback rehearsal evidence;
- deletion request-linearization proof for work already in flight before the durable 202 fence, plus multi-account worker saturation;
- iOS App Group/Keychain/Share Extension security evidence;
- independent security review with zero unresolved Critical/High.

Do not claim perfect security, unhackability, complete privacy, backend completion, or production readiness.

## Binding boundaries

- Identity authority is Apple issuer + subject, never email.
- Client-supplied account, owner, epoch, bucket, object key or version is never authority.
- Runtime roles are fixed and non-superuser; user security tables use `FORCE RLS`.
- Signed uploads bind one owner/epoch/job/key/size/checksum/type/expiry and completion verifies exact stored metadata/version.
- Untrusted parsing occurs outside database transactions.
- Parser input/output, CPU, memory, file descriptors, wall-clock and record sizes are bounded.
- Spool paths are supervisor-owned; symlink following, unknown entries and overwrite publication are rejected.
- Published manifests remain untrusted until independent verification succeeds.
- Apply uses an exact Preview hash and idempotency binding; destructive safe-field updates are disabled until append-only supersession exists.
- Account deletion returns 202 only after the account epoch/state fence is durable; asynchronous erasure follows through the resumable worker.
- Former sessions are normalized to authentication failure after fencing; canonical account-state read failures remain service failures rather than being disguised as authentication failures.
- Write-boundary epoch checkpoints run through the already-open scoped PostgreSQL transaction; they must not borrow a nested connection that can self-deadlock a bounded pool.
- Raw imported memory content, tokens, authorization codes, secrets and signed URLs are forbidden from logs, analytics, notifications and crash reports.

## Production-operability anti-conflation rules

The following substitutions are forbidden:

- transaction rollback is not migration rollback;
- object versioning is not backup completion;
- component fault injection is not chaos completion;
- CI green is not production observability;
- authentication is not rate limiting;
- fuzz/race/integration tests are not load-capacity evidence;
- version pinning is not compatibility proof;
- local PostgreSQL/MinIO PASS is not production or production-equivalent evidence;
- a bounded local ramp with no saturation signal is not a production operating threshold;
- a short CI stability sample is not sustained soak or leak proof.

## Validation

```bash
python -m pip install -r requirements-security-validation.txt
python scripts/validate-memory-os-security.py
python scripts/validate-memory-os-authorization.py
python scripts/validate-memory-os-postgresql-rls.py
python scripts/validate-memory-os-apple-auth.py
python scripts/validate-memory-os-signed-upload-openapi.py
python scripts/validate-memory-os-parser-security.py
python scripts/validate-memory-os-preview-spool.py
python scripts/validate-memory-os-canonical-records.py
python scripts/validate-memory-os-memory-provenance.py
python scripts/validate-memory-os-load.py
python scripts/validate-memory-os-load-evidence-index.py
python scripts/validate-memory-os-live-load.py
python scripts/validate-memory-os-live-object-load.py
python scripts/validate-memory-os-capacity-ramp.py
python scripts/validate-memory-os-short-stability-sample.py
python scripts/validate-memory-os-deletion-under-load.py
python scripts/validate-memory-os-operability.py
python scripts/validate-memory-os-entry-docs.py

cd services/import-api
test -z "$(gofmt -l .)"
go vet ./...
go test ./...
go test -race ./...
```

A PASS applies only to the exact tested commit. Never write “every push is green” or carry an old run forward to a newer HEAD.

## Release blockers

Production remains blocked until all machine-readable P0 operability gates are `READY` with existing evidence references. Security release also requires:

- production identity/key handling evidence;
- cross-tenant HTTP/PostgreSQL isolation evidence through deployment principals;
- sensitive-log canaries and supply-chain controls;
- deletion non-resurrection after restore;
- client security evidence;
- independent review with zero unresolved Critical/High;
- zero unresolved P0.

## Vulnerability reporting

A private reporting channel is not yet published because the product is not public production. Before beta, publish a security contact, supported versions, acknowledgement/remediation targets and coordinated-disclosure policy.

Never place personal data, credentials, tokens, live secrets or exploit payloads in a public GitHub issue.
