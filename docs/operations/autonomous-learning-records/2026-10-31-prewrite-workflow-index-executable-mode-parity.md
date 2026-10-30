# Supplemental OPS learning — prewrite Git index/worktree executable-mode parity (2026-10-31)

Append-only operational learning only. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. Never use this record as production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure — worktree mode drift masked by raw-byte proof

- **symptom:** A workflow YAML worktree file can change its executable bit while retaining identical raw bytes and a clean cached Git diff, so the previous strict source-identity audit did not reject an index/worktree mode mismatch.
- **evidence:** Disposable Git control on the local runner created a tracked `100644` workflow, chmodded it to `0755`, and observed `git diff --cached --quiet HEAD` exit 0. The reverse `100755` index versus `0644` worktree also left cached diff exit 0. Source review at `5b97f723dc2be32277c10c0bb6379017362e9da3` showed index modes were validated for allowed values but not compared to descriptor executable bits. This is an observed local source-identity bypass, not a production incident.
- **rootCauseOrUnknown:** Verified absence of index executable-mode parity in the bounded workflow descriptor reader. Runtime consequences of making YAML executable are not claimed; the source-authority mismatch itself is proven.
- **failedApproach:** Treating valid index mode, raw Git blob equality and a clean cached diff as a complete index/worktree source identity proof.
- **correction:** [`52beb38d`](https://github.com/m-shogo/memories-project/commit/52beb38dac79b4573ac1df69922114137e9c80c1) carries the reviewed `100644`/`100755` index executable identity into the same descriptor-pinned read and rejects either direction of mismatch.
- **recurrenceGuard:** Two real-Git CLI negatives exercise `100644→0755` and `100755→0644` mismatch, verify cached diff remains clean, require exact fail-closed diagnostics, and verify restoration positives. The disposable fixture explicitly sets initial `0644` independent of runner umask. Printed canonical negatives rise from 572 to **574**.
- **retryCondition:** Only revisit for a reviewed Git filemode/checkout semantics change with a real Git fixture, positive/negative controls and exact-source CI. Do not retry unchanged MinIO HTTP 401, workflow-write permission, large canonical-learning transport or human-promotion blockers.

## Material success and authority check

- **outcome:** Read-only mode-parity guard and two CLI negatives landed at `52beb38dac79b4573ac1df69922114137e9c80c1`.
- **evidence:** Exact-source [Autonomous Learning Guard #41080701378](https://github.com/m-shogo/memories-project/actions/runs/41080701378) completed SUCCESS. Job logs show append-only PASS, mandatory learning contract PASS, **574** canonical negatives, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document PASS and clean/read-only completion.
- **whySafe:** Only the existing read-only prewrite auditor and its CI-reachable negative validator changed. Git mode mutations occur only inside disposable local fixtures. No workflow YAML, Go runtime, credentials, traffic, production, backup/restore, generation, objective, reviewed request, recovery evidence, typed eight-domain coverage, independent review or promotion authority changed.
- **reusableMechanism:** Carry index mode identity alongside Git blob hashes and compare it inside the descriptor snapshot, rather than relying on cached Git diff or a separate racy worktree stat.
- **protectedAuthorityCheck:** The code commit changed exactly the two Python scripts. Ten protected authority paths are untouched, including canonical learning blob `b809c69d`, contract `87712ea9`, production status `55b3e639` and OPS-P0-007 snapshot `dbaa36b0`. Canonical history full-text transfer remains unavailable; no learning record substitutes for it.
- **production boundary:** `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, no human-approved current objective, executable reviewed drill request, request-bound evidence, complete typed eight-domain record, final candidate, independent review or separate human promotion.

## Next safe target

Check strict Git checkout metadata source authority (`.git` directory and index inode): a writable or aliased index can undermine the otherwise correct index/worktree parity. Keep this scoped; it does not establish complete Git object-store or transitive CI reachability.
