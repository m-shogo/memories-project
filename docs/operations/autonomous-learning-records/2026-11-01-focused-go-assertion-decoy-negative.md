# Supplemental OPS learning — Go test assertion decoy rejection (2026-11-01)

Append-only operational learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and the mandatory `contracts/operations/autonomous-learning-system.json`. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, recovery-objective, generation, typed eight-domain, independent-review or promotion evidence.

## Material failure

- **symptom:** The reviewed Upload Route focused-Go-test source guard could accept a test whose only apparent failure assertion had been converted into a line comment or a quoted string.
- **evidence:** At code HEAD `3274bc3f`, the guard searched the whole test body for an unanchored `t.Fatal`-family expression. The real `TestRoutePrefilterPreservesKnownAndRejectsUnknownShapes` has one `t.Fatalf` line. Replacing it with `// t.Fatalf(...)` or `t.Log("t.Fatalf(")` left the previous unanchored regex satisfied while no executable failure assertion remained. This was a verified static admission gap, not a witnessed production failure.
- **rootCauseOrUnknown:** Verified false-positive lexical assertion detection: comment/string text was treated as executable Go assertion presence.
- **failedApproach:** Requiring any `t.Fatal` substring after a reviewed test declaration; the earlier early-return hardening did not resolve decoy assertion text.
- **correction:** [`325fe7ec`](https://github.com/m-shogo/memories-project/commit/325fe7ec748146a210107512d4db5c4071ae8d70) requires an assertion call at the start of a Go source line (allowing indentation), excluding single-line comments and quoted string decoys under the existing fail-closed block-comment/raw-string restrictions.
- **recurrenceGuard:** The CI-reachable `prove_upload_route_focused_go_test_negatives` now injects both commented and quoted decoy assertions and requires the exact `unreviewed Upload Route focused Go test target` failure. Post-write static controls confirmed both decoys rejected and all four original reviewed Go test bodies still admitted. This is not a Go compiler or Go test execution proof.
- **retryCondition:** Revalidate on test source changes, Go lexical constructs, reviewed test selector changes, or validator changes. Any legitimate same-line `if ... { t.Fatal(...) }` assertion requires explicit review rather than silently relaxing the anchored guard.

## Material success

- **outcome:** Existing executable negative validation now rejects two additional false-positive assertion classes, independently of the earlier return-bypass guard.
- **evidence:** [`325fe7ec`](https://github.com/m-shogo/memories-project/commit/325fe7ec748146a210107512d4db5c4071ae8d70) modifies only `scripts/validate-autonomous-learning-system-negative.py`. Static source checks show the reviewed route and live test bodies have anchored `t.Fatal`-family assertions, no `return` tokens and no direct `Skip` forms. Exact-source CI and Go execution outcomes remain unverified in this record.
- **whySafe:** No Go implementation, workflow, production authority, evidence, credential, traffic, environment generation, recovery objective, or promotion was changed. The guard is read-only and already part of the canonical learning negative CI path.
- **reusableMechanism:** Treat syntactic presence as insufficient for test-execution evidence; require source-level anti-decoy negatives and separately obtain real test execution with explicit non-skip confirmation.
- **protectedAuthorityCheck:** The only code path changed is the negative validator. Canonical learning and mandatory contract blobs remain `b809c69d` and `87712ea9`, and the production operability status remains `b55ee4ad` with `productionDecision=NO_GO`. All ten protected authorities remain untouched by this single-path code change; existing learning records were not edited. OPS-P0-007's separate generation, human-approved objective, executable reviewed request, request-bound evidence, typed eight-domain coverage, independent review and human promotion gates remain mandatory and unsatisfied by learning.

## Scoped blocker / next target

The Upload Route publisher and PR workflows still start Quay MinIO before Go tests. Known registry HTTP 401 and workflow-write permission conditions have not changed and must not be retried unchanged. Next obtain a real pre-MinIO, exact-source focused Go test result through an authorized independent execution path, or continue independent negative hardening without claiming Go runtime coverage.
