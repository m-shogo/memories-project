# Supplemental OPS learning — drill request validator JSON file-identity guard (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or semantically eligible generation, recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** The independent drill-request planning validator admitted regular JSON files without rejecting hardlinks, group/world-writable modes or in-place modification during a read. No actual malicious file or production incident was observed.
- **evidence:** At `so` HEAD `0f05a574`, `scripts/validate-memory-os-backup-restore-drill-request.py` checked only `stat.S_ISREG(os.fstat(fd).st_mode)`, the 1 MiB bound and JSON syntax after a no-follow open; it did not compare the owned FD to the pathname after reading.
- **rootCauseOrUnknown:** Verified incomplete file-identity/mode boundary; external control of production authority files is unknown.
- **failedApproach:** Treating one regular-file check and no-follow leaf open as proof of stable, single-link, non-writable authority bytes.
- **correction:** [`b0a19689`](https://github.com/m-shogo/memories-project/commit/b0a196899e438027700fd6317ca87addc026cc34) requires single-link, non-group/world-writable regular sources and matching pre/post FD and pathname identity, mode, size, mtime and ctime with complete bounded reads before parsing.
- **recurrenceGuard:** The existing CI-reached drill-request load-negative suite now tests hardlinked and writable sources, an in-place read mutation, positive restoration and the previous primary/secondary close-fault cases.
- **retryCondition:** Revisit only if the reviewed validator's JSON source or metadata rules, negative fixture or exact-source CI changes. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permission or absent external/human production evidence.

## Material success

- **outcome:** The independent drill-request validator now rejects unsafe file modes/links and in-read mutation while preserving strict JSON ambiguity and private failure handling.
- **evidence:** Exact-source [Unreadable Authority Negatives #41354111493](https://github.com/m-shogo/memories-project/actions/runs/41354111493) completed **SUCCESS** on `b0a19689`; job `124990375955` logs `PASS: actual drill request JSON reader positive, unsafe-link/mode, mutation and close-fault negatives`, `Drill-request unreadable/escaped-authority negative suite PASS`, and `production decision: NO_GO`. Exact-source [Drill Request Admission #41354111464](https://github.com/m-shogo/memories-project/actions/runs/41354111464) also completed **SUCCESS**. These are synthetic Python CI checks, not production restore, readiness or current-source focused Go evidence.
- **whySafe:** Only the existing read-only drill-request validator and CI-reached synthetic negative suite changed; no reviewed workflow, production registry, credential, traffic or human promotion authority was modified.
- **reusableMechanism:** Reuse a pre/post FD + no-follow pathname identity check, reject writable/hardlinked sources, and prove read-time mutation rejection with isolated fixtures before JSON parsing.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`. Preflight still uses only unsuperseded semantically eligible generations from distinct environments plus a current explicitly human-approved recovery objective; reviewed requests remain planning-only, generation recovery evidence must bind a current executable reviewed request, final candidates require typed eight-domain coverage and independent review, and human production promotion remains separate/non-automatic.

## Next safe target

Audit the drill-request validator and reconciler's acquired-descriptor ownership checks. Reject invalid or boolean FD returns before ownership/cleanup and prove with CI-reached negative fixtures, without modifying protected authorities.
