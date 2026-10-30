# Supplemental OPS learning — deterministic workflow inode-swap and exact byte ceiling (2026-10-30)

Append-only operational learning only; canonical learning and mandatory contract remain unchanged. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material risk and executable recurrence prevention

- **symptom:** The new descriptor-pinned workflow reader checks path identity and enforces a 256 KiB read limit, but its exact inode-swap rejection and inclusive maximum-size behavior were not independently exercised by the initial fixtures.
- **evidence:** Source review after [3cfead7d](https://github.com/m-shogo/memories-project/commit/3cfead7d58055005831a2ca7d4002b22e4966b02) showed a post-read `Path.lstat` inode comparison and a `MAX_WORKFLOW_SOURCE_BYTES + 1` read. Prior tests covered oversized input but not a same-content path replacement at the final lstat, nor an exactly-maximum-size positive. No observed production incident.
- **rootCauseOrUnknown:** Verified test-coverage gap, not a demonstrated bypass of the implemented guard. Residual races outside a single descriptor snapshot remain an explicit limit, not a claim of complete filesystem atomicity.
- **failedApproach:** Treating the presence of an inode comparison and upper-bound check as sufficient behavioral proof without exercising both boundaries.
- **correction:** [463ca009](https://github.com/m-shogo/memories-project/commit/463ca0097ef100dbf70a73ad29ed667e9ca42f66) adds a deterministic mocked-lstat same-content inode replacement negative to the read-only self-test, plus an actual CLI positive at exactly 256 KiB while retaining the existing 256 KiB + 1 rejection.
- **recurrenceGuard:** The inode-swap fixture must execute its replacement and reject the mismatched source identity; the real CLI must match the expected workflow at the inclusive byte ceiling and reject one extra byte. Exact source is checked by the existing CI-bound negative harness.
- **retryCondition:** Revisit if the descriptor identity algorithm, source size policy or actual filesystem behavior changes. Do not retry unchanged MinIO, workflow-write permission, large canonical learning transport or human-promotion blockers.

## Observed success and protected authority

- **outcome:** [Autonomous Learning Guard #41034136517](https://github.com/m-shogo/memories-project/actions/runs/41034136517) completed **SUCCESS** on exact source `463ca0097ef100dbf70a73ad29ed667e9ca42f66`.
- **evidence:** CI job logs show **510** canonical fail-closed negatives (509 previously), 195 fanout synthetic cases, 1,186 helper-ancestor negatives, 52 source-negative workflows, 63 direct Python commands and 204 execution-path fixtures. Append-only, learning contract, entry-document, helper ancestor and read-only steps PASS. The inode-swap self-test executes within the fanout suite and is not separately counted as a canonical negative.
- **whySafe:** Changes were confined to read-only Python self-tests and the existing CI-reachable negative harness. The inode swap occurs only in a disposable temporary directory. No workflow YAML, production, credential, traffic, generation, objective, drill, backup/restore, evidence, non-resurrection, independent review or promotion authority was changed.
- **reusableMechanism:** Pair a source-identity check with deterministic replacement at the precise verification boundary, and pair a hard read ceiling with exact-limit positive and limit-plus-one negative.
- **protectedAuthorityCheck:** All ten protected blob SHAs remained unchanged after the code commit: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED` with registered/eligible generations 0/0 and no approved recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or separate human promotion.

## Next safe target

Continue read-only audit of remaining source identity boundaries without conflating local prewrite guards with complete transitive CI closure. Go-only Focused Upload Route Test before MinIO and its source-change trigger coverage remain unproven; workflow permission and external evidence blockers must not be retried without changed preconditions.
