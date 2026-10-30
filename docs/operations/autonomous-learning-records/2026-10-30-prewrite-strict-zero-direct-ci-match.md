# Supplemental OPS learning — strict zero-direct-CI-match prewrite guard (2026-10-30)

Append-only supplemental learning governed by `contracts/operations/autonomous-learning-system.json`. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains blob-SHA verified, with large-blob full-text transport unavailable. **Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure / direct CI reachability gap

- **symptom:** A zero-match prewrite trigger audit returned `BOUNDED_DIRECT_MATCH_ONLY` with exit 0. This can be mistaken for a safe write even though mandatory `ciReachabilityRequired` cannot be established without a directly matching push/PR workflow.
- **evidence:** At run-start `7d2a0617`, `classify([])` returned `BOUNDED_DIRECT_MATCH_ONLY`; the CLI warned that direct matching was not permission or transitive closure, but it did not offer an executable zero-match blocker. This is a static fail-closed gap, not a production incident.
- **rootCauseOrUnknown:** Verified missing zero-match rejection in the optional prewrite classification policy; no actual CI reachability proof is claimed.
- **failedApproach:** Treating a bounded fanout count of zero as sufficient evidence of CI coverage.
- **correction:** [`ca3bd7f4`](https://github.com/m-shogo/memories-project/commit/ca3bd7f47ab32675ea405b0866b0729a908af597) adds explicit `--require-direct-push-pr-match` mode, returning `BLOCKED_NO_DIRECT_PUSH_PR_MATCH` with exit 2 for zero direct matches while retaining legacy diagnostic behavior and all higher-priority known-risk classifications. [`bb90eff0`](https://github.com/m-shogo/memories-project/commit/bb90eff0cdca54365fd3b871fbb44135304d927d) adds exact real-CLI zero-match and positive-match controls.
- **recurrenceGuard:** Three synthetic classification controls and two exact stdout/exit-status real CLI controls. A direct match remains **necessary, never sufficient** for CI reachability; the flag does not assert transitive workflow-call closure, executable test coverage or write authorization. Exact-source negatives **491 → 493**, fanout synthetic **182 → 185**.
- **retryCondition:** Only relax zero-match blocking after an independently verified CI path or reviewed policy change with real CLI negative/positive proof. Do not retry unchanged workflow-write permissions, external MinIO 401, canonical-learning transport or human promotion blockers.

## Material success / authority check

- **outcome:** Exact-source [Autonomous Learning Guard #41014677090](https://github.com/m-shogo/memories-project/actions/runs/41014677090) completed **SUCCESS** for `bb90eff0cdca54365fd3b871fbb44135304d927d`.
- **evidence:** CI job logs report append-only PASS, learning contract PASS, **493** fail-closed negatives, **185** fanout synthetic cases, **1,186** helper-ancestor negative mutations, entry-document PASS and read-only completion.
- **whySafe:** Only the read-only auditor and CI-reachable negative validator changed. No workflow YAML, production runtime, credentials, traffic, recovery evidence, readiness, objective, generation or promotion authority changed.
- **reusableMechanism:** Separate diagnostic blast-radius classification from strict prewrite prerequisites; reject zero direct push/PR matches explicitly, but never equate a nonzero direct match with full CI reachability.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained equal to run-start `7d2a0617`, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, and no human recovery or promotion approval.
- **limits / nextSafeTarget:** The flag is opt-in and does not fix Go-only Upload Route CI triggers or external MinIO. Continue with a real-repository strict-mode regression and Git index checkout-source identity, without unauthorized workflow edits.
