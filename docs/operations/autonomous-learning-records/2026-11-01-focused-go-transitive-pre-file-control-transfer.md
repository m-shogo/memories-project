# Supplemental OPS learning — transitive Go pre-file control-transfer guard (2026-11-01)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, or human-promotion gates.

## Material failure

- **symptom:** Even after the transitive `for file in files` loop was required to be a direct `while pending` child, an unconditional/conditional `continue`, `break`, or zero-exit could be inserted before the file loop. The exact per-file guard would remain syntactically present yet be skipped.
- **evidence:** Read-only AST inspection of code HEAD `d06066db2a31b9e527bece55d70727c05d394eab` found no check of control transfers in `while pending` statements preceding the direct file loop. The legitimate `if package in visited: continue` must remain permitted. This was a static source-guard gap, not an observed production bypass.
- **rootCauseOrUnknown:** Verified incomplete control-flow binding: direct AST parenthood of the file loop does not prove that earlier sibling statements cannot skip it.
- **failedApproach:** Treating direct nested-loop placement as sufficient proof of unconditional per-package file scanning.
- **correction:** [38999dd9](https://github.com/m-shogo/memories-project/commit/38999dd9930e1b6a169dfb486b4d546b60471285) requires exactly one AST-equivalent reviewed duplicate-package skip, rejects any other pre-file `continue`/`break`/`return` or previously guarded successful process termination, and leaves the existing per-file exact callsite checks in place.
- **recurrenceGuard:** Five deterministic mutations exercise unconditional pre-file `continue`, conditional `break`, `raise SystemExit(0)`, `sys.exit(0)`, and a shadowed `if True: continue` replacing the reviewed skip. All must fail with `unreviewed Upload Route transitive initializer callsite`. The unchanged real traversal is the positive control.
- **retryCondition:** Revisit if the reviewed duplicate-package control flow changes, a new verified bypass is found, or an authorized non-MinIO exact-source Focused Go Test execution path becomes available. Do not retry unchanged MinIO HTTP 401 or workflow-write permission blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41282306728](https://github.com/m-shogo/memories-project/actions/runs/41282306728) completed SUCCESS on exact code HEAD `38999dd9930e1b6a169dfb486b4d546b60471285`.
- **evidence:** Job logs show canonical learning contract PASS, 601 canonical fail-closed negatives PASS, 52 source-negative workflows / 63 direct Python commands / 204 fixtures, 195 fanout synthetic cases PASS, helper-ancestor 1,186 mutations PASS, append-only PASS, and clean/read-only checks PASS. Git compare from `2271403d` to `38999dd9` changed only `scripts/validate-autonomous-learning-system-negative.py` (+29/-1 lines). This does not establish actual non-skipped Go test execution.
- **whySafe:** The existing read-only Python negative validator was the sole code target. No workflow, Go runtime/test, production/recovery authority, generation/objective, drill/evidence, credential, traffic, readiness or promotion authority changed; prior learning records remain append-only.
- **reusableMechanism:** Security-critical loops require both direct AST reachability and fail-closed control-transfer analysis of their preceding sibling statements, with an exact reviewed exception for legitimate duplicate-work skips.
- **protectedAuthorityCheck:** Canonical learning blob `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, approved objectives 0), and six production-equivalent/recovery/drill/non-resurrection/promotion registries remain unchanged and empty. Human promotion remains separate and non-automatic.

## Next safe target

Audit direct import-closure file discovery and file-loop input membership for bypassable source ordering, without duplicating the existing 109-input/digest authority. Seek an authorized actual pre-MinIO Go test path; static Python guard CI cannot substitute for it.
