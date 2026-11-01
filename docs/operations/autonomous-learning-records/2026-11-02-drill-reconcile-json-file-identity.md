# Supplemental OPS learning — drill reconcile JSON identity and mode guard (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or semantically eligible generation, recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** The drill-request planning reconciler accepted a regular JSON file even if hardlinked or group/world-writable, and did not verify that the file identity, size, mode and timestamps remained unchanged while reading. No actual attacker or production incident was observed.
- **evidence:** At `so` HEAD `349f5737`, `read_text` required only `stat.S_ISREG(os.fstat(fd).st_mode)` and a 1 MiB bound, then decoded the bytes without comparing pre-read, post-read and pathname metadata.
- **rootCauseOrUnknown:** Verified incomplete source-file trust boundary. External control of canonical production authority files is unknown.
- **failedApproach:** Treating no-follow leaf opening and a one-time regular-file check as sufficient for stable, single-link, non-writable authority bytes.
- **correction:** [`343abe19`](https://github.com/m-shogo/memories-project/commit/343abe197aec1b85f42d8d3554955c94ab24f2b0) rejects hardlinks and group/world-writable files and requires matching pre/post FD and pathname identity, mode, size, mtime and ctime with a complete bounded read.
- **recurrenceGuard:** The existing CI-reached drill-request load-negative suite exercises hardlink and writable-mode rejection, in-place mutation during a pinned FD read, positive restoration and the earlier double-close-fault cases. The new check runs before decoding, so a race cannot be mistaken for an ordinary JSON parse outcome.
- **retryCondition:** Revisit only when reviewed JSON reader semantics, file-identity metadata, CI fixtures or canonical authority layout change. Do not retry unchanged MinIO HTTP 401, workflow permission or external production evidence blockers.

## Material success

- **outcome:** The drill-request reconciler now refuses unsafe hardlink/mode sources and detected in-read mutations while preserving the canonical positive read and prior private error behavior.
- **evidence:** Exact-source [Unreadable Authority Negatives #41353886196](https://github.com/m-shogo/memories-project/actions/runs/41353886196) completed **SUCCESS** on `343abe19`; job `124989686292` logs `PASS: drill reconcile reader positive, unsafe-link/mode, in-read mutation and private close-fault negatives`, `Drill-request unreadable/escaped-authority negative suite PASS` and `production decision: NO_GO`. Exact-source [Drill Request Admission #41353886230](https://github.com/m-shogo/memories-project/actions/runs/41353886230) also completed **SUCCESS**. These are synthetic Python CI checks, not production or current-source focused Go evidence.
- **whySafe:** Only the existing planning reconciler and its CI-reached synthetic negative suite changed. The publisher retained its bounded source check; no protected production status, registry, credential, traffic or human promotion authority was changed.
- **reusableMechanism:** For a bounded authority read, compare FD pre/post metadata with a no-follow pathname observation; reject hardlinks and writable modes and prove mid-read mutation rejection in an isolated negative fixture.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs remained unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`. Preflight still requires unsuperseded semantically eligible generations from distinct environments and a current explicitly human-approved recovery objective; reviewed requests remain planning-only, new recovery evidence requires a current executable reviewed request, final candidates require typed eight-domain coverage and independent review, and human promotion remains separate/non-automatic.

## Next safe target

Apply the same file-identity and mode-race audit to the independent drill-request validator JSON reader using its existing CI-reached negative suite, without modifying protected authorities or reviewed workflows.
