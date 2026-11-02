# Supplemental OPS learning — over-budget pinned source read loop correction (2026-11-02)

Append-only correction to `2026-11-02-generation-reconciler-transport-classifier-fixture-guards.md`, governed by canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Neither record nor synthetic testing constitutes production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved recovery objective, executable reviewed drill request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure — introduced negative would not terminate without a reader guard

- **symptom:** The newly added oversized mocked `os.read` negative in commit `25690fd2` could cause the existing `while remaining:` loop to continue with a negative budget, rather than reject the over-budget chunk.
- **evidence:** At `so` HEAD `2bc07cc8c567deee439cb4d655674df7608a9e7f`, the reader started with `remaining = MAX_RECONCILER_SOURCE_BYTES + 1`, subtracted `len(chunk)` without a per-chunk upper bound, and used `while remaining:`. The new negative returns `MAX_RECONCILER_SOURCE_BYTES + 2` bytes on every call. After one response `remaining == -1`, which is truthy in Python; repeated oversized responses keep the loop active. This was detected by deterministic source/arithmetic review, **not** by a claimed observed CI hang.
- **rootCauseOrUnknown:** Verified missing `len(chunk) <= remaining` guard before decrement. The test introduced an over-budget input that the reader had not previously defended against; whether a real OS read could exhibit this is not established.
- **failedApproach:** Adding a large-response negative under the assumption that the final `len(source) <= MAX` check would be reached. It would not be reached under repeated oversized reads.
- **correction:** [`b607e62f`](https://github.com/m-shogo/memories-project/commit/b607e62f8bab9665fbac010bc6d736e1b51eab0b) requires `len(chunk) <= remaining` before appending or decrementing, using the existing private `reconciler source changed during read` domain error.
- **recurrenceGuard:** The already committed oversized-read negative in `25690fd2` now exercises this new per-chunk guard; fragmented positive, early EOF and nonbytes cases remain. Any future read loop using a decrementing budget must reject over-budget responses before mutation, not rely on a final size check.
- **retryCondition:** Check exact-source read-only Negative Suite once run metadata/logs are observable. If the suite fails or times out, diagnose that observed failure and append a separate record before retrying; do not repeat the unbounded mocked-read approach. Unchanged Quay MinIO 401, canonical large-blob transport, publisher-coupled writer and absent human evidence remain scoped blockers.

## Observed correction outcome

- **outcome:** `b607e62f` was committed to `so`, and GitHub diff/readback confirm the new check is positioned before the decrement in `pinned_reconciler_source`.
- **evidence:** Commit diff and exact `so` source readback. GitHub combined status and commit workflow-run queries yielded no push-run conclusion; **no exact-source CI SUCCESS is claimed**.
- **whySafe:** The change affects only the independently read-only negative harness, not the production reconciler or publisher trigger. It prevents a synthetic pathological reader response from causing unbounded test execution.
- **reusableMechanism:** Guard each read against the remaining byte budget before concatenation/decrement; test both legitimate short reads and oversized responses with deterministic error classification.
- **protectedAuthorityCheck:** Following the correction, unchanged Git blobs were observed for production status `d677a1c9` (`productionDecision=NO_GO`), generations `bfd1b045`, objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, canonical learning `b809c69d`, and mandatory contract `87712ea9`. The commit changed no protected authority. OPS-P0-007 production prerequisites remain unfulfilled; no human promotion is inferred.

## Next safe target

Verify the full read-only Negative Suite at exact source `b607e62f` or a descendant containing the correction. Only then extend the same bounded-read guard audit to other independent source readers, without re-running unchanged external blockers.
