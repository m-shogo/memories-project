# Supplemental OPS learning — generation transaction preflight private-path normalization (2026-11-03)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This synthetic read-only record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered generation, human-approved objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure class

- **symptom:** The generation-evidence transaction negative harness's initial writer-path identity check could propagate private filesystem errors before descriptor-pinned source acquisition.
- **evidence:** At initial `so` HEAD `f78a5789b30c1fc515309270ece1b26a1607b529`, `require_writer_identity()` directly called `WRITER.is_file()` and `WRITER.resolve(strict=True)` outside any exception classifier. The later pinned-reader `try` could not normalize an exception thrown at that earlier boundary. This was an identified synthetic fault-injection gap, **not** an observed production leak.
- **rootCauseOrUnknown:** Verified absence of private exception normalization at the pre-descriptor path metadata boundary; real-world exploitability and sensitive data disclosure are unknown.
- **failedApproach:** Assuming the subsequent descriptor-pinned read and its private error handling also protect path probes that execute before entering the reader's `try`.
- **correction:** [`be1a2c6b`](https://github.com/m-shogo/memories-project/commit/be1a2c6b49fb59df4480f3d998046ae051d829f9) wraps the exact identity probe and converts `OSError`, `ValueError`, `TypeError` and `RuntimeError` to the fixed `source authority drift` domain failure with suppressed context.
- **recurrenceGuard:** Two executable, disposable-fixture negative cases inject a private-canary `OSError` separately through `Path.is_file` and `Path.resolve`, require the fixed `Fail` and `__suppress_context__`, assert no canary in the visible diagnostic, verify the hook was actually invoked, and restore the original methods. Existing positive, descriptor ownership, bounded read, chmod, parent swap and rollback cases remain.
- **retryCondition:** Revisit when canonical writer-path identity checks, filesystem exception behavior, negative harness import topology or CI reachability changes. Do not retry unchanged publisher workflow permissions, Quay MinIO HTTP 401, canonical 4.17 MB learning contents-API transport or absent human evidence blockers.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41484858700](https://github.com/m-shogo/memories-project/actions/runs/41484858700) completed **SUCCESS** on exact source `be1a2c6b49fb59df4480f3d998046ae051d829f9`. Job `125412374853` logged `generation evidence registry transaction negative PASS`, pinned writer importer PASS, and `production decision: NO_GO`.
- **evidence:** Exact GitHub Actions run conclusion, decoded job log, committed source readback and protected Git blob inventory.
- **whySafe:** Only an independent read-only negative harness changed. Its workflow uses `contents: read`, exact-source checkout and disposable fixtures. The production-capable Generation Evidence publisher is not triggered by this harness path; no evidence or readiness authority was written.
- **reusableMechanism:** Normalize path preflight errors before any FD acquisition, prove each independent path method's private exception boundary with a live synthetic hook, and retain exact-source CI plus protected-authority verification.
- **protectedAuthorityCheck:** Ten protected blob SHAs remained unchanged: production status `d677a1c9` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), registered environment generations `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion review `99cb895f`, canonical learning `b809c69d`, mandatory learning contract `87712ea9`. Registered/semantically eligible generations remain distinct and empty; no current human-approved objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain coverage, independent final candidate or human production promotion is established. Learning and synthetic tests cannot satisfy any production, recovery or promotion gate.

## Next independent safe target

Audit the neighboring read-only generation-evidence validator transport for path-resolution `RuntimeError` redaction and exact-source CI. The real Generation Evidence writer still has path-based staging/replacement and remains a separate scoped TOCTOU issue; no writer fix is claimed here.
