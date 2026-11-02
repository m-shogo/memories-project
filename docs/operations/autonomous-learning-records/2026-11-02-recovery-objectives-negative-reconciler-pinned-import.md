# Supplemental OPS learning — recovery objective negative-harness reconciler pinned import (2026-11-02)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. It is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, approved-objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, final-candidate or human-promotion evidence.

## Material failure

- **symptom:** The CI-reached recovery-objective reconcile negative harness still executed the reconciler module through `SourceFileLoader.exec_module` after a mutable pathname check. This was a source-level TOCTOU gap, not an observed real-world exploit.
- **evidence:** Before [a77738c2](https://github.com/m-shogo/memories-project/commit/a77738c260011acac8ab90440479811cd8d47675), `scripts/validate-memory-os-recovery-objectives-reconcile-negative.py::load_reconciler` used `spec_from_file_location` then `spec.loader.exec_module`, independently of the now-pinned canonical writer importer.
- **rootCauseOrUnknown:** Verified: the outer negative harness had a separate pathname-based module import. Whether the file was ever swapped during a real CI execution is unknown.
- **failedApproach:** Assuming a protected nested writer importer also protected the negative harness's own outer reconciler loader.
- **correction:** [a77738c2](https://github.com/m-shogo/memories-project/commit/a77738c260011acac8ab90440479811cd8d47675) binds the reviewed reconciler path to owned no-follow directory and leaf descriptors, checks stable mode, inode, size and parent identity, reads bounded bytes, and executes only the captured source.
- **recurrenceGuard:** The existing CI-reachable negative suite now proves a real positive synthetic module import, rejects group/other-writable source, and swaps the parent to a redirected executable canary after source capture. It requires execution of the trusted snapshot and unchanged canary bytes.
- **retryCondition:** Revalidate when the reconciler import mechanism, reviewed path, source capture or exact-source CI changes. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permissions, or missing human production evidence.

## Material success

- **outcome:** [Recovery Objectives Reconcile Negative #41372760738](https://github.com/m-shogo/memories-project/actions/runs/41372760738) completed **SUCCESS** on exact code HEAD `a77738c2`. Job #125046560176 logs `PASS: recovery objective negative reconciler importer pinned after parent swap`, `Recovery objective reconcile negative suite PASS`, and `production decision: NO_GO`. [Recovery Objectives Admission #41372760749](https://github.com/m-shogo/memories-project/actions/runs/41372760749) also completed SUCCESS on that source.
- **evidence:** GitHub Actions run conclusions and observed job logs, not only source-level CI reachability.
- **whySafe:** Only the read-only synthetic negative harness changed; no workflow, Production Status, generation/objective/drill/evidence/typed non-resurrection registry, credential, traffic or human promotion authority was modified.
- **reusableMechanism:** Review outer test-harness importers separately from inner production-adjacent helpers; pin reviewed module bytes and prove after-capture parent swaps cannot redirect execution.
- **protectedAuthorityCheck:** Twelve protected Git blobs unchanged: Production Status `d677a1c9` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b0` remains `PREREQUISITES_BLOCKED`; generation registry `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, binding contract `cf965325`, evidence contract `57e5e7e5`, objectives admission contract `be0b4604`, typed non-resurrection `26bb1cc7`, human promotion `99cb895f` and learning contract `87712ea9` remain unchanged. Registered generations are distinct from unsuperseded semantically eligible generations; preflight requires distinct environments and an explicitly human-approved current objective; reviewed drill requests are planning-only; recovery evidence requires current executable reviewed request; final candidates require typed eight-domain coverage and independent review; human promotion is separate/non-automatic.

## Next safe target

Audit other CI-reachable negative harness importers and validate that source-pinning guards reject mid-read parent changes and descriptor ownership faults, without duplicating production authority.
