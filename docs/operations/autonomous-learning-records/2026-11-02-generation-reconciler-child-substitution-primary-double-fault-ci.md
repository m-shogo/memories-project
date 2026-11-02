# Supplemental OPS learning — substituted-child primary double-fault negative CI (2026-11-02)

Append-only supplemental record governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This learning and synthetic CI are not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered environment generation, approved recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human production-promotion authority.

## Material regression risk / failure mode

- **symptom:** The substituted-child cleanup negative previously asserted identity-drift rejection only when the test body succeeded; it did not explicitly prove that an independent body failure remains primary during the same child-name substitution.
- **evidence:** After [`ce400aa3`](https://github.com/m-shogo/memories-project/commit/ce400aa31bf3717beb63893c74dbbac70c5d4599) corrected the earlier exact-source CI failure, `prove_child_substitution_before_cleanup_rejected` covered a substituted symlink without an intentional primary body exception. The separate cleanup-precedence test injected `shutil.rmtree` `ValueError`, not a simultaneous child identity rejection. No production failure was observed.
- **rootCauseOrUnknown:** Verified missing interaction test for the two independent failure boundaries; real-world occurrence unknown.
- **failedApproach:** Assuming the separate substituted-child and generic cleanup double-fault negatives prove the combined identity-plus-primary precedence case without executing it.
- **correction:** [`5c1d008e`](https://github.com/m-shogo/memories-project/commit/5c1d008ed6ddd8aafc283563fe31c1b068d25e43) extends the existing negative to run both standalone identity drift and identity drift with an intentional `PRIMARY_GENERATION_SUBSTITUTED_CHILD_FAILURE`.
- **recurrenceGuard:** Both cases assert the exact intended `Fail`, preserve the original parked child and the unowned replacement, require the replacement directory remain empty, and rely on the outer owned pinned fixture for cleanup. The earlier generic secondary cleanup double-fault negative remains invoked.
- **retryCondition:** Revisit only on fixture cleanup identity checks, primary-error precedence, test orchestration or exact-source CI regression. Do not retry unchanged Quay MinIO 401, publisher-coupled writer, canonical learning large-blob retrieval or absent human production evidence.

## Observed material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41419520851](https://github.com/m-shogo/memories-project/actions/runs/41419520851) completed **SUCCESS** on `5c1d008ed6ddd8aafc283563fe31c1b068d25e43`.
- **evidence:** Job `125191434939` logged `PASS: generation reconcile fixture cleanup preserves primary failure`, `PASS: reconcile negative substituted child rejects cleanup and preserves primary failure`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. GitHub diff changed only the independent read-only reconcile-negative harness.
- **whySafe:** The negative operates on isolated temporary fixtures and executes through `contents: read` exact-source CI. No production registry, recovery evidence, credentials, traffic or readiness is modified.
- **reusableMechanism:** Pair standalone rejection and simultaneous primary/secondary failure within one bounded negative, assert exact private error precedence and non-deletion of unowned replacements.
- **protectedAuthorityCheck:** All ten protected Git blob identities unchanged after the code commit: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. Registered/semantically eligible generations 0/0, approved objective 0, executable reviewed request 0, request-bound evidence 0, complete typed eight-domain coverage 0 and final candidate 0. Human production promotion is separate and nonautomatic.

## Next safe target

Validate explicit non-OS `ValueError`/`TypeError` fixture acquisition and mkdir redaction without reintroducing the known broad-exception masking failure.
