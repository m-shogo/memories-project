# Supplemental OPS learning — generation-evidence transport invalid acquired FD negatives (2026-11-02)

Append-only learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure / regression coverage gap

- **symptom:** The generation-evidence transport pinned validator importer checked acquired descriptor type/range but did not explicitly test malformed `os.open` returns at each owned acquisition boundary.
- **evidence:** At `so` HEAD `e219d9e703bf31a54612b6dfab7c7bb640a337cb`, `pinned_validator_source` already required `type(fd) is int and fd >= 0`; the read-only transport negative harness covered flags, writable source, hardlink and parent swap, but no invalid FD returns. Prior drill-binding learning recorded a failed fixture based on absolute path depth, so that approach was not repeated. No real OS malformed descriptor or production incident was observed.
- **rootCauseOrUnknown:** Verified missing executable regression cases in this independent importer; actual OS/runtime corruption unknown.
- **failedApproach:** Treating source-level checks as sufficient without proving cleanup ownership after a partial acquisition, or inferring the `os.open` ordinal from absolute path depth.
- **correction:** Commit [`8759b69e`](https://github.com/m-shogo/memories-project/commit/8759b69e2a9213d141d819f9eea239c429aef8aa) adds twelve synthetic malformed returns (`None`, `True`, `-1`, `"7"`) at actual ROOT, `scripts` ancestor and leaf acquisition positions.
- **recurrenceGuard:** Each read-only negative asserts the intended ordinal was reached, requires `descriptor invalid`, and verifies exact reverse cleanup of only previously owned real FDs. Monkeypatched `os.open` and `os.close` are restored; positive pinned source, safety flag, writable/hardlink and swap negatives remain.
- **retryCondition:** Revisit on descriptor ownership/order, Python syscall wrapper, fixture layout or exact-source CI changes. Do not retry unchanged publisher-coupled writer edits, Quay MinIO HTTP 401, canonical learning blob retrieval or missing human evidence.

## Material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41397714517](https://github.com/m-shogo/memories-project/actions/runs/41397714517) completed **SUCCESS** on `8759b69e2a9213d141d819f9eea239c429aef8aa`; job `125122558167` logged `Memory OS generation-evidence execution transport negative PASS`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. The committed source executes all twelve cases before the existing transport tests.
- **evidence:** GitHub Actions conclusion, exact-source job output and committed source diff. Synthetic CI only.
- **whySafe:** Only the independently read-only generation-evidence transport negative harness changed. The write-capable publisher does not trigger on its path, and the fixture runs without modifying canonical production authorities.
- **reusableMechanism:** Reuse the actual-ordinal malformed-FD acquisition matrix with type/range rejection and owned-FD cleanup accounting across distinct executable importers.
- **protectedAuthorityCheck:** Post-code GitHub blob SHAs unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d` and mandatory contract `87712ea9`. Registered/semantically eligible generations 0/0; approved current objective, executable reviewed request, request-bound recovery evidence, typed coverage and final candidate 0. Independent review and human promotion remain separate and nonautomatic.

## Next safe target

Prove fragmented positive reads, premature EOF and non-bytes return rejection in the generation-evidence transport pinned source reader using its existing read-only exact-source CI.
