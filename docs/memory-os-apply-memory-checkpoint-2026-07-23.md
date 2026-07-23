# Memory OS Apply and Memory Persistence Checkpoint

最終更新: 2026-07-23

## Verdict

```txt
Apply confirmation persistence + minimal Memory materialization + Preview read API:
CREATED AND LIVE-TESTED OVER AUTHENTICATED HTTP

Apple code exchange / deletion fencing / clients:
NOT IMPLEMENTED

production:
NO-GO
```

The last unimplemented service interface of the vertical slice is now
concrete: a committed Preview can be read back by its owner over HTTP and
applied — exact-hash-bound, idempotent, fully accounted — into durable
memory rows, all through runtime-role FORCE-RLS access.

## Implemented files

```txt
infra/postgresql/security/005_memory_os_apply_memory.sql
infra/postgresql/security/test_memory_os_apply_memory.sql
services/import-api/internal/pgrepo/apply.go
services/import-api/internal/previewread/service.go
services/import-api/internal/httpapi/preview_handler.go
services/import-api/internal/httpserver/server.go (preview + apply wiring)
services/import-api/cmd/import-api-server/main.go
.github/workflows/security-contracts.yml (005 + apply/memory test steps)
```

## Migration 005

- `apply_confirmation` gains the idempotency state machine (`in_progress →
  applied`): claim columns, counts, a partial UNIQUE on `(owner,
  idempotency_key)`, and — deliberately narrowing the stub's update-free
  stance — one owner-scoped UPDATE policy for the API role, because the
  claim pattern cannot exist without it. The legacy `'active'` state stays
  allowed for the RLS security-test rows.
- `memory_os.memory_item` is the minimal applied-memory persistence: one row
  per applied candidate with its canonical record, dedupe fingerprint and
  source-preview binding, under the standard FORCE-RLS owner policy (api:
  select/insert/update; deletion: select/delete). The richer Memory domain
  model remains future work and is labeled as such.

## Apply repository (pgrepo.Apply)

Implements the existing `apply.Repository` contract exactly:

- `GetPreview` reads the owner's ready Preview (hash, counts, expiry);
- `ClaimIdempotency` inserts the `in_progress` claim; on key collision it
  reports replay (with stored counts), in-progress, or conflict — a key held
  invisibly by another tenant is a conflict, never a leak;
- `ApplyMaterializedPreview` is fully set-based inside the claim
  transaction: it re-reads the preview binding by hash, counts fingerprint
  matches once per candidate, then materializes under the three policies
  (`skip_existing` / `keep_both` / `update_safe_fields`) with counts that
  always account for every candidate;
- `CompleteApply` moves the claim to `applied` with the final counts.

## Preview read API

`GET /v1/import-jobs/{jobID}/preview` returns the owner's committed Preview
summary plus bounded pages (default 100, max 500) of candidates and safe
rejections, read under the API runtime role. `POST
/v1/previews/{id}/apply` was already routed by the existing strict handler;
both are now wired into the executable server.

## Live evidence

SQL suite (6 blocks): claim → complete → re-read round-trip; duplicate
idempotency keys rejected; cross-tenant confirmations/items invisible and
un-updatable; worker role denied entirely; undersized fingerprints, invalid
preview bindings and foreign-owner inserts rejected.

HTTP journey (one live test over the real middleware + DB + MinIO):

- owner reads the committed Preview (hash, 2 candidates, 1 rejection);
  foreign tenant gets 404;
- apply with the exact hash → 200, `created=2`, two `memory_item` rows;
- exact replay with the same idempotency key → same apply ID, `replayed`;
- a new key with `skip_existing` → `created=0, skipped=2`;
- wrong hash → 409; foreign tenant apply → 404.

## Findings

- the same persistence-across-runs trap recorded at the importctl checkpoint
  applies to fixed idempotency keys and owners in live tests: the parallel
  full suite failed against state a previous isolated run had committed;
  run-unique identifiers fixed it.

## Validation language

```txt
local golang:1.23 + postgres:16 + minio (scripts/dev-up.sh),
exact code HEAD 556e366a03543c3ad25ceb75316bfb99c06856ef:
gofmt clean + go vet + go build ./cmd/... + go test ./... + go test -race ./...
(22 packages, all live suites included) + both 5s fuzz smokes PASS

migration 005 + all five SQL test suites verified on a fresh database: PASS

remote workflows (pushed HEAD 498565a, code identical to 556e366):
Import API Security Slice run 30016036537 SUCCESS (apply/preview HTTP journey executed under race)
Security Contracts run 30016036295 SUCCESS (005 migration + apply/memory SQL suite executed)
```

## Residual risks

- `memory_item` is deliberately minimal: no shelf/type modeling, no search
  indexes, no update-safe field allowlist beyond whole-record replacement;
- fingerprint dedupe trusts the canonical record's fingerprint field;
- Apple code exchange, deletion fencing (memory_item is deletable by the
  deletion role but nothing orchestrates it) and clients remain
  unimplemented.

## Immediate next task

```txt
Deletion fencing boundary: account-epoch bump + deletion-runtime sweep
across jobs, authorizations, quarantine objects, previews, applies and
memory items, with live proof that a bumped epoch fences every path.
```
