# Supplemental OPS learning — generation-binding transport non-OS private read CI (2026-11-02)

Append-only supplemental learning under canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Neither learning nor synthetic CI satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human production-promotion authority.

## Material failure mode / coverage gap

- **symptom:** The independently read-only generation-binding transport pinned validator importer normalized `OSError` but could expose private `ValueError`/`TypeError` diagnostics from the same source-reader boundary.
- **evidence:** Before [`e24194dc`](https://github.com/m-shogo/memories-project/commit/e24194dc3cb685ee896ba99a192deffbd4e2ca19), `pinned_validator_source` caught only `OSError`; the harness tested EOF, nonbytes and over-budget responses but no injected private reader exceptions. No actual private leak or production incident was observed.
- **rootCauseOrUnknown:** Verified exception-type normalization and negative-coverage gap in this distinct source importer; actual runtime occurrence unknown.
- **failedApproach:** Assuming OSError-only classification or an equivalent test in a neighboring importer proves this loader's exception boundary; avoiding an unqualified broad catch that previously masked fixed-domain `Fail`.
- **correction:** `e24194dc` normalizes `(OSError, ValueError, TypeError)` to the fixed private `pinned source unreadable` error and injects three private canary reader exceptions.
- **recurrenceGuard:** Every injected exception must yield the exact private `Fail`, suppressed context, no canary leakage and restored `os.read`. Existing fragmented positive, malformed FD, close-fault precedence, EOF, nonbytes, over-budget, hardlink and parent-swap negatives remain.
- **retryCondition:** Revisit only on pinned-source exception handling, private diagnostic classification, owned FD cleanup or exact-source CI regression. Do not retry unchanged MinIO 401, publisher-coupled writer, canonical learning large-blob retrieval or absent human evidence.

## Observed material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41420282627](https://github.com/m-shogo/memories-project/actions/runs/41420282627) completed **SUCCESS** on `e24194dc3cb685ee896ba99a192deffbd4e2ca19`.
- **evidence:** Job `125193908124` logged `Memory OS generation-binding loader transport negative PASS`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. The new private reader negatives execute before the binding transport PASS summary. GitHub diff changed only the independently read-only binding transport negative script.
- **whySafe:** Synthetic fixtures in `contents: read` exact-source CI, no production publisher trigger for this path and no canonical evidence, credential, traffic or readiness mutation.
- **reusableMechanism:** Explicitly normalize `OSError`, `ValueError`, `TypeError` at the pinned source read boundary, preserving fixed-domain `Fail` and checking exact private error and suppressed context for each exception class.
- **protectedAuthorityCheck:** Ten protected Git blob identities unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. Registered/semantically eligible generations 0/0; approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage and final candidates 0. Human promotion remains separate/nonautomatic.

## Next safe target

Audit remaining independent read-only validator exception boundaries and the supplemental-learning record-only CI reachability, without weakening protected production authority or repeating unchanged workflow permission blockers.
