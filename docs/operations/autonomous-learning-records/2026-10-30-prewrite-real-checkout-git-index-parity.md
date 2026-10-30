# Supplemental OPS learning — real checkout Git index/direct-match parity (2026-10-30)

Append-only supplemental learning under `contracts/operations/autonomous-learning-system.json`. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains blob-SHA verified; its large-blob full-text transport is unavailable. **Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure / real-checkout proof gap

- **symptom:** The optional Git index workflow identity guard had only disposable Git fixture coverage. Its behavior on the real GitHub Actions checkout and the repository's full tracked workflow tree was not independently proven.
- **evidence:** [`39f0c535`](https://github.com/m-shogo/memories-project/commit/39f0c535bebf7ea42aa38bad0b7fa6a0fc52cfed) exercised a temporary tracked workflow, dirty file, untracked file and missing `.git`; the actual checkout was not passed through the new optional mode. This is a static regression gap, not an observed production incident.
- **rootCauseOrUnknown:** Verified missing real-checkout invocation and parity assertion for the optional index flag.
- **failedApproach:** Inferring real GitHub checkout index cleanliness and exact workflow-source identity from disposable fixture success.
- **correction:** [`0ef4cfe8`](https://github.com/m-shogo/memories-project/commit/0ef4cfe80901c2790546b88e05ce2f5fc68f471b) runs the real auditor source with both `--require-direct-push-pr-match` and `--require-git-index-identity`, requiring identical stdout and exit status to the already reviewed strict real-source direct-match audit and empty stderr.
- **recurrenceGuard:** One additional real checkout exact CLI parity check; index mismatch, staged/working-tree drift, missing Git metadata, changed direct workflow identities or altered classification fail closed. Canonical fail-closed negatives **499 → 500**, fanout synthetic remains **190**.
- **retryCondition:** Any legitimate checkout/index divergence requires reviewed source authority, exact CI and disposable positive/negative controls. Do not retry unchanged external MinIO, workflow-write permission, canonical-learning transfer or human approval blockers.

## Material success / protected authority

- **outcome:** Exact-source [Autonomous Learning Guard #41015293672](https://github.com/m-shogo/memories-project/actions/runs/41015293672) completed **SUCCESS** for `0ef4cfe80901c2790546b88e05ce2f5fc68f471b`.
- **evidence:** CI log shows append-only PASS, contract PASS, **500** fail-closed negatives, **190** fanout synthetic cases, **1,186** helper-ancestor negative mutations, entry-document PASS and read-only completion. Real-checkout Git index/direct-match parity executed within the negative validator.
- **whySafe:** Only CI-reachable read-only negative validator changed; no workflow YAML, production runtime, credentials, traffic, recovery evidence, readiness, generation/objective or promotion authority changed.
- **reusableMechanism:** Pair disposable index mutation controls with an actual clean GitHub checkout parity check, while keeping direct push/PR matching distinct from full CI reachability and write permission.
- **protectedAuthorityCheck:** Ten protected authority blobs matched run-start `7d2a0617`, including canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no human-approved current recovery objective or human production promotion.
- **limits / nextSafeTarget:** No full Go/Python transitive closure or MinIO-independent Go-only CI route is claimed. Continue index mode/stage mutation negatives and independent CI trigger reachability review before any workflow write.
