# Supplemental OPS learning — generation writer-authority read-only trigger gap (2026-11-02)

Append-only scoped blocker record under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate, or promotion evidence.

## Material failure / blocker

- **symptom:** The standalone generation-evidence writer-authority validator still loads reviewed Python modules with `SourceFileLoader.exec_module` after a pathname check, but a direct code change would trigger the production-capable Generation Evidence publisher workflow without independently triggering its read-only counterpart.
- **evidence:** On current `so`, `scripts/validate-memory-os-backup-restore-generation-evidence-writer-authority.py::load_module` uses `spec_from_file_location` and `spec.loader.exec_module`. `.github/workflows/backup-restore-generation-evidence.yml` includes that script and its negative suite in push triggers and has a `contents: write` publication job. `.github/workflows/backup-restore-generation-evidence-readonly.yml` invokes both validators but its exact push/PR trigger list omits their paths. Both workflow source blobs were read; no workflow write was attempted.
- **rootCauseOrUnknown:** Verified static path-reopen gap and exact trigger asymmetry. Whether an attacker ever swapped executable source or whether a future publisher would mutate protected authority is unknown.
- **failedApproach:** Relying on the existing read-only workflow's runtime invocation as proof of exact-source CI reachability for a change to the writer-authority scripts. The code was not modified and no unsafe publisher dispatch was attempted.
- **correction:** Scoped blocker: defer writer-authority import changes until a reviewed, permission-safe, exact-source read-only trigger path is established. Existing publisher guard, status and human authority remain untouched.
- **recurrenceGuard:** Require an independent read-only CI workflow with exact source SHA and trigger coverage for both writer-authority scripts before applying pinned-source import changes; verify the workflow's event, branch, job and permission semantics and test an after-capture parent swap. No executable guard was added in this scoped audit.
- **retryCondition:** Retry when workflow-file write permission or a separate approved read-only execution path materially changes, or when an independently reviewed existing trigger becomes available. Do not repeatedly retry unchanged workflow-write permissions, MinIO 401, canonical large-blob transport or absent human recovery evidence.

## Material success / safe continuation

- **outcome:** Identified the vulnerable helper import and the exact read-only/publisher trigger mismatch without making an unsafe authority or workflow mutation. Independent recovery-objective code/test hardening proceeded in this run instead.
- **evidence:** GitHub file reads of the two workflows and writer-authority validator; successful exact-source Recovery Objectives Reconcile Negative #41374133591, #41374288619, and #41374454023 from the separate safe target.
- **whySafe:** Read-only investigation; no workflow, publisher, production authority, generation, objective, drill request, typed evidence, credential, traffic, readiness or promotion record changed.
- **reusableMechanism:** Audit both CI invocation and path-trigger topology before hardening executable imports; separate a scoped permission blocker from independent safe work.
- **protectedAuthorityCheck:** Production Status `d677a1c9` remains `NO_GO`, OPS-P0-007 snapshot `dbaa36b0` remains blocked; generation `bfd1b045`, objectives `f4d74f33`, drill `acebcd02`, evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f` and learning contract `87712ea9` are unchanged. Distinct registered versus semantically eligible unsuperseded environments, human-approved current objective, executable reviewed request, request-bound recovery, complete typed eight-domain coverage, independent review and separate nonautomatic human promotion remain mandatory.

## Next safe target

Audit the remaining recovery-objective read/write transaction boundaries using the existing exact-source read-only negative suite. Do not attempt a writer-authority workflow edit without a changed permission/retry condition.
