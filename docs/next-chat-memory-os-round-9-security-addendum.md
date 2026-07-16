# Next Chat Addendum — Memory OS Round 9 Security / S2 Backend Slice

最終更新: 2026-07-16

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

毎回、小さくcommit / pushする。

---

# Read first

1. `SECURITY.md`
2. `docs/memory-os-current-authority-order-round-9-security.md`
3. `docs/memory-os-round9-s2-backend-security-slice-progress-2026-07-16.md`
4. `services/import-api/README.md`
5. `docs/memory-os-round9-security-foundation-progress-2026-07-16.md`
6. `docs/memory-os-capture-import-security-architecture-round-9.md`
7. `docs/memory-os-capture-import-threat-model-round-9.md`
8. `docs/memory-os-security-verification-gate-round-9.md`
9. `contracts/openapi/memory-os-import-security.v1.openapi.json`
10. `infra/postgresql/security/001_memory_os_import_rls.sql`
11. `infra/postgresql/security/test_memory_os_import_rls.sql`
12. `.github/workflows/security-contracts.yml`
13. `.github/workflows/import-api-security-slice.yml`

---

# Absolute status

```txt
security perfection:
never claim

Capture / Import priority:
unchanged

security contracts / validators:
created through parser and archive boundary

first executable Go backend security slice:
created

local Go validation:
go test / vet / race PASS

remote GitHub Actions:
workflow exists; result not confirmed by available connector

concrete PostgreSQL repositories:
not created

concrete object-storage adapter:
not created

parser supervisor runtime:
not created

iOS / Portal:
not created

production:
NO-GO
```

設計・schema・unit testの存在は本番安全性の証明ではない。

---

# Binding stack

```txt
iOS:
Swift 6 + SwiftUI
Share Extension
GRDB / SQLite
Keychain / App Group

Desktop migration support:
Vite + React + TypeScript thin Portal

Backend:
Go API
PostgreSQL with FORCE RLS
private versioned S3-compatible quarantine
isolated parser supervisor / worker

Town later:
SpriteKit
Metal only after measured blocker
```

Parser、adapter、dedupe、Preview、ApplyをSwift / browser / Goへ三重実装しない。

---

# Executable Go inventory

Location:

```txt
services/import-api/
```

Current local inventory:

```txt
Go files:   25
unit tests: 52
```

Implemented packages:

```txt
internal/security
  verified Principal
  request-context boundary

internal/dbscope
  fixed PostgreSQL role allowlist
  transaction-local account / epoch

internal/appleauth
  RS256 JWT validation
  duplicate-key and size rejection
  fixed-origin JWKS client
  code exchange / replay / account-binding interfaces

internal/cryptoids
  160-bit opaque IDs

internal/upload
  signed upload issue / completion core
  exact object metadata and version binding

internal/httpapi
  strict upload HTTP handlers
  no-store and generic error behavior

internal/adapters/genericcsv
  bounded streaming CSV parser

internal/preview
  immutable source / adapter / options / candidate hash binding

internal/apply
  iOS-only exact-hash idempotent Apply

internal/pipeline
  cancellation-safe CSV → Preview stream
```

Executed locally:

```bash
cd services/import-api
go test ./...
go vet ./...
go test -race ./...
```

All passed in the current local Go 1.23 environment.

---

# Most important implementation boundaries

## Identity

- Principal fields are private.
- Client account ID / email / subject are not authority.
- Apple identity token requires RS256, exact issuer/audience, time window, nonce and subject.
- Unknown `kid` refreshes JWKS once, then fails closed.
- JWKS fetch is fixed to Apple HTTPS origin with response and cache bounds.
- Code exchange must bind subject, client and original redirect when present.
- Canonical account binding is issuer + subject.

Still missing:

- concrete Apple code exchanger;
- client-secret signing / rotation;
- replay store;
- account binding repository;
- application session issuer.

## PostgreSQL scope

