# Supplemental OPS learning — scoped Python CI fixture lifetime recovery (2026-10-31)

Append-only operational history, never canonical production evidence. The canonical learning authority and mandatory learning contract remain unchanged. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, recovery-generation/objective/request, typed eight-domain non-resurrection, independent-review, or human-promotion gates.

## Material failure and verified diagnosis

- **symptom:** Four newly added actual-CLI Python dependency trigger negatives failed at the first `requirements-security-validation.txt` case, despite the reviewed three workflow YAML path filters appearing to omit it.
- **evidence:** [CI #41088311549](https://github.com/m-shogo/memories-project/actions/runs/41088311549) failed on `f58d7c1` with a generic classification mismatch. Diagnostic-only commit [c6bf417](https://github.com/m-shogo/memories-project/commit/c6bf4177d2e012d9d69b4062eba5b06d3cbb3edf) produced [CI #41088632082](https://github.com/m-shogo/memories-project/actions/runs/41088632082): `rc=1`, empty stdout, stderr `PREWRITE TRIGGER AUDIT FAILED: workflow directory missing or symlinked`.
- **rootCauseOrUnknown:** **Verified:** The newly inserted Python-input loop was indented outside the `with tempfile.TemporaryDirectory(...)` block. The temporary `.github/workflows` fixture directory had already been removed when the CLI ran. The expected no-direct-match classification was never reached; the failure did not prove an event-filter mismatch.
- **failedApproach:** Appending new fixture checks before a function's final return without verifying their lifetime relative to the existing context manager; assuming the error was about workflow trigger semantics before obtaining stdout/stderr.
- **correction:** [91f862e](https://github.com/m-shogo/memories-project/commit/91f862e732d492194efb2bd5586998398dbaa687) moves all four Python checks into the live temporary directory context and adds an explicit `workflow.parent.is_dir()` precondition.
- **recurrenceGuard:** The CI-bound real CLI fixture now checks the temporary workflow directory exists immediately before each subprocess invocation, then demands the exact fail-closed no-direct-Push/PR result. A missing fixture directory is diagnosed separately from a true path-filter mismatch.
- **retryCondition:** Run exact-source CI for `91f862e` and inspect the four CLI outcomes. If another mismatch occurs, use the captured return code/stdout/stderr to distinguish real trigger coverage from fixture or parser defects. Do not repeat the already disproven assumption that a deleted temporary directory can support a valid classification.

## Protected authority and status

The recovery changes only the read-only negative validator. Neither Go code nor workflow YAML nor the canonical learning contract/status/OPS-P0-007 registry authority was edited. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, 0 registered and 0 semantically eligible environment generations; no approved current recovery objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain non-resurrection record, independent review or separate human promotion. Exact-source CI outcome for `91f862e` was pending when this record was created. Supplemental learning is never readiness evidence.

## Next safe target

Confirm the corrected four-input scoped no-direct-trigger classification with exact-source CI, then continue auditing transitive Go/Python input and Push/PR workflow reachability. Do not alter workflow permissions or retry unchanged external MinIO HTTP 401.
