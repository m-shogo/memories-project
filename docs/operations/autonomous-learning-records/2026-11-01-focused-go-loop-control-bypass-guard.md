# Supplemental OPS learning — focused Go route loop-control bypass guard (2026-11-01)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final-candidate or human promotion evidence.

## Material failure

- **symptom:** A table-driven route test can retain all reviewed cases, expected-value predicates, and failure assertions but execute none of them by jumping over the body with `continue`, `break` or `goto`.
- **evidence:** Source inspection after the first case-coverage guard found it checked table contents and statement presence but did not reject loop-control bypass tokens. An independent local Go 1.23.2 synthetic test confirmed that `if true { continue }` and `if true { break }` can compile and PASS while leaving subsequent `t.Fatal` unreachable. A separate synthetic `goto done` test also compiled and PASSed. These are **synthetic compiler demonstrations**, not exact repository Go-test runs or production failures.
- **rootCauseOrUnknown:** Verified source-only admission gap: lexical presence of the assertion does not prove it is reached when loop control exits before it.
- **failedApproach:** Relying on reviewed table membership, invocation text and non-tautological comparisons without guarding unconditional loop-control jumps.
- **correction:** [`47c1b2fc`](https://github.com/m-shogo/memories-project/commit/47c1b2fcaa0d4f6fe6f187ad06f599072359932b) fail-closes on `continue`, `break` or `goto` in either reviewed environment-free route test body. This conservative lexical check may reject legitimate future control flow until explicitly reviewed.
- **recurrenceGuard:** Three CI-executed source-negative mutations inject a route `continue`, prefilter `break` and `goto` bypass; all must receive the exact `unreviewed Upload Route focused Go test target` rejection. The `goto` mutation is lexical rather than a standalone compilable test; compiler-valid independent Go `goto` behavior was checked separately. No exact-repository Go compilation claim is made.
- **retryCondition:** Revisit on route test-body control-flow changes, Go source guard changes, a need for reviewed loop control, or availability of authorized exact-source pre-MinIO Go test execution. Do not repeat unchanged Quay MinIO HTTP 401 or workflow-write permission attempts.

## Material success

- **outcome:** The existing read-only source validator now rejects three additional loop-control bypass classes without modifying the Go runtime, route fixtures, or workflows.
- **evidence:** [Autonomous Learning Guard #41272508087](https://github.com/m-shogo/memories-project/actions/runs/41272508087) completed **SUCCESS** on exact code HEAD `47c1b2fcaa0d4f6fe6f187ad06f599072359932b`. Job logs show canonical learning contract PASS, 601 fail-closed negatives PASS, 39 supplemental-history fixtures PASS, 195 fanout synthetic cases PASS, helper ancestor reachability and 1,186 negatives PASS, plus append-only and read-only checks. GitHub compare from `533f9c4f` to `47c1b2fc` shows only `scripts/validate-autonomous-learning-system-negative.py` changed (13 added lines, zero deletions).
- **whySafe:** Existing CI-reachable source-negative validation only. No production/recovery authority, evidence, credential, traffic, environment generation, objective, drill, independent review, or human promotion was written.
- **reusableMechanism:** Combine reviewed test-case/statement binding with explicit control-flow bypass negatives; syntactic and synthetic-Go proof must remain separate from actual exact-source package execution.
- **protectedAuthorityCheck:** The one-file code diff and this append-only record leave all ten protected production/recovery authorities untouched. Canonical learning SHA `b809c69d`, mandatory contract SHA `87712ea9`, and production status SHA `b55ee4ad` with `productionDecision=NO_GO` remain unchanged. OPS-P0-007 remains `PREREQUISITES_BLOCKED`; zero registered/semantically eligible generations and no human-approved current objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain coverage, independent review or human promotion are asserted or created.

## Next safe target

Audit constant-false branches that can hide reviewed assertions without using a loop-control token. The known MinIO-first focused Go workflows still do not provide independent pre-MinIO execution proof; do not treat source guard success as Go test PASS.
