# Supplemental OPS learning — synthetic sustained-soak postrebase guard (2026-11-02)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This fixture is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Scoped source risk / executable independent correction

- **symptom:** The write-capable `.github/workflows/sustained-local-soak.yml` run-result step checks source-critical paths before a later `git pull --rebase origin so`, leaving a possible unreviewed source change between those operations. No actual stale publication or production incident was observed.
- **evidence:** Workflow blob `610afce0` contains a critical-path diff against `SOURCE_SHA`, then `git reset --hard origin/so`, source-bound result validation, a result commit, `git pull --rebase origin so` and `git push origin HEAD:so` without an obvious post-rebase critical-path check in that step.
- **rootCauseOrUnknown:** The shell ordering and potential race window are source-observed; actual exploitability, allowed append-only semantics and production impact remain explicitly unknown.
- **failedApproach:** Assuming the earlier source-critical diff protects a later rebase against a concurrent critical-source update.
- **correction:** [`35bb00d2`](https://github.com/m-shogo/memories-project/commit/35bb00d2cbbe8c7bcaf3dca4990571cd71fd67ac) adds an independent synthetic local Git race fixture in the read-only autonomous learning negative suite. It advances the remote after the precheck, rebases a source-bound result, then proves a post-rebase comparison of original `SOURCE_SHA` to the final result commit's parent rejects a critical change but permits a noncritical change. The fixture never pushes the rebased result or invokes the publisher.
- **recurrenceGuard:** The test pins the source workflow's reviewed check/reset/rebase/push ordering and requires both critical and noncritical synthetic branches to behave deterministically.
- **retryCondition:** Change the write-capable workflow only after a separately reviewed, exact-source, publisher-independent negative CI path and a human-reviewed decision on allowed append-only source drift.

## Material fixture implementation failure / correction

- **symptom:** The generated synthetic Python fixture initially contained double-escaped newline sequences in file payloads. This could make test files contain literal backslash-n rather than LF.
- **evidence:** Source re-read after `35bb00d2` showed `"v1\\\\n"` and `"source=" + source_sha + "\\\\n"` in the Python source. The code had not been accepted as a verified CI success.
- **rootCauseOrUnknown:** Verified cross-language escaping mistake in the generated fixture; no production effect.
- **failedApproach:** Trusting intended Python string semantics without inspecting generated source bytes.
- **correction:** [`668cb068`](https://github.com/m-shogo/memories-project/commit/668cb068c9d5029ccb81395f765bef1cd380cd3b) uses actual LF-terminated Python string payloads and adds exact-byte baseline and result newline assertions.
- **recurrenceGuard:** Fixture fails closed if its files are not LF-terminated. A local isolated two-branch Git prototype passed before committing; exact-source CI for the corrected code remains pending at record time.
- **retryCondition:** Revisit only if the fixture byte grammar, Git behavior or CI results change; do not reuse the double-escaped source-generation pattern.

## Observed safe progress

- **outcome:** The two code commits and their single-file diffs were verified on `so`; the corrected exact-source workflow result was not yet available when this record was written.
- **evidence:** GitHub source re-read confirmed the LF byte assertions, local Git-only remote and no final writer push. GitHub diff shows only `scripts/validate-autonomous-learning-system-negative.py` modified.
- **whySafe:** All fixture repositories are temporary local Git repositories. No actual publisher, production evidence, credentials, traffic, readiness or promotion authority is modified.
- **reusableMechanism:** A deterministic concurrent branch-advance test that distinguishes precheck success from post-rebase critical-source drift, with explicit source-bound result and no external write.
- **protectedAuthorityCheck:** Production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d` and contract `87712ea9` remain outside the code diff.

## Next safe target

Confirm exact-source CI for the corrected synthetic fixture. Then build a source-bound, post-rebase writer guard and negative tests in a publisher-independent CI path before considering changes to `sustained-local-soak.yml`. Keep production promotion human-only and `NO_GO`.
