# Supplemental OPS learning — Upload Route SQL migration apply/error boundary (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, or human-promotion gates.

## Material failure — previously unguarded SQL apply/error path

- **symptom:** The reviewed Upload Route SQL migration inventory bound eleven runtime file names and their Git blobs, but did not bind the Go live-test helper's actual `pool.Exec(ctx, string(payload))` application and failure propagation. A source change could retain all eleven file reads while suppressing migration execution or swallowing an error, leaving the static input guard green.
- **evidence:** Read-only inspection of `services/import-api/internal/httpserver/server_live_test.go` at `90baade8e` found the eleven-file loop followed by conditional `pool.Exec`, `migrateErr = fmt.Errorf(...)`, early return and `t.Fatal(migrateErr)`. The existing `require_reviewed_upload_route_sql_migrations` validated the read expression and SQL content hashes but not this apply/error chain. No production failure or actual live Go integration test was observed.
- **rootCauseOrUnknown:** Verified static-guard coverage gap: runtime input identity does not imply runtime application or fail-closed error handling. Complete dynamic execution and transitive dependency closure remain unproven.
- **failedApproach:** Inferring that unchanged SQL file names/blob hashes and one `os.ReadFile` occurrence proved migrations were applied successfully.
- **correction:** [`a2b69634`](https://github.com/m-shogo/memories-project/commit/a2b6963438ebf0e12675c6430981c743f590faaf) pins the exact conditional SQL execution/error-propagation chain and final fatal check in the CI-reachable read-only negative validator, without modifying Go test code or SQL.
- **recurrenceGuard:** Five executable source mutations must be rejected: discarded SQL execution, ignored read error, discarded apply error, continued execution after migration failure and suppressed final fatal. The existing eleven-file name/blob and Push/PR SQL trigger-gap checks remain separate.
- **retryCondition:** Any legitimate migration execution/error-handling change requires a reviewed new source contract, matching negative controls, exact-source CI and protected-authority verification. The unchanged Quay MinIO HTTP 401, workflow-write permission and human promotion blockers must not be retried without changed prerequisites.

## Material success

- **outcome:** [Autonomous Learning Guard #41028483909](https://github.com/m-shogo/memories-project/actions/runs/41028483909) completed **SUCCESS** for exact source `a2b6963438ebf0e12675c6430981c743f590faaf`.
- **evidence:** GitHub Actions reports all validate-job steps successful: exact clean checkout, append-only learning authority, learning contract and executable negatives, independent helper-ancestor reachability and read-only execution. Commit comparison confirms only `scripts/validate-autonomous-learning-system-negative.py` changed (+44 lines).
- **whySafe:** The changed file is a CI-reachable read-only validator. The five mutations are synthetic in-memory Go source variants, not edits to live Go code, SQL migrations, workflows, production traffic, credentials or protected evidence.
- **reusableMechanism:** Bind both input identity and the effect/error boundary for safety-critical runtime dependencies; distinguish static source invariants from executed integration evidence and leave unproven Go-only pre-MinIO CI reachability explicit.
- **protectedAuthorityCheck:** Comparing the before/after Git trees found no changes in the canonical learning authority, any `contracts/operations/` authority or the tracked recovery/objective/request/non-resurrection/promotion authorities. Canonical learning SHA `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` remain unchanged. `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, with no approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, independent final review or human promotion.

## Next safe target

Audit and pin the live Go SQL migration cross-process advisory-lock acquire/release and failure boundary with negative controls. Continue the Go-only pre-MinIO focused-test CI and full Go/Python runtime dependency/trigger closure audit without editing workflow YAML or claiming production readiness.
