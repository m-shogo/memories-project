# Supplemental OPS learning — transitive Go pre-guard control-flow skip (2026-11-01)

Append-only operational learning subordinate to the canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final-candidate or human-promotion evidence.

## Material failure

- **symptom:** The AST callsite guard required the transitive initializer check to appear immediately after `source = file.read_text(...)`, but could still accept a `continue`, `break`, `return`, conditional skip, or replacement of the reviewed path check inserted before the read. The guarded call would remain syntactically present but could be bypassed at runtime.
- **evidence:** Read-only AST review of the existing `for file in files` import-closure loop showed the prior guard compared only the final read/call pair, not the complete preceding executable statement prefix. This is a source-guard gap, not an observed production bypass.
- **rootCauseOrUnknown:** Verified incomplete control-flow binding: the AST check did not constrain the statements preceding the reviewed source read and initializer guard.
- **failedApproach:** Treating immediate adjacency of read and guard as sufficient to establish unconditional per-file execution.
- **correction:** [b766ca96](https://github.com/m-shogo/memories-project/commit/b766ca964fb3a88b2d2a00233c5884b735f5b2a5) requires the exact three-statement prefix: `require_unaliased_go_path(source_root, file)`, `inputs.add(file.relative_to(source_root).as_posix())`, and `source = file.read_text(encoding="utf-8")`, followed directly by the exact guard call.
- **recurrenceGuard:** Five new AST negative mutations insert unconditional/conditional `continue`, `break`, `return`, or remove the path check; all must reject with `unreviewed Upload Route transitive initializer callsite`. Existing removed/comment/conditional/dead/wrong-source/reordered/duplicate-call negatives remain. This is structural, not full dynamic control-flow proof.
- **retryCondition:** Revisit if the reviewed loop prefix changes, an earlier return/conditional enclosing the entire loop is found, the Go import closure is refactored, or a stronger executable integration test is available. Do not retry unchanged MinIO HTTP 401 or workflow permission blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41280966559](https://github.com/m-shogo/memories-project/actions/runs/41280966559) completed SUCCESS on exact code HEAD `b766ca964fb3a88b2d2a00233c5884b735f5b2a5` at 2026-11-01 06:33:08 UTC.
- **evidence:** CI logs show canonical learning contract PASS, 601 fail-closed negatives PASS, 39 supplemental-history fixtures verified, source-negative reachability 52 workflows / 63 Python commands / 204 fixtures, fanout 195 synthetic cases PASS, and helper ancestor 1,186 fail-closed mutations PASS. GitHub compare `197e049b..b766ca96` shows only the existing negative validator modified (+29/-4 lines).
- **whySafe:** Only the existing read-only negative validator changed. No Go service/test, workflow, production or recovery evidence, credential, traffic, readiness, promotion authority or previous learning history changed.
- **reusableMechanism:** Bind a security-critical loop guard to an exact executable AST prefix, not merely the presence or adjacency of its call, and exercise plausible control-flow skips as negative mutations.
- **protectedAuthorityCheck:** Canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`, generations 0/0, approved objectives 0), and all protected registries remained unchanged. No readiness or promotion gate was satisfied.

## Next safe target

Audit top-level early returns or enclosing dead branches before the transitive `while pending` loop. Keep the guard fail-closed and preserve the separate production-promotion authority. A non-MinIO, non-skipped exact-source Route Authority Go test remains unproven.
