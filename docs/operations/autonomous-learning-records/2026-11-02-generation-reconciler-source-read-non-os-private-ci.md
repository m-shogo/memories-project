# Supplemental OPS learning — generation reconciler pinned-source non-OS private read CI (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Neither this record nor synthetic CI satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human production-promotion authority.

## Material failure mode / verified coverage gap

- **symptom:** The independently read-only generation-evidence reconciler pinned-source reader normalized `OSError` but could propagate private `ValueError` or `TypeError` diagnostics from `os.read` without a domain classification.
- **evidence:** Before [`3839bd31`](https://github.com/m-shogo/memories-project/commit/3839bd31a5ef0b9ad30afef6d6dde8486b28bb64), `pinned_reconciler_source` caught only `OSError`, and the existing private read negative injected only `OSError("PRIVATE_RECONCILER_SOURCE_READ_CANARY")`. No real private disclosure or production incident was observed.
- **rootCauseOrUnknown:** Verified exception-type coverage gap in this independent pinned-source reader; actual OS/Python wrapper failure occurrence unknown.
- **failedApproach:** Assuming an `OSError`-only redaction and unrelated negative tests prove all private reader failures are suppressed, or using a broad catch that could repeat the previously observed fixed-domain `Fail` masking bug.
- **correction:** `3839bd31` normalizes only `(OSError, ValueError, TypeError)` to the fixed `generation evidence reconciler pinned source unreadable` domain error with suppressed context. The private read negative now injects all three types.
- **recurrenceGuard:** Each injected canary must yield the exact private `Fail`, no canary text and `__suppress_context__`; `os.read` is restored. Existing expected-domain `Fail` tests for EOF, nonbytes and oversized responses remain intact.
- **retryCondition:** Revisit on source-reader exception classification, private diagnostics, owned FD cleanup or exact-source CI regression. Do not retry unchanged MinIO HTTP 401, publisher-coupled writer, canonical learning large-blob retrieval or absent human evidence.

## Observed material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41420129298](https://github.com/m-shogo/memories-project/actions/runs/41420129298) completed **SUCCESS** on `3839bd31a5ef0b9ad30afef6d6dde8486b28bb64`.
- **evidence:** Job `125193402453` logged `PASS: generation reconciler negative classifier private exception redaction`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. The three private reader cases run before those summaries. GitHub diff changed only the independently read-only reconcile-negative script.
- **whySafe:** No production reconciler, publisher, evidence, credential, traffic or readiness change; the source is validated in `contents: read` exact-source CI using synthetic fixtures.
- **reusableMechanism:** Extend private error normalization only to explicit expected Python syscall exception classes and prove each through exact-diagnostic canary injection, while preserving intentional domain failures.
- **protectedAuthorityCheck:** Ten Git blob identities unchanged after code commit: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, learning contract `87712ea9`. Registered/semantically eligible generations 0/0; current approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage and final candidate 0. Human promotion remains separate/nonautomatic.

## Next safe target

Close the same `ValueError`/`TypeError` reader gap in independent generation-evidence and generation-binding transport negative importers, with their own exact-source CI and append-only evidence.
