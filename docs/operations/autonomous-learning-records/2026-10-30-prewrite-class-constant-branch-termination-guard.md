# Supplemental OPS learning — eager class and literal-boolean branch termination (2026-10-30)

Append-only supplemental learning only. Mandatory `contracts/operations/autonomous-learning-system.json` and canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remain unchanged. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure — prospective nested eager prewrite termination

- **symptom:** A prewrite candidate can preserve an exact top-level `__main__` guard yet terminate first inside a class body or a statically true conditional branch, e.g. `class Helper: raise SystemExit(0)`, `if True: raise SystemExit(0)`, or the `else` branch of `if False`.
- **evidence:** At `95b431425a5d7fed6086e55b137c9b76b6f7cc00`, the direct-termination guard examined only top-level `ast.Raise` and `ast.Expr(Call)`. The existing main-binding shadow visitor recursed into class bodies and `if` statements but did not classify these direct exits. Python AST parsing/compilation accepts the forms. This is a prospective static reachability gap, not observed live CI or production termination.
- **rootCauseOrUnknown:** Verified: the source-order terminator classifier did not model eager class bodies or literal-boolean conditional branch selection.
- **failedApproach:** Treating direct top-level statements as exhaustive for pre-guard eager execution.
- **correction:** [`73704455`](https://github.com/m-shogo/memories-project/commit/737044555f885ce3e6e876d5c0aec87764583f28) introduces a bounded recursive `eager_direct_termination` classifier for direct `Raise`/exit calls, eager class bodies and exactly selected `if True`/`if False` branches. Deferred methods/functions remain excluded. This does not claim full symbolic control flow, exception handling or reflective alias closure.
- **recurrenceGuard:** Four executable exact-diagnostic `entry guard unreachable` negatives cover true-branch raise, false-branch else exit, class-body raise and class-body true-branch abort. Three positive controls preserve a false-branch raise, a class false-branch raise and a deferred class-method raise.
- **retryCondition:** Expand the reviewed execution model only after proving additional source-order semantics, preserving deferred/untaken positives, running exact-source CI and comparing protected authority. Do not retry unchanged external MinIO, workflow-write, canonical-learning transfer or human promotion blockers.

## Material success

- **outcome:** Exact-source [Autonomous Learning Guard #41055728590](https://github.com/m-shogo/memories-project/actions/runs/41055728590) completed **SUCCESS** on `737044555f885ce3e6e876d5c0aec87764583f28`.
- **evidence:** GitHub Actions job log confirms append-only PASS, learning contract PASS, **547 canonical fail-closed cases**, **195 fanout synthetic cases**, entry-document PASS, **1,186 helper-ancestor negatives**, and clean/read-only success. The seven new prewrite self-test cases are nested and not separately reflected in the printed 547.
- **whySafe:** Only the CI-reachable read-only Python validator changed (+34/-8 lines); no fixture payload was executed, no workflow YAML, Go service, credential, traffic, readiness, production evidence, recovery generation/objective, drill, typed eight-domain review or human promotion authority was written.
- **reusableMechanism:** Model limited eager execution through class bodies and literal-boolean branch selection while preserving deferred function/method and untaken-branch positives.
- **protectedAuthorityCheck:** All ten protected blobs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, recovery objective registry `f4d74f33`, drill request registry `acebcd02`, generation recovery evidence registry `ae7e57ef`, typed non-resurrection registry `26bb1cc7`, human promotion review registry `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, and all separate evidence/review/human promotion gates remain unsatisfied.

## Next safe target

Audit bounded unconditional `try/finally` and direct `with` class/module execution-order boundaries, or prioritize the known Go-only pre-MinIO CI trigger reachability and complete Go/Python transitive dependency closure. No workflow YAML change without permission and full reviewed authority.
