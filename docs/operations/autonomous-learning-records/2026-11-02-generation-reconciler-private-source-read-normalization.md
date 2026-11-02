# Supplemental OPS learning — generation reconciler negative pinned-source private read normalization (2026-11-02)

Append-only supplemental learning governed by canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Neither this record nor synthetic CI is production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure / latent disclosure boundary

- **symptom:** The independently read-only generation-evidence reconciler negative harness's pinned-source importer allowed raw `OSError` exceptions from its descriptor-read path to propagate instead of normalizing them to a private domain error.
- **evidence:** At `so` HEAD `8242f3da6a306646fe906ef47b62174a2709d9c2`, `pinned_reconciler_source` had a `try/finally` cleanup but no `except OSError` redaction. The other independent pinned importers already normalized private read failures. No actual secret disclosure or production incident was observed.
- **rootCauseOrUnknown:** Verified missing exception normalization in this separate harness; actual private OS error occurrence unknown.
- **failedApproach:** Assuming owned-FD cleanup alone prevents sensitive filesystem diagnostics from escaping, or that neighboring importers' exception guards cover this loader.
- **correction:** [`208973d6`](https://github.com/m-shogo/memories-project/commit/208973d6bb646ac2a8b0d80d4ffb40bacdae1877) maps `OSError` to `Fail("generation evidence reconciler pinned source unreadable") from None`.
- **recurrenceGuard:** An executable read-boundary negative injects `OSError("PRIVATE_RECONCILER_SOURCE_READ_CANARY")`, requires the exact private domain error, asserts the canary is absent and `__suppress_context__` is true, and restores `os.read`. Existing positive import, zero-byte source, inert flags and parent swap controls remain.
- **retryCondition:** Revisit on source-reader exception handling, cleanup ownership, private diagnostic wording or read-only exact-source CI reachability changes. Do not retry unchanged MinIO 401, large canonical learning blob transport, publisher-coupled writer changes or missing human evidence.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41400565374](https://github.com/m-shogo/memories-project/actions/runs/41400565374) completed **SUCCESS** on exact HEAD `208973d6bb646ac2a8b0d80d4ffb40bacdae1877`; job `125131275559` logged `PASS: generation evidence negative reconciler importer pinned after parent swap`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`. The committed source invokes the private read negative before its existing controls.
- **evidence:** GitHub Actions exact-source conclusion, job logs, and committed source diff; synthetic validation only.
- **whySafe:** Only an independently read-only negative harness changed; the production publisher's trigger excludes this script. No authority registry or production evidence was written.
- **reusableMechanism:** Normalize private descriptor errors with `raise DomainFail(...) from None` while preserving owned-FD cleanup and asserting both the exact failure class and suppressed exception context.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. Registered/semantically eligible generations `0/0`; approved objective, executable reviewed request, request-bound recovery evidence, complete typed coverage and final candidate all `0`. Human production promotion remains separate/nonautomatic.

## Next safe target

Add malformed acquired-FD ownership/cleanup and fragmented-read/EOF/nonbytes negatives to this same independent pinned reconciler source reader, reusing existing read-only exact-source CI and preserving all production authorities.
