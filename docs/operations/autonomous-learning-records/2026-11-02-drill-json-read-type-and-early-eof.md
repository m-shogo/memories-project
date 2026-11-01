# Supplemental OPS learning — drill JSON read-result and early-EOF guards (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or semantically eligible generation, recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** The two drill-request JSON readers accepted any truthy `os.read` result for `bytearray.extend` and treated any falsy result as EOF. A substituted list of integers could be silently interpreted as authority bytes, while `None` or a string could produce inconsistent failure classes. No real OS read returned these values or production incident was observed.
- **evidence:** At `so` HEAD `21e6e561`, `scripts/validate-memory-os-backup-restore-drill-request.py` and `scripts/reconcile-memory-os-backup-restore-drill-request.py` had no exact `bytes` check after `part = os.read(...)`. The already installed pre/post identity and complete-size checks rejected premature EOF but did not reject nonbytes before parsing.
- **rootCauseOrUnknown:** Verified unchecked read-result type boundary. External runtime substitution is unknown.
- **failedApproach:** Assuming a truthy result from the read transport is always raw bytes and a falsy result is necessarily genuine EOF.
- **correction:** [`5cff4f38`](https://github.com/m-shogo/memories-project/commit/5cff4f38696844b572bcbc20b0df91a54e81c415) requires `type(part) is bytes` before any EOF or buffer handling in both readers.
- **recurrenceGuard:** The existing CI-reached drill-request load-negative suite injects `None`, private-marker string, integer list and boolean results into each reader and checks exact fixed-class rejection; an immediate `b""` on a nonempty source must fail the existing complete-size identity check. Normal positive reads, invalid acquired FD, mode/link, mutation and cleanup-fault tests remain active.
- **retryCondition:** Revisit only if reviewed read transport, byte limits, EOF semantics or CI-reached negative fixtures change. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permissions or missing external/human evidence.

## Material success

- **outcome:** Both bounded JSON readers now reject nonbytes read results before buffer mutation, and early EOF cannot be accepted as a complete authority snapshot.
- **evidence:** Exact-source [Unreadable Authority Negatives #41354695784](https://github.com/m-shogo/memories-project/actions/runs/41354695784) completed **SUCCESS** on `5cff4f38`; job `124992156535` logs `PASS: actual drill request JSON reader positive, invalid-FD/read, early-EOF, mode/link and close-fault negatives`, `PASS: drill reconcile reader positive, invalid-FD/read, early-EOF, mode/link and close-fault negatives`, `Drill-request unreadable/escaped-authority negative suite PASS` and `production decision: NO_GO`. Exact-source [Drill Request Admission #41354695864](https://github.com/m-shogo/memories-project/actions/runs/41354695864) also completed **SUCCESS**. These are synthetic Python CI checks, not production recovery or current-source focused Go evidence.
- **whySafe:** Only the existing read-only validator, planning reconciler and CI-reached negative suite changed; no workflow, production evidence, credential, traffic, protected registry or human promotion authority was modified.
- **reusableMechanism:** Check exact read-result type before EOF handling, then prove both invalid types and early EOF with an isolated negative fixture; retain pre/post identity and complete-size guards.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`. Registered generations remain distinct from unsuperseded semantically eligible generations from distinct environments; preflight requires an explicitly human-approved current recovery objective; reviewed requests are planning-only; new recovery evidence binds a current executable reviewed request; final candidates require complete typed eight-domain coverage and independent review; human production promotion remains separate/non-automatic.

## Next safe target

Audit the drill-request reconciler's parent-directory symlink/permission boundary and canonical helper import TOCTOU, reusing existing no-follow/pinned-source tests. Preserve all protected authorities and avoid unchanged external blockers.
