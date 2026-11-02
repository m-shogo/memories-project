# Supplemental OPS learning — generation-evidence transport oversized read guard (2026-11-02)

Append-only learning under canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Neither this record nor synthetic CI is production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, human-approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure / latent over-budget read loop

- **symptom:** The independently read-only generation-evidence transport negative harness could fail to terminate when a mocked/faulty `os.read` returned more than the remaining byte budget.
- **evidence:** At `so` HEAD `820448305465833e2bc6a7674a571222dc2741e3`, `pinned_validator_source` used `while remaining:` and `remaining -= len(chunk)` without checking the response length. A response of `MAX_VALIDATOR_SOURCE_BYTES + 2` bytes would make the remaining budget negative and truthy. Existing tests covered fragmented reads, premature EOF and nonbytes but not oversized response. This is deterministic source/arithmetic analysis, not an observed CI hang.
- **rootCauseOrUnknown:** Verified missing per-chunk upper bound in this separate source reader; actual OS over-read occurrence unknown.
- **failedApproach:** Assuming a final aggregate size check is reachable for every mocked read behavior. Prior generation reconciler and generation-binding transport learning showed this assumption was unsafe.
- **correction:** [`28fa3c9f`](https://github.com/m-shogo/memories-project/commit/28fa3c9fe32277124f92d68190ebe7446076c7d6) adds `len(chunk) <= remaining` before append/decrement and an oversized mocked-response negative alongside the existing EOF/nonbytes cases.
- **recurrenceGuard:** Exact domain error for over-budget responses, restoration of `os.read` in every case, and explicit private nonbytes-canary exclusion; fragmented-read positive control remains.
- **retryCondition:** Verify exact-source read-only Negative Suite outcome when available; append observed CI failures before retry. Do not repeat unchanged publisher, MinIO, canonical large-blob or absent human-evidence blockers.

## Observed code-change outcome

- **outcome:** `28fa3c9f` committed to `so`; GitHub diff confirms only `scripts/validate-memory-os-backup-restore-generation-evidence-transport-negative.py` changed.
- **evidence:** Commit diff, exact branch comparison, and protected blob checks. The independent `backup-restore-generation-evidence-reconcile-negative.yml` includes this script and has `contents: read`; the write-capable publisher excludes it. GitHub commit-status returned no checks; **no exact-source CI SUCCESS is claimed**.
- **whySafe:** The correction only hardens synthetic source-reader transport tests and cannot establish production-equivalent evidence or promotion.
- **reusableMechanism:** Reject over-budget individual read responses before modifying the remaining counter, with deterministic negative input and private diagnostics.
- **protectedAuthorityCheck:** Verified unchanged Git blobs: production status `d677a1c9` (`productionDecision=NO_GO`), generations `bfd1b045`, objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, canonical learning `b809c69d`, mandatory contract `87712ea9`. OPS-P0-007 remains blocked and human promotion remains separate/nonautomatic.

## Next safe target

Obtain exact-source CI for the read-only generation reconciler, generation-binding transport and generation-evidence transport suites. Do not modify the Recovery Objectives negative importer with a write-capable Admission trigger until a safe independent validation path is available.
