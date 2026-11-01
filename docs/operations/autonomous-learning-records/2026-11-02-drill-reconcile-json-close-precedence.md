# Supplemental OPS learning — drill reconcile JSON close-fault precedence (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or semantically eligible generation, recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — primary read failure masked by descriptor cleanup

- **symptom:** A secondary `os.close` OSError could replace a primary invalid-UTF-8/read rejection in the drill-request reconciler. No real production incident was observed.
- **evidence:** At `so` HEAD `ab0db126`, `scripts/reconcile-memory-os-backup-restore-drill-request.py` raised a cleanup `Fail` unconditionally from its `finally` handler even while a read or decoding failure was active.
- **rootCauseOrUnknown:** Verified Python `finally` exception precedence; operational occurrence is unknown.
- **failedApproach:** Letting a secondary descriptor-close failure supersede the original fixed-class authority rejection.
- **correction:** [`951d023d`](https://github.com/m-shogo/memories-project/commit/951d023d7a7646fd89d3f50546e9e9a37d4bfbac) preserves an active primary failure while rejecting a standalone close fault.
- **recurrenceGuard:** The existing CI-reached drill-request load-negative suite injects primary invalid UTF-8 and secondary close OSError, then a standalone close OSError after valid bytes; both cases check fixed private-safe failure classes, descriptor closure and positive restoration.
- **retryCondition:** Revisit only if the reviewed bounded JSON reader, descriptor lifecycle or CI-reached negative suite changes.

## Material failure — invalid UTF-8 fixture was accidentally valid

- **symptom:** Exact-source [Drill Request Admission #41353480586](https://github.com/m-shogo/memories-project/actions/runs/41353480586) and [Unreadable Authority Negatives #41353480614](https://github.com/m-shogo/memories-project/actions/runs/41353480614) FAILED at code HEAD `951d023d`.
- **evidence:** Job `124988472905` reported `DRILL REQUEST LOAD NEGATIVE FAILED: primary UTF-8 rejection survives secondary close fault: wrong drill reconcile reader rejection class`. Source inspection found `b"{\\xff}"`, which encodes printable backslash characters rather than byte 255.
- **rootCauseOrUnknown:** Verified double-escaped byte fixture; no production authority or actual read failure was implicated.
- **failedApproach:** Embedding a multi-layer escaped byte literal without checking its resulting Python source semantics.
- **correction:** [`462947ed`](https://github.com/m-shogo/memories-project/commit/462947ed5f797b5da2ee6fb406b3995ce0844306) uses unambiguous `bytes((123, 255, 125))` to create the invalid-UTF-8 test input.
- **recurrenceGuard:** The same CI-reached positive/negative fixture now proves the actual decoding failure class and secondary close-fault precedence. Use numeric bytes for future multi-layer generated negative inputs instead of assuming escape preservation.
- **retryCondition:** Revisit only if test source serialization/encoding changes or an exact-source CI regression demonstrates a new mismatch; do not rerun the known-broken double-escaped fixture.

## Scoped write transport failure

- **symptom/evidence:** The first attempt to commit the corrected fixture returned an opaque GitHub GraphQL execution error; a subsequent branch read showed an independent diagnostic commit had advanced `so`. The target file was still unchanged.
- **rootCauseOrUnknown:** Unknown whether the GraphQL error was transient transport or concurrent ref movement; no failed write was claimed successful.
- **failedApproach:** Treating an unconfirmed Git-object write as committed without re-reading the branch and target.
- **correction:** Re-read `so` and the exact target blob, then used a new expected-HEAD CAS update; `462947ed` was observed on the branch.
- **recurrenceGuard:** On ambiguous write failure, inspect branch HEAD and target SHA before any bounded retry; never force-push, overwrite a concurrent commit or retry an unchanged blocker.
- **retryCondition:** Retry only after a fresh branch/target read shows the intended change is absent and a new expected-HEAD lease is available.

## Material success

- **outcome:** Both primary-error precedence and standalone descriptor-cleanup failure are now exercised with actual invalid UTF-8 bytes; the canonical reader remains fail-closed.
- **evidence:** Exact-source [Unreadable Authority Negatives #41353526485](https://github.com/m-shogo/memories-project/actions/runs/41353526485) completed **SUCCESS** on `462947ed`; job `124988614038` logs `PASS: drill reconcile reader positive, oversized, UTF-8, symlink, FIFO, directory, raced-open and double-close-fault negatives`, `Drill-request unreadable/escaped-authority negative suite PASS`, and `production decision: NO_GO`. Exact-source [Drill Request Admission #41353526449](https://github.com/m-shogo/memories-project/actions/runs/41353526449) also completed **SUCCESS**. These are synthetic Python CI checks, not production restore or current-source focused Go evidence.
- **whySafe:** Only the existing planning reconciler and its CI-reached synthetic negative suite changed. The unrelated diagnostic commit was preserved. No production evidence, credentials, traffic, promotion authority or workflow was written.
- **reusableMechanism:** Preserve primary exceptions across secondary descriptor close faults; prove both error paths using unambiguous numeric bytes and owned-FD checks; use expected-HEAD CAS after each fresh authority read.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion review `99cb895f`. Registered generations remain distinct from unsuperseded semantically eligible generations from distinct environments; preflight requires an explicitly human-approved current recovery objective. Reviewed requests are planning-only, new recovery evidence requires a current executable reviewed request, final candidates need complete typed eight-domain coverage plus independent review, and human promotion remains separate and non-automatic.

## Next safe target

Audit drill-request validator and reconciler helper imports and negative child execution for mutable-path TOCTOU, reusing the established pinned-source execution mechanism and existing CI-reached private transport fixtures. Do not retry unchanged Quay MinIO HTTP 401, workflow permission or external production-evidence blockers.
