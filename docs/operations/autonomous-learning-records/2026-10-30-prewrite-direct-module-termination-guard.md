# Supplemental OPS learning — direct prewrite module termination before main guard (2026-10-30)

Append-only supplemental learning under `contracts/operations/autonomous-learning-system.json`; canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains unchanged. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure A — prospective unreachable prewrite entry guard

- **symptom:** A candidate can retain the exact canonical `if __name__ == "__main__": raise SystemExit(main())` AST while an earlier unconditional module-level `raise SystemExit(0)`, `sys.exit(0)`, `os.abort()`, `os._exit(0)` or equivalent direct exit prevents the guard from executing.
- **evidence:** Source inspection at `217f71dd1c35f43ec9cb705837fa3ab76d284f13` found exact entry-guard AST counting but no source-order terminator check. Local Python AST parsing and compilation admitted direct module `Raise` and `Expr(Call)` before the guard. This is a static reachability gap, not an observed production or CI compromise.
- **rootCauseOrUnknown:** Verified: exact guard identity was checked independently of preceding unconditional termination.
- **failedApproach:** Treating one syntactically exact guard node as proof of live execution.
- **correction:** [`154f8cd8`](https://github.com/m-shogo/memories-project/commit/154f8cd8f01fdd0b422d81087d43614fa5a5491b) adds bounded source-order rejection of direct top-level `Raise` and explicit `sys.exit`, `os.abort/_exit`, `builtins.exit/quit`, and bare exit calls before the canonical guard. This does not prove arbitrary nested control-flow or reflective callable closure.
- **recurrenceGuard:** Seven exact-diagnostic `entry guard unreachable` negatives, plus deferred function/lambda exit and constant-false conditional exit positive controls.
- **retryCondition:** Revisit a legitimate direct pre-guard terminator only with explicit execution-order review, exact-source CI and paired positive/negative fixtures. Keep separate real production gates unchanged.

## Material failure B — positive fixture placed before the guard

- **symptom:** Initial [CI #41055115089](https://github.com/m-shogo/memories-project/actions/runs/41055115089) on `154f8cd8` **FAILED** during the learning contract self-test with `AUTONOMOUS LEARNING VALIDATION FAILED: prewrite candidate entry guard unreachable`.
- **evidence:** The purported `exit after entry guard` positive was passed to a fixture helper that always inserts source by `baseline.replace('if __name__', insertion + 'if __name__')`, placing `sys.exit(0)` before the guard. The new rejection was correct; the fixture expectation was wrong.
- **rootCauseOrUnknown:** Verified fixture-placement mismatch, not a false positive in the direct-termination guard.
- **failedApproach:** Labelling a fixture `after entry guard` without checking the shared insertion mechanism.
- **correction:** [`3c8b8680`](https://github.com/m-shogo/memories-project/commit/3c8b8680089a058ceec6029b8ac3141aed00aeb9) replaces it with a genuinely deferred lambda exit positive control, preserving the strict guard.
- **recurrenceGuard:** The same executable self-test now requires deferred function/lambda and unreachable conditional positives while rejecting direct top-level termination. Future positive fixtures must be reviewed against their insertion site, not just their label.
- **retryCondition:** Do not restore a pre-guard direct-exit positive without changed reviewed execution-order preconditions; run exact-source CI and verify diagnostics after any fixture insertion change.

## Material success

- **outcome:** Corrected exact-source [Autonomous Learning Guard #41055139514](https://github.com/m-shogo/memories-project/actions/runs/41055139514) completed **SUCCESS** on `3c8b8680089a058ceec6029b8ac3141aed00aeb9`.
- **evidence:** GitHub Actions job log shows append-only PASS, learning contract PASS, **547 canonical fail-closed cases**, **195 prewrite fanout synthetic cases**, entry-document PASS, **1,186 helper-ancestor negatives**, and clean/read-only job success. New prewrite fixtures are nested and are not separately reflected in the printed 547.
- **whySafe:** Two commits modified only the CI-reachable read-only Python validator; no workflow YAML, Go service, credentials, traffic, readiness, evidence, generation, objective, reviewed request, eight-domain coverage or human promotion authority changed. Candidate source is parsed/compiled, not executed.
- **reusableMechanism:** Bind exact entry-guard AST identity to a bounded source-order termination check, and validate both rejection and genuinely deferred positive behavior at the actual insertion point.
- **protectedAuthorityCheck:** All ten protected blobs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objective registry `f4d74f33`, drill request registry `acebcd02`, recovery evidence registry `ae7e57ef`, typed non-resurrection registry `26bb1cc7`, human promotion review registry `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and all human/evidence gates remain unsatisfied.

## Next safe target

Review class-body and constant-true conditional termination before the prewrite entry guard with bounded execution-order tests. Independently maintain the known Go-only pre-MinIO CI and Go/Python transitive dependency closure blockers without retrying unchanged MinIO 401, workflow-write permissions, canonical learning transport or human approvals.
