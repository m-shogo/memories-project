# Memory OS Round 9 — S2 Backend Security Slice Progress

最終更新: 2026-07-16

## Verdict

```txt
Capture / Import priority:
unchanged

first executable Go security slice:
created

local Go validation:
PASS

concrete PostgreSQL / object-storage / parser-runtime composition:
not created

remote GitHub Actions result:
not confirmed by the available connector

production:
NO-GO
```

This document records executable progress. It is not a production-security claim.

---

# 1. Implemented code

Location:

```txt
services/import-api/
```

Current inventory:

```txt
Go files:   25
unit tests: 52
```

## 1.1 Verified identity boundary

Implemented:

- private verified-principal fields;
- fixed authority allowlist;
- validated principal request-context storage;
- rejection of request-body account identity as authority.

The only supported principal construction path requires an account ID, account epoch and recognized server-side authority.

## 1.2 PostgreSQL scoped transaction boundary

Implemented:

```txt
verified principal
→ BEGIN transaction
→ SET LOCAL ROLE from fixed allowlist
→ set_config(app.current_account_id, verified account, transaction-local)
→ set_config(app.current_account_epoch, verified epoch, transaction-local)
→ repository callback
→ COMMIT or ROLLBACK
```

Role names cannot be built from user input.

## 1.3 Sign in with Apple verification core

Implemented:

- compact JWT structure and size limits;
- duplicate JSON key rejection;
- RS256 signature verification;
- exact issuer and allowed audience;
- expiration and issued-at window;
- exact nonce claim;
- required subject;
- unknown `kid` refresh once, then fail closed;
- fixed-origin Apple JWKS client;
- HTTPS-only redirect boundary;
- JWKS response-size, key-count and cache limits;
- authorization-code exchange interface;
- subject / client / conditional redirect binding;
- atomic replay-guard interface;
- canonical `issuer + subject` account-binding interface.

Not yet implemented:

- Apple client-secret signing;
- concrete authorization-code exchange client;
- concrete replay store and account-binding repository;
- session token issuance.

## 1.4 Signed quarantine upload

Implemented:

- strict issue and completion HTTP handlers;
- unknown JSON-field and request-body-size rejection;
- verified principal only;
- exact owner / epoch / job derivation;
- server-generated quarantine object key;
- fixed maximum file size and short authorization TTL;
- exact length, SHA-256, content type and required-header binding;
- no-store responses;
- server-side object metadata lookup;
- object version ID requirement;
- metadata mismatch revocation;
- atomic authorization consumption interface;
- scan ticket bound to exact object version, ETag and checksum;
- replay rejection.

Not yet implemented:

- concrete S3-compatible signer;
- concrete object-storage HEAD adapter;
- concrete PostgreSQL upload repository;
- private bucket policy integration test.

## 1.5 Generic CSV adapter

Implemented as a streaming parser:

```txt
maximum input:   256 MiB
maximum rows:    100,000
maximum columns: 256
maximum cell:    1 MiB
```

Controls:

- comma or tab only;
- explicit title/date/URL/text mapping;
- client cannot expand P0 limits;
- invalid UTF-8 rejected;
- duplicate normalized headers rejected;
- inconsistent columns rejected;
- mapped-column absence rejected;
- `http` / `https` URL validation without fetching;
- URL userinfo rejected;
- formula-like text remains literal and receives an issue code;
- missing title rejects only that row;
- deterministic candidate fingerprints;
- emitter backpressure and cancellation.

## 1.6 Immutable Preview

Implemented:

- worker-lease-only materialization;
- exact quarantine object key and version binding;
- exact source checksum;
- adapter ID, version and artifact digest binding;
- mapping-options hash;
- normalized candidate storage interface;
- per-candidate hash;
- length-prefixed aggregate candidate hash;
- immutable Preview hash;
- candidate-count limit;
- bounded Preview TTL.

The Preview hash changes if source, adapter, options or any candidate changes.

## 1.7 Idempotent Apply

Implemented:

- iOS user authority only;
- browser pairing token denied;
- exact Preview ID and hash required;
- owner and account epoch required;
- expired / non-ready Preview rejected;
- idempotency key bound to request hash;
- same completed request returns the prior result without applying again;
- same key with different request rejected;
- in-progress request reported explicitly;
- no Apply-time parser interface;
- created / updated / skipped total must equal candidate count;
- accounting mismatch returns an error so the transaction rolls back;
- partial Apply cannot be reported as success.

Not yet implemented:

- concrete PostgreSQL Preview / candidate / Apply repository;
- concrete Memory record persistence and duplicate resolution;
- deletion-epoch cancellation during Apply.

## 1.8 CSV-to-Preview pipeline

Implemented:

- bounded channel between parser and materializer;
- accepted candidates only enter Preview;
- rejected rows emit only safe row number, decision and issue codes;
- mapping options are deterministically hashed;
- cancellation stops a blocked parser when materialization fails;
- race-detector coverage for the pipeline.

---

# 2. Validation evidence

Executed in the local Go 1.23 environment:

```bash
go test ./...
go vet ./...
go test -race ./...
```

Result:

```txt
PASS
```

Covered packages:

```txt
internal/adapters/genericcsv
internal/appleauth
internal/apply
internal/cryptoids
internal/dbscope
internal/httpapi
internal/pipeline
internal/preview
internal/security
internal/upload
```

GitHub workflow:

```txt
.github/workflows/import-api-security-slice.yml
```

It checks format, vet and race tests on changes under `services/import-api/**`.
The available connector has not returned a remote workflow result, so this document does not claim remote CI PASS.

---

# 3. Remaining production blockers

```txt
1. executable API composition and server lifecycle
2. Apple code exchange, client-secret rotation and session issuance
3. concrete PostgreSQL driver and repositories
4. live FORCE RLS integration from Go transactions
5. concrete private S3-compatible signer and object adapter
6. bucket versioning / policy / lifecycle evidence
7. isolated parser supervisor and real runtime manifest
8. adapter artifact digest verification at execution
9. malicious archive / JSON / CSV corpus and fuzzing
10. concrete Preview / Apply / Memory persistence
11. deletion epoch cancellation and cleanup
12. sensitive log canary tests
13. external security review
```

Production remains `NO-GO`.

---

# 4. Next correct sequence

```txt
1. extend PostgreSQL migration for Import Job, upload, Preview candidate and Apply tables
2. implement concrete PostgreSQL repositories
3. run Go integration tests against PostgreSQL 16 with FORCE RLS
4. implement local S3-compatible signed upload adapter with versioning enabled
5. execute exact header / checksum / overwrite / cancellation tests
6. implement parser supervisor and safe Generic CSV worker entrypoint
7. implement deletion epoch fencing across queue, parser, Preview and Apply
8. add strict Preview / Apply HTTP handlers
9. only then begin iOS Share Extension vertical slice
```

Memory Town remains behind Capture / Import P0 security evidence.
