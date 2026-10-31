# Supplemental OPS learning — pinned reader close and source-negative shadow (2026-11-01)

This is append-only execution learning under `contracts/operations/autonomous-learning-system.json`, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final recovery candidate or human promotion evidence. Canonical learning and protected authorities remain unchanged.

## Material failure A — pinned reader close could mask a primary read error

- **symptom:** `read_regular_bytes` closed its pinned descriptor in an unguarded `finally`; an independent close failure could replace an earlier `os.read` error. No live production corruption or leak was observed.
- **evidence:** The source before [`8938aac0`](https://github.com/m-shogo/memories-project/commit/8938aac087fc7d01909bc49a5e4e414da5eb276e) used `finally: os.close(descriptor)`. The new disposable proof injects a primary read error and faults the actual reader FD close both before and after its syscall effect.
- **rootCauseOrUnknown:** Verified exception-masking risk in unguarded cleanup. After a close error, whether the FD was consumed is explicitly unknown without independent observation.
- **failedApproach:** Letting a cleanup close replace a primary read error, or retrying a close whose completion status is ambiguous.
- **correction:** [`8938aac0`](https://github.com/m-shogo/memories-project/commit/8938aac087fc7d01909bc49a5e4e414da5eb276e) preserves the active read error and attaches a bounded `pinned reader descriptor close status unknown` note; a close failure without an earlier read error still raises. The final validated version uses the reader-scoped `read_failure` variable.
- **recurrenceGuard:** The existing CI-reached `prove_nonblocking_special_file_reads` tests exact `before-read-close` and `after-read-close` cases, original error, uncertainty note, independently observed FD state, original bytes and an external canary. AST source binding, source-negative mutation and proof-loop mutation reject disabled fault injection or weakened handler.
- **retryCondition:** Revisit only when pinned reader ownership, `os.read`/`os.close` behavior, Python exception notes or the reviewed proof topology changes.

## Material failure B — new reader error variable shadowed an existing source-negative mutation target

- **symptom:** The first read-close patch failed both independent CI entrypoints as `upload-route pinned publication mutation accepted`.
- **evidence:** [Operability Contracts #41236438277](https://github.com/m-shogo/memories-project/actions/runs/41236438277) and [Autonomous Learning Guard #41236438354](https://github.com/m-shogo/memories-project/actions/runs/41236438354) FAILED on exact `8938aac0`. The existing publication mutation suite requires exactly one source occurrence of `original_failure = sys.exception()`; the new reader used the same identifier, making two occurrences.
- **rootCauseOrUnknown:** Verified global string-count collision across distinct reader and writer functions; not a runtime authority corruption.
- **failedApproach:** Reusing a source-negative mutation marker in an independent function without checking the full-source occurrence count before publishing. This known class of source-binding collision must not recur.
- **correction:** [`f52cd36d`](https://github.com/m-shogo/memories-project/commit/f52cd36d73c6f2aeb7b26948eec47ef5b819e555) uses `read_failure = sys.exception()` in the reader and updates its exact AST binding, restoring the writer marker's unique occurrence.
- **recurrenceGuard:** The existing executable publication mutation suite fails closed unless its target occurs exactly once; the reader binding independently requires the reader-scoped name and exception guard. Prewrite review must count all existing source-negative targets across the full module, not only the changed function.
- **retryCondition:** Revisit only when reader/writer failure capture, source-negative mutation topology or the exact source markers change; never repeat the colliding identifier without an independently validated new scope.

## Material success — isolated read close faults preserve the first error

- **outcome:** Both pre-effect and post-effect reader close faults retain the original read failure and do not change original or independent file bytes.
- **evidence:** [Autonomous Learning Guard #41236716798](https://github.com/m-shogo/memories-project/actions/runs/41236716798) and [Operability Contracts #41236716649](https://github.com/m-shogo/memories-project/actions/runs/41236716649) completed SUCCESS on exact code HEAD `f52cd36d`.
- **whySafe:** The change affects only pinned reader cleanup error preservation. Existing no-follow, regular-file, single-link, bounded-read and live-leaf identity checks remain; synthetic faults use disposable files and never create production evidence.
- **reusableMechanism:** Keep primary failures separate from ambiguous descriptor cleanup, and scope independent guard variables so existing full-source negative mutations retain unique targets.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs stayed unchanged through both code commits and append-only learning; no production or human-promotion authority was modified.

## Remaining authority boundary and next safe target

`productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`; registered and semantically eligible generations remain 0/0. Preflight requires unsuperseded semantically eligible generations from distinct environments plus an explicitly human-approved current recovery objective. Reviewed drill requests remain planning-only; new generation recovery evidence requires a current executable reviewed request. Final recovery candidates require complete typed eight-domain non-resurrection coverage and independent review; human production promotion remains separate and non-automatic.

[Upload Route #41236716623](https://github.com/m-shogo/memories-project/actions/runs/41236716623) failed at MinIO image startup with Quay HTTP 401, before focused Go/HTTP tests. Workflow-write permission, supplemental-learning-only Push/PR CI reachability and independent pre-MinIO focused Go execution remain unchanged blockers; do not retry them without changed preconditions. This learning-only commit does not itself prove independent exact-source CI SUCCESS.

**Next safe target:** Audit `open_pinned_parent` ancestor traversal when closing the old directory FD fails after the close actually consumed it. Verify whether subsequent cleanup can double-close a reused descriptor, with isolated before/after-close tests and explicit ownership checks before any production-path change.
