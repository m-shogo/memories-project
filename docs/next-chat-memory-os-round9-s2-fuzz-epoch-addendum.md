# Next Chat Addendum — Memory OS Round 9 S2 Fuzz / Epoch Fence

最終更新: 2026-07-16

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

Every change is committed and pushed in small steps.

## Read first

1. `SECURITY.md`
2. `docs/memory-os-current-authority-order-round-9-security.md`
3. `docs/memory-os-round9-s2-fuzz-and-epoch-fence-progress-2026-07-16.md`
4. `docs/memory-os-round9-s2-backend-security-slice-progress-2026-07-16.md`
5. `services/import-api/README.md`
6. `docs/next-chat-memory-os-round-9-security-addendum.md`

## Current status

```txt
Go files:     33
unit tests:   64
fuzz targets:  2

local test: PASS
local vet: PASS
local race: PASS
local short fuzz: PASS

remote CI: unconfirmed
production: NO-GO
```

## New executable work

```txt
internal/adapters/genericcsv/fuzz_test.go
internal/appleauth/fuzz_test.go
internal/epochguard/guard.go
internal/epochguard/guard_test.go
internal/fenced/services.go
internal/fenced/services_test.go
```

Production composition must use `internal/fenced` wrappers. Raw upload, Preview and Apply services are lower-level domain components and do not by themselves satisfy deletion-race fencing.

## Fencing rules

```txt
Upload:
start / authorization insert / post-HEAD / consume / scan enqueue

Preview:
start / pre-Finalize

Apply:
start / idempotency claim / pre-Memory-write / completion
```

PostgreSQL RLS and atomic write predicates remain authoritative. The Go guard is an additional fast-fail layer.

## Immediate next tasks

```txt
1. canonical account-control PostgreSQL schema
2. Import Job / upload / Preview candidate / Apply / Memory domain tables
3. concrete PostgreSQL repositories
4. Go + PostgreSQL 16 FORCE RLS integration tests
5. private versioned object-storage integration
6. deletion epoch increment / lease cancellation / cleanup tests
7. parser supervisor runtime
8. longer fuzz corpus
```

Do not claim remote CI pass. The available connector returns no push-triggered workflow run information.
