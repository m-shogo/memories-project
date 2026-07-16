# Security

最終更新: 2026-07-16

Memory OSは、ユーザーの人生の文脈、画像、URL、視聴・読書・食事・旅行・人間関係などの高感度になり得る情報を扱う。

## Current status

```txt
security architecture / threat model / verification gate:
defined

machine-readable security foundation:
22 schemas / 21 tracked fixtures

first executable Go security slice:
created

local Go validation:
go test / vet / race PASS

concrete PostgreSQL / object storage / parser runtime / iOS / Portal:
incomplete

GitHub Actions:
workflows created; remote result not confirmed by the available connector

production readiness:
NO-GO
```

このrepositoryはsecurity-foundationと初期backend vertical-slice段階である。「完璧に安全」「hack不可能」「完全なprivacy」をclaimしない。

## Read first

1. [Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)
2. [S2 Backend Security Slice Progress](docs/memory-os-round9-s2-backend-security-slice-progress-2026-07-16.md)
3. [Round 9 Security Foundation Progress](docs/memory-os-round9-security-foundation-progress-2026-07-16.md)
4. [Capture / Import Security Architecture](docs/memory-os-capture-import-security-architecture-round-9.md)
5. [Capture / Import Threat Model](docs/memory-os-capture-import-threat-model-round-9.md)
6. [Security Verification Gate](docs/memory-os-security-verification-gate-round-9.md)
7. [Import API Security Slice](services/import-api/README.md)
8. [Security Schema Registry](docs/schemas/memory-os-security/schema-registry.v1.json)
9. [Security Fixture Index](docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json)
10. [Signed Upload OpenAPI](contracts/openapi/memory-os-import-security.v1.openapi.json)

Re-run contract checks:

```bash
python -m pip install -r requirements-security-validation.txt
python scripts/validate-memory-os-security.py
python scripts/validate-memory-os-authorization.py
python scripts/validate-memory-os-postgresql-rls.py
python scripts/validate-memory-os-apple-auth.py
python scripts/validate-memory-os-signed-upload-openapi.py
python scripts/validate-memory-os-parser-security.py
```

Re-run Go slice checks:

```bash
cd services/import-api
go test ./...
go vet ./...
go test -race ./...
```

## Security priorities

```txt
1. prevent cross-user disclosure
2. prevent unauthorized or silent Memory writes
3. isolate untrusted imports and parsers
4. bind Preview to exact Apply content
5. keep raw files short-lived
6. prevent retry and deletion resurrection
7. keep private content out of logs, analytics and notifications
8. preserve export and deletion rights
```

## Binding implementation boundaries

- Sign in with Apple identity is verified server-side; canonical account binding is issuer + subject, not email.
- Client-provided account ID, epoch, owner, bucket and object key are never authority.
- Verified principal fields are private and enter request handling through a dedicated server context.
- PostgreSQL work uses fixed-role, transaction-local account ID and account epoch context.
- Every Import Job, pairing session, upload authorization, quarantine object, Preview, Apply, report and export is object-authorized.
- User-owned PostgreSQL security tables use `FORCE RLS`; runtime privilege roles are `NOLOGIN NOINHERIT NOBYPASSRLS` and do not own tables.
- Signed upload is bound to one owner, epoch, job, generated object key, size, SHA-256, content type and expiry.
- Upload completion checks real object metadata and binds scan work to the exact object version.
- Generic CSV parsing is streaming and bounded by input, row, column and cell limits.
- Parser input never triggers URL fetching; URL validation is syntactic only.
- Formula-like CSV content remains literal and is flagged rather than executed.
- Preview is bound to exact source version, source checksum, adapter digest, options and normalized candidates.
- Final Apply is iOS-user-only, exact-hash-bound and idempotent; browser pairing authority is denied.
- Created, updated and skipped counts must account for every Preview candidate or the Apply transaction fails.
- Parser workers must remain outside the public API process, non-root, networkless, read-only and resource-limited.
- App Group data is minimized; secrets remain in Keychain.
- Audit events cannot contain private content, raw filenames, raw URLs, tokens, email addresses or user notes.
- Account deletion fences jobs, workers, signed URLs, objects, Preview, Apply, caches, exports, App Group files and restored backups.

## Current executable evidence

```txt
Go files:                              25
Go unit tests:                         52
local go test ./...:                   PASS
local go vet ./...:                    PASS
local go test -race ./...:             PASS
registered schemas:                    22
tracked fixtures:                      21
object authorization cases:             8
PostgreSQL RLS cases:                  14
Sign in with Apple cases:              16
parser sandbox unsafe mutations:       16
archive / JSON / CSV cases:            25
```

This evidence does not prove production safety. Concrete PostgreSQL repositories, object storage, parser sandbox runtime, deletion fencing, iOS and Portal are still incomplete.

## Production blockers

Production remains blocked until the Security Verification Gate has evidence for:

- remote CI success;
- real cross-user HTTP and PostgreSQL isolation;
- concrete Sign in with Apple code exchange, replay store and session issuance;
- signed upload enforcement against private versioned object storage;
- concrete Preview, Apply and Memory persistence;
- parser sandbox runtime inspection;
- malicious archive / JSON / CSV corpus and fuzzing;
- deletion race and backup-restore tests;
- App Group crash recovery and local storage inspection;
- Portal CSP / XSS / browser-token tests;
- sensitive log canary tests;
- dependency, secret, container, SBOM and provenance gates;
- independent review with zero unresolved Critical / High findings;
- zero unresolved P0 security findings.

## Vulnerability reporting

A private vulnerability-reporting channel has not yet been published because the product is not in public production.

Before public beta, this repository must define and publish:

- private security contact;
- supported versions;
- acknowledgement target;
- severity and remediation targets;
- disclosure coordination policy.

Do not place private user data, credentials, tokens or live exploit payloads in a public GitHub issue.
