# Supplemental OPS learning — promotion-review atomic raw-FD ownership (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — raw FD not owned across promotion-review stream acquisition

- **symptom:** The promotion-review reconciler could leak the temporary descriptor when `os.fchmod` or `os.fdopen` failed before stream ownership was established.
- **evidence:** At `8f88830f`, `scripts/reconcile-memory-os-backup-restore-promotion-review.py` called `os.fchmod(fd, mode)` and `os.fdopen(fd, "wb")` without an outer retained raw-FD cleanup. The reviewed production/human promotion authority was not modified, and no actual production leak was observed.
- **rootCauseOrUnknown:** Verified missing explicit FD ownership across pre-fdopen and constructor exception boundaries. Actual production occurrence is unknown.
- **failedApproach:** Assuming all failing stream acquisitions release the original `mkstemp` descriptor. An exceptional numeric reclose after ambiguous ownership transfer was already prohibited by prior canonical-reader learning and was not reused.
- **correction:** [dbf15c74](https://github.com/m-shogo/memories-project/commit/dbf15c7487263abea7d3b0de652203caf628e6dd) retains raw ownership via `os.fdopen(fd, "wb", closefd=False)`, closes the descriptor once before replacement, and releases a retained descriptor in the failure-path `finally`.
- **recurrenceGuard:** The existing CI-invoked isolated promotion-review reconcile negative suite injects `fchmod` and `fdopen` OSError, binds `closefd=False`, checks the captured FD is closed, verifies no temporary authority residue, and compares isolated and canonical contract/registry bytes and modes.
- **retryCondition:** Revisit only after reviewed promotion-review atomic writer/FD ownership change, Python closefd contract change or exact-source CI regression. Do not retry unchanged Quay MinIO 401, workflow permissions or missing human approval.

## Material success — exact-source CI evidence

- **outcome:** Promotion-review atomic writing now retains explicit raw-FD ownership and the constructor-failure negatives execute through existing read-only CI.
- **evidence:** [Backup Restore Promotion Review Readonly #41331873136](https://github.com/m-shogo/memories-project/actions/runs/41331873136) completed **SUCCESS** on exact code HEAD `dbf15c74`; logs explicitly report `promotion-review fchmod/fdopen faults close retained raw descriptors`, successful and failed isolated atomic mode preservation, second-replace rollback, aggregate operability rollback and full promotion-review reconcile negative PASS. [Backup Restore Promotion Review #41331873161](https://github.com/m-shogo/memories-project/actions/runs/41331873161) also completed **SUCCESS** on the same code HEAD.
- **whySafe:** Only the existing promotion-review reconciler and its isolated CI-reached negative suite changed. No reviewed workflow, production status, generation/objective/request/recovery/typed/promotion registry, credentials or traffic changed. No human promotion was authorized.
- **reusableMechanism:** Non-owning stream `closefd=False`, exactly one raw-FD close before atomic replace, scoped pre-fdopen and fdopen fault injection, and byte/mode-exact canonical checks.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, environment generations `bfd1b045`, recovery objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion registry `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound evidence 0, complete typed eight-domain coverage 0 and final candidates 0. Preflight still requires unsuperseded semantically eligible generations from distinct environments and current explicit human recovery-objective approval; reviewed requests are planning-only, generation recovery evidence stays bound to a current executable reviewed request, final candidates need typed eight-domain coverage and independent review, and human promotion remains separate/nonautomatic.

## Next safe target

Audit other approved atomic writers for explicit raw-FD ownership and primary-versus-cleanup error precedence, reusing existing CI-reached negative suites. Never let synthetic learning satisfy operational gates.
