# Supplemental OPS learning — transitive Go file-loop reachability (2026-11-01)

Append-only operational learning subordinate to the canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, or human-promotion evidence.

## Material failure

- **symptom:** A top-level `while pending` loop could contain an `if False:` wrapper around the `for file in files` traversal, leaving the exact per-file initializer checker syntactically present but unreachable.
- **evidence:** The earlier AST guard at `d87ce8c0` located the `for file in files` using `ast.walk(while_loop)` and required exactly one matching loop, but did not require that loop to be a direct child of the reviewed `while pending` body. This is a verified source-structure gap, not evidence of a production bypass.
- **rootCauseOrUnknown:** Verified incomplete structural reachability: recursive AST membership does not imply direct execution of a nested loop.
- **failedApproach:** Counting a single syntactically present nested `for` as sufficient proof of per-file guard execution.
- **correction:** [d06066db](https://github.com/m-shogo/memories-project/commit/d06066db2a31b9e527bece55d70727c05d394eab) requires the transitive file loop to be a direct AST child of `while pending`.
- **recurrenceGuard:** A deterministic `if False:` wrapper mutation indents the real `for file in files` and its body, retaining the exact guard call and its argument ordering. The checker must reject the mutation as `unreviewed Upload Route transitive initializer callsite`. Existing source-read, per-file path, pre-loop return/exit and nested-while negatives remain active.
- **retryCondition:** Revisit if the import-closure loop is refactored, a new conditional control-flow bypass is observed, or a reviewed non-MinIO exact-source Focused Go Test execution path becomes available. Do not retry unchanged MinIO HTTP 401 or workflow-write permission blockers.

## Material success

- **outcome:** Exact-source [Autonomous Learning Guard #41282049038](https://github.com/m-shogo/memories-project/actions/runs/41282049038) completed SUCCESS on code HEAD `d06066db2a31b9e527bece55d70727c05d394eab`.
- **evidence:** Job logs show canonical contract PASS, 601 canonical negatives PASS, 52 source-negative workflows / 63 direct Python commands / 204 fixtures, 195 fanout synthetic cases PASS, and the helper ancestor negative step succeeded. Git compare from `7fcbc037` to `d06066db` changed only `scripts/validate-autonomous-learning-system-negative.py` (+12/-2 lines). This is static Python guard CI, not real Focused Go Test execution.
- **whySafe:** Only the existing read-only negative validator changed; the earlier supplemental learning record remained append-only. No workflow, Go service/test, production/recovery authority, evidence, credential, traffic or promotion decision changed.
- **reusableMechanism:** Bind a critical nested traversal to its exact direct AST parent and demonstrate a syntactically present but dead conditional wrapper is rejected.
- **protectedAuthorityCheck:** Canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad` (`productionDecision=NO_GO`) and OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, approved objectives 0) remained unchanged. The one-file code diff confirms no protected registries, recovery evidence, typed eight-domain records, independent review or human promotion were modified.

## Next safe target

Reject unreviewed `continue`, `break`, and zero-exit control transfers preceding the transitive file loop, while retaining the reviewed `if package in visited: continue` branch. Keep actual non-skipped Go test evidence separate from static guard CI.
