# Memory OS Preview PostgreSQL Domain Checkpoint

最終更新: 2026-07-18

## Verdict

```txt
Preview spool package (filesystem / writer / seal / verifier / reconciliation):
PARTIAL IMPLEMENTATION

production Preview PostgreSQL domain schema:
CREATED (SQL + live SQL tests)

pgx.CopyFrom Go repository:
NOT CREATED

production:
NO-GO
```

This checkpoint creates the commit-side database boundary as SQL before any Go repository code, per the Round 9 commit contract.

## Implemented files

```txt
infra/postgresql/security/003_memory_os_preview_domain.sql
infra/postgresql/security/test_memory_os_preview_domain.sql
.github/workflows/security-contracts.yml (migration + test steps)
```

`memory_os.import_preview` remains the Round 9 RLS security stub; the production domain is three new tables.

## Schema authority

```txt
memory_os.preview_ready      — one immutable ready Preview per job
memory_os.preview_candidate  — accepted candidates, FK-cascade children
memory_os.preview_rejection  — safe rejections, FK-cascade children
```

`preview_ready` binds, with database CHECK/UNIQUE/FK enforcement:

- `prv_`/`spl_` ID patterns and a 64-hex deterministic `commit_key` (globally unique);
- exactly one ready Preview per job (`job_id` unique) and per spool attempt (`spool_id` unique);
- `state = 'ready'` only — a `building` Preview cannot exist in the database;
- composite tenant FK `(job_id, owner_account_id, account_epoch)` to `import_job`, `ON DELETE RESTRICT`;
- exact source binding: quarantine object key whose second segment must equal `job_id` (`split_part`), version ID, content length (1..256 MiB), source SHA-256;
- adapter ID/semver/reviewed artifact SHA-256 and options SHA-256 patterns;
- fixed accepted/rejected record-format literals;
- `accepted_count >= 1`, row totals `accepted + rejected = source_row_count <= 100000`;
- byte totals `accepted + rejected = spool_byte_length <= 512 MiB`;
- exact empty-rejection representation (`0 count ⇔ 0 bytes` and the empty-input SHA-256);
- sealed TTL `expires > created` and `<= 24 hours`;
- final `preview_hash_sha256`.

Children bind `(preview_id, owner_account_id, account_epoch)` with `ON DELETE CASCADE`, unique `(preview_id, ordinal)` and `(preview_id, source_row)`, ordinal/source-row bounds 1..100000. `preview_rejection` has **no free-text columns**: only the source row number and `IMPORT_[A-Z0-9_]+` codes (validated by `memory_os.valid_import_issue_codes`) can be stored, so raw user values are structurally impossible.

`memory_os.assert_preview_complete(preview_id)` is SECURITY INVOKER (tenant RLS stays in force) and must be the last statement before COMMIT: it proves candidate and rejection rows are exactly the sealed counts with contiguous `1..n` ordinals, raising `P0002` otherwise. Because the composite FK requires the parent row, the commit transaction inserts `preview_ready` first, bulk-copies children, then asserts completeness; atomic transaction visibility keeps the "no partial Preview" property unchanged.

## RLS and immutability

All three tables get `ENABLE` + `FORCE ROW LEVEL SECURITY` with the standard owner/epoch policy:

```txt
SELECT: memory_api_runtime, memory_worker_runtime, memory_deletion_runtime
INSERT: memory_worker_runtime only
UPDATE: nobody
DELETE: memory_deletion_runtime only
```

No UPDATE grant or policy exists, so a committed Preview is immutable to every runtime role.

## Live SQL tests

`test_memory_os_preview_domain.sql` (runs in the Security Contracts live PostgreSQL 16 job after the existing RLS/upload suites):

- worker commits one complete Preview (ready + candidates + rejection + completeness assertion) atomically;
- API role cannot insert; worker cannot update ready/candidate rows;
- cross-tenant job binding rejects (23503); commit-key and per-job uniqueness reject duplicates (23505);
- `building` state, row/byte-total mismatches, byte limit, wrong empty-rejection hash/bytes, foreign-job object key, >24h TTL and wrong format literals all reject (23514);
- duplicate ordinals/source rows, zero ordinal, stale-epoch child insert reject;
- free-form or empty rejection code lists reject;
- completeness assertion rejects missing rows and ordinal gaps (P0002);
- cross-tenant and stale-epoch contexts see zero rows and cannot probe completeness;
- job deletion is blocked while its Preview exists; deletion runtime removes the Preview with cascading children.

Existing RLS/upload test TRUNCATE lists were extended for the new FK graph; migration 003 re-applies idempotently.

## Validation language

```txt
local PostgreSQL 16 (postgres:16-alpine container):
001 + 002 + 003 migrations and all three SQL test suites PASS
re-applied migrations and re-run tests PASS (idempotent)

remote Security Contracts live job with 003 + preview tests:
recorded after the push completes
```

## Residual risks

- no Go `pgx.CopyFrom` repository yet; the commit transaction order and epoch recheck exist only as contract + SQL surface;
- contiguity is asserted by `assert_preview_complete`, which the commit path must actually call before COMMIT;
- the machine-readable RLS contract fixture still enumerates the original 9 security-stub tables; the three preview domain tables are covered by live SQL tests and should be added to the fixture in a later contract revision;
- deployment role wiring (`SET ROLE`, `SET LOCAL` context) remains unproven in production.

## Immediate next task

```txt
Implement the pgx.CopyFrom Preview commit repository only:
BEGIN → SET LOCAL ROLE memory_worker_runtime → SET LOCAL owner/epoch
→ verify job owner/epoch/state and canonical epoch
→ verify sealed-spool evidence via previewspool.Verifier in the same flow
→ insert preview_ready (claims commit key)
→ CopyFrom preview_candidate / preview_rejection
→ SELECT memory_os.assert_preview_complete(...)
→ mark job preview_ready → COMMIT, full ROLLBACK on any error
→ prove duplicate/conflicting retry and rollback with integration tests
```

Do not add object storage, parser-container or client wiring in that checkpoint.
