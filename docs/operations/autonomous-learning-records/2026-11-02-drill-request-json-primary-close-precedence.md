# Supplemental OPS learning — drill request JSON primary failure survives close fault (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or semantically eligible generation, recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** A secondary descriptor-close OSError could replace a primary drill-request planning JSON parse rejection with a different cleanup failure. No real production failure or malicious input was observed.
- **evidence:** Before code commit `81f097aa`, `scripts/validate-memory-os-backup-restore-drill-request.py` unconditionally raised `Fail("drill request JSON descriptor cleanup failed")` from its `finally` close handler, even while a duplicate-key or malformed JSON rejection was active.
- **rootCauseOrUnknown:** Verified Python `finally` exception precedence; actual exploitation or operational occurrence is unknown.
- **failedApproach:** Treating a secondary close fault as unconditionally higher priority than an already active fail-closed JSON rejection.
- **correction:** [`81f097aa`](https://github.com/m-shogo/memories-project/commit/81f097aac851bd23014e0d5fa6845b451bd69d3b) preserves the primary rejection across a secondary OSError, while a standalone close fault still fails closed with a fixed private-safe diagnostic.
- **recurrenceGuard:** The existing CI-reached drill-request load-negative suite injects a duplicate-key rejection followed by an OSError after the descriptor is actually closed; it also injects a standalone close failure, asserts both exact failure classes, checks no leaked descriptor or private marker, and restores the canonical positive control. Both code and tests were committed atomically.
- **retryCondition:** Revisit only after a change to the drill-request JSON reader/descriptor lifecycle or a new exact-source CI regression. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permission or missing human/external evidence blockers.

## Material success

- **outcome:** The primary duplicate-key rejection remains authoritative during a secondary close fault, while standalone cleanup failure is rejected and descriptors are released.
- **evidence:** Exact-source [Backup Restore Drill Request Admission #41353176843](https://github.com/m-shogo/memories-project/actions/runs/41353176843) completed **SUCCESS** at `81f097aa`; job `124987558176` logs `PASS: actual drill request JSON reader positive and 18 fail-closed negatives` and `production decision: NO_GO`. This is synthetic Python CI, not production recovery evidence or a current-source focused Go test.
- **whySafe:** Only the existing read-only drill-request validator and its existing CI-reached synthetic negative suite changed. The registered generation/objective/request/evidence registries, promotion review, workflows, credentials and production traffic were not written.
- **reusableMechanism:** In a descriptor `finally`, detect an active primary exception before cleanup; preserve that exception if cleanup also fails, but reject standalone cleanup faults. Prove both branches with a private-safe double-fault negative and owned-FD leak check.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs remained unchanged after `81f097aa`: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, recovery objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion review `99cb895f`. Registered generations and semantically eligible unsuperseded generations from distinct environments remain distinct; preflight requires a current explicitly human-approved recovery objective. Reviewed requests are planning-only, new recovery evidence must bind a current executable reviewed request, final candidates need complete typed eight-domain coverage and independent review, and human production promotion remains separate and non-automatic.

## Next safe target

Audit the separate drill-request reconciler's bounded JSON reader for the same primary/secondary close-fault precedence, reusing its existing CI-reached load-negative suite. Keep the publisher source guard and all protected production authorities unchanged.
