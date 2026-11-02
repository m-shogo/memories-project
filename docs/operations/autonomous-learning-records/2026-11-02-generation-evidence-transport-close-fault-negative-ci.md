# Supplemental OPS learning — generation-evidence transport descriptor-close negative CI (2026-11-02)

Append-only supplemental learning governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Neither learning nor synthetic CI is production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material regression risk / failure mode

- **symptom:** The independently read-only generation-evidence transport pinned validator importer had no executable negative asserting how descriptor-close exceptions interact with an existing source-read failure.
- **evidence:** At `so` HEAD `ce400aa31bf3717beb63893c74dbbac70c5d4599`, `pinned_validator_source` already tracked owned descriptors and attempted all closes, preserving a primary exception or emitting `descriptor cleanup failed`. The harness tested invalid acquisition and reader failures but not `os.close` double faults. No real close failure, leaked production descriptor or incident was observed.
- **rootCauseOrUnknown:** Verified regression-coverage gap; actual OS close failure behavior and production reachability are unknown.
- **failedApproach:** Relying only on source inspection and invalid-acquisition cleanup accounting as proof that a secondary close exception cannot mask the primary failure or disclose private diagnostics.
- **correction:** [`a5ae0dc6`](https://github.com/m-shogo/memories-project/commit/a5ae0dc697e1a948b1b1dcd907e1a91f5257af9a) adds two executable cases in `prove_pinned_validator_import`: close-then-raise private `ValueError` with and without an independent premature-EOF primary failure.
- **recurrenceGuard:** Both cases require the exact private domain result, no canary in the diagnostic, suppressed context for the no-primary close error, all three owned descriptors closed, and restoration of patched `os.close`/`os.read`. Existing fragmented positive, EOF, nonbytes, over-budget, invalid FD, hardlink and swap tests remain.
- **retryCondition:** Revisit only if owned-FD lifecycle, cleanup classification, negative test source, CI trigger or observed exact-source failure changes. Do not repeat unchanged external MinIO HTTP 401, publisher-coupled writer, large canonical blob retrieval or absent human evidence.

## Observed material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41418688094](https://github.com/m-shogo/memories-project/actions/runs/41418688094) completed **SUCCESS** on `a5ae0dc697e1a948b1b1dcd907e1a91f5257af9a`.
- **evidence:** Job `125188709340` logged `PASS: generation transport pinned importer rejects invalid FDs, EOF, nonbytes, hardlink and swap; fragmented read works`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. The newly added close-fault cases run before the summary. The commit changed only the independently read-only transport-negative script.
- **whySafe:** The changed harness has a `contents: read` exact-source workflow and is excluded from the write-capable generation-evidence publisher's trigger. It creates no production authority or recovery evidence.
- **reusableMechanism:** Simulate a descriptor successfully closed followed by a synthetic exception, test both primary/no-primary exception precedence, count owned FD closures, and suppress private error context.
- **protectedAuthorityCheck:** After the code commit, ten protected Git blobs were unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. Registered/eligible generations remain 0/0, approved current objective 0, executable reviewed request 0, request-bound recovery evidence 0, typed eight-domain complete records 0 and final candidates 0. Human production promotion remains separate and nonautomatic.

## Next safe target

Confirm the analogous generation-binding transport close-fault negative on its own exact-source read-only CI; if it fails, diagnose and append a distinct correction record without altering this history.
