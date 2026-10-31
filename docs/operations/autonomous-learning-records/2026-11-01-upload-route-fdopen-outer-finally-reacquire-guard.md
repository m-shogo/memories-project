# Supplemental OPS learning — failed fdopen must release outer-finally ownership (2026-11-01)

Append-only operational learning governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound generation-evidence, typed eight-domain non-resurrection, independent-review, final-candidate or human-promotion evidence.

## Material failure class — indirect reclose bypass of the no-close rule

- **symptom:** The existing source-negative guard rejected a direct `os.close(descriptor)` in the failed `fdopen` handler, but did not independently bind the handoff's `untransferred_stage_fd = None` assignment. Changing that assignment to the original descriptor would cause the outer `finally` to close a possibly recycled numeric FD, bypassing the direct-close guard.
- **evidence:** At source HEAD `63e0d4f3`, the `fdopen_exc` handler ended in `untransferred_stage_fd = None; raise`, and the outer cleanup still contains `if untransferred_stage_fd is not None: os.close(untransferred_stage_fd)`. The prior AST check examined direct `os.close(descriptor)` calls in the exception handler, not the last ownership-release assignment. This is a static regression gap, not a production incident.
- **rootCauseOrUnknown:** Verified: an indirect reclose through the outer-finally ownership variable was not structurally constrained by the existing direct-call AST guard.
- **failedApproach:** Assuming that forbidding `os.close(descriptor)` within the exception handler was sufficient to prevent all close paths after ambiguous handoff.
- **correction:** [16602272](https://github.com/m-shogo/memories-project/commit/16602272f8f8c37cb76b2efda533abd0b1610357) extends the existing read-only AST guard to require the unique `fdopen_exc` handler's penultimate direct statement to assign the constant `None` to `untransferred_stage_fd`, immediately followed by a raise.
- **recurrenceGuard:** A new source-negative mutation changes that assignment to `untransferred_stage_fd = descriptor`. The canonical CI entrypoint rejects it while continuing to reject a direct `os.close(descriptor)`. The existing 4,096-line prewrite budget is preserved.
- **retryCondition:** Revalidate on changes to outer-finally FD ownership, exception-handler topology, helper delegation, or CI source-negative binding. Do not infer atomic FD ownership or leak-free pre-effect cleanup; do not retry unchanged external MinIO 401 or workflow-write blockers.

## Material success — observed exact-source CI

- **outcome:** The indirect outer-finally reclose mutation now fails closed through the existing CI-reached validator.
- **evidence:** [Autonomous Learning Guard #41252759570](https://github.com/m-shogo/memories-project/actions/runs/41252759570) and [Operability Contracts #41252759578](https://github.com/m-shogo/memories-project/actions/runs/41252759578) both completed **SUCCESS** on exact code HEAD `16602272f8f8c37cb76b2efda533abd0b1610357`. Guard logs confirm 601 canonical negatives, 39 supplemental-history fixtures, 52 source-negative workflows / 63 direct Python commands / 204 negative fixtures, 195 fanout synthetics and 1,186 helper-ancestor mutations.
- **whySafe:** Only the existing read-only CI entrypoint was modified; runtime FD cleanup, reviewed workflow YAML, production evidence, recovery authority, credentials, traffic, readiness and human promotion were not changed.
- **reusableMechanism:** For exceptional ownership handoff, protect both the immediate close site and any state variable that would authorize a later indirect cleanup. Bind the release assignment's location and value structurally, then mutate it to a dangerous retained owner in source-negative CI.
- **protectedAuthorityCheck:** Ten protected blobs unchanged after code publication: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 `dbaa36b0`, generations `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`. Prior learning history was not edited.

## Authority and next target

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered / unsuperseded semantically preflight-eligible generations `0/0`, approved recovery objectives `0`. Preflight requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current objective. Reviewed drill requests are planning-only; new generation recovery evidence requires a current executable reviewed request; complete typed eight-domain non-resurrection coverage and independent review are mandatory for final candidates; human promotion is separate and non-automatic.

**Next safe target:** Investigate a fully testable retained-original/direct-write protocol that removes the exceptional pre-effect unlinked-FD leak without permitting any ambiguous close. Existing independent pre-MinIO Go-test, workflow-permission, supplemental-only trigger and MinIO HTTP 401 blockers remain scoped and unchanged.
