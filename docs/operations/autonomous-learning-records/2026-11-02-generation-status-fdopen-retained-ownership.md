# Supplemental OPS learning — generation-status retained raw-FD ownership (2026-11-02)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure 1 — untransferred mkstemp descriptor

- **symptom:** Generation-status atomic writing could leak a raw temporary FD if `os.fdopen` raised before returning a stream.
- **evidence:** At `9b06cae0`, `scripts/reconcile-memory-os-backup-restore-generation-status.py` passed the descriptor directly to `os.fdopen` and had no raw-FD cleanup in `finally`. This was a source-level latent failure; no real FD leak was observed.
- **rootCauseOrUnknown:** Verified missing explicit ownership/cleanup at the constructor exception boundary. Actual occurrence in approved production workflows is unknown.
- **failedApproach:** Assuming `fdopen` always takes ownership and closes the descriptor even when construction fails.
- **correction:** Initial [7d437a7c](https://github.com/m-shogo/memories-project/commit/7d437a7ca16d55a4c220cb568ebcc503be611e9d) added a raw-FD cleanup and negative test, then the safer retained-ownership correction below superseded it.
- **recurrenceGuard:** CI-reached negative injects an `fdopen` OSError, checks the retained descriptor is closed, checks no temporary file remains and compares protected status/contract bytes.
- **retryCondition:** Revisit only on a reviewed generation-status atomic-writer ownership change, Python stream contract change or exact-source CI regression.

## Material failure 2 — known unsafe exceptional reclose and CI reachability

- **symptom:** The initial fix attempted to close a numeric FD after a potentially ownership-transferring `fdopen` call, and its negative test was added to a standalone script not invoked by the reviewed Generation Binding CI.
- **evidence:** At `7d437a7c`, `with os.fdopen(fd, ...)` transferred stream ownership on success and an outer `finally` closed the old numeric FD on constructor failure. Existing [canonical reader FD-ownership learning](https://github.com/m-shogo/memories-project/blob/so/docs/operations/autonomous-learning-records/2026-11-01-canonical-reader-retained-fd-ownership.md) already warned of a recycled-FD close after ambiguous handoff. The reviewed `.github/workflows/backup-restore-generation-binding.yml` invokes `validate-memory-os-backup-restore-generation-status-authority-negative.py`, not the standalone reconcile-negative script.
- **rootCauseOrUnknown:** Verified known failure-class reuse without checking the specific FD-ownership lesson, plus wrong assumption about CI entrypoint reachability. An actual recycled FD was not observed.
- **failedApproach:** Unconditional exceptional numeric FD close after ambiguous `fdopen` ownership, with a test only in a non-CI-reached script.
- **correction:** [1a01edef](https://github.com/m-shogo/memories-project/commit/1a01edef4d84cd635906e490dce00cab47855726) moved the negative into the already CI-invoked authority suite. [681a8006](https://github.com/m-shogo/memories-project/commit/681a8006ac64c4de57c354b71f75aadeac408fd2) changes the writer to `os.fdopen(..., closefd=False)`, retaining raw ownership and closing the descriptor exactly once before atomic replacement; the negative now binds `closefd=False` explicitly.
- **recurrenceGuard:** Runtime negative checks explicit non-owning stream construction, a synthetic pre-effect `fdopen` failure, closed raw descriptor, zero temporary residue and unchanged protected bytes/modes. Existing approved Generation Binding workflow invokes this negative directly.
- **retryCondition:** Revisit if stream ownership, close ordering, FD reuse model, CI command topology or exact-source negative outcome changes. Do not repeat the old ambiguous-close approach or unchanged external MinIO/permission/human-evidence blockers.

## Material success and current validation

- **outcome:** Generation-status writer now retains explicit raw-FD ownership across stream use, closes once before replace, and the negative is in an existing CI-reached suite.
- **evidence:** Git comparison `9b06cae0..681a8006` changes only the existing reconciler and existing authority-negative suite. At record preparation, [Generation Binding workflow #41331300960](https://github.com/m-shogo/memories-project/actions/runs/41331300960) was pending; **no exact-source CI PASS is claimed yet**.
- **whySafe:** No protected production status, OPS-P0-007 snapshot, environment generation, recovery objective, drill request, recovery evidence, typed coverage, promotion authority, workflow, credential or traffic was modified.
- **reusableMechanism:** Prefer explicit non-owning stream (`closefd=False`) and single raw-FD close before publication; guard constructor failure with a real-descriptor negative executed through the reviewed CI entrypoint. Do not use numeric reclose after ambiguous transfer.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, objectives `f4d74f33`, requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion registry `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved recovery objectives 0, executable reviewed requests 0, request-bound evidence 0, complete typed eight-domain coverage 0 and final candidates 0. Preflight still requires unsuperseded semantically eligible generations from distinct environments and a current human-approved objective; reviewed requests are planning-only; new recovery evidence must be current executable-request-bound; complete typed eight-domain coverage and independent review are required; human promotion is separate and nonautomatic.

## Next safe target

Verify exact-source Generation Binding CI, then audit generation-evidence and promotion-review atomic writers for the same ownership gap using their existing CI-reached negative suites. Never use learning or synthetic tests to satisfy production gates.
