# Autonomous Operations Learning

This is an append-only operational learning log for autonomous work on branch `so`.
It records reusable execution lessons only. It is not production evidence, readiness authority,
a promotion decision, a recovery objective, or drill evidence.

## 2026-09-20 — Blocked workflow write must not stop unrelated safe progress

### What worked
- Fail-closed OPS-P0-007 authority was preserved: missing real production-equivalent evidence did not become readiness.
- `productionDecision=NO_GO` remained authoritative.
- Permission limitations were not bypassed with force-push, history rewriting, direct ref tricks, or fabricated evidence.
- The blocked workflow mutation was identified explicitly rather than silently treated as complete.

### What went poorly
- The autonomous loop was stopped after encountering a workflow-write permission blocker.
- That incorrectly promoted a scoped implementation blocker into a project-wide stop condition.
- It also prevented useful read-only audits and safe non-workflow hardening from continuing.

### Durable correction
1. A permission or external-evidence blocker is scoped to the affected write/evidence path; it is not a global stop condition.
2. After a blocked write, re-read current `so` and continue to the next independent, high-value, safe target.
3. Use CI wait time for validator diagnostics, negative-suite review, deterministic-authority drift checks, and existing-contract discovery.
4. Do not repeatedly retry an unchanged permission failure. Record it once and retry only after a relevant state/permission change.
5. Before every write, re-read the target file and current `so` authority so concurrent changes are not overwritten.
6. Prefer extending existing validators/contracts/tests over adding parallel authorities.
7. Keep learning records separate from evidence records: this file can improve execution behavior but can never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion gates.
8. A run ends early only when every remaining high-value target is genuinely blocked by external/human evidence or would require unsafe/speculative change.

### OPS-P0-007 invariants to retain
- Registered environment generations and semantically preflight-eligible generations are distinct states.
- Preflight can consume only unsuperseded, semantically eligible generations from distinct environments and an explicitly human-approved current recovery objective.
- Reviewed drill requests are planning authority only.
- New generation recovery evidence stays bound to a current executable reviewed request.
- Final production-equivalent recovery candidates require all existing generation/objective gates, complete typed eight-domain non-resurrection coverage, and independent review.
- Human production-promotion review is a separate non-automatic decision.
- No autonomous process may invent production-equivalent generations, recovery objectives, drill/production evidence, credentials, production traffic, readiness, or promotion.

## 2026-09-20 — Learning must be a closed loop, not a diary

### Durable correction
1. Every material failure must produce a reusable lesson: observed symptom, verified root cause when known, failed approach, correction, and a guard that prevents recurrence.
2. Every material success must record why it was safe and which invariant or check made it succeed, so later work can reuse the mechanism rather than rediscover it.
3. Before implementing a fix, search this learning log and existing contracts/scripts/workflows for the same failure class. Repeating a known failed approach without changed preconditions is a regression.
4. Prefer executable guards over prose: when practical, turn a lesson into a validator, negative test, deterministic check, or bounded reconcile rule. Documentation alone is not considered full prevention when an executable guard is feasible.
5. After each change, verify the intended behavior and also verify protected authorities did not drift. Record only observed results.
6. Periodically compact repeated lessons into stable rules while preserving the historical entries; do not delete failure history merely because the current implementation is green.
7. Track scoped blockers with their retry condition. A blocker is retried only when that condition changes; meanwhile unrelated safe work continues.
8. Treat autonomous improvement as: observe -> diagnose -> search prior knowledge -> change -> validate -> persist lesson -> re-read current authority -> continue.
