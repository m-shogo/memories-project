# Supplemental OPS learning — Git operational error 128 fail-closed shell negatives (2026-11-02)

Append-only subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This synthetic Git shell fixture is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material scoped failure mode

- **symptom:** A mocked `git merge-base` or `git diff` returning only ordinary status 1 does not prove the reviewed shell guard rejects operational failures such as status 128. A failed `git fetch` must also not be interpreted as success.
- **evidence:** Reviewed `controlled-saturation-repeatability.yml` blob `1f4b20c0` uses `git fetch`, `if ! git merge-base --is-ancestor`, and `if ! git diff --quiet` before publication. The earlier isolated shell mock covered return codes 0/1 but not 128. No real remote transport error or stale publication was observed.
- **rootCauseOrUnknown:** Verified missing error-class coverage in the synthetic test. The actual shell guard uses `set -euo pipefail` and explicit failure exits; production exploitability remains unknown.
- **failedApproach:** Treating status-1-only mocked Git failures as complete proof of fail-closed behavior for transport and Git object errors.
- **correction:** [`23e07cd8`](https://github.com/m-shogo/memories-project/commit/23e07cd819fdbf6db27f8bbed1ceba62b42a61c0) extends the local Bash Git mock to emit status 128 for fetch, ancestry or critical diff, with three exact expected outcomes.
- **recurrenceGuard:** A fetch error must return 128 without a push. An ancestry or critical diff error must return the guard's reviewed exit 75 without a push. Existing safe, divergent, critical, and mutation cases remain required. Isolated local Bash prototype passed all new status-128 cases.
- **retryCondition:** Revisit only if exact-source CI fails or the reviewed Git/error policy changes; never treat a transport error as successful source validation.

## Material safe progress

- **outcome:** One independent negative-suite code commit accepted on `so`. Exact-source [Autonomous Learning Guard #41445094523](https://github.com/m-shogo/memories-project/actions/runs/41445094523) was queued at record creation, not claimed as SUCCESS.
- **evidence:** Source re-read confirmed mock-only `return 128` branches and three new cases; local Bash prototype returned 128 for fetch and 75 for both ancestry/diff errors, with no synthetic push marker.
- **whySafe:** No real Git remote, workflow publisher, credential, traffic, readiness, production authority or promotion was touched. The Bash `git()` mock intercepts every reviewed Git invocation.
- **reusableMechanism:** Test operational-error classes independently of ordinary diff/ancestry mismatch, and assert both failure status and absence of publication.
- **protectedAuthorityCheck:** Post-code tree confirmed unchanged ten protected blobs: production status `d677a1c9` (`NO_GO`), OPS-P0-007 `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, contract `87712ea9`.

## Next safe target

Confirm exact-source CI and independently audit the three soak publisher paths without triggering writer workflows. Keep `productionDecision=NO_GO` and separate human promotion authority.
