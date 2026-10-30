# Supplemental OPS learning — Upload Route migration advisory-lock scope and CI recovery (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human-promotion gates.

## Material failure A — unpinned migration advisory-lock lifecycle

- **symptom:** The live HTTP Go helper's SQL migration loop was bound to its runtime inputs and apply/error chain, but the cross-process PostgreSQL advisory-lock acquisition, error handling, deferred release and unlock were not independently protected by the read-only validator.
- **evidence:** Read-only source inspection of `server_live_test.go` found a maintenance-database connection, `pg_advisory_lock(730001)`, deferred unlock and the migration loop. Without the lock, concurrent migration/role changes could collide; no actual production incident was observed.
- **rootCauseOrUnknown:** Verified static-guard coverage gap; migration input/application identity does not establish lock lifecycle identity.
- **failedApproach:** Treating pinned migration file reads and `pool.Exec` error handling as a complete cross-process serialization proof.
- **correction:** [`1bb24a44`](https://github.com/m-shogo/memories-project/commit/1bb24a449b1ff643b1ab424cc47fce5ef3950af5) added an exact reviewed migration-lock source chain and seven synthetic mutation controls.
- **recurrenceGuard:** The read-only validator rejects changed advisory lock/unlock IDs, premature connection/pool release, wrong lock connection, premature unlock and discarded lock-acquisition error. This is a source-bound check, not an executed PostgreSQL concurrency drill.
- **retryCondition:** Legitimate lock changes require reviewed serialization design, exact negative controls, CI and protected-authority checks; external MinIO and human promotion blockers are unchanged.

## Material failure B — duplicate lock callsites made the first negative fixture ambiguous

- **symptom:** [CI #41029010810](https://github.com/m-shogo/memories-project/actions/runs/41029010810) FAILED in the new negative suite with `SQL advisory lock fixture anchor drift: wrong advisory lock ID`.
- **evidence:** Job traceback points to the source-wide `source.count(old) != 1` fixture assertion. A fresh source read found **two** occurrences each of `pg_advisory_lock(730001)`, `pg_advisory_unlock(730001)`, `lockPool.Acquire(ctx)` and deferred releases: one in `newLiveServer`, one in `appLoginPool`.
- **rootCauseOrUnknown:** Verified: the negative fixture used a global count for a callsite-specific mutation; the second legitimate deployment-principal lock invalidated the uniqueness assumption. The production Go code was not faulty based on this test failure.
- **failedApproach:** Requiring a global unique advisory-lock token in a source file with two reviewed lock scopes.
- **correction:** [`d9e6bbd4`](https://github.com/m-shogo/memories-project/commit/d9e6bbd4e739417c9b3c68f702114b1984f272f8) scopes mutation anchors and replacement to the exact `newLiveServer` function body, preserving the separate `appLoginPool` callsite.
- **recurrenceGuard:** All seven CI-bound mutations now require unique anchors within the reviewed helper and must trigger the exact advisory-lock diagnostic; function boundary drift fails closed.
- **retryCondition:** If the helper boundary or lock layout changes, re-read both callsites and reconcile fixture scope before retrying. Do not repeat a source-wide uniqueness assertion without proving the duplicate is gone.

## Material success

- **outcome:** [Autonomous Learning Guard #41029171229](https://github.com/m-shogo/memories-project/actions/runs/41029171229) completed **SUCCESS** on exact source `d9e6bbd4e739417c9b3c68f702114b1984f272f8`.
- **evidence:** Logs confirm append-only PASS, learning contract PASS, 509 canonical fail-closed negatives, 193 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only checks PASS. The seven advisory-lock controls are nested and do not increment the printed 509.
- **whySafe:** Only the CI-reachable read-only Python validator changed; the Go helper, PostgreSQL migrations, workflow YAML, credentials, production traffic, protected registries and human-promotion authority were untouched.
- **reusableMechanism:** Scope source mutation fixtures to the actual reviewed function/callsite rather than assuming a globally unique token; pin acquisition and deferred release around safety-critical database operations.
- **protectedAuthorityCheck:** Before/after Git tree comparison found no drift in canonical learning, `contracts/operations/` authorities, production status, OPS-P0-007 snapshot or protected recovery/review authorities. Canonical learning SHA `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, all human objective, reviewed request, request-bound evidence, typed eight-domain coverage, independent review and human-promotion gates unsatisfied.

## Next safe target

The second `appLoginPool` advisory lock protects cluster-wide `ALTER ROLE memory_app_login` using the same lock ID as migration 007. Audit and bind that independent role-change lock/ordering boundary, then continue Go-only pre-MinIO CI reachability and complete Go/Python runtime dependency/trigger closure without changing workflow YAML.
