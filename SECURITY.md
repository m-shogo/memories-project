# Security

最終更新: 2026-07-16

Memory OSは、ユーザーの人生の文脈、画像、URL、視聴・読書・食事・旅行・人間関係などの高感度になり得る情報を扱う。

## Current status

```txt
security architecture / threat model / verification gate:
defined

registered machine-readable schemas:
22

tracked contract fixtures:
21

validators:
created for schema, object authorization, PostgreSQL RLS,
Sign in with Apple, signed upload OpenAPI, parser sandbox and archive safety

PostgreSQL migration and integration-test SQL:
created

GitHub Actions workflow:
created; remote run result not confirmed by the available connector

Go / iOS / Portal / object-storage implementation:
not created

production readiness:
NO-GO
```

このrepositoryは設計・machine-contract・security-foundation段階である。「完璧に安全」「hack不可能」「完全なprivacy」をclaimしない。

## Read first

1. [Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)
2. [Round 9 Security Foundation Progress](docs/memory-os-round9-security-foundation-progress-2026-07-16.md)
3. [Capture / Import Security Architecture](docs/memory-os-capture-import-security-architecture-round-9.md)
4. [Capture / Import Threat Model](docs/memory-os-capture-import-threat-model-round-9.md)
5. [Security Verification Gate](docs/memory-os-security-verification-gate-round-9.md)
6. [Security Schema Registry](docs/schemas/memory-os-security/schema-registry.v1.json)
7. [Security Fixture Index](docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json)
8. [Signed Upload OpenAPI](contracts/openapi/memory-os-import-security.v1.openapi.json)
9. [Capture / Import Implementation Architecture](docs/memory-os-capture-import-implementation-architecture-round-8.md)
10. [Privacy and Ethics](docs/privacy-and-ethics.md)

Re-run current checks:

```bash
python -m pip install -r requirements-security-validation.txt
python scripts/validate-memory-os-security.py
python scripts/validate-memory-os-authorization.py
python scripts/validate-memory-os-postgresql-rls.py
python scripts/validate-memory-os-apple-auth.py
python scripts/validate-memory-os-signed-upload-openapi.py
python scripts/validate-memory-os-parser-security.py
```

## Security priorities

```txt
1. prevent cross-user disclosure
2. prevent unauthorized / silent Memory writes
3. isolate untrusted imports and parsers
4. bind Preview to exact Apply content
5. keep raw files short-lived
6. prevent retry / deletion resurrection
7. keep private content out of logs, analytics and notifications
8. preserve export and deletion rights
```

## Binding implementation boundaries

- Sign in with Apple identity is verified server-side; account binding uses issuer + subject, not email.
- Client-provided account ID, epoch, owner, bucket and object key are never authority.
- Every Import Job, pairing session, upload authorization, quarantine object, Preview, Apply confirmation, report and export is object-authorized.
- PostgreSQL user-owned security tables use `FORCE RLS`, owner + epoch policies and non-owner runtime roles.
- Runtime privilege roles are `NOLOGIN NOINHERIT NOBYPASSRLS`.
- Signed upload is bound to one owner, epoch, job, server-generated object key, size, SHA-256, content type and expiry.
- Upload completion rechecks the real object in private storage; it does not trust client metadata.
- Parser workers run outside the public API process, non-root, networkless, read-only and resource-limited.
- Parser input and output are mediated by a supervisor; parser receives no cloud, DB or signing secrets.
- Archive extraction rejects traversal, absolute paths, links, special files, expansion bombs, collisions and unsafe nesting.
- Browser pairing tokens cannot final-apply confirmed Memory records in P0.
- Preview and Apply are exact-hash bound; Apply is idempotent and cannot silently reparse.
- App Group data is minimized; secrets remain in Keychain.
- Audit events cannot contain private content, raw filenames, raw URLs, tokens, email addresses or user notes.
- Account deletion fences jobs, workers, signed URLs, objects, caches, exports, App Group files and restored backups.

## Current contract evidence

```txt
registered schemas:                    22
tracked fixtures:                      21
generic negative cases:                24
object authorization:                   8  (2 allow / 6 deny)
PostgreSQL RLS:                         14  (4 allow / 10 deny)
Sign in with Apple:                     16  (1 allow / 15 deny)
parser sandbox unsafe mutations:        16  (all deny)
archive / JSON / CSV cases:             25  (1 allow / 24 deny)
signed upload OpenAPI operations:        3
```

This evidence validates contracts and prepared SQL tests. It does not yet prove the future API, object storage, parser runtime, iOS application or Portal implementation is secure.

## Production blockers

Production remains blocked until the Security Verification Gate has evidence for:

- remote CI success;
- real cross-user API and PostgreSQL isolation;
- real Sign in with Apple token/code verification;
- signed upload enforcement against private object storage;
- parser sandbox runtime inspection;
- malicious archive / JSON / CSV corpus and fuzzing;
- Preview / Apply integrity and idempotency;
- App Group crash recovery and local storage inspection;
- Portal CSP / XSS / browser-token tests;
- deletion race and backup-restore tests;
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
