# Supplemental OPS learning — Upload Route fdopen descriptor ownership (2026-10-31)

Append-only operational learning only; not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure: latent descriptor leak before stream ownership

- **symptom:** `atomic_write_bytes` staged a descriptor with `tempfile.mkstemp` and entered `with os.fdopen(descriptor, "wb")`. If `fdopen` failed before returning a stream, the `finally` removed the temporary pathname but never closed the raw descriptor. This is a source-proven latent resource leak, **not** an observed production leak.
- **evidence:** At parent `fbedf539`, the writer had no descriptor cleanup between `mkstemp` and `fdopen`. A disposable local Python probe created a descriptor, simulated failure before `fdopen` acquired it, removed the temporary pathname and confirmed `os.fstat(fd)` still succeeded until explicit `os.close(fd)`.
- **rootCauseOrUnknown:** Verified ownership-transfer gap: the `with` context manager only closes a successfully returned stream; `finally: temporary.unlink` closes no file descriptor.
- **failedApproach:** Treating temporary pathname cleanup as sufficient resource cleanup even when stream construction fails.
- **correction:** [af6c87db](https://github.com/m-shogo/memories-project/commit/af6c87dbe67388f63a9ee57654e0289e133b1ee3) explicitly closes the raw descriptor on `fdopen` acquisition failure, suppressing only an `OSError` from closing a descriptor already closed by `fdopen`, then re-raises the original exception. Successful stream ownership, mode preservation, `fsync`, `os.replace` and existing rollback semantics remain unchanged.
- **recurrenceGuard:** A disposable `prove_atomic_fdopen_failure_cleanup` negative captures the real `mkstemp` descriptor, injects `fdopen` failure, asserts `EBADF` on `fstat`, unchanged 0755 mode and bytes, and no temporary residue. The existing pre-MinIO CI entrypoint AST-requires a single direct `main` invocation and actual `module.atomic_write_bytes` transport; the real suite runs with exact PASS stdout and empty stderr.
- **retryCondition:** Revisit if the staged-descriptor acquisition, file stream lifecycle, temporary cleanup or CI proof call graph changes. Directory-fd/no-follow and path-check-to-rename races remain separate, explicitly unproven work; do not retry unchanged external MinIO HTTP 401.

## Material safe success

- **outcome:** The raw descriptor is closed on `fdopen` failure, and the failure path is independently regression-tested in a MinIO-free CI chain.
- **evidence:** [Autonomous Learning Guard #41174738048](https://github.com/m-shogo/memories-project/actions/runs/41174738048) **SUCCESS** on exact source `af6c87db`; append-only, contract/negative execution, independent helper-ancestor reachability and read-only job steps all succeeded. [Reconcile Upload Route Authority #41174738166](https://github.com/m-shogo/memories-project/actions/runs/41174738166) failed at the unchanged `Start local MinIO` step; focused Go/HTTP tests were skipped and cannot be claimed as passed.
- **whySafe:** The change only affected the Upload Route reconciler's exceptional descriptor cleanup, its disposable negative and the existing read-only CI entrypoint. No workflow YAML, real production/recovery evidence, credentials, traffic, approval or promotion authority was mutated. The reconciler was not executed against production by this task.
- **reusableMechanism:** Make descriptor ownership transfer explicit and close any untransferred resource on acquisition failure; fault-inject the exact boundary, verify `EBADF`, and prove no byte/mode/residue side effects.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs remained unchanged after `af6c87db`: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill-request/recovery-evidence/non-resurrection/promotion registries `bfd1b045`, `f4d74f33`, `acebcd02`, `ae7e57ef`, `26bb1cc7`, `99cb895f`. CI/learning are never admission evidence.

## Strict production boundary and next safe target

`productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with registered/semantically preflight-eligible generations 0/0. Preflight requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current recovery objective. Reviewed drill requests are planning-only; generation recovery evidence must be bound to a current executable reviewed request; final production-equivalent recovery candidates additionally require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion review remains separate and non-automatic.

Next safe target: investigate directory-fd/no-follow protection against path-check-to-rename races, then strengthen independent pre-MinIO Focused Go test reachability and supplemental-learning-only Push/PR append-only CI coverage when workflow authority permits. No full-chain exact-source SUCCESS is asserted for this learning-only commit.
