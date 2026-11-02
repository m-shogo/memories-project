# Supplemental OPS learning — generation-evidence transport non-OS private read CI (2026-11-02)

Append-only supplemental record governed by canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Neither learning nor synthetic CI can satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered generation, approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human production-promotion authority.

## Material failure mode / coverage gap

- **symptom:** The independent generation-evidence transport pinned validator importer could leak a private `ValueError` or `TypeError` diagnostic from `os.read`, while only `OSError` was normalized.
- **evidence:** Before [`e04383bc`](https://github.com/m-shogo/memories-project/commit/e04383bc25a82681d9748a12a58be0e1623d55f6), `pinned_validator_source` caught only `OSError` and the negative harness exercised EOF/nonbytes/oversized read results but not exceptions with private canaries. No actual private disclosure or production incident was observed.
- **rootCauseOrUnknown:** Verified missing Python syscall exception classification and test coverage; real-world occurrence unknown.
- **failedApproach:** Treating `OSError`-only handling or neighboring reconciler tests as sufficient proof for this separate source importer, or using an unqualified broad catch that risks masking fixed-domain `Fail`.
- **correction:** `e04383bc` normalizes `(OSError, ValueError, TypeError)` to a fixed private `pinned source unreadable` error and adds three injected reader canary negatives.
- **recurrenceGuard:** Each negative asserts exact `Fail`, suppressed context, no private canary leakage and `os.read` restoration. Existing positive fragmented reads, invalid FDs, close-fault precedence, EOF, nonbytes, oversized response, hardlink and swap tests remain.
- **retryCondition:** Revisit on pinned-source read classification, owned descriptor cleanup, CI source or fixture changes. Do not retry unchanged MinIO 401, publisher-coupled writer, canonical learning large-blob retrieval or absent human evidence.

## Observed material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41420219443](https://github.com/m-shogo/memories-project/actions/runs/41420219443) completed **SUCCESS** on `e04383bc25a82681d9748a12a58be0e1623d55f6`.
- **evidence:** Job `125193698743` logged `PASS: generation transport pinned importer rejects invalid FDs, EOF, nonbytes, hardlink and swap; fragmented read works`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. The new exception cases run before the transport PASS summary; the code commit changed only the independent read-only transport-negative script.
- **whySafe:** Synthetic read-only exact-source workflow (`contents: read`), no production publisher trigger for this path, no canonical production evidence, credential, traffic or readiness mutation.
- **reusableMechanism:** Redact explicit `OSError`/`ValueError`/`TypeError` at the pinned-source read boundary, assert fixed domain and context suppression through private canaries without catching expected domain `Fail`.
- **protectedAuthorityCheck:** Ten protected Git blob identities unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed request registry `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, learning contract `87712ea9`. Registered/semantically eligible generations 0/0; approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage and final candidates all 0. Human production promotion remains separate/nonautomatic.

## Next safe target

Verify the analogous independent generation-binding transport reader's exact-source CI and preserve its separate lesson.
