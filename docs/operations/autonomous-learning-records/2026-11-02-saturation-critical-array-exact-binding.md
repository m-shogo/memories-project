# Supplemental OPS learning — exact saturation critical-array binding (2026-11-02)

Append-only subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Synthetic array expansion and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material scoped failure mode

- **symptom:** An executable `verify_critical_source` function can still provide incomplete protection if its `critical=(...)` source array loses a path, gains an alias/duplicate, is commented out or contains shell expansion/injection. A source-body guard check alone does not bind the array content.
- **evidence:** Reviewed `.github/workflows/controlled-saturation-repeatability.yml` blob `1f4b20c0` defines a 16-path critical array directly before the post-rebase source guard function. The earlier `0d618f27` shell mock used a synthetic one-path array, not the workflow's real critical-path inventory.
- **rootCauseOrUnknown:** The incomplete test binding is verified from code. Actual omission of a path or stale publication was not observed. Real-world publisher exploitability remains unknown.
- **failedApproach:** Treating a mocked one-path Bash array as evidence that the workflow's actual critical-path list is complete, or accepting unreviewed shell tokens before executing Bash.
- **correction:** [`60b7d6ee`](https://github.com/m-shogo/memories-project/commit/60b7d6ee87c773019e0c6560bd7602fb28d7e6fd) adds `prove_saturation_critical_path_array_binding` to the existing read-only negative suite. It extracts the source array from a uniquely anchored block, requires a strict literal-only grammar and an exact ordered 16-path inventory, then verifies Bash expands those exact paths.
- **recurrenceGuard:** Executable negative mutations cover removed, duplicated, commented, expanded, command-injected and reordered paths. Bash execution is permitted only after literal grammar and exact inventory checks. A local isolated Bash expansion prototype returned 0 with 16 expected paths.
- **retryCondition:** Revisit if the source workflow's reviewed critical inventory changes, exact-source CI fails, or a reviewed requirement changes the critical-path set. Never silently relax the inventory or run unreviewed shell expressions.

## Material safe progress

- **outcome:** One read-only negative-suite code commit was accepted on `so`; a local 16-path Bash expansion prototype passed. Exact-source [Autonomous Learning Guard #41443485948](https://github.com/m-shogo/memories-project/actions/runs/41443485948) was queued/in progress at record creation and is **not** counted as SUCCESS.
- **evidence:** GitHub source re-read confirmed the strict token regex, exact inventory, six negative mutations, and shell expansion check. The only code target is `scripts/validate-autonomous-learning-system-negative.py`; the writer workflow remains unchanged.
- **whySafe:** The script uses a temporary isolated Bash process with no credentials or Git network operations. It validates source bytes and cannot create production-equivalent evidence or authorize promotion.
- **reusableMechanism:** Bind guard semantics and the exact data array that the guard consumes separately; fail closed on missing or substituted critical inputs before running even a local shell expansion.
- **protectedAuthorityCheck:** Post-code Git tree read showed unchanged blob SHAs for all ten protected authorities: production `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`.

## Next safe target

Confirm exact-source CI for both new code commits. Independently audit the three soak publisher rebase-to-push shell paths without invoking or modifying write-capable workflows. Maintain `productionDecision=NO_GO`.
