# Supplemental OPS learning — transitive Go pre-closure zero-exit bypass (2026-11-01)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, or human-promotion evidence.

## Material failure

- **symptom:** A source-visible, top-level `while pending` import traversal and exact per-file initializer call could coexist with an earlier `raise SystemExit(0)`, `sys.exit(0)`, `os._exit(0)`, or builtin `exit(0)`. The source-structure guard would previously accept the traversal although the Python negative validator could terminate successfully before executing it.
- **evidence:** Read-only inspection of `require_reviewed_upload_route_transitive_callsite` at code HEAD `723eaee10efa320517aaf4ffff860c8fb9f14c08` showed its pre-loop recursive AST predicate rejected `ast.Return` only. The existing transitive callsite negative suite had early-return and unreachable-wrapper cases but no zero-exit cases. This is a verified static guard gap, not evidence of a production bypass.
- **rootCauseOrUnknown:** Verified incomplete control-flow classification: pre-loop successful process termination is distinct from a Python `return` AST node.
- **failedApproach:** Treating a direct top-level loop plus pre-loop return rejection as sufficient proof that the transitive Go initializer guard cannot be skipped.
- **correction:** [d87ce8c0](https://github.com/m-shogo/memories-project/commit/d87ce8c080be088149853aa5d58b91a8d003bc00) extends the existing read-only AST predicate to reject pre-loop `SystemExit` raises, `sys.exit`, `os._exit`, and builtin `exit`/`quit`, including conditional occurrences. Deferred nested function/class bodies remain excluded.
- **recurrenceGuard:** Five deterministic source mutations exercise unconditional and conditional `SystemExit(0)`, `sys.exit(0)`, `os._exit(0)`, and builtin `exit(0)` before the transitive loop; each must fail with `unreviewed Upload Route transitive initializer callsite`. Existing early-return, nested-loop, per-file call and source-order negatives remain active.
- **retryCondition:** Revisit if the Python import traversal is refactored, a verified new pre-loop termination form or alias bypass is observed, or an authorized exact-source non-skipped Go test execution path becomes available. Do not retry unchanged MinIO HTTP 401 or workflow-write permission blockers.

## Material success

- **outcome:** Exact-source [Autonomous Learning Guard #41281739798](https://github.com/m-shogo/memories-project/actions/runs/41281739798) completed SUCCESS for code HEAD `d87ce8c080be088149853aa5d58b91a8d003bc00`.
- **evidence:** Job logs show canonical contract PASS, 601 canonical fail-closed negatives PASS, 52 source-negative workflows / 63 direct Python commands / 204 reachability fixtures, 195 fanout synthetic cases PASS, 1,186 helper-ancestor mutations PASS, append-only PASS, and clean/read-only source checks PASS. Git compare from `723eaee1` to `d87ce8c0` changed only `scripts/validate-autonomous-learning-system-negative.py` (+30/-4 lines). The new tests are static AST source negatives; they are not actual repository Focused Go Test execution.
- **whySafe:** Only the existing read-only negative validator changed. No Go runtime/test source, workflow, protected production/recovery authority, credential, traffic, evidence, promotion decision or prior learning record was modified.
- **reusableMechanism:** Prove critical loop reachability against successful process termination as well as ordinary return and unreachable nesting; require exact-source CI and a clean-source post-check.
- **protectedAuthorityCheck:** Canonical learning blob `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, approved objectives 0), and other protected authorities did not change in the one-file code commit. The reviewed request/evidence/eight-domain/independent-review/human-promotion gates remain separate and unmet.

## Next safe target

Prove the `for file in files` loop itself is a direct executable child of `while pending`, not a dead conditional wrapper. Independently pursue authorized pre-MinIO non-skipped Focused Go Test evidence without treating static CI as runtime proof.
