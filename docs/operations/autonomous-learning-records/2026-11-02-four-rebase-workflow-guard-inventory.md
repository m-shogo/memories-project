# Supplemental OPS learning — four-workflow postrebase source inventory (2026-11-02)

Append-only subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is diagnostic source/negative-test evidence, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material scoped source observation

- **symptom:** Four of 104 lexical writer-signal workflows use `git pull --rebase origin so`. Only one reviewed source visibly repeats a critical-source guard after the rebase; the other three need independent review. No actual stale publication was observed.
- **evidence:** At immutable `so` workflow sources, `controlled-saturation-repeatability.yml` (blob `1f4b20c0`) calls `verify_critical_source` after its rebase and before push. `sustained-local-soak.yml` (`610afce0`), `sustained-local-soak-parallel-request.yml` (`88a14aaa`) and `sustained-local-soak-parallel-v2.yml` (`2ba5967d`) contain one, one and three rebase-to-push paths respectively without that named postrebase guard. The parallel-v2 paths include run result, diagnostic and aggregate publication.
- **rootCauseOrUnknown:** Source-level guard placement is verified; equivalent alternative checks, actual exploitability, workflow-call closure and production consequences remain unknown. A lexical match is not shell control-flow or permission proof.
- **failedApproach:** Assuming that all rebasing publishers use the same reviewed source lease because they contain `SOURCE_SHA`, remote fetch and remote-comparison tokens.
- **correction:** [`e5889397`](https://github.com/m-shogo/memories-project/commit/e5889397216ac5eb6af91f0307721117470a0648) adds a read-only four-workflow rebase-guard placement inventory to the existing negative suite, comparing one reviewed postrebase guard against three scoped potential gaps. The existing writer workflows are unchanged.
- **recurrenceGuard:** Executable fixtures reject comment-only and pre-rebase guard placement, missing push boundary, and unexpected rebase/guard inventory drift. No absence of a marker authorizes a write.
- **retryCondition:** Modify any write-capable workflow only after an independent read-only exact-source CI route, reviewed job permissions, source lease and bounded reconcile behavior are established.

## Material implementation failure / correction

- **symptom:** The initial generated rebase inventory code repeated a known double-escaping error in Python raw regexes and fixture newlines.
- **evidence:** Source re-read of `e5889397` showed `r"\\\\s*"`, `r"\\\\b"` and double-escaped fixture newline tokens, despite prior learning from the writer-signal inventory. This was a repeated failed approach, not an accepted successful test.
- **rootCauseOrUnknown:** Verified cross-language JavaScript template escaping; no production mutation.
- **failedApproach:** Manually layering JavaScript escaping over Python raw regex and string literals instead of preserving exact source.
- **correction:** [`884701d1`](https://github.com/m-shogo/memories-project/commit/884701d1f8614f484b7cb2f13ef7783df52e2d4c) uses exact raw-source replacements and adds executable positive/comment-only controls that fail on incorrect regex/newline semantics.
- **recurrenceGuard:** Future source generation must use literal-preserving `String.raw` or equivalent exact-source construction, reject double-escaped patterns before write, and re-read generated source after commit. The new fixture checks actual executable guard placement.
- **retryCondition:** Retry only after corrected source bytes and exact-source CI; do not repeat manual double-escaping without changed preconditions.

## Observed safe progress

- **outcome:** The code diff and corrected source were re-read and verified; exact-source CI for the corrected rebase inventory was not yet complete when this record was written.
- **evidence:** GitHub comparisons show only `scripts/validate-autonomous-learning-system-negative.py` changed in the two code commits. The earlier independent [synthetic soak rebase CI #41437245810](https://github.com/m-shogo/memories-project/actions/runs/41437245810) completed SUCCESS on `668cb068`, including its source-bound critical/noncritical Git race fixture.
- **whySafe:** Only read-only negative-suite code and temporary local Git fixtures were changed. No publisher, workflow permission, production evidence, credential, traffic, readiness or promotion authority was modified.
- **reusableMechanism:** Use an existing reviewed postrebase critical-source guard as a positive source pattern; mutation-test its placement and track other rebasing publishers as explicit scoped unknowns.
- **protectedAuthorityCheck:** Production `d677a1c9` (`NO_GO`), OPS-P0-007 `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d` and mandatory contract `87712ea9` remained outside the changed diff.

## Next safe target

Verify corrected exact-source CI. Then build a publisher-independent shell/control-flow negative fixture for each soak rebase path and separately review a post-rebase source-critical check before any writer workflow change. Keep OPS-P0-007 and `productionDecision=NO_GO`.
