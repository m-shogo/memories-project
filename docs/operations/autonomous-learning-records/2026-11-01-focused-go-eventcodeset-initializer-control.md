# Supplemental OPS learning — real eventCodeSet-style Go initializer control (2026-11-01)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent-review, final-candidate, or human-promotion evidence.

## Material failure

- **symptom:** The transitive Go initializer guard's original benign `obslog.eventCodeSet` fixture used a static map literal. The actual reviewed `services/import-api/internal/obslog/codes.go` initializes `eventCodeSet` with an immediately invoked `func() map[EventCode]struct{} { ... }()`. The positive fixture did not exercise this real initializer shape.
- **evidence:** Read-only inspection of `obslog/codes.go` verified the invoked function and its bounded `AllEventCodes` map construction. Isolated Go 1.23.2 synthetic packages confirmed that a benign immediately invoked map builder allows the deliberately failing test to execute (exit code 1), while injecting `os.Exit(0)` into the same initializer makes `go test` return code 0 without running that test. Synthetic evidence only, not actual repository Go test success.
- **rootCauseOrUnknown:** Verified fixture representativeness gap, not a proven production defect: the original static-map positive did not represent the existing function-valued package initialization mechanism.
- **failedApproach:** Treating a map-literal positive fixture and generic `var _ = func(){os.Exit(0)}()` negative as sufficient coverage of the real `eventCodeSet` initializer pattern.
- **correction:** [f7941226](https://github.com/m-shogo/memories-project/commit/f79412269aa06f3b2468d7833e90898c4e10fa11) adds a function-valued map-builder positive and an `eventCodeSet`-shaped `os.Exit(0)` negative to the existing CI-reachable transitive package guard, and points the fixture to the actual `obslog/codes.go` path.
- **recurrenceGuard:** The positive preserves legitimate immediate function invocation; the negative rejects process termination inside the same initializer form. Both are checked through the existing `require_reviewed_upload_route_transitive_package_init` helper and its AST-bound import-closure callsite. No new production authority was introduced.
- **retryCondition:** Revisit if `eventCodeSet` source changes, a compiler-valid bypass is observed, the reviewed local Go closure changes, or an authorized Go test runner becomes available. Do not retry unchanged MinIO HTTP 401 or workflow permission blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41280615214](https://github.com/m-shogo/memories-project/actions/runs/41280615214) completed SUCCESS on exact code HEAD `f79412269aa06f3b2468d7833e90898c4e10fa11` at 2026-11-01 06:26:49 UTC.
- **evidence:** CI job logs show canonical learning contract PASS, 601 fail-closed negatives PASS, 39 supplemental-history fixtures verified, source-negative reachability 52 workflows / 63 direct Python commands / 204 fixtures, fanout 195 synthetic cases PASS, and helper ancestor 1,186 fail-closed mutations PASS. GitHub compare `27089653..f7941226` shows only the existing negative validator changed (+7/-1 lines).
- **whySafe:** No Go implementation/test, workflow, production or recovery evidence, credentials, traffic, readiness, promotion authority or prior learning history changed. This is a read-only synthetic validator improvement; no real repository Focused Go Test success is claimed.
- **reusableMechanism:** Positive controls must mirror the reviewed source's execution mechanism, not merely its final data shape. Pair the legitimate initializer with an otherwise identical early-exit negative.
- **protectedAuthorityCheck:** Canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`, generations 0/0, approved objective 0) and all protected evidence/review registries remained unchanged. No production gate was satisfied or relaxed.

## Read-only next-target discovery

`.github/workflows/live-object-stage-source-negative.yml` already has a pre-MinIO Go 1.23.x setup and exact-source test command, but it selects `TestLiveObjectStageLabelClosedVocabulary|TestAtomicLocalLoadResultWriter`, not the two Upload Route Authority tests. The Upload Route workflows still start MinIO before their Go test step. Do not repurpose the reviewed test names or modify workflow authority without an authorized, separately validated change. Next safe target: identify a permitted exact-source route-test runner and prove selected tests actually execute; otherwise continue independent source-negative hardening.
