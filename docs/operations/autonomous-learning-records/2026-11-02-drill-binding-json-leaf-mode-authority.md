# Supplemental OPS learning — pinned planning JSON leaf mode authority (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** Two pinned drill-generation-binding planning JSON readers accepted group/world-writable JSON leaf files and did not explicitly bind permission mode into the pre/post leaf descriptor and pathname identity. No malicious JSON modification or production incident was observed.
- **evidence:** Starting `so` HEAD `62894ef2` enforced no-follow, regular-file/single-link, size, content and parent-directory identity, but `before.st_mode` was only checked for regular-file type and leaf `identity` omitted `st_mode`. Existing JSON negative fixtures did not cover writable leaf or mid-read leaf chmod.
- **rootCauseOrUnknown:** Verified writable JSON leaf admission gap; actual exploitability in a real checkout is unknown.
- **failedApproach:** Treating pinned, stable inode/size/timestamps and non-writable parents as sufficient planning authority even when the JSON file itself could be modified by another user/group.
- **correction:** [`83c81a06`](https://github.com/m-shogo/memories-project/commit/83c81a061ae83d5d1bfb0cab2e7cddda623851d0) rejects `before.st_mode & 0o022` for both independent JSON readers and includes `st_mode` in their pre/post FD, leaf and final lexical pathname identity tuples.
- **recurrenceGuard:** The established CI-reached drill-generation-binding reconcile negative suite now chmods an isolated JSON authority to group/world-writable mode and requires rejection, and separately changes its mode during pinned `os.read` and requires a changed-source rejection. Each case restores the original mode; prior positive, parent, symlink, hardlink, bounded-read and cleanup controls remain.
- **retryCondition:** Revisit only when canonical JSON file-mode policy, pinned reader identity, fixture semantics or exact-source CI changes. Do not retry unchanged MinIO HTTP 401, workflow-write permissions or missing real production evidence.

## Material success

- **outcome:** Both pinned planning JSON readers reject writable JSON leaves and leaf-mode changes during acquisition before treating bytes as canonical authority.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41346009918](https://github.com/m-shogo/memories-project/actions/runs/41346009918) completed **SUCCESS** for code HEAD `83c81a06`. Job `124965853090` logs show `PASS pinned JSON` with `writable JSON leaf, leaf mode race`, `Drill generation eligibility binding reconcile negative suite PASS` and `production decision: NO_GO`. This is synthetic Python CI, not a non-skipped current Go test, real production restore or readiness evidence.
- **whySafe:** Only two existing JSON reader helpers and their disposable CI-reached negative fixtures changed. Canonical read-only JSON positive controls still pass. No production status, recovery registry, evidence, credential, traffic, workflow permission or human promotion authority changed.
- **reusableMechanism:** For canonical planning JSON, check file permission mode before accepting a pinned read and include mode in pre/post FD and lexical pathname identity; pair writable-file and mid-read chmod negatives with an unchanged valid JSON positive case.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs remained unchanged after the code commit: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, recovery objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain non-resurrection `26bb1cc7`, human promotion review `99cb895f`. Registered and unsuperseded semantically preflight-eligible generations remain distinct; preflight requires distinct environments and an explicitly human-approved current recovery objective. Reviewed requests remain planning-only; new generation evidence stays bound to current executable reviewed requests, and final candidates require complete typed eight-domain coverage, independent review and separate human promotion.

## Next safe target

Audit child-validator subprocess path TOCTOU and safe pinned execution semantics before changing its CLI transport. An approved historical pre-MinIO focused Go test exists in `parser-process-group-reaping.yml`, but its last persisted PASS source is `24d9cd3f` (2026-09-03), not current `so`; do not treat that historical synthetic result as current-source or production evidence.
