# Supplemental OPS learning — compiler-valid focused Go goto negative (2026-11-01)

Append-only learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery-objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final-candidate or promotion evidence.

## Material failure

- **symptom:** The previous focused-Go `goto` source-negative fixture inserted `goto skipCases` without defining the target label. The source validator rejected it, but the mutation alone was not a compiler-valid example of a test that silently skips assertions.
- **evidence:** The previous `reject("route loop goto bypass", ...)` mutation contained an unresolved `skipCases` label; this limitation was explicitly recorded in `2026-11-01-focused-go-loop-control-bypass-guard.md`. An independent local Go 1.23.2 synthetic test with a `goto skipCases` label after a `t.Run` call compiled and PASSed while bypassing the assertion. This synthetic test is not an exact repository package test.
- **rootCauseOrUnknown:** Verified fixture construction defect: lexical mutation rejection was mistaken for a realistic compiler-valid Go bypass without the necessary label.
- **failedApproach:** A one-replacement `goto` fixture with an unresolved label. This could prove only lexical detection, not a valid bypass shape.
- **correction:** [`e25914ff`](https://github.com/m-shogo/memories-project/commit/e25914ff1bc7b9f9c0580d8793544fa2bbaa84a8) replaces it with a two-anchor source mutation: jump before `t.Run`, define `skipCases:` after the assertion, and use `_ = test` as a valid target statement within the same loop.
- **recurrenceGuard:** The existing CI-reachable negative validator now requires both exact source anchors, constructs the labelled bypass, and demands the canonical `unreviewed Upload Route focused Go test target` rejection. A standalone Go 1.23.2 test separately confirmed the control-flow pattern compiles and PASSes. CI itself does not compile the mutated repository fixture; do not claim that additional proof.
- **retryCondition:** Revisit if Go test layout, loop source anchors, Go compiler semantics, or independent Go-test execution capability changes. Do not retry unchanged MinIO HTTP 401 or workflow-write permission blockers.

## Material success

- **outcome:** The `goto` regression fixture now models a Go-compilable assertion bypass rather than a syntactically incomplete jump, without weakening the production source guard.
- **evidence:** [Autonomous Learning Guard #41273139735](https://github.com/m-shogo/memories-project/actions/runs/41273139735) completed **SUCCESS** on exact code HEAD `e25914ff1bc7b9f9c0580d8793544fa2bbaa84a8`. Job logs show canonical learning contract PASS, 601 fail-closed negatives PASS, 39 supplemental-history fixtures PASS, 195 fanout synthetic cases PASS, helper ancestor reachability and 1,186 negatives PASS, append-only and read-only checks. GitHub compare from `ebe7467d` to `e25914ff` shows only the existing negative validator changed (21 additions, 3 deletions).
- **whySafe:** Only a read-only CI negative fixture changed. No reviewed Go implementation/test source, workflow, protected authority, production evidence, credentials, traffic or human promotion was modified.
- **reusableMechanism:** For source-negative tests of executable language bypasses, use compiler-valid control-flow shapes and retain separate evidence boundaries: local synthetic compile proof, exact-source static CI guard, and unverified actual package test execution.
- **protectedAuthorityCheck:** All ten protected authority blobs are unchanged. Canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad` (`productionDecision=NO_GO`) and OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`) remain intact. Registered/eligible generations, approved objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records, final candidates, independent review and human promotion remain absent and cannot be supplied by learning.

## Next safe target

Establish actual exact-source, non-skipped pre-MinIO focused Go execution only through a permitted independent runner or a genuine workflow-permission change. Continue read-only negative-fixture audits in the meantime; do not treat static CI SUCCESS as Go runtime test success.
