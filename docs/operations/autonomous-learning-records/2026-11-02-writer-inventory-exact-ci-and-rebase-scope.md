# Supplemental OPS learning — exact CI for writer inventory and scoped rebase audit (2026-11-02)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Learning and synthetic CI are never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure — confirmed CI and corrected guard

- **symptom:** The first source-derived 221-workflow lexical inventory test failed its exact-source CI.
- **evidence:** [Autonomous Learning Guard #41436241471](https://github.com/m-shogo/memories-project/actions/runs/41436241471) completed FAILURE on `554cd0ee`. Job `125246574044` passed the positive learning contract, then raised `RuntimeError: prewrite source-derived writer-signal inventory drift` from the negative suite. Source re-read independently showed double-escaped Python raw regexes.
- **rootCauseOrUnknown:** Verified malformed regex escaping from JavaScript-generated Python source; no unsafe publisher run or production mutation observed.
- **failedApproach:** Unchecked double-escaping of raw regex tokens, causing a lexical inventory false-negative.
- **correction:** [`01d5fcaa`](https://github.com/m-shogo/memories-project/commit/01d5fcaaf1615ac04db2546b435a733f47bf2974) corrected the patterns and added positive/negative live marker fixtures.
- **recurrenceGuard:** The test now fails before inventory acceptance if `contents: write` or `git push` is not recognized or `contents: read` is incorrectly recognized. Exact 104-name membership and six inventory mutations remain.
- **retryCondition:** Retry only when source regex, reviewed writer-signal inventory or CI execution environment changes; do not repeat the double-escaped generation approach.

## Material successes — observed exact-source CI

- **outcome:** Both independent read-only negative-suite code heads completed SUCCESS:
  - [#41435871981](https://github.com/m-shogo/memories-project/actions/runs/41435871981) on `40038d9e`, covering byte-exact external and shared-entrypoint prewrite transcripts.
  - [#41436284979](https://github.com/m-shogo/memories-project/actions/runs/41436284979) on corrected `01d5fcaa`, covering the source-derived 221-workflow lexical writer inventory.
- **evidence:** Jobs `125245375825` and `125246718564` completed SUCCESS with all steps green. Logs for both reported `Autonomous learning negative validation PASS (601 fail-closed cases)` and `prewrite fanout audit PASS: 195 synthetic cases`. The new transcript and inventory mutations are inside the existing suite and not separately counted by the printed 601.
- **whySafe:** Both workflows checked exact clean Git SHA, append-only canonical learning, negative tests, helper reachability and clean read-only completion; no publisher or production authority was changed.
- **reusableMechanism:** Exact byte-level CLI transcripts plus a Git-index-verified full-workflow lexical writer inventory, with mutation tests that reject source-identity drift and never equate missing lexical markers with permission to write.
- **protectedAuthorityCheck:** Ten protected Git blobs remained unchanged: production status `d677a1c9` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d` and mandatory contract `87712ea9`.

## New scoped writer race requiring independent review

- **symptom:** A potential post-validation source-drift window exists in `.github/workflows/sustained-local-soak.yml` (blob `610afce0`) in its append-only run-result publisher. This is a **source-observed risk hypothesis**, not an observed stale publication.
- **evidence:** The workflow's run-result step first fetches `so` and checks critical paths against `SOURCE_SHA`, then resets to `origin/so`, validates the result, commits it, executes `git pull --rebase origin so`, and finally `git push origin HEAD:so`. The reviewed step does not visibly repeat the critical-path diff and result validation after that rebase. A critical-source change between the first check and rebase may require an additional guard; actual concurrency exploitability and intended append-only policy remain unverified.
- **rootCauseOrUnknown:** Explicit unknown until a deterministic concurrent-branch-advance fixture proves or refutes the risk. Do not call this a confirmed production defect.
- **failedApproach:** Assuming a pre-commit critical-path check alone proves source consistency across a later rebase.
- **correction:** Do not modify the write-capable workflow without a separately reviewed exact-source read-only negative CI route. Continue independent diagnostic work and preserve existing source/production authorities.
- **recurrenceGuard:** Next safe executable target is a synthetic Git race fixture that advances a critical source between precheck and rebase, with fail-closed source SHA/result binding assertions and no production publisher execution.
- **retryCondition:** Revisit only after the independent read-only fixture and safe workflow-trigger/permission review are established.

## Additional bounded writer evidence

A separate lexical audit of all 104 signal-bearing workflows found each contains source-SHA, remote-fetch and remote-comparison tokens. This is **not** proof that every push path is guarded: source control flow, job-level effective permissions, aliases, rebase and transitive workflow calls remain unverified. Do not use the lexical inventory as write authorization.

## Next safe target

Implement and CI-validate the sustained-soak synthetic rebase-race negative fixture in a publisher-independent read-only test, then review the prewrite writer-classifier integration and audit-script CI trigger reachability. Preserve OPS-P0-007 `NO_GO`.
