# Supplemental OPS learning — Go block comments can spoof focused test discovery (2026-10-30)

Append-only supplemental learning only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy is `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — hidden Go test declarations

- **symptom:** A focused Go test can be enclosed in a balanced `/* ... */` block comment while the old line-anchored Python regex still detects its `func Test...` signature and `t.Fatal` assertion. A pinned `go test -run` selector could then silently execute fewer tests. This is a prospective static test-discovery gap, not an observed production test failure.
- **evidence:** A disposable Go 1.23.2 module with `TestHidden` inside a block comment and `TestVisible` outside showed only `TestVisible` in `go test -list`, while a line-start `grep '^func Test'` returned both names. Both reviewed Upload Route focused test source files currently contain zero `/*` and `*/` tokens.
- **rootCauseOrUnknown:** Verified: lexical regex matching is not Go comment-aware and cannot distinguish commented-out declarations/assertions from compiled code.
- **failedApproach:** Treating raw line-anchored test signatures and assertion substrings as proof of actual Go test discovery.
- **correction:** [`3cedc3f0`](https://github.com/m-shogo/memories-project/commit/3cedc3f047fa0e99d9d12bdfe7aecf2e24f7c7ae) conservatively rejects any block-comment delimiter in the two reviewed focused Go test sources.
- **recurrenceGuard:** The CI-bound negative wraps the first reviewed route test in a balanced block comment while preserving the lexical signature, and requires the exact focused-test rejection. Existing unchanged test sources remain positive controls.
- **retryCondition:** A legitimate block comment in a selected test source requires a reviewed Go-aware test-discovery parser or actual pre-MinIO `go test -list`, bounded negative/positive fixtures, exact-source CI and protected-authority comparison. Do not retry unchanged workflow permission or MinIO HTTP 401.

## Material success

- **outcome:** [Autonomous Learning Guard #41026192777](https://github.com/m-shogo/memories-project/actions/runs/41026192777) completed **SUCCESS** on exact source `3cedc3f047fa0e99d9d12bdfe7aecf2e24f7c7ae`.
- **evidence:** Job logs confirm append-only and contract PASS, 509 canonical fail-closed negatives, 193 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only validation PASS. The new balanced-comment fixture runs within the existing suite and is not separately counted in 509.
- **whySafe:** Only the read-only CI-reachable Python negative validator changed (+25 lines); no Go source, workflow YAML, production evidence, credential, traffic, generation, objective, request, recovery, eight-domain review or promotion authority changed.
- **reusableMechanism:** Pair exact test-selector/source identity with a comment-aware fail-closed boundary and a real-Go discovery control; keep static discoverability distinct from actual integration execution.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and all independent objective/request/evidence/eight-domain/review/promotion gates unsatisfied. Reviewed requests are planning authority only; human promotion is separate.

## Next safe target

Cover Go raw-string test spoofing and selector-whitespace skip bypass; continue the Go-only pre-MinIO CI reachability and complete Go/Python dependency closure audit without workflow edits.
