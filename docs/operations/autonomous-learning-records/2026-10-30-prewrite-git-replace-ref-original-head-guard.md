# Supplemental OPS learning — Git replacement-ref HEAD identity guard (2026-10-30)

Append-only operational learning, separate from canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md`. Mandatory `contracts/operations/autonomous-learning-system.json` remains authoritative. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, or human-promotion evidence.

## Material failure — staged Git drift masked by replacement objects

- **symptom:** A checkout with a staged workflow edit can report a clean `git diff --cached --quiet HEAD` when a Git replacement ref substitutes a different tree for HEAD.
- **evidence:** A disposable local Git repository produced exit 1 for staged-vs-HEAD comparison before replacement, exit 0 after `git replace <original-head> <staged-tree-commit>`, and exit 1 with `git --no-replace-objects diff --cached --quiet HEAD`. No production failure was observed.
- **rootCauseOrUnknown:** Verified Git replacement-object resolution changes the commit tree consulted by the default cached diff without changing the HEAD ref identity.
- **failedApproach:** Treating a clean cached diff as original committed HEAD/index parity without disabling replace-object resolution.
- **correction:** [686f57ca](https://github.com/m-shogo/memories-project/commit/686f57ca578349da1b77573b43aa8812065dd18c) adds `--no-replace-objects` to the existing read-only Git helper and a disposable real-Git control, staged-drift negative and cleanup positive in the CI-bound negative validator.
- **recurrenceGuard:** The real CLI must reject replacement-masked staged drift with the exact `prewrite workflow Git index content drift` diagnostic, then accept the restored clean checkout. The source is not authorized to mutate workflow YAML or bypass independent CI dependency/permission review.
- **retryCondition:** Revisit if Git replacement-object semantics, the Git command wrapper or its original-object parity invariant changes; do not retry unchanged external MinIO, workflow-write permission, large canonical learning update transport or human-promotion blockers.

## Material failure — negative-fixture newline escaping

- **symptom:** [Autonomous Learning Guard #41032115666](https://github.com/m-shogo/memories-project/actions/runs/41032115666) FAILED on exact source `686f57ca` at `Git replace-ref staged-drift CLI negative failed`.
- **evidence:** The CI traceback identifies the new real-Git negative. Source inspection showed two backslash bytes followed by `n` (92,92,110) in both the fixture workflow string and its expected diagnostic; the Python string therefore contained a literal backslash-n rather than a newline.
- **rootCauseOrUnknown:** Verified over-escaping in the JavaScript-generated Python patch. The failure was fixture construction, not an observed production incident.
- **failedApproach:** Embedding an extra escaping layer without verifying the committed Python literal's actual bytes before CI.
- **correction:** [75f23d37](https://github.com/m-shogo/memories-project/commit/75f23d37c6bef13a2286a1278ae7735f9ed29f50) corrects both to one backslash followed by `n` (92,110), restoring intended Python newline interpretation.
- **recurrenceGuard:** Exact-source CI exercises the control, rejection diagnostic and restored positive; future generated fixture patches should inspect character codes of escaped literals before commit.
- **retryCondition:** Retry this fixture only after verified escaping correction or a changed Git/source parser precondition. The corrected exact-source CI is already successful.

## Material success — exact-source CI and protected authority

- **outcome:** [Autonomous Learning Guard #41032374085](https://github.com/m-shogo/memories-project/actions/runs/41032374085) completed **SUCCESS** on exact source `75f23d37c6bef13a2286a1278ae7735f9ed29f50`. Job steps confirmed append-only learning, learning contract, executable negatives, entry document, helper ancestor reachability and read-only completion PASS.
- **evidence:** The job log reports **509** canonical fail-closed negatives, **193** prewrite fanout synthetic cases, **1,186** helper-ancestor negatives, and 52 source-negative workflows/63 direct Python commands/204 execution-path fixtures. The new real-Git replacement-ref negative is not separately counted in the printed 509.
- **whySafe:** Only existing read-only Python auditor and CI-reachable negative validator changed. Disposable Git repositories supply the test, not any production or recovery evidence. No workflow, credential, traffic, generation, objective, drill, typed eight-domain record, independent review or promotion authority was changed.
- **reusableMechanism:** Bind Git HEAD/index parity to original objects with `git --no-replace-objects`; pair a reproducible masked-diff control with a precise rejection and restored clean positive. Preserve exact-source CI evidence separately from static checks and production admission.
- **protectedAuthorityCheck:** Ten protected blob SHAs were unchanged after both code commits: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and all six generation/objective/drill/evidence/non-resurrection/promotion registries. Snapshot remains `PREREQUISITES_BLOCKED` with registered/eligible generations 0/0 and zero approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record or final candidate. `productionDecision=NO_GO`; separate explicit human promotion authority remains unsatisfied.

## Next safe target

Conservatively audit the unreviewed `*(...)` glob spelling against Python `fnmatch` and the existing GitHub path-filter scanner. Do not claim a complete transitive Go/Python closure or a MinIO-independent Go-only CI route until source-change triggers and execution order are proven.
