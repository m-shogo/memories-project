# Supplemental OPS learning — generation reconciler transport, classifier and fixture flag guards (2026-11-02)

Append-only supplemental record under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record and any synthetic test are **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved recovery objective, executable reviewed drill request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human production-promotion authority.

## Material failure / latent transport test gap

- **symptom:** The independent generation-evidence reconciler pinned-source reader had no executable regression cases for fragmented successful reads, premature EOF, non-byte reads or an oversized mocked read response.
- **evidence:** At `so` HEAD `fad0520d558967bbcee048a9aa396e6564aface3`, the reader already accumulated bounded chunks and checked source size/type, but `prove_pinned_reconciler_import` exercised a private `OSError` and empty source rather than these transport shapes. No actual incident was observed.
- **rootCauseOrUnknown:** Verified missing coverage of these four input shapes; whether a future regression would have reached production is unknown.
- **failedApproach:** Treating successful single-call reads and metadata-only negative fixtures as sufficient coverage for a chunked source reader.
- **correction:** [`25690fd2`](https://github.com/m-shogo/memories-project/commit/25690fd2dd288ded757e55a44eef20ddd7fbcda0) adds a 3-byte fragmented-read positive control and deterministic early-EOF, nonbytes and over-budget negative cases, followed by a fresh positive import.
- **recurrenceGuard:** Exact expected domain error strings, a private-data canary exclusion, restoration of `os.read` after every injection, and a final reviewed-source positive control in the existing read-only Negative Suite.
- **retryCondition:** Revisit when the pinned reader, read type/size semantics or exact-source CI visibility changes. Do not repeat unchanged Quay MinIO 401, publisher-coupled writer changes, canonical learning blob transport or missing human evidence.

## Material failure / latent classifier disclosure

- **symptom:** The harness `expect_domain_fail` included the unexpected exception's class and raw string in its public failure, potentially leaking synthetic private data into CI logs.
- **evidence:** The source before [`79652d5b`](https://github.com/m-shogo/memories-project/commit/79652d5bca69be9a0fc66ce2ee3a74ec6e7027ab) interpolated `type(exc).__name__` and `exc`. Neighboring Recovery Objectives negative classifier already used redacted diagnostics. No real secret leak was observed.
- **rootCauseOrUnknown:** Verified raw exception interpolation in this separate harness; actual private input exposure unknown.
- **failedApproach:** Assuming a negative-only assertion helper cannot publish sensitive unexpected exception text.
- **correction:** `79652d5b` normalizes unexpected exceptions to a fixed `Fail` message with suppressed context.
- **recurrenceGuard:** Executable private-canary `TypeError` test checks exact redacted message, suppressed context and absence of spurious success output; invoked from `main`.
- **retryCondition:** Revisit if negative classifier output, exception transport or workflow logging changes.

## Material failure / latent fixture safety flag gap

- **symptom:** The independent temporary-directory fixture guard checked only that `O_NOFOLLOW` and `O_DIRECTORY` names existed, accepting defined-but-zero values.
- **evidence:** At `so` HEAD `79652d5bca69be9a0fc66ce2ee3a74ec6e7027ab`, `_pinned_temporary_directory` used `hasattr` before constructing open flags. Prior pinned-importer learning had established this class of failure elsewhere. No actual platform corruption was observed.
- **rootCauseOrUnknown:** Verified name-only capability check; actual runtime exploitation unknown.
- **failedApproach:** Assuming presence of an OS constant proves an effective safety flag.
- **correction:** [`ba8740f8`](https://github.com/m-shogo/memories-project/commit/ba8740f8e35e931bfc305f708dd5be6e751677f2) requires exact positive integers for both flags.
- **recurrenceGuard:** Six executable `0`/`False`/`"inert"` negative mutations must fail before fixture creation, restore the original constants and preserve the existing parent-swap tests.
- **retryCondition:** Revisit on platform flag semantics or pinned fixture creation changes.

## Observed code-change outcomes and validation boundary

- **outcome:** Three sequential commits `25690fd2`, `79652d5b` and `ba8740f8` were written to `so`; each GitHub commit diff was fetched and confirmed to change only `scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-negative.py`. The last source SHA was `4d251cd00318990822dccb529a3cc79aa3f643fb`.
- **evidence:** GitHub commit diffs, target source readback, exact branch-head comparisons and protected blob reads. The existing `backup-restore-generation-evidence-reconcile-negative.yml` includes this script in its `so` push trigger and invokes it in a `contents: read` job; the write-capable `backup-restore-generation-evidence.yml` does not include this negative harness in its trigger.
- **whySafe:** Changes are confined to the independent read-only synthetic harness; no registry, evidence, readiness or production publisher authority was modified.
- **reusableMechanism:** Pair positive fragmented transport with negative malformed/EOF/over-budget cases, redact unexpected exceptions at the classifier boundary, and require non-inert OS safety flags before acquiring any fixture descriptor.
- **protectedAuthorityCheck:** After each code commit, verified unchanged blobs: production status `d677a1c9` (`productionDecision=NO_GO`), generation registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, canonical learning `b809c69d`, mandatory contract `87712ea9`. The code diffs contain no changes to any protected authority; prior supplemental learning also identifies unchanged OPS-P0-007 snapshot `dbaa36b0` and promotion review `99cb895f`, not independently re-fetched in this run. No production evidence or human promotion was created.
- **validation limitation:** GitHub's available commit-status response was empty and its commit workflow-run endpoint returns only PR-triggered runs, so **no exact-source CI SUCCESS is claimed** for these three commits. Diff/trigger inspection is not executable test success. CI outcome and full suite logs must be checked when available, and any failure recorded in a new append-only record.

## Next safe target

Obtain exact-source read-only Negative Suite conclusions for `25690fd2`, `79652d5b` and `ba8740f8`. Then review remaining descriptor ownership/cleanup negatives independently of the publisher-coupled Generation Evidence atomic writer. Maintain `productionDecision=NO_GO` until separate explicit human production-promotion authority is actually satisfied.
