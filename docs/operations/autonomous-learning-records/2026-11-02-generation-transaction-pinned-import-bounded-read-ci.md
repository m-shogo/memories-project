# Supplemental OPS learning — generation transaction pinned writer import bounded reads (2026-11-02)

Append-only supplemental learning under the canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Neither this history nor synthetic CI is production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure / regression coverage gap

- **symptom:** The independent generation-evidence registry-transaction pinned writer-import negative harness verified hardlink, mode race and parent swap but did not exercise fragmented positive reads, premature EOF, nonbytes returns or private `os.read` exceptions.
- **evidence:** At `so` HEAD `42da968396d508903086da4c3b156f7ec97f9d0d`, `pinned_writer_source` already contained a bounded chunk loop, exact bytes type check, stable source metadata and a private `OSError` normalization. The existing `prove_pinned_writer_import` lacked the corresponding four read-boundary controls. No real OS failure or production incident was observed.
- **rootCauseOrUnknown:** Verified missing executable negative/positive regression coverage in this separate harness; actual exploitation or runtime corruption unknown.
- **failedApproach:** Assuming neighboring transport importer CI and source-level checks proved this distinct transaction importer, without exercising its own `os.read` boundary.
- **correction:** [`2f81c260`](https://github.com/m-shogo/memories-project/commit/2f81c2608a7fe2e7de549f7522ba4db17137db2a) adds a deterministic three-byte fragmented-read positive, early EOF rejection, nonbytes rejection, and secret-bearing `OSError` normalization/context-suppression negative.
- **recurrenceGuard:** Exact domain error strings are taken from the target reader; the fragment fixture must run more than twice; the private canary must not surface; `__suppress_context__` is asserted for the private `OSError`; monkeypatched `os.read` is restored after each case. Existing invalid-FD ownership, hardlink, chmod, parent swap and rollback tests remain.
- **retryCondition:** Revisit on pinned importer read logic, error wording, source authority or exact-source workflow reachability changes. Do not retry unchanged MinIO 401, canonical learning large-blob transport, publisher-coupled writer modifications or missing human production evidence.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41399188053](https://github.com/m-shogo/memories-project/actions/runs/41399188053) completed **SUCCESS** on exact code HEAD `2f81c2608a7fe2e7de549f7522ba4db17137db2a`. Job `125127056866` logged `PASS: generation transaction pinned writer import rejects EOF, nonbytes, private read errors, hardlinks, chmod and swaps; fragmented reads work`, `generation evidence registry transaction negative PASS`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`.
- **evidence:** GitHub Actions exact-source run conclusion, job log and source diff. This is synthetic safety validation only.
- **whySafe:** Only the independently read-only transaction negative harness changed; the write-capable publisher trigger excludes this script. All tests use temporary files and restored monkeypatches; no production authority was written.
- **reusableMechanism:** Exercise each independent pinned-source importer with a bounded fragmented read, EOF/type failures, private exception normalization and exact failure assertions rather than relying on another importer's CI.
- **protectedAuthorityCheck:** Git blob SHAs unchanged after the code commit: Production Status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, recovery objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, learning contract `87712ea9`. Registered/semantically eligible generations `0/0`, approved objective `0`, executable reviewed request `0`, request-bound evidence `0`, typed coverage `0`, final candidate `0`; human promotion remains separate and nonautomatic.

## Next safe target

Audit the independent generation-evidence reconciler negative harness's pinned import for inert `O_DIRECTORY`, `O_NOFOLLOW` and `O_NONBLOCK` constants, then add deterministic rejection cases using its read-only CI.
