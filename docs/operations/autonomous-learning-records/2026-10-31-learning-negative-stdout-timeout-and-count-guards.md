# Supplemental OPS learning — negative stdout, nested timeout and complete negative inventory (2026-10-31)

Append-only supplemental operational learning under the mandatory `contracts/operations/autonomous-learning-system.json`. Canonical learning authority `docs/operations/AUTONOMOUS-OPS-LEARNING.md` is unchanged. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, or promotion evidence.

## Material failure mode 1 — negative child stdout contamination

- **symptom:** Static inspection found that `require_canonical_rejection` accepted a synthetic child with exit 1 and canonical stderr even if the same child emitted a false success marker on stdout. No actual contaminated production or CI output was observed.
- **evidence:** At starting `so` `702633ac`, the canonical negative classifier checked return code and stderr prefix/traceback but not stdout. The downstream positive PASS classifier already required a clean stdout/stderr boundary.
- **rootCauseOrUnknown:** Verified omitted stdout predicate in the negative admission classifier; no observed runtime exploit or production failure.
- **failedApproach:** Treating exit 1 plus canonical-looking stderr as sufficient proof while ignoring an inconsistent success channel.
- **correction:** [1c7f8bcc](https://github.com/m-shogo/memories-project/commit/1c7f8bccd91fb3ef0bf1a6e36ea10d16ba3835c7) rejects any negative child stdout before accepting the canonical stderr class.
- **recurrenceGuard:** A deterministic `CompletedProcess` negative supplies exit 1, a false PASS marker on stdout, and canonical stderr; the synthetic positive still requires empty stdout and exact canonical rejection.
- **retryCondition:** Revisit only on an actual changed canonical child output contract or a new exact-source classifier failure; never admit mixed success/failure output without an independently reviewed proof.

## Material failure mode 2 — nested execution deadline drift

- **symptom:** The nested learning guard used a reviewed 120-second timeout but its policy check allowed any integer between 1 and 300, so increasing the deadline to hide a performance regression would pass the old check. No unreviewed timeout change was observed.
- **evidence:** Starting source `scripts/validate-memory-os-entry-docs.py` contained `LEARNING_GUARD_TIMEOUT_SECONDS = 120` and the permissive `1 <= timeout <= 300` predicate; prior learning recorded the real 606-case nested 120-second failure and prohibited raising the bound without changed prerequisites.
- **rootCauseOrUnknown:** Verified mismatch between the reviewed operational deadline and the executable range guard.
- **failedApproach:** Equating an arbitrary bounded deadline with the reviewed 120-second nested CI contract.
- **correction:** [81438a4b](https://github.com/m-shogo/memories-project/commit/81438a4b5e2e67547dd30bc4743766d6b46a2bcf) pins the actual nested invocation to an exact integer 120 seconds.
- **recurrenceGuard:** CI-executed synthetic checks accept 120 and reject 0, 119, 121, 300, boolean true, floating 120.0, and string "120". The original nested subprocess still executes independently with the 120-second timeout.
- **retryCondition:** Revisit only with a measured per-phase bottleneck, a changed human-reviewed deadline policy, and independent exact-source CI; do not increase timeout merely to conceal slower negative fixtures.

## Material failure mode 3 — obsolete negative-suite admission floor

- **symptom:** The CI entrypoint still accepted 128 canonical negative cases although the actual suite now executes 601, leaving a potential 473-case reduction admissible by count alone. This was a latent coverage gap, not an observed truncation.
- **evidence:** `MIN_LEARNING_NEGATIVE_CASES = 128` at `81438a4b`; exact-source runs had already observed 601 direct and 601 independently nested negatives.
- **rootCauseOrUnknown:** Verified admission minimum was not updated as the negative suite expanded.
- **failedApproach:** Relying on an obsolete historical count floor as evidence that the current reviewed negative inventory executed.
- **correction:** [e9329b1b](https://github.com/m-shogo/memories-project/commit/e9329b1bbefad2b817033ed8691b2da118f77be4) raises the classifier floor to 601.
- **recurrenceGuard:** The existing deterministic classifier rejects 600 and accepts 601 or more; direct and independent nested executions still verify complete source-ordered case labels. Future cases can increase the count without relaxing the floor.
- **retryCondition:** Revisit only if a reviewed fixture inventory changes, with a matching exact-source CI proof and explicit justification for any reduction; never reduce the floor to mask a timeout.

## Material successes and protected-authority verification

- **outcome/evidence:** [Autonomous Learning Guard #41122330479](https://github.com/m-shogo/memories-project/actions/runs/41122330479) SUCCESS on exact `1c7f8bcc`; [#41122599336](https://github.com/m-shogo/memories-project/actions/runs/41122599336) SUCCESS on exact `81438a4b`; [#41122827434](https://github.com/m-shogo/memories-project/actions/runs/41122827434) SUCCESS on exact `e9329b1b`. Each log shows append-only and mandatory contract PASS, **601 direct** and **601 independently nested** canonical negatives PASS, **52 source-negative workflows / 63 direct Python commands / 204 semantic fixtures**, entry-document PASS, **195 fanout synthetic cases**, **1,186 helper-ancestor negatives**, and read-only completion. These are CI observations, not production admission evidence.
- **whySafe:** Three code commits changed only the two existing CI-reachable read-only Python validation scripts. No workflow YAML, production Go/Python implementation, external MinIO, credential, traffic, generation, objective, reviewed drill request, recovery evidence, typed eight-domain record, independent review or human promotion was written.
- **reusableMechanism:** Require mutually consistent child stdout/stderr/exit status; pin a reviewed deadline by exact type and value with negative controls; advance a CI classifier floor when a complete deterministic suite grows. Validate the exact source in direct and nested execution rather than accepting a first PASS alone.
- **protectedAuthorityCheck:** Git tree comparisons for all three code commits changed only `scripts/validate-autonomous-learning-system-negative.py` or `scripts/validate-memory-os-entry-docs.py`. Ten protected blobs remained unchanged: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries `bfd1b045`, `f4d74f33`, `acebcd02`, `ae7e57ef`, `26bb1cc7`, `99cb895f`.

## Production boundary and next safe target

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered and semantically preflight-eligible generations 0/0. No explicitly human-approved current recovery objective, executable reviewed drill request, request-bound recovery evidence, complete typed eight-domain non-resurrection coverage, independent review, final candidate or separate human promotion. Reviewed requests remain planning-only; preflight requires unsuperseded eligible generations from distinct environments and a current approved objective. Learning cannot satisfy any production gate.

Next safe target: measure and reduce 601-case fixture setup overhead without weakening canonical ancestor ctime/inode/mode checks or the nested 120-second deadline; independently audit complete Go/Python dependency closure and Push/PR triggers before asserting a pre-MinIO focused upload-route CI path. Unchanged MinIO HTTP 401, workflow-write permission and human-approval blockers must not be retried. The final learning-only HEAD has no implied full production admission-chain success.
