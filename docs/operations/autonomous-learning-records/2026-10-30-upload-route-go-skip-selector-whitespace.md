# Supplemental OPS learning — Go Skip selector whitespace and newline coverage (2026-10-30)

Append-only supplemental learning only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy: `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure A — horizontal whitespace selector bypass

- **symptom:** The focused-test direct-skip guard and selected-source skip inventory matched only `t.Skip(...)`, so a valid Go `t . Skip(...)` could be inserted without changing the reviewed skip count.
- **evidence:** A disposable Go 1.23.2 `TestSpaceSelector` using `t . Skip("...")` completed as **SKIP**, while the previous Python regex returned no match. Both reviewed selected test sources currently use the normal `t.Skip` spelling.
- **rootCauseOrUnknown:** Verified: Go permits horizontal whitespace around selector dots; the previous lexical regex did not.
- **failedApproach:** Equating the exact `t.Skip` token sequence with every syntactically valid direct Skip selector.
- **correction:** [`be7301a2`](https://github.com/m-shogo/memories-project/commit/be7301a2566b4664879c1a740d00c03a27834d1a) extends all four existing Skip matchers to horizontal whitespace around the selector dot.
- **recurrenceGuard:** Two CI-bound negatives inject `t . Skip` into a selected test and `t . SkipNow` into the source-file inventory, requiring the existing exact rejection diagnostics.
- **retryCondition:** Any intentional change to selected test skip behavior requires reviewed helper preconditions, executable Go syntax controls, exact-source CI and protected-authority checks.

## Material failure B — newline after selector dot

- **symptom:** A horizontal-whitespace-only matcher still missed valid Go `t.\nSkip(...)`.
- **evidence:** A disposable Go 1.23.2 test using a newline immediately after the selector dot compiled and completed as **SKIP**; the horizontal-only regex did not match it.
- **rootCauseOrUnknown:** Verified: Go does not insert a semicolon immediately after `.`, allowing the selector to continue on the next line.
- **failedApproach:** Expanding only to spaces/tabs and assuming Go selectors cannot span lines.
- **correction:** [`0e51ea82`](https://github.com/m-shogo/memories-project/commit/0e51ea82dc8b96112b669c1ecb0b35331b1a9ffd) also accepts CR/LF after the selector dot in the four Skip matchers.
- **recurrenceGuard:** Two additional CI-bound negatives inject newline-separated `t.Skip` and `t.SkipNow` forms into the focused test and inventory paths.
- **retryCondition:** Reconsider this lexical boundary only with a Go-aware parser or executable Go control demonstrating a changed grammar/precondition, exact-source CI and protected-authority verification.

## Material successes

- **outcome/evidence:** [Autonomous Learning Guard #41026379715](https://github.com/m-shogo/memories-project/actions/runs/41026379715) completed **SUCCESS** on exact source `be7301a2566b4664879c1a740d00c03a27834d1a`. [Autonomous Learning Guard #41026438893](https://github.com/m-shogo/memories-project/actions/runs/41026438893) completed **SUCCESS** on exact source `0e51ea82dc8b96112b669c1ecb0b35331b1a9ffd`. Both logs show append-only/contract PASS, 509 canonical fail-closed negatives, 193 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only PASS. New nested selector fixtures are not separately counted in 509.
- **whySafe:** Only the CI-reachable read-only negative validator changed in these two commits. The Go syntax demonstrations used disposable local modules; no production/test Go source, workflow YAML, credentials, traffic, recovery, generation, objective, eight-domain review or promotion authority changed.
- **reusableMechanism:** Validate security-sensitive lexical patterns against real language grammar, then pin every newly discovered valid spelling with an executable negative. Preserve the distinction between a static skip inventory and full transitive test execution.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0 and separate human-approved objective, executable reviewed request, request-bound evidence, typed eight-domain coverage, independent review and human promotion all absent.

## Next safe target

Detect aliased Skip receivers and method values without claiming complete Go test control-flow proof. Continue Go-only pre-MinIO CI reachability and complete Go/Python dependency closure; workflow-write and MinIO blockers remain unchanged.
