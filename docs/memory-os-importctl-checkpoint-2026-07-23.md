# Memory OS importctl Harness Checkpoint

最終更新: 2026-07-23

## Verdict

```txt
first visible end-to-end import run (CLI harness, no HTTP):
CREATED, LIVE-TESTED, AND EXECUTED FOR REAL

parser worker as a separately built artifact:
CREATED (cmd/parser-worker)

executable HTTP server / session issuance / clients:
NOT IMPLEMENTED

production:
NO-GO
```

For the first time, a person can point one command at a local CSV file and
watch the entire supervised import pipeline produce a committed Preview in
the terminal. Nothing in the security path was shortcut to make that visible.

## Implemented files

```txt
services/import-api/cmd/parser-worker/main.go   (separate worker artifact)
services/import-api/cmd/importctl/main.go       (thin CLI over internal/importcli)
services/import-api/internal/importcli/         (orchestration + live tests)
services/import-api/testdata/sample-import.csv
scripts/dev-import.sh                           (one-command visible run)
infra/postgresql/security/001_memory_os_import_rls.sql (race-safe role creation)
```

## The visible run

```bash
scripts/dev-up.sh
scripts/dev-import.sh          # or: scripts/dev-import.sh path/to/your.csv
```

builds `parser-worker` and `importctl` in a golang container on the dev
network and executes: migrations (advisory-locked) → job provisioning →
presigned PUT upload of the CSV → HEAD recheck → version-pinned verified
fetch → supervised parse in the **separately built, digest-pinned worker
binary** → seal → independent verification → canonical record decode →
atomic commit → Preview printed to the terminal.

Actual first run (sample CSV, Japanese titles, one empty-title row):

```txt
worker digest (computed, NOT a reviewed pin): c146a57aade99355…
job: job_tdbn2qmvl4pml35o5zqz2mvjtvjnvn2n (owner acct_thf2653v…, epoch 1)
uploaded: quarantine/job_…/upl_… (version 19035ff4-…, 254 bytes)

preview:     prv_b6nedladt4jb7sls5b54ftpuydedojg3
commit key:  5e4eacd1a91f5711…
accepted:    3 records (819 bytes, sha256 917acd87be51eaa5…)
rejected:    1 records

candidates:
    1 (row 2)  夏の京都旅行   2026-07-21T00:00:00Z  https://example.com/kyoto
    2 (row 3)  ラーメン記録   2026-07-19T00:00:00Z
    3 (row 5)  映画『雪国』                         https://example.com/movie
rejections:
    1 (row 4)  IMPORT_CSV_TITLE_REQUIRED

job state:   preview_ready
```

## Boundaries kept honest

- the harness computes the worker digest when no pin is provided and prints
  `NOT a reviewed pin`; a supplied `-worker-sha256` that mismatches the binary
  refuses to run (tested);
- the CLI is a dev tool: it targets the `scripts/dev-up.sh` stack, connects as
  the stack's superuser (RLS does not bind superusers) and must never point at
  production — stated in the package documentation;
- a second differing import for one job is **rejected** (`ErrCommitConflict`,
  one Preview per job), not silently replaced — tested through the CLI path;
- all security boundaries run unmodified: this checkpoint added composition
  and printing only.

## Live tests (4 top-level, gated on the dev-stack env)

- full CLI run commits and prints the Preview (asserted on output text and
  database rows, in its own `memory_os_importcli` database);
- second differing import for one job rejected;
- empty configuration rejected;
- mismatched worker digest pin refused.

## Findings recorded during implementation

- **PostgreSQL advisory locks are scoped per database**, while role/grant DDL
  touches cluster-wide catalogs: three suites applying migrations to three
  databases raced (`pg_authid` duplicate key, then `tuple concurrently
  updated`). Two fixes: migration 001's role creation now catches
  `duplicate_object`/`unique_violation` instead of check-then-act, and every
  migration applier (both test suites and importcli) now takes the advisory
  lock through a connection to the always-present `postgres` maintenance
  database, giving one shared lock scope.

## Validation language

```txt
local golang:1.23 + postgres:16 + minio (fresh via scripts/dev-up.sh),
exact code HEAD 80c3b4ecdfe67a7d79a0ec71a51e3a7c5c9bb41a:
gofmt clean + go vet + go build ./cmd/... + go test ./... + go test -race ./...
(20 packages, all live suites included) + non-race parsersup bounds
+ both 5s fuzz smokes PASS

changed migration 001 re-verified on a fresh database:
001→002→003 + all three SQL test suites PASS

scripts/dev-import.sh executed for real against the dev stack: SUCCESS (output above)

remote workflows (pushed HEAD f36dc86, code identical to 80c3b4e):
Import API Security Slice run 29994162132 SUCCESS (importcli live suite executed under race)
Security Contracts run 29994162154 SUCCESS
```

## Residual risks

- the CLI bypasses RLS for its read-back printing (superuser dev connection);
  the executable API must read through the runtime roles instead;
- worker digest pinning is real but the pin itself is operator-supplied; a
  reviewed artifact registry remains future work;
- no HTTP surface, session issuance, Apply/Memory persistence or clients.

## Immediate next task

```txt
compose the executable API: production main wiring auth/session/repositories
(Apple code exchange, replay store, session issuance, runtime-role DB access)
over the already-proven flow — still no client work.
```
