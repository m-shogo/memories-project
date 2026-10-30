# Supplemental OPS learning — deployment-principal role lock and escaped boundary recovery (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure A — unguarded second advisory lock

- **symptom:** The HTTP live-test helper `appLoginPool` alters the cluster-wide `memory_app_login` password. It must use the same PostgreSQL advisory-lock ID as the migration helper, yet prior source checks protected only the migration lock and the deployment-principal password Skip boundary.
- **evidence:** Read-only inspection of `server_live_test.go` found `appLoginPool` uses the shared `/postgres` maintenance database, `pg_advisory_lock(730001)`, deferred unlock, and `ALTER ROLE memory_app_login PASSWORD`. The source comments explain migration 007 also alters this role and concurrent changes can collide. No actual production collision was observed.
- **rootCauseOrUnknown:** Verified static-guard gap: the two lock callsites serve distinct critical operations; guarding one does not protect the other's ID, connection scope, deferred release or ordering.
- **failedApproach:** Inferring that the reviewed migration advisory lock also guaranteed the deployment-principal password change remained serialized.
- **correction:** [`4a04aa7c`](https://github.com/m-shogo/memories-project/commit/4a04aa7caa4f29804b289b2fa930d9655f15a441) adds a CI-reachable function-scoped source chain and eight synthetic negatives for maintenance database, lock/unlock ID, premature release, wrong connection, wrong role and wrong mutation connection.
- **recurrenceGuard:** A bounded `appLoginPool` source-body identity check pins lock acquisition/deferred release and the `ALTER ROLE` operation in order, while the separate `newLiveServer` migration lock remains independently guarded.
- **retryCondition:** Legitimate role-lock changes require reviewed shared lock-ID/maintenance-database design, negative controls, exact-source CI and protected-authority checks. Do not retry unchanged MinIO, workflow-write or human-promotion blockers.

## Material failure B — incorrectly escaped helper-boundary delimiter

- **symptom:** [CI #41029692631](https://github.com/m-shogo/memories-project/actions/runs/41029692631) FAILED in `require_reviewed_upload_route_role_lock` before its synthetic mutations completed.
- **evidence:** The first committed Python source searched for the literal two-character backslash-n sequence (`"\\nfunc "`) instead of the newline delimiter (`"\nfunc "`). The CI traceback showed `RuntimeError: unreviewed Upload Route deployment principal role lock boundary`. A subsequent source inspection confirmed the incorrect escape.
- **rootCauseOrUnknown:** Verified generation/escaping error while constructing the Python source from an external code string; the Go helper itself was unchanged.
- **failedApproach:** Using an extra escape layer in the generated Python function-boundary search without inspecting the resulting source before commit.
- **correction:** [`54cddbeb`](https://github.com/m-shogo/memories-project/commit/54cddbeb4eee0a70d68955c785c4a315d13e13e4) corrects the delimiter to a Python newline escape. The error was identified and corrected before the first CI result, then the first CI failure was confirmed from its exact-source logs.
- **recurrenceGuard:** The corrected boundary is exercised by the real source positive control and all eight negative mutations in the exact-source CI. For future generated source, inspect literal escaping at the emitted-file boundary before writing.
- **retryCondition:** Only revisit delimiter escaping if the actual Go function boundary changes or a new exact-source test exposes a mismatch; do not retry the known failed two-backslash form.

## Material success

- **outcome:** [Autonomous Learning Guard #41029717745](https://github.com/m-shogo/memories-project/actions/runs/41029717745) completed **SUCCESS** on exact source `54cddbeb4eee0a70d68955c785c4a315d13e13e4`.
- **evidence:** CI logs confirm append-only and learning contract PASS, 509 canonical fail-closed negatives, 193 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only checks PASS. The eight new role-lock negatives are nested and not included in the printed 509.
- **whySafe:** Only the CI-reachable read-only Python negative validator changed; no Go service source, PostgreSQL SQL, workflow YAML, production evidence, credentials, traffic or protected registries changed.
- **reusableMechanism:** When two operations require the same database advisory lock, independently pin both callsites and their shared ID, maintenance-database scope, deferred release and protected mutation ordering; distinguish static source identity from actual concurrency/drill evidence.
- **protectedAuthorityCheck:** Before/after Git tree comparison found no drift in canonical learning or `contracts/operations/` authorities, including production status and OPS-P0-007 snapshot. Canonical learning SHA `b809c69d`, contract `87712ea9`, production status `55b3e639`, snapshot `dbaa36b0` remain unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, no approved current recovery objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain non-resurrection record, independent review or human promotion.

## Next safe target

Pin the deployment-principal connection's non-superuser/non-BYPASSRLS identity assertion so Upload Route live tests cannot silently become vacuous if `appLoginPool` is changed. Continue Go-only pre-MinIO focused CI and complete Go/Python runtime dependency/trigger closure without changing workflow YAML.
