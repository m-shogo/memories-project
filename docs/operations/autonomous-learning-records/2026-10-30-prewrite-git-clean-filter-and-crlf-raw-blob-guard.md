# Supplemental OPS learning — Git clean-filter execution and raw workflow identity (2026-10-30)

Append-only supplemental history under `contracts/operations/autonomous-learning-system.json`. The canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` authority remains unchanged and blob-SHA verified, not fully transferred. **This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound evidence, typed eight-domain non-resurrection, independent-review, or human-promotion evidence.**

## Material failure A — Git normalization can hide worktree drift

- **symptom:** The optional read-only prewrite workflow index audit used `git diff --quiet HEAD` as proof that checked-out YAML matched Git index/HEAD bytes. A Git clean filter or CRLF normalization can report no diff despite changed raw workflow bytes.
- **evidence:** Disposable Git fixtures demonstrated that `.gitattributes` `filter=opaque` with a clean command returning the original `on: push` blob masks a worktree edit to `on: workflow_dispatch`; `git diff --quiet HEAD -- .github/workflows` exits 0. Separately, `text eol=crlf` masks raw CRLF-vs-LF drift with the same exit 0. SHA-1 over `blob <byte-length>\\0<raw bytes>` disagreed with the indexed blob for the changed files. These are controlled source-identity reproductions, not production incidents.
- **rootCauseOrUnknown:** Verified: Git's clean/line-ending conversions normalize worktree content for diff, so a successful diff does not prove raw byte identity.
- **failedApproach:** Treating filtered Git worktree diff equality as raw source identity.
- **correction:** [`8535acca`](https://github.com/m-shogo/memories-project/commit/8535acca45b4e05e651c485d99f24b055dcec87e) pins raw workflow bytes to the staged Git blob SHA (SHA-1 or SHA-256 according to object ID width), with bounded source size. [`caa06f3f`](https://github.com/m-shogo/memories-project/commit/caa06f3fa216a2968bcce0db9b6235174bfbdcee) adds an actual CLI clean-filter negative and restored positive; [`18535c62`](https://github.com/m-shogo/memories-project/commit/18535c6214957a8219affef0c61016fb79e610a6) adds CRLF negative and restoration positive.
- **recurrenceGuard:** The CI-bound negative validator invokes the actual prewrite CLI in a disposable Git repository and requires a precise `prewrite workflow Git index raw blob drift` rejection even when Git's filtered diff reports clean. Existing clean-source and staged-only drift controls remain.
- **retryCondition:** Accept alternate worktree encoding/filtering only after explicit source-identity review, deterministic raw-byte/index verification, executable positive/negative tests, exact-source CI and protected-authority comparison. Do not relax identity based on a clean Git diff alone.

## Material failure B — read-only Git diff can execute a clean filter

- **symptom:** The same nominally read-only audit invoked `git diff` on worktree content and could execute a checkout-controlled filter command.
- **evidence:** A disposable Git `filter.opaque.clean` script wrote a harmless `.filter-marker` during `git diff --quiet HEAD`; cached diff did not create the marker. This demonstrates an executable checkout-config boundary, not malicious activity.
- **rootCauseOrUnknown:** Verified: Git worktree diff applies configured clean filters, and those filters can run external programs.
- **failedApproach:** Disabling `core.fsmonitor` alone while retaining a worktree diff and assuming all Git queries were non-executable.
- **correction:** [`724e95e2`](https://github.com/m-shogo/memories-project/commit/724e95e2e5259823e2a99f219e29638ab67a2f9a) removes the worktree diff; cached index-vs-HEAD diff remains, while the raw-byte check independently validates worktree content. [`1facbcb4`](https://github.com/m-shogo/memories-project/commit/1facbcb47578362bcec7ca2f361e7fcd319e36a9) adds an executable-marker positive control followed by a no-marker actual CLI negative.
- **recurrenceGuard:** The fixture must first prove the configured filter executes under an intentionally unguarded Git diff; then the audited CLI must reject the changed raw blob **without** recreating the marker.
- **retryCondition:** Any future worktree Git command requires independent proof that it cannot invoke checkout-controlled filters/hooks, or a reviewed sandbox and explicit executable side-effect policy.

## Material failure C — first-diagnostic fixture drift

- **symptom:** Exact-source [Autonomous Learning Guard #41019635935](https://github.com/m-shogo/memories-project/actions/runs/41019635935) FAILED in `prove_prewrite_fanout_cli` at `dirty tracked Git workflow CLI negative failed`.
- **evidence:** The actual CLI now rejects dirty raw bytes with `prewrite workflow Git index raw blob drift`, while the older fixture still required `prewrite workflow Git index content drift`. The staged-only case still correctly expects the latter.
- **rootCauseOrUnknown:** Verified from the job log: removing the worktree diff changed the earliest rejection for a dirty unstaged file, but its exact diagnostic expectation was not updated.
- **failedApproach:** Changing the validator's rejection order without updating both self-test and independently CI-bound CLI negative diagnostics.
- **correction:** [`43940cb7`](https://github.com/m-shogo/memories-project/commit/43940cb750137fb4dbdf78173c96e85023faa0c4) updates the dirty self-test, and [`8043fc39`](https://github.com/m-shogo/memories-project/commit/8043fc39aa778e08b5d10e4f2870ddcc6bdc2cb1) updates the dirty CLI negative. Staged-only diagnostic remains unchanged.
- **recurrenceGuard:** Distinct exact-diagnostic negatives for unstaged raw drift, staged index drift, clean-filter masking, CRLF normalization and no-execution marker.
- **retryCondition:** Re-run exact-source CI on the corrected head; only a completed successful run plus job-log checks can establish CI success.

## Material success — bounded observed evidence

- **outcome:** The raw Git object hash check and three actual CLI fixture classes are committed; local Git reproductions confirmed filtered and CRLF diff masking, raw mismatch and executable clean-filter behavior. [Autonomous Learning Guard #41019487641](https://github.com/m-shogo/memories-project/actions/runs/41019487641) completed SUCCESS for the earlier raw-blob/CLI stage at `caa06f3f`. The corrected `8043fc39` exact-source CI was **pending** at the time of this record and must not be reported as successful until independently verified.
- **evidence:** Local Git SHA/raw-byte and filter-marker controls; exact-source CI run links and the first-diagnostic failure log above.
- **whySafe:** Only two read-only Python validation scripts and append-only supplemental learning changed; no workflow YAML, production code, traffic, credentials, backup/restore, recovery authority, evidence registries or promotion was written.
- **reusableMechanism:** Compare unfiltered worktree bytes against indexed Git blob identity, compare index against HEAD without worktree filter execution, and prove fail-closed behavior with executable positive controls and exact diagnostics.
- **protectedAuthorityCheck:** All ten protected blob SHAs unchanged through `8043fc39`: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. Actual snapshot remains `PREREQUISITES_BLOCKED`: registered/eligible generations 0/0, current human-approved objective 0, executable reviewed request 0, request-bound evidence 0, complete typed eight-domain record 0, final candidate 0. `productionDecision=NO_GO` and separate human promotion remain mandatory.

## Next safe target

Verify corrected exact-source CI, then bind validated raw workflow bytes to the bytes parsed in the same audit pass to avoid a read-after-check race. Independently continue Go/Python transitive dependency and CI trigger coverage work; do not retry unchanged MinIO HTTP 401 or workflow-write permission blockers.
