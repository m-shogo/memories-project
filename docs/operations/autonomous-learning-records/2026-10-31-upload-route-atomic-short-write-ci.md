# Supplemental OPS learning — upload-route atomic short-write rejection (2026-10-31)

Append-only operational learning, not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or promotion evidence.

## Material failure: latent truncated atomic publication

- **symptom:** The Upload Route writer could publish a truncated staged payload if a buffered `write` returned a short count without raising. This was a source-verified latent defect, not an observed production file truncation.
- **evidence:** At `ac5193ae`, `atomic_write_bytes` called `handle.write(payload)` and ignored the returned count, then flushed, fsynced and atomically replaced the target. Prior canonical learning had already identified this same failure class in generation/objective atomic writers, so the proven count-check approach was reused for this distinct target.
- **rootCauseOrUnknown:** Verified: successful non-exceptional buffered writes were assumed complete without checking their exact integer byte count.
- **failedApproach:** Treating a non-raising `write` and `fsync` as proof that every requested byte was staged.
- **correction:** [`3e2db61d`](https://github.com/m-shogo/memories-project/commit/3e2db61dc198a409b035ee5e7e1d27e191593739) requires `type(written) is int and written == len(payload)` before flush/fsync/replace, rejecting short, boolean and missing return counts with a fail-closed `ReconcileFailure`.
- **recurrenceGuard:** The existing pre-MinIO rollback validator wraps the actual `fdopen` stream with a disposable partial-write transport. Three deterministic cases return `1`, `True` and `None` after writing one byte; each must reject publication, preserve original bytes and 0755 mode, close the stream and leave no temporary residue. The existing read-only entry-document AST validator now requires the new proof to be a direct `main` invocation exercising `module.atomic_write_bytes`.
- **retryCondition:** Revisit on writer stream/atomic publication changes, negative CI regression, or a reviewed platform-specific write contract change. Do not repeat the unchecked-write assumption or retry unchanged MinIO/permission/human-evidence blockers.

## Material safe success

- **outcome/evidence:** [Autonomous Learning Guard #41176590349](https://github.com/m-shogo/memories-project/actions/runs/41176590349) completed **SUCCESS** at exact source `3e2db61d`. Job log reports 601 direct and 601 nested learning negatives, 39 supplemental history cases, the actual Upload Route rollback negative PASS, 195 fanout synthetic cases, 1,186 helper-ancestor negatives, append-only/contract/read-only checks and `Memory OS entrypoint document validation PASS`. [Operability Contracts #41176590432](https://github.com/m-shogo/memories-project/actions/runs/41176590432) also completed SUCCESS.
- **whySafe:** Only the Upload Route Python writer, its disposable negative harness and the already CI-reachable read-only entrypoint validator changed. No workflow YAML, production evidence, credentials, traffic, readiness or human promotion was written.
- **reusableMechanism:** Check exact integer write length before fsync/replace; prove partial/noninteger return rejection using a real temporary-file stream and preserve byte/mode/cleanup invariants; bind proof invocation into existing independent CI.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs were unchanged at code HEAD: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill-request/recovery-evidence/non-resurrection/promotion registries `bfd1b045`, `f4d74f33`, `acebcd02`, `ae7e57ef`, `26bb1cc7`, `99cb895f`.
- **scoped blocker:** [Reconcile Upload Route #41176590442](https://github.com/m-shogo/memories-project/actions/runs/41176590442) failed before rollback/Go tests at unchanged MinIO bootstrap; no focused Go/HTTP success is claimed. No unchanged failed external dependency was manually retried.

## Independent source audit and next safe target

At `3e2db61d`, `snapshot_authority_files`, the `ROLLBACK_SNAPSHOT` prewrite branch, and the owned rollback preflight still use `Path.read_bytes` on mutable filesystem paths without a regular-file/nonblocking descriptor gate immediately before the read. A path replaced by a FIFO could block a snapshot/rollback reader; this is a source-verified potential hang, **not** an observed production hang. Next evaluate descriptor-pinned `O_NONBLOCK | O_NOFOLLOW` regular-file reads and deterministic FIFO negatives, preserving FD ownership and the existing rollback safety checks. Do not claim directory-fd parent-swap protection from a simple path check.

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0. Human-approved recovery objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain coverage, independent review, final candidate and human promotion remain absent.
