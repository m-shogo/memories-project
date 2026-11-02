# Supplemental OPS learning — inert postrebase guards and commented push boundaries (2026-11-02)

Append-only subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is source/negative-test learning only; it is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate, or human promotion authority.

## Material failure mode / correction

- **symptom:** The four-workflow lexical rebase inventory could classify a `verify_critical_source` marker after an unconditional `exit 0` or inside a dead conditional as a protected postrebase path. It could also mistake a commented-out `git push origin HEAD:so` for a real publication boundary. No real stale publication or production incident was observed.
- **evidence:** At the previous `so` code blob `ea54ff1d`, `rebase_guard_status` searched the entire rebase-to-first-textual-push segment for a standalone guard marker and used an unanchored `git push` regex. Isolated Python controls confirmed the corrected parser distinguishes executable adjacent guards, inert later guards, and commented-only push boundaries.
- **rootCauseOrUnknown:** Verified lexical classifier overapproximation; shell control-flow, actual workflow exploitability, and production consequences remain explicitly unknown.
- **failedApproach:** Treating any later guard marker and any textual push token as proof of effective source guarding, without considering early termination or comments.
- **correction:** [31f3a4f9](https://github.com/m-shogo/memories-project/commit/31f3a4f9ed6830217046f6889579a6bdc4140b0e) requires a guard on the immediate next source line after rebase and an executable-looking anchored push boundary; [ec0a2058](https://github.com/m-shogo/memories-project/commit/ec0a2058fe90fb0615173434ff2f5b52bd060022) adds a commented-only push missing-boundary negative.
- **recurrenceGuard:** Executable positive and negative fixtures now cover immediate guard, early exit, dead conditional, comment-only guard, commented push followed by real push, and commented-only push with no real push. This is intentionally a conservative lexical source inventory, **not** a shell execution proof or permission to publish.
- **retryCondition:** Reconsider writer workflow changes only after independently reviewed shell/control-flow semantics, source lease, permissions, bounded reconcile, and exact-source read-only CI. Do not promote the lexical classification into a production or publication gate.

## Observed safe progress

- **outcome:** Two code-only commits were confirmed by GitHub diffs and exact-source re-reads; isolated local Python positive/negative fixtures passed. At record creation, GitHub exact-source Autonomous Learning Guard runs [#41439309194](https://github.com/m-shogo/memories-project/actions/runs/41439309194) and [#41439393350](https://github.com/m-shogo/memories-project/actions/runs/41439393350) were still in progress, **not** counted as SUCCESS.
- **evidence:** The first commit changed only `scripts/validate-autonomous-learning-system-negative.py` (one parser and three fixtures); the second changed only that script (two missing-push cases). GitHub source re-read showed the intended Python raw regex and LF fixture strings. Local Python checks rejected absent and commented-only push.
- **whySafe:** No publisher workflow, write-capable job, production evidence, credential, traffic, readiness, or promotion authority changed; the guard executes under the existing `Autonomous Learning Guard` read-only workflow.
- **reusableMechanism:** Prefer immediate source adjacency and anchored executable-looking command boundaries over unbounded lexical presence checks; mutation-test both comment and early-termination decoys before considering source checks authoritative.
- **protectedAuthorityCheck:** After both code changes, the Git blob SHAs of production operability status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, and mandatory learning contract `87712ea9` were unchanged.

## Next safe target

Verify the two exact-source CI outcomes; if they fail, diagnose and append a separate correction without rewriting this record. Then review the three soak publisher rebase paths independently using shell/control-flow negative tests. Keep `productionDecision=NO_GO` and human promotion authority separate.
