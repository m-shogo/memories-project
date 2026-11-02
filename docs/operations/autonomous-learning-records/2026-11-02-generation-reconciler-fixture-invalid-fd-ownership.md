# Supplemental OPS learning — generation reconcile fixture invalid-FD ownership (2026-11-02)

Append-only supplemental learning under canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record and synthetic checks do not satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure / latent invalid acquisition boundary

- **symptom:** The independent read-only generation-evidence reconcile negative harness could treat a malformed `os.open` result as a directory FD and pass it into `os.fstat`, `os.close` or later fixture operations.
- **evidence:** Before [`90f49140`](https://github.com/m-shogo/memories-project/commit/90f491405988590b92ee860c520422cca0767f84), `_pinned_temporary_directory` assigned root and ancestor `os.open` results directly without validating `type(fd) is int and fd >= 0`. In particular, `True` is an `int` subclass and could be misinterpreted as FD 1. Similar importer ownership failures had been covered by earlier independent OPS learning; no actual OS descriptor corruption was observed.
- **rootCauseOrUnknown:** Verified missing acquisition validation and premature ownership transfer in this separate fixture directory implementation. Actual runtime occurrence unknown.
- **failedApproach:** Assuming `os.open` always yields a valid owned integer or raises `OSError`; using `os.close` without first establishing ownership.
- **correction:** `90f49140` validates exact nonnegative integer root and ancestor descriptors before ownership transfer and preserves the newly acquired descriptor as the cleanup target before closing the previous owned descriptor.
- **recurrenceGuard:** Sixteen executable negative cases cover each actual acquisition ordinal (root and three ancestors) with `None`, `True`, `-1` and `"7"`. They require a specific private `Fail`, exact call count, every acquired owned FD closed once, no invalid FD closed and no new fixture child. Acquisition order is derived from the repository-relative parent path rather than absolute path depth.
- **retryCondition:** Revisit on fixture directory traversal, FD acquisition/cleanup or exact-source read-only CI changes. Do not retry unchanged external MinIO 401, canonical learning blob transport, publisher-coupled writer changes or absent human evidence.

## Observed code-change outcome

- **outcome:** `90f49140` was committed to `so`; GitHub diff and readback confirm the new checks and executable negative are present and invoked by `main`.
- **evidence:** Commit diff, exact branch comparison, source readback and protected Git blob reads. The existing read-only workflow includes the changed script in its `so` trigger and invocation. GitHub's available status response was empty; **no exact-source CI SUCCESS is claimed**.
- **whySafe:** Only the independent read-only synthetic harness changed. Its workflow has `contents: read`, while the publisher trigger excludes this negative script; no production authority was written.
- **reusableMechanism:** Validate exact FD type/range before claiming ownership, explicitly track descriptor transfer, and use acquisition-order negative injections with close-accounting assertions.
- **protectedAuthorityCheck:** Following the code commit, unchanged Git blobs were observed for production status `d677a1c9` (`productionDecision=NO_GO`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, canonical learning `b809c69d` and mandatory contract `87712ea9`. No protected production authority changed. OPS-P0-007 prerequisites and separate human promotion authority remain unsatisfied.

## Next safe target

Confirm exact-source CI for the independent Negative Suite including `90f49140`, then audit cleanup-failure precedence in this same fixture directory guard. Do not broaden into production-publisher-coupled atomic writer changes without a separate safe validation boundary.