- Role comes from fixed Go constants only.
- Account ID and epoch enter `set_config(..., true)` from verified Principal only.
- Transaction rollback is mandatory on callback error or panic.
- Existing SQL contract still requires FORCE RLS and non-owner runtime roles.

Still missing:

- concrete driver composition;
- repositories;
- Go ↔ PostgreSQL live integration tests.

## Signed upload

- Client cannot choose owner, epoch, key or bucket.
- Length, SHA-256, type, expiry and generated key are exact-bound.
- Completion reads Storage metadata itself.
- Storage version ID is mandatory.
- Scan ticket references exact object version.
- Metadata mismatch revokes authorization.
- Consumption and scan enqueue share one transaction interface.
- HTTP input rejects unknown fields, owner injection and oversized bodies.

Still missing:

- concrete signer;
- concrete HEAD adapter;
- versioned private bucket tests;
- PostgreSQL repository.

## Generic CSV

- Streaming only; not full-file memory loading.
- Maximum 256 MiB, 100,000 rows, 256 columns, 1 MiB per cell.
- Limits cannot be expanded by client options.
- Explicit field mapping.
- Invalid UTF-8, duplicate header, inconsistent row and oversized cell rejected.
- URL is validated but never fetched.
- Formula-like cells stay literal and are flagged.
- Missing title rejects only the row.
- Deterministic fingerprint ignores source row.

## Preview

- Worker lease only.
- Exact source object key, version and checksum.
- Adapter ID, version and artifact digest.
- Mapping options hash.
- Normalized candidate and per-candidate hash.
- Aggregate candidate hash and Preview hash.
- Bounded candidate count and TTL.

## Apply

- iOS user authority only; browser pairing denied.
- Exact Preview ID + hash.
- Same owner and epoch.
- Idempotency key bound to request hash.
- Same completed request returns previous result.
- Same key with different request rejects.
- No parser dependency exists in Apply service.
- Counts must equal candidate total or transaction fails.

---

# Production blockers

Do not proceed to production while any remains:

- remote CI unconfirmed or failing;
- concrete Apple auth exchange/session absent;
- concrete PostgreSQL repositories absent;
- live FORCE RLS integration absent;
- concrete private object storage absent;
- parser supervisor runtime absent;
- adapter artifact verification absent;
- concrete Preview / Apply / Memory persistence absent;
- deletion epoch cancellation absent;
- malicious corpus / fuzzing absent;
- sensitive log scan absent;
- iOS storage / App Group evidence absent;
- Portal CSP / token evidence absent;
- independent review unresolved Critical / High;
- unresolved P0 > 0.

---

# Next correct sequence

```txt
1. extend PostgreSQL schema for Import Job / upload / Preview candidate / Apply / Memory
2. implement concrete PostgreSQL repositories
3. run Go integration tests against PostgreSQL 16 with FORCE RLS
4. implement local versioned S3-compatible signer and object adapter
5. test exact headers / checksum / overwrite / expiry / cancellation
6. implement parser supervisor and safe Generic CSV worker command
7. verify executing adapter artifact digest
8. implement deletion epoch fencing and cleanup
9. add strict Preview / Apply HTTP handlers
10. compose executable API process without production secrets
11. build malicious ZIP / JSON / CSV corpus and fuzz harness
12. add log canary and dependency / secret / container scans
```

After backend P0 vertical slice:

```txt
13. iOS Share Extension URL / text
14. App Group minimal intake
15. safe Preview and final iOS confirmation
16. limited Desktop Portal pairing and upload
```

Only after Capture / Import P0 unresolved zero:

```txt
17. TownSceneSnapshot Swift models
18. SpriteKit static Town prototype
```

---

# Latest milestone commits

```txt
4eabe37  bounded Generic CSV adapter
fb0e3c6  immutable Preview materializer
dc48b64  idempotent Apply service
7ee21f3  CSV-to-Preview pipeline
eafeee5  S2 progress report
88bdf0f  Round 9 authority synchronization
f9f6548  SECURITY.md synchronization
```

Every implementation step was committed directly to `so`. Do not squash away security history without an explicit release decision.
