# Supplemental OPS learning — raw Go strings can spoof focused test discovery (2026-10-30)

Append-only supplemental learning only. Canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract is `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure — raw-string hidden test

- **symptom:** A focused Go test signature and assertion can appear at the start of lines inside a backtick raw string, making a line-anchored Python regex falsely report the test as discoverable while Go does not compile that declaration.
- **evidence:** A disposable Go 1.23.2 module containing `TestHidden` inside a top-level raw-string variable and `TestVisible` as a real test showed only `TestVisible` in `go test -list`, while a lexical `grep '^func Test'` returned both. The reviewed route test file has zero backticks; the live test file has 35 balanced raw literals and none contain a line-start `func Test` or `t.Fatal/Error/Fail/Skip` assertion call.
- **rootCauseOrUnknown:** Verified: raw-string contents are data, but the prior focused-test guard scanned them as Go declarations and executable assertions.
- **failedApproach:** Assuming a regex declaration or assertion match in raw Go source is executable without separating raw literals.
- **correction:** [`b82a365a`](https://github.com/m-shogo/memories-project/commit/b82a365afe164e1fbdfbbd6903c7fbdfc073b7c9) rejects unbalanced backticks and raw literals containing test-declaration or assertion/skip spellings in the two reviewed focused test sources.
- **recurrenceGuard:** A balanced raw-string negative wraps the first route test while leaving its lexical signature intact and requires exact focused-test rejection. All 35 existing benign live-file raw literals remain positive controls.
- **retryCondition:** Review any legitimate new raw literal containing test-like text using a Go-aware lexer or actual pinned `go test -list`, executable positives/negatives, exact-source CI and protected-authority checks. Do not retry unchanged MinIO, workflow-write, canonical learning transfer or human-promotion blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41026303742](https://github.com/m-shogo/memories-project/actions/runs/41026303742) completed **SUCCESS** on exact source `b82a365afe164e1fbdfbbd6903c7fbdfc073b7c9`.
- **evidence:** Job logs show append-only and learning contract PASS, 509 canonical fail-closed negatives, 193 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only checks PASS. The raw-string fixture runs nested inside the CI-bound suite.
- **whySafe:** Only the existing read-only negative validator changed (+26 lines); no Go production/test source, workflow YAML, credentials, traffic, evidence, recovery, generation, objective, typed eight-domain review or human promotion authority changed.
- **reusableMechanism:** Separate raw-string data from test-discovery and assertion identity; use real Go discovery to demonstrate the false-green condition while keeping runtime integration success unclaimed.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, human-approved objective, executable reviewed request, request-bound evidence, typed eight-domain coverage, final candidate and human promotion absent.

## Next safe target

Guard Go `t.Skip` selector whitespace/newline forms and continue pre-MinIO Go-only CI reachability plus complete transitive Go/Python input closure. Static source guards are not proof that integration tests ran.
