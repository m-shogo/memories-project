# Supplemental OPS learning — generation-binding transport close-fault negative CI (2026-11-02)

Append-only learning subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record and synthetic CI are not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered generation, human-approved recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material regression risk / failure mode

- **symptom:** The independently read-only generation-binding pinned validator importer lacked a deterministic test for a secondary descriptor-close exception with and without a primary pinned-source read failure.
- **evidence:** At `so` HEAD `1925453004cfc74efa167079dfcccbe19d6af046`, `pinned_validator_source` tracked owned descriptors and had a primary-error-preserving `finally`, but the negative suite covered malformed acquisition, early EOF, nonbytes and oversized reads without testing cleanup double faults. No actual OS close failure or production descriptor leak was observed.
- **rootCauseOrUnknown:** Verified negative-coverage gap; real-world close error frequency and production reachability are unknown.
- **failedApproach:** Assuming the analogous generation-evidence transport test or a source-level `finally` check proves this separate importer's behavior without executing its own failure boundary.
- **correction:** [`19455c42`](https://github.com/m-shogo/memories-project/commit/19455c42a8e0c25dddc19c090bc59bf4cdb503b8) adds both close-then-raise private `ValueError` cases to `prove_pinned_validator_import`.
- **recurrenceGuard:** Requires the exact `source changed during read` primary failure when an early EOF coincides with close failure, or the private `descriptor cleanup failed` classification without a primary. Both exclude the canary; the latter requires suppressed context. All three real owned descriptors are closed, patches restored, and existing positive/negative source checks retained.
- **retryCondition:** Revisit only on source importer FD ownership, close error classification, exact-source CI regression or fixture change. Do not repeat unchanged MinIO 401, canonical learning large-blob transport, publisher-coupled writer or absent human evidence.

## Observed material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41418875218](https://github.com/m-shogo/memories-project/actions/runs/41418875218) completed **SUCCESS** on `19455c42a8e0c25dddc19c090bc59bf4cdb503b8`.
- **evidence:** Job `125189326804` logged `Memory OS generation-binding loader transport negative PASS`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. The two new close-fault cases execute before the binding transport PASS summary. GitHub commit diff changed only the independent transport-negative script.
- **whySafe:** Read-only exact-source workflow (`contents: read`), synthetic fixture only, no production publisher trigger for the changed path, no production authority or recovery evidence mutation.
- **reusableMechanism:** Repeat the bounded post-close fault and primary/no-primary exception-precedence test per independent loader, asserting exact diagnostics, context suppression, real FD closure accounting and monkeypatch restoration.
- **protectedAuthorityCheck:** Ten Git blob identities unchanged after code commit: production status `d677a1c9` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed request registry `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection registry `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, learning contract `87712ea9`. Registered/semantically eligible generations 0/0; approved objective, executable reviewed request, request-bound recovery evidence, typed complete records and final candidates all 0. Human promotion remains separate/nonautomatic.

## Next safe target

Check the generation-evidence reconciler's independent pinned source importer for the same close-fault precedence, then verify exact-source read-only CI and append its distinct lesson.
