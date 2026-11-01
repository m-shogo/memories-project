# Supplemental OPS learning — promotion-review primary atomic cleanup precedence (2026-11-02)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** A secondary temporary-file unlink failure could replace the promotion-review reconciler's primary fixed-class atomic-write failure.
- **evidence:** At `b5ab5402`, `scripts/reconcile-memory-os-backup-restore-promotion-review.py` wrapped `os.replace` OSError into `Fail("promotion reconcile authority atomic write failed")` but raised a different cleanup `Fail` from its `finally` on secondary `os.unlink` OSError. No actual production or human-promotion mutation was observed.
- **rootCauseOrUnknown:** Verified Python finally exception precedence. Real-world occurrence of the secondary cleanup failure is unknown.
- **failedApproach:** Treating cleanup failure as automatically superseding the original private-safe atomic-write diagnostic.
- **correction:** [e4a698ec](https://github.com/m-shogo/memories-project/commit/e4a698ec854a5730f37a618a8ec123258aaa410f) preserves an active primary write exception across secondary cleanup OSError. A standalone cleanup failure still fails closed; orphan private temps remain subject to existing clean-source/rollback checks.
- **recurrenceGuard:** The existing CI-invoked isolated promotion-review reconcile negative suite injects a primary `os.replace` OSError and secondary `os.unlink` OSError, asserts the exact private-safe original `Fail`, verifies cleanup was attempted, compares fixture/canonical contract and registry bytes/modes, and removes only newly created synthetic temp files.
- **retryCondition:** Revisit only on reviewed promotion-review atomic writer/rollback changes or exact-source CI regression. Do not retry unchanged MinIO HTTP 401, workflow permission, production evidence or human promotion blockers.

## Material success

- **outcome:** The promotion-review atomic writer now preserves the original failure across cleanup while retaining explicit raw-FD ownership from the prior guard.
- **evidence:** [Backup Restore Promotion Review Readonly #41332384670](https://github.com/m-shogo/memories-project/actions/runs/41332384670) and [Backup Restore Promotion Review #41332384693](https://github.com/m-shogo/memories-project/actions/runs/41332384693) both completed **SUCCESS** on exact code HEAD `e4a698ec`. Read-only logs explicitly report `promotion-review primary atomic failure survives secondary cleanup OSError`, `fchmod/fdopen faults close retained raw descriptors`, isolated atomic mode preservation, second-replace rollback, aggregate rollback and full negative suite PASS.
- **whySafe:** Only the existing reconciler and existing CI-reached synthetic negative suite changed. No production status, generation/objective/request/recovery/typed/promotion registry, reviewed workflow, credential or traffic was modified, and no human promotion was authorized.
- **reusableMechanism:** Capture active primary exception before finally cleanup, preserve its fixed private-safe diagnostic, fail closed on standalone cleanup error and prove with a two-fault isolated negative and byte/mode identity.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion registry `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound evidence 0, complete typed eight-domain coverage 0 and final candidates 0. Preflight requires unsuperseded semantically eligible generations from distinct environments and explicit current human-approved recovery objective; reviewed requests are planning-only; new generation recovery evidence remains current executable-request-bound; final candidates require complete typed eight-domain non-resurrection coverage and independent review; human promotion remains separate/nonautomatic.

## Next safe target

Audit generation-status and other local atomic writers for remaining non-OSError cleanup masking or FD ownership gaps using existing CI-reached negatives, without altering protected authorities.
