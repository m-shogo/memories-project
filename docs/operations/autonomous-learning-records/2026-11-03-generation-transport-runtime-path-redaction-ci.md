# Supplemental OPS learning — generation validator transport RuntimeError redaction (2026-11-03)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Synthetic read-only regression evidence only, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure class

- **symptom:** The independent Generation Evidence validator transport's initial canonical-path probe classified `OSError`, `ValueError` and `TypeError`, but not `RuntimeError` from path resolution. A synthetic symlink-loop or fault-injected `Path.resolve` could therefore escape the fixed-domain classifier.
- **evidence:** At `so` HEAD `be1a2c6b49fb59df4480f3d998046ae051d829f9`, `require_validator_identity()` used `except (OSError, ValueError, TypeError)`; the private-canary negative iterated exactly those three types. No production leak or real symlink-loop incident was observed.
- **rootCauseOrUnknown:** Verified incomplete exception family at a path preflight boundary preceding owned-FD acquisition; exploitability in a real checkout is unknown.
- **failedApproach:** Assuming the three previously tested path exception classes exhaust `Path.resolve(strict=True)` failures.
- **correction:** [`25c5982c`](https://github.com/m-shogo/memories-project/commit/25c5982c1fadbcb28996bb75bd5587cb85a5c219) adds `RuntimeError` to the fixed suppressed-context classifier and to the live `Path.resolve` private-canary negative loop.
- **recurrenceGuard:** A fourth executable synthetic exception case requires the exact `generation evidence transport validator source authority unreadable` `Fail`, suppressed context and no canary disclosure. Existing positive, invalid-FD, bounded-read, close-fault and swap tests remain.
- **retryCondition:** Revisit on changed Python path-resolution semantics, validator identity topology, exception classifier or CI reachability. Do not retry unchanged production publisher workflow permission, canonical learning large-content transport, Quay MinIO HTTP 401 or absent human evidence blockers.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41485238525](https://github.com/m-shogo/memories-project/actions/runs/41485238525) completed **SUCCESS** on exact source `25c5982c1fadbcb28996bb75bd5587cb85a5c219`. Job `125413720037` logged `PASS: generation transport pinned importer rejects invalid FDs, EOF, nonbytes, hardlink and swap; fragmented read works`, `Memory OS generation-evidence execution transport negative PASS`, and `production decision: NO_GO`.
- **evidence:** GitHub Actions conclusion, decoded job log, exact source and Git blob post-write comparison.
- **whySafe:** Only a read-only negative transport script changed; its existing CI path is `contents: read` with exact-source checkout and no persisted credentials. The production-capable writer was not modified.
- **reusableMechanism:** Keep pre-descriptor path exception classifiers aligned with real path APIs and prove each exception family by executable canary injection, not merely by a catch clause.
- **protectedAuthorityCheck:** Ten protected blobs stayed unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), registered generations `bfd1b045`, approved objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion review `99cb895f`, canonical learning `b809c69d`, mandatory learning contract `87712ea9`. Registered and semantically eligible generations remain distinct and zero; no current human-approved objective, executable reviewed request, request-bound evidence, complete eight-domain coverage or final candidate exists. Human promotion remains separate and nonautomatic; synthetic learning cannot satisfy any production gate.

## Next independent safe target

Audit Generation Evidence reconciler negative harness preflight identity and pinned fixture directory exception provenance, retaining publisher-independent exact-source validation. The real writer's path-based staging and replacement remains a separate scoped TOCTOU risk, not closed by this transport test.
