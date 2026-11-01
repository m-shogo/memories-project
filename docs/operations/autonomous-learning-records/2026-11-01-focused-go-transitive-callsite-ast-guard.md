# Supplemental OPS learning — executable transitive Go callsite binding (2026-11-01)

Append-only operational learning subordinate to the canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure

- **symptom:** A standalone negative test of the new transitive Go initializer checker could remain green if the checker call were deleted, commented out, moved to a dead branch, conditioned on a filename, duplicated, or supplied a different source value inside the real local-import traversal.
- **evidence:** The previous [25cf4dae](https://github.com/m-shogo/memories-project/commit/25cf4daebbf667b2b361c1a8b58da3e2a106ce49) helper had nine isolated rejection fixtures, but no executable test binding its callsite to the actual `while pending` / `for file in files` import-closure loop. This was a static coverage gap, not evidence that the guard was bypassed in production.
- **rootCauseOrUnknown:** Verified test-design gap: unit-level fail-closed behavior does not establish that the production validator invokes the guard for every transitive source.
- **failedApproach:** Treating helper-local negative fixtures and a visually present source call as sufficient CI reachability proof.
- **correction:** [ebe26029](https://github.com/m-shogo/memories-project/commit/ebe26029a7455831aa83d6e962fb1c7489574639) adds an AST check of the existing `prove_upload_route_go_direct_inputs` implementation, requiring exactly one direct invocation inside the transitive file loop, immediately after `file.read_text(encoding="utf-8")`, with the exact path and source arguments.
- **recurrenceGuard:** Seven deterministic mutations (removed, comment-only decoy, conditional, unreachable, wrong source, before read, duplicate call) must fail with `unreviewed Upload Route transitive initializer callsite`. The unchanged real callsite is the positive control. This binds the guard to source structure but does not prove full Go semantic behavior or actual Focused Go Test execution.
- **retryCondition:** Revisit if the import-closure traversal is intentionally refactored, a stronger executable integration fixture is added, the Go toolchain/CI path changes, or a new observed bypass changes the threat model. Do not retry unchanged MinIO HTTP 401 or workflow-write permission blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41280346789](https://github.com/m-shogo/memories-project/actions/runs/41280346789) completed SUCCESS on exact code HEAD `ebe26029a7455831aa83d6e962fb1c7489574639` (2026-11-01 06:22:07 UTC).
- **evidence:** CI job logs show canonical learning contract PASS, 601 fail-closed negatives PASS, 39 supplemental-history fixtures verified, source-negative reachability 52 workflows / 63 direct Python commands / 204 fixtures, fanout 195 synthetic cases PASS, and helper ancestor 1,186 negative mutations PASS. GitHub compare `0bbb6cec..ebe26029` shows only the existing negative validator changed (+85 lines).
- **whySafe:** The change is an AST-only negative guard within the existing read-only validator. No Go service/test, workflow, production or recovery evidence, credential, traffic, promotion authority or existing learning history changed.
- **reusableMechanism:** For guards traversing an imported-source closure, prove both local rejection behavior and the executable traversal callsite with exact AST arguments, direct loop-body placement, ordering and mutation negatives.
- **protectedAuthorityCheck:** Canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, approved objectives 0), and all protected registries remained unchanged. No readiness or promotion gate was met.

## Next safe target

Strengthen the transitive initializer positive/negative fixture to mirror the actual `obslog.eventCodeSet = func() map[...] { ... }()` initializer, then seek a separate authorized pre-MinIO exact-source Go test execution path.
