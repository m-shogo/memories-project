# Supplemental OPS learning — reject malformed acquired JSON source descriptors (2026-11-02)

Append-only learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** The two new pinned planning JSON readers immediately appended each `os.open` return to the owned-descriptor list, without verifying its exact type and nonnegative range. A malformed synthetic return could reach `fstat` or cleanup as an unowned descriptor.
- **evidence:** At HEAD `aa8aad00`, both readers used `owned.append(parent_fd)` and `owned.append(source_fd)` without `type(fd) is int` checks. Prior [canonical reader invalid-FD learning](2026-11-01-canonical-ancestor-alias-path-fault-invalid-fd.md) documented this precise failure class and prohibited closing an unverified numeric alias. No ordinary CPython `os.open` malformed return or production incident was observed.
- **rootCauseOrUnknown:** Verified missing pre-ownership type/range checks in two newly introduced readers; real-world occurrence unknown.
- **failedApproach:** Assuming a returned `os.open` value was automatically a valid owned FD, despite the previously recorded failure mechanism.
- **correction:** [`87ce8f4f`](https://github.com/m-shogo/memories-project/commit/87ce8f4f74e904dfcd84c8cf8c9f47b3ff9a7161) requires `type(fd) is int and fd >= 0` before appending each root, ancestor or leaf FD to the owned list. Invalid results fail closed without reaching descriptor use or cleanup.
- **recurrenceGuard:** The existing CI-reached drill binding negative suite injects `None`, `True`, `-1`, `1.5` and `"7"` as initial `os.open` results for both independent readers; spies forbid `fstat` and `close` on unverified results and a real external FD canary must remain valid after every rejection. All previous pinned-path, mutation, cleanup and strict JSON tests remain active.
- **retryCondition:** Revisit only if acquired-FD ownership semantics, reader acquisition sequence, Python syscall wrappers or exact-source CI changes. Do not retry unchanged Quay MinIO HTTP 401, workflow write permissions, external evidence or human promotion blockers.

## Material success

- **outcome:** Invalid synthetic acquired descriptors are now rejected before ownership, use or cleanup in both planning JSON readers.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41342512228](https://github.com/m-shogo/memories-project/actions/runs/41342512228) completed **SUCCESS** at code HEAD `87ce8f4f`. Logs report `PASS pinned JSON: both readers reject leaf/parent symlink, hardlink, EOF, nonbytes and mutation, parent swap, cleanup double fault, invalid FD; fragmented positive`, `Drill generation eligibility binding reconcile negative suite PASS`, and `production decision: NO_GO`. This is CI validator evidence, not a Go test or production restore.
- **whySafe:** Only the two read-only planning JSON loaders and their disposable-fixture negative suite changed. No protected registry, production status, workflow permission, credential, traffic or promotion authority was modified.
- **reusableMechanism:** Reuse the previously verified canonical-reader rule: validate exact integer FD type and nonnegative range immediately after acquisition, before any `fstat`, ownership tracking or close; pair with forbidden-call spies and a live canary.
- **protectedAuthorityCheck:** Ten protected Git blobs remain unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. Registered and unsuperseded semantically eligible generations remain distinct; preflight requires two distinct eligible environments and an explicitly human-approved current recovery objective. Reviewed requests are planning-only; request-bound recovery evidence, complete typed eight-domain non-resurrection, independent review and separate human promotion remain mandatory.

## Next safe target

Exercise malformed descriptor acquisition at an intermediate ancestor and leaf, not only the first open, and verify already-owned descriptors close exactly once without touching an invalid return. Separately continue locating an approved non-skipped Focused Go Test execution path before MinIO.
