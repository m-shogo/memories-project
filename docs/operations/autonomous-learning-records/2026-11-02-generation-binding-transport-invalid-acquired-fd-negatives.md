# Supplemental OPS learning — generation-binding transport invalid acquired FD negatives (2026-11-02)

Append-only learning governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, human-approved recovery objective, reviewed drill request, request-bound recovery, typed eight-domain coverage, independent review, final candidate or promotion evidence.

## Material failure / latent regression risk

- **symptom:** The generation-binding transport pinned importer checked exact nonnegative integer acquired descriptors, but lacked negative coverage for malformed `os.open` results at the ROOT, ancestor and leaf boundaries.
- **evidence:** At `so` HEAD `ce0d511a79400af6112ab8805f4a7e8e70992bf7`, `pinned_validator_source` required `type(fd) is int and fd >= 0` before owned append, while the existing negative harness tested safety flags, writable/hardlinked source and parent races but not malformed acquisition returns. Prior drill-binding learning proved that deriving acquisition ordinals from absolute path depth is incorrect. No actual OS failure or production compromise observed.
- **rootCauseOrUnknown:** Verified missing regression tests for this independent loader. Real-world malformed `os.open` returns are unknown.
- **failedApproach:** Assuming a checked source path and a syntactically successful open are sufficient proof of owned FD identity; deriving test ordinals from absolute path components is a previously recorded failed approach.
- **correction:** Commit [`5967299e`](https://github.com/m-shogo/memories-project/commit/5967299e3249932f011dae42e90eb26abe0e7140) injects `None`, `True`, `-1` and `"7"` at each of the three actual acquisitions (ROOT, `scripts`, leaf).
- **recurrenceGuard:** Twelve read-only synthetic cases require the domain `descriptor invalid` failure, exact injection ordinal, reverse-order close of only real acquired FDs, and restoration of monkeypatched `os.open`/`os.close`. Positive pinned import, zero/noninteger safety flags, hardlink, parent chmod and swap negatives remain active.
- **retryCondition:** Revisit only on descriptor acquisition/ownership, fixture ordering or exact-source CI trigger changes. Do not retry unchanged publisher coupling, MinIO HTTP 401, large canonical blob retrieval or absent human production evidence.

## Material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41397241865](https://github.com/m-shogo/memories-project/actions/runs/41397241865) completed **SUCCESS** on `5967299e3249932f011dae42e90eb26abe0e7140`; job `125121109365` logged `Memory OS generation-binding loader transport negative PASS`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. The committed source invokes all twelve cases before the remaining positive/negative controls.
- **evidence:** GitHub Actions conclusion, exact-source job logs and source diff. This is synthetic CI only.
- **whySafe:** Only the independently read-only generation-binding transport negative harness changed. The production-capable publisher's trigger list excludes this path. Temporary fixture files and monkeypatches cannot supply production authority or evidence.
- **reusableMechanism:** Reuse the proven actual-ordinal malformed-acquisition matrix with exact type/range rejection and owned-FD cleanup accounting, rather than absolute path depth or a prose-only check.
- **protectedAuthorityCheck:** Post-code GitHub blobs unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, learning contract `87712ea9`. Registered/semantically eligible generations 0/0; approved current objective, executable reviewed request, request-bound recovery, typed coverage and final candidate 0. Independent review and separate nonautomatic human production promotion remain mandatory.

## Next safe target

Add equivalent invalid acquired-FD ownership and cleanup negatives to the independent generation-evidence transport pinned importer, using its read-only exact-source workflow.
