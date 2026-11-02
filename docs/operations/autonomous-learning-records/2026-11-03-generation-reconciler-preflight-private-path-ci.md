# Supplemental OPS learning — generation reconciler preflight private-path redaction (2026-11-03)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Synthetic read-only test evidence only; not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered generation, human-approved objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or promotion evidence.

## Material failure class

- **symptom:** The independent Generation Evidence reconcile negative harness could propagate private filesystem exceptions from `RECONCILER.is_file()` or `RECONCILER.resolve(strict=True)` before its pinned-source read exception classifier.
- **evidence:** At `so` HEAD `fc0cd85f774a9d0e075929c72ca5e709997ac81f`, `require_reconciler_identity()` directly called both path methods without a classifier; the later `pinned_reconciler_source()` `try` began only after that call. This was a verified static/fault-injection gap, not an observed production disclosure.
- **rootCauseOrUnknown:** Verified missing pre-descriptor private-error classification. Whether an actual hostile filesystem could exploit this in CI is unknown.
- **failedApproach:** Treating the later descriptor-pinned importer `except` as sufficient protection for earlier lexical path probes.
- **correction:** [`9ee3a70a`](https://github.com/m-shogo/memories-project/commit/9ee3a70a3048d382eff769e836fa3a65b8b18cf3) normalizes `OSError`, `ValueError`, `TypeError`, and `RuntimeError` to fixed `generation evidence reconciler source authority drift` with suppressed context.
- **recurrenceGuard:** Two disposable negative fixtures inject a private-canary `OSError` through `Path.is_file` and a private-canary `RuntimeError` through `Path.resolve`, verify the hook actually fired, require exact fixed `Fail` and suppressed context, forbid canary disclosure, and restore each method. Existing source FD, read, cleanup, parent-swap and transaction tests remain.
- **retryCondition:** Revisit when reconciler import identity, Python path exception behavior, CI workflow or source-lease authority changes. Do not retry unchanged production-capable workflow write permissions, Quay MinIO HTTP 401, large canonical learning contents-API update or absent human evidence blockers.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41485568541](https://github.com/m-shogo/memories-project/actions/runs/41485568541) completed **SUCCESS** on exact code HEAD `9ee3a70a3048d382eff769e836fa3a65b8b18cf3`. Job `125414873156` logged `PASS: generation evidence negative reconciler importer pinned after parent swap`, `PASS: generation reconcile fixture private OS/value/type errors redacted`, and `production decision: NO_GO`.
- **evidence:** Exact-source GitHub Actions run conclusion, decoded job log, committed source and protected Git blob comparison.
- **whySafe:** Only an independent read-only negative harness changed. The workflow has `contents: read`, exact-source checkout and disposable fixture cleanup; no production-capable writer or evidence authority was modified.
- **reusableMechanism:** Classify pre-FD path failures before invoking pinned imports; pair both a metadata and resolution-loop fault with a fixed private-domain assertion, then confirm exact-source CI.
- **protectedAuthorityCheck:** Ten protected blobs remained unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), environment generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion review `99cb895f`, canonical learning `b809c69d`, learning contract `87712ea9`. Registered and semantically preflight-eligible generations remain distinct and zero; no current approved objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain coverage or final candidate exists. Human production promotion is separate and nonautomatic; learning cannot satisfy production gates.

## Next independent safe target

Inspect the same negative harness's pinned temporary-fixture preflight, particularly root path metadata and `relative_to` exception cause suppression, before any directory FD acquisition. Keep Generation Evidence writer path-based atomic Stage/Replace/Cleanup as a separate scoped TOCTOU risk, not fixed by these read-only import tests.
