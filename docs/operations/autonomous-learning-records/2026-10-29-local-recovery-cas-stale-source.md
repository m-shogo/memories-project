# Supplemental OPS learning — local recovery stale source CAS protection (2026-10-29)

Append-only supplemental learning only. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence.

## Material failure / recurrence guard
- **Symptom:** The corrected local migration recovery source-negative CI passed, but the corresponding artifact rehearsal publisher job failed with exit code 1.
- **Observed evidence:** [Local Migration Recovery Artifact Rehearsal #40740180180](https://github.com/m-shogo/memories-project/actions/runs/40740180180), exact source `0b00785c67e34b43d228bf0df89954e05fdfc692`, passed local source and artifact validation (`result: NOT_REQUESTED`, `production evidence: false`). The subsequent `git fetch origin so` advanced `origin/so` from `0b00785c` to `0439fa30`, and `test "$(git rev-parse origin/so)" = "$BASE_SHA"` returned nonzero. The latter commit was an independent append-only learning record.
- **Verified root cause:** Concurrent append-only learning publication advanced the branch after the publisher job checked out its exact source. The existing source-CAS precondition correctly rejected stale authority reconciliation.
- **Failed approach:** Publishing a separate learning-only commit while a source-bound publisher workflow was still running; treating a failed publisher job as proof of an invalid recovery validator would misclassify the failure.
- **Correction:** Do not modify or weaken the publisher's existing branch/SHA CAS guard. Classify the result as a bounded stale-source rejection and allow a future normal source event to reconcile only when it starts from the then-current `so`. No forced push or immediate unchanged retry.
- **Executable recurrence guard:** Reuse the existing `BASE_SHA` vs `origin/so` deterministic check and stale-write refusal; it prevented publishing from an outdated source. The [Local Migration Recovery Source Negative #40740180198](https://github.com/m-shogo/memories-project/actions/runs/40740180198) completed **SUCCESS** on the same corrected code, independently confirming validator behavior.
- **Retry condition:** A new source-bound workflow run must start at the current branch head, with no competing writes during its reconcile window. A mere unchanged rerun of the stale source is prohibited.

## Material success / protected authority
- **Observed outcome/evidence:** The publisher did not push stale authority, did not produce a requested recovery artifact, and did not change production evidence or traffic. Its failure is a successful fail-closed CAS protection, not an admission success.
- **Why safe:** No production contract, registry, environment generation, recovery objective, drill request, evidence, credential, traffic, readiness or human promotion authority was changed by the failed job.
- **Reusable mechanism:** Classify CAS rejection using observed source/remote SHAs, distinguish CI source-negative SUCCESS from publisher admission failure, and schedule no automatic stale-source retry.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs remained unchanged. `productionDecision=NO_GO`; registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records, final candidates and human promotion approvals remain zero.
- **Next safe target:** Continue independent read-only source-negative guards; avoid overlapping learning writes with active source-bound reconciliation where feasible.
