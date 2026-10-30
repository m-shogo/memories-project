# Supplemental OPS learning — eager assignment RHS termination (2026-10-30)

Append-only supplemental operational learning only. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure / prospective direct RHS termination

- **symptom:** A prewrite candidate can preserve the exact canonical main guard but exit earlier through an eagerly evaluated assignment RHS: `result = sys.exit(0)`, `result: object = os.abort()` or `result += os._exit(0)`.
- **evidence:** At `61f04fb894844d59197152e17200080d0282dbf1`, the bounded `eager_direct_termination` source-order check returned false for `ast.Assign`, `ast.AnnAssign` and `ast.AugAssign` regardless of direct RHS calls. The separate main-binding visitor did not reject assignments to unrelated variables. No production incident or executed CI bypass was observed.
- **rootCauseOrUnknown:** Verified: direct process termination nested as an assignment RHS was outside the reviewed eager-termination classifier. Arbitrary nested expressions, aliases, evaluation order and symbolic reachability remain unproven.
- **failedApproach:** Treating a direct top-level exit expression check as covering all eager statement contexts.
- **correction:** [`999fb2e7`](https://github.com/m-shogo/memories-project/commit/999fb2e79ca99b9133c109915aba542bbc1a4674) classifies a direct `Call` RHS in assignment, annotated assignment and augmented assignment using the existing direct terminator check. Three exact-diagnostic negatives cover `sys.exit`, `os.abort` and `os._exit`; three positives preserve a benign assignment, annotation without initializer and deferred assigned lambda.
- **recurrenceGuard:** The CI-reachable prewrite self-test enforces three negative and three safe positive AST fixtures without executing candidate code.
- **retryCondition:** Revisit only with changed reviewed RHS semantics or a demonstrated false positive, paired fixtures, exact-source CI and protected-authority verification. Do not retry unchanged Quay MinIO 401, workflow-write permission, large canonical learning transport or human promotion blockers.

## Material success and authority

- **outcome:** [Autonomous Learning Guard #41063752824](https://github.com/m-shogo/memories-project/actions/runs/41063752824) completed **SUCCESS** on exact source `999fb2e79ca99b9133c109915aba542bbc1a4674`.
- **evidence:** GitHub Actions validate job `124089739555` completed SUCCESS; logs show append-only PASS, learning contract PASS, **547 canonical fail-closed negatives**, **195 fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS, clean source and read-only PASS. Six new nested prewrite fixtures are not separately counted in the printed 547.
- **whySafe:** Only the CI-reachable read-only Python validator changed (+18 lines); no workflow YAML, Go service, production evidence, credentials, traffic, recovery generation/objective/drill/eight-domain authority, independent review or promotion.
- **reusableMechanism:** Reuse the exact direct-termination callee classifier across multiple eagerly evaluated AST statement forms; retain deferred/initializer-free positive controls and exact-source CI.
- **protectedAuthorityCheck:** Ten protected blobs unchanged: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and all separate evidence/review/human gates unmet.

## Next safe target

Review eagerly evaluated `if`/`while` test, `for` iterable and `with` context expressions containing direct termination. Go-only pre-MinIO Focused Upload Route Test and complete Go/Python transitive source/trigger closure remain unproven; no workflow YAML change without permission.
