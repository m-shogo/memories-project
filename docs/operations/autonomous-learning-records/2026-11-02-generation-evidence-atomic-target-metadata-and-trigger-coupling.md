# Supplemental OPS learning — generation evidence atomic target metadata and publisher trigger coupling (2026-11-02)

Append-only supplemental history under the canonical learning authority and mandatory autonomous-learning contract. Never treat this as production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate, or human promotion evidence.

## Material failure — atomic target metadata

- **symptom:** Generation-evidence reconciliation could open a path-resolved symlink, hardlinked target or group/world-writable existing authority for atomic replacement without rejecting unsafe target identity before staging.
- **evidence:** At prior HEAD `1b0844ae`, `scripts/reconcile-memory-os-backup-restore-generation-evidence.py::write_text` checked `path.parent.is_dir()` and derived `existing_mode` from `path.stat()` but did not reject symlinks, hardlinks or writable leaf/parent metadata. This was a verified source-level gap; no real production attack was observed.
- **rootCauseOrUnknown:** Verified use of following-stat and insufficient pre-stage metadata constraints. Actual malicious substitution is unknown.
- **failedApproach:** Assuming repository-relative resolution and an atomic rename alone establish the existing authority inode's safety.
- **correction:** [`b31c59ac`](https://github.com/m-shogo/memories-project/commit/b31c59ac23182be4112a3c96f810543e0a2bfb2b) requires an existing unique regular non-group/world-writable leaf and a non-group/world-writable real parent directory before staging.
- **recurrenceGuard:** Existing exact-source read-only `backup-restore-generation-evidence-reconcile-negative.yml` now executes fixture-isolated hardlink, symlinked leaf, writable leaf and symlinked parent rejection, checks original bytes/modes and no staged residue.
- **retryCondition:** Revisit if generation-evidence target metadata, stage, commit, cleanup, CI trigger or publisher source guards change. The new pre-stage guard is not a full TOCTOU closure; parent/leaf can still change after metadata inspection.

## Material failure — CI trigger topology

- **symptom:** The code/test commit also started the production-capable `Backup Restore Generation Evidence` publisher, despite an independently reachable read-only negative suite.
- **evidence:** After `b31c59ac`, publisher [#41382441848](https://github.com/m-shogo/memories-project/actions/runs/41382441848) ran the `validate` job with `contents: write`. The publisher workflow's `push.paths` includes `scripts/reconcile-memory-os-backup-restore-generation-evidence.py`; the read-only negative workflow includes the same script. This coupling should have been checked before committing. The publisher completed **SUCCESS**, and a fresh `so` HEAD check showed no extra publication commit.
- **rootCauseOrUnknown:** Verified workflow trigger coupling and incomplete pre-write topology review in this execution. No protected authority drift was observed; whether an alternate future publisher event could change an authority depends on genuine evidence and source guards, not this synthetic test.
- **failedApproach:** Checking only the read-only workflow's trigger coverage without also checking every write-capable workflow triggered by the same path.
- **correction:** Do not make further generation-evidence reconciler or writer-authority changes until both read-only and write-capable path-trigger topology and permission scope have been reviewed. Existing workflow permission/write blocker remains scoped; no workflow edit was attempted.
- **recurrenceGuard:** Mandatory pre-write audit must enumerate all `push.paths` and job-level `permissions` for a target path, not merely the desired read-only workflow. A new executable workflow guard was not added because the permission-safe workflow-edit path is not established; do not claim it was.
- **retryCondition:** Retry this code surface only with an explicitly reviewed publisher-coupled execution plan or a proven independent read-only trigger path and changed workflow permission condition. Do not repeatedly retry unchanged workflow writes, MinIO HTTP 401 or absent external/human production evidence.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41382441974](https://github.com/m-shogo/memories-project/actions/runs/41382441974) completed **SUCCESS** at exact source `b31c59ac`; job `125075962954` logged `PASS: generation evidence atomic target hardlink/symlink/writable-parent guards`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. [Generation Evidence Rollback Diagnostics Negative #41382441899](https://github.com/m-shogo/memories-project/actions/runs/41382441899), [Unreadable Authority Negatives #41382441929](https://github.com/m-shogo/memories-project/actions/runs/41382441929), [Non-Resurrection Admission #41382441941](https://github.com/m-shogo/memories-project/actions/runs/41382441941) and the publisher [#41382441848](https://github.com/m-shogo/memories-project/actions/runs/41382441848) also completed **SUCCESS** on the same HEAD.
- **evidence:** Observed exact-source job conclusions and targeted negative log. The publisher completed without moving the branch HEAD. These are code/CI observations only, not production recovery evidence.
- **whySafe:** The metadata negative uses disposable files and compares canonical authority bytes/modes. The production-capable workflow's execution was not desired, but its observed result did not change the protected authorities; do not infer that running such publishers is generally safe.
- **reusableMechanism:** Pre-stage exact leaf/parent metadata checks plus negative canaries; for process safety, audit both read-only and publisher trigger topology before any write.
- **protectedAuthorityCheck:** Compared starting `c6bcdb85` to code HEAD `b31c59ac`: canonical learning `b809c69d`, mandatory learning contract `87712ea9`, production status `d677a1c9`, OPS-P0-007 snapshot `dbaa36b0`, generation `bfd1b045`, recovery objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, and human promotion review `99cb895f` are byte-identical. `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved current objective 0, executable reviewed request 0, request-bound recovery 0, complete typed eight-domain coverage 0, final candidate 0. Human production promotion remains separate and nonautomatic.

## Next safe target

Avoid further publisher-coupled generation-evidence script changes under unchanged conditions. Audit a distinct, read-only CI-reachable path with complete trigger topology, or verify previously pending exact-source CI outcomes without modifying any production authority.
