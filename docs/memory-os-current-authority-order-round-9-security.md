# Memory OS Security Authority — Round 9

最終更新: 2026-07-25

Status: CURRENT SECURITY-ARCHITECTURE AUTHORITY, SUBORDINATE TO ROUND 10

Production-readiness judgement is governed by [`memory-os-current-authority-order-round-10-operability.md`](memory-os-current-authority-order-round-10-operability.md). This document defines security architecture and invariants only. It must not be used by itself to claim production readiness.

## Current security verdict

```txt
product hierarchy:
Capture / Import first

platform direction:
iOS canonical client + limited Desktop Import Portal

security architecture / threat model / verification gate:
DEFINED

backend:
PARTIAL SECURITY VERTICAL SLICE
executable HTTP server exists
not a production backend

production:
NO_GO
```

Current code and executable tests decide implementation facts. Historical checkpoints explain the evidence available at their recorded commit and never override current code.

## Identity and authorization

- Sign in with Apple identity is verified server-side.
- Canonical identity is issuer + subject, not email.
- Authorization code exchange, nonce/code replay protection, account binding and session issuance are implemented against a fake Apple boundary; real-Apple deployment evidence remains required.
- Client account/owner/epoch values are never authority.
- Browser pairing authority cannot final Apply.
- Runtime roles are fixed, non-superuser and `NOBYPASSRLS`.
- User security tables use `ENABLE RLS` and `FORCE RLS`.
- Session storage keeps token digests rather than raw bearer tokens.

## Upload and object storage

- Server-generated authorization binds owner, epoch, job, object key, size, checksum, content type and expiry.
- Completion verifies authoritative stored metadata and exact object version.
- Object keys are server-generated and path-normalized.
- Private versioned object storage remains quarantine, not backup.
- Production TLS, scoped credentials, lifecycle and independent retention evidence remain required.

## Parser and adapter boundary

- Untrusted parsing occurs outside database transactions.
- Generic CSV parsing is bounded synchronous pull with sticky cancellation/failure behavior.
- Parser options are canonicalized and SHA-256-bound.
- Worker artifacts are digest-pinned.
- Workers are secretless and resource-bounded.
- Network namespace/seccomp/container deployment evidence remains required.
- Reviewed artifact registry and transition procedure remain incomplete.

## Preview spool and commit

```txt
version-bound source
→ transaction-free supervised parse
→ bounded private spool
→ durable no-replace manifest publication
→ independent strict decode / count / re-hash
→ canonical record validation
→ one short atomic PostgreSQL transaction
→ immutable ready Preview or full rollback
```

Binding invariants:

- manifests contain no filesystem paths;
- symlink following and cross-attempt reuse are forbidden;
- fixed-name entries use restrictive ownership/mode/link checks;
- unknown filesystem state fails closed or remains quarantined;
- published manifests remain untrusted until independent verification;
- candidates and safe rejections are counted, hashed and completeness-checked;
- deterministic commit keys make exact retries idempotent and conflicting retries reject;
- `FORCE RLS` remains active during persistence.

## Apply and Memory persistence

- Final Apply is exact-Preview-hash-bound and idempotent.
- Rejected rows never enter Apply.
- Created + updated + skipped must account for every accepted candidate or the transaction rolls back.
- Current minimal `memory_item` persistence is not the rich Memory domain.
- Destructive `update_safe_fields` behavior is closed fail-closed and live-proven to modify no row.
- Append-only supersession is the required future replacement.

## Account deletion

- Epoch bump fences subsequent jobs, sessions, uploads, objects, Preview and Apply activity.
- Account deletion returns after fencing; leased deletion work erases asynchronously and resumes after interruption.
- Stored object versions are included in erasure evidence.
- Backup restore non-resurrection remains unproven and is governed by `OPS-P0-007`.

## Privacy boundaries

The following must never enter logs, metrics, tracing attributes, analytics, notifications or crash reports:

- imported memory content;
- raw Apple authorization codes or nonce values;
- private keys, client secrets or signing material;
- bearer/session tokens;
- signed object URLs or object credentials;
- unbounded parser payloads;
- email as canonical identity.

Opaque request/job/trace identifiers may be used only under bounded retention and redaction rules.

## Security evidence versus production evidence

The following distinctions are binding:

- transaction rollback is not migration rollback;
- object versioning is not backup completion;
- component fault injection is not chaos completion;
- CI green is not production observability;
- fake-Apple integration is not real-provider deployment evidence;
- authentication is not rate limiting;
- restartable deletion work is not an operator incident runbook.

## Current blockers

Security and production remain blocked on, at minimum:

- real-provider/key-rotation evidence;
- production object-storage security configuration;
- parser deployment isolation evidence;
- structured privacy-safe telemetry and canary tests;
- distributed rate limiting;
- load/capacity evidence;
- backup/PITR and isolated restore rehearsal;
- migration and incident procedures;
- mixed-version compatibility proof;
- critical system-level failure drills;
- client security evidence;
- independent review with zero unresolved Critical/High;
- zero unresolved P0.

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
python scripts/validate-memory-os-operability.py
python scripts/validate-memory-os-entry-docs.py
```

Historical PASS applies only to the exact tested commit and scope. A newer HEAD requires new evidence.
