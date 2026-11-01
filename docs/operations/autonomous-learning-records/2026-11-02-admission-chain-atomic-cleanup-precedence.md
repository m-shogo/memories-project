# Supplemental OPS learning — admission-chain atomic cleanup exception precedence (2026-11-02)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. **Not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, executable request, recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or promotion evidence.

## Material failure

- **symptom:** A secondary non-OSError from temporary-file cleanup could mask the original admission-chain atomic-write failure.
- **evidence:** At `5b3b355b`, `scripts/reconcile-memory-os-backup-restore-admission-chain.py` wrapped primary `os.replace` OSError into domain `Fail`, but its `finally` cleanup only suppressed `FileNotFoundError`/other `OSError`. A synthetic cleanup `ValueError` could replace the primary diagnostic. No actual production corruption or real-world cleanup failure was observed.
- **rootCauseOrUnknown:** Verified Python finally exception precedence and incomplete cleanup exception boundary. Real-world reachability of a non-OSError from a normal `os.unlink` call is unknown.
- **failedApproach:** Treating OSError-only cleanup suppression as preserving all primary write exceptions.
- **correction:** [87f25fc4](https://github.com/m-shogo/memories-project/commit/87f25fc40e979e12133588f0bc4f1429575fd025) records whether a primary exception is active, preserves it across ordinary cleanup exceptions, and fails closed if cleanup alone fails.
- **recurrenceGuard:** The existing CI-reached admission-chain reconcile negative suite injects primary `os.replace` OSError and secondary `os.unlink` ValueError, asserts the primary fixed-class failure, compares canonical contract bytes/mode and production-status bytes, verifies the cleanup was attempted, and removes only new synthetic temporary files.
- **retryCondition:** Revisit on reviewed admission-chain atomic-writer/rollback changes or an exact-source CI regression. Do not retry unchanged Quay MinIO HTTP 401, workflow permissions, production evidence or human approval blockers.

## Material success

- **outcome:** The double-fault negative confirms the admission-chain reconciler preserves the original atomic-write failure while leaving protected authority bytes and modes unchanged.
- **evidence:** [Backup Restore Admission Chain Reconcile Negative #41330567639](https://github.com/m-shogo/memories-project/actions/runs/41330567639) completed **SUCCESS** on exact code HEAD `87f25fc40e979e12133588f0bc4f1429575fd025`. Other CI workflows at record preparation were not yet classified as SUCCESS.
- **whySafe:** Only the existing admission-chain reconciler and existing read-only negative suite changed. The synthetic test deliberately rejects replacement, never publishes the canonical contract, and cleans its scoped temporary fixture.
- **reusableMechanism:** Capture active primary exception before cleanup, suppress secondary ordinary cleanup exceptions only while preserving the primary, and prove precedence with a double-fault negative and byte-exact protected-authority checks.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, environment generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion registry `99cb895f`. Production decision remains `NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with registered/semantically eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound recovery evidence 0, complete typed eight-domain coverage 0, and final candidates 0. Preflight still requires unsuperseded semantically eligible generations from distinct environments plus an explicitly human-approved current objective. Reviewed drill requests are planning-only, generation evidence must remain bound to a current executable reviewed request, final candidates need complete typed eight-domain coverage and independent review, and human production promotion is separate and nonautomatic.

## Next safe target

Audit generation-evidence and other admission reconcilers for the same cleanup precedence class using existing CI-reachable negative suites. Keep synthetic learning separate from every operational gate.
