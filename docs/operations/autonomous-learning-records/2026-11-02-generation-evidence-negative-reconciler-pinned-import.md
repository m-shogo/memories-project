# Supplemental OPS learning — generation evidence negative-harness reconciler pinned import (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, request-bound recovery, typed eight-domain non-resurrection, independent review, final-candidate or human-promotion evidence.

## Material failure

- **symptom:** The CI-reachable generation-evidence reconcile negative harness loaded its canonical reconciler by `spec.loader.exec_module` after pathname inspection, leaving an unpinned module-source TOCTOU gap. No actual adversarial swap or production incident was observed.
- **evidence:** Before [2d3480c0](https://github.com/m-shogo/memories-project/commit/2d3480c0da1b5f65189d88c2bda112b540238308), `scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-negative.py::load_reconciler` used `spec_from_file_location` and `spec.loader.exec_module` without an owned-FD source snapshot.
- **rootCauseOrUnknown:** Verified loader pathname reopening in the test harness; whether an actual source swap occurred on a CI runner is unknown.
- **failedApproach:** Assuming the reconciler's internal hardened writer import also protected the separate outer negative harness importer.
- **correction:** [2d3480c0](https://github.com/m-shogo/memories-project/commit/2d3480c0da1b5f65189d88c2bda112b540238308) binds the exact reviewed reconciler path to owned no-follow directory/file descriptors, checks parent/leaf identity, mode, link count and bounded source bytes, and executes the captured bytes directly instead of loader pathname reopening.
- **recurrenceGuard:** The same CI-reachable negative harness now executes a positive pinned synthetic module, rejects a writable synthetic source, and swaps the parent to a malicious symlink after source capture. The trusted captured module must execute while the redirected canary remains unchanged.
- **retryCondition:** Revisit if the negative-harness import implementation, reviewed reconciler path, source-byte binding, or exact-source CI behavior changes. Do not retry unchanged MinIO HTTP 401, workflow permission or human approval blockers.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41372401953](https://github.com/m-shogo/memories-project/actions/runs/41372401953) completed **SUCCESS** on exact code HEAD `2d3480c0`. Job #125045455151 logs `PASS: generation evidence negative reconciler importer pinned after parent swap`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. [Backup Restore Admission Chain #41372401985](https://github.com/m-shogo/memories-project/actions/runs/41372401985) also completed SUCCESS on that source.
- **evidence:** Observed GitHub Actions run conclusions and job log; this is synthetic validation, not production recovery evidence.
- **whySafe:** Only the existing read-only negative test harness changed; no canonical generation/objective/drill/recovery registry, Production Status, workflow, credential, traffic or promotion authority was modified.
- **reusableMechanism:** Apply the same reviewed source-pinning boundary to test-harness importers as to production-adjacent reconciler helpers, with an after-capture parent-swap negative and a writable-source negative.
- **protectedAuthorityCheck:** Canonical Production Status `d677a1c9` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b0` remains `PREREQUISITES_BLOCKED`. Environment registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, generation binding `cf965325`, evidence contract `57e5e7e5`, objectives admission `be0b4604`, learning contract `87712ea9`, typed eight-domain registry `26bb1cc7` and human promotion registry `99cb895f` remain unchanged. Preflight still requires distinct unsuperseded semantically eligible environments and a current human-approved objective. Reviewed requests remain planning-only; request-bound recovery evidence, complete typed eight-domain coverage, independent review and separate human production promotion remain mandatory.

## Next safe target

Audit the recovery-objectives negative harness's own reconciler module importer for mutable-path reopening. Preserve append-only learning and all production authorities.
