# Supplemental OPS learning — real-source strict direct CI audit (2026-10-30)

Append-only supplemental learning governed by `contracts/operations/autonomous-learning-system.json`. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains blob-SHA verified, not fully retrievable via the large-blob transport. **This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure / real-source coverage gap

- **symptom:** The strict zero-direct-push/PR-match mode had only disposable synthetic workflow fixtures. Its behavior against the repository's actual 221-workflow tree and the auditor's own source path was not independently checked.
- **evidence:** [`bb90eff0`](https://github.com/m-shogo/memories-project/commit/bb90eff0cdca54365fd3b871fbb44135304d927d) covered synthetic no-match and one-match CLI behavior; the existing real-repository checks covered other paths, not the auditor source in strict mode. This is a static regression-risk gap, not an observed production incident.
- **rootCauseOrUnknown:** Verified missing real-source strict-mode test; whether the auditor source has zero or nonzero direct workflow matches is deliberately treated as a runtime-observed value, not fabricated from partial connector inventory.
- **failedApproach:** Assuming synthetic strict-mode cases prove the classification and exact workflow identity of the real checkout.
- **correction:** [`b9dc6dcc`](https://github.com/m-shogo/memories-project/commit/b9dc6dcc663c4c9c67f6422f13944851adfc1275) runs the strict auditor CLI against `scripts/audit-memory-os-workflow-trigger-fanout.py` in the real checked-out repository, reconciles the reported direct-match count to emitted sorted unique workflow identities, and requires zero matches to produce `BLOCKED_NO_DIRECT_PUSH_PR_MATCH` with exit 2. Nonzero direct matches must not be classified as zero, and risk/exit must remain consistent.
- **recurrenceGuard:** One additional real-source exact CLI regression, separate from synthetic fixture controls; fail closed on count/identity mismatch or incorrect zero/nonzero risk/exit. Fail-closed negatives **493 → 494**; fanout synthetic remains **185**.
- **retryCondition:** Reassess after a reviewed workflow trigger/CI-reachability change with actual checkout, exact-source CI and full dependency closure; do not retry unchanged workflow-write permission, MinIO 401, canonical-learning transfer or human approval blockers.

## Material success / protected authority

- **outcome:** Exact-source [Autonomous Learning Guard #41014834721](https://github.com/m-shogo/memories-project/actions/runs/41014834721) completed **SUCCESS** for `b9dc6dcc663c4c9c67f6422f13944851adfc1275`.
- **evidence:** CI job log shows append-only PASS, contract PASS, **494** fail-closed negatives, **185** fanout synthetic cases, **1,186** helper-ancestor negative mutations, entry-document PASS and read-only completion. The new real-source strict CLI check executed within the negative validator; it does not report an independent workflow trigger proof.
- **whySafe:** Only the CI-reachable read-only negative validator changed. No workflow YAML, production code, credentials, traffic, recovery evidence, readiness, generation/objective or promotion authority changed.
- **reusableMechanism:** Bind synthetic fail-closed mode tests to a real-checkout source path and reconcile exact CLI risk/count/identity/exit without treating direct matches as transitive CI coverage.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs matched run-start `7d2a0617`, including canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no human-approved current recovery objective or human promotion.
- **limits / nextSafeTarget:** Actual Go-only Upload Route CI reachability remains blocked by workflow permission and MinIO ordering. Continue optional Git index/checkout identity checks, then prove source-level CI trigger coverage before workflow edits.
