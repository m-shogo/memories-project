# Supplemental OPS learning — preflight reader double-fault precedence (2026-11-02)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final-candidate or human-promotion evidence.

## Material failure

- **symptom:** The preflight reconciler's bounded descriptor-pinned `read_text` could replace its primary unreadable-authority diagnostic with a secondary descriptor-close failure.
- **evidence:** At starting HEAD `fcac8158`, `read_text` always raised `Fail("preflight reconcile authority cleanup failed")` from `finally` if any `os.close` failed, even after `os.fdopen` had already raised `OSError` and the body had converted it to `Fail("preflight reconcile authority unreadable")`. The new isolated negative injects both faults and verifies the original fixed-class diagnostic, that cleanup was attempted and all opened descriptors were closed. No real production fault or corruption was observed.
- **rootCauseOrUnknown:** Verified Python `finally` exception precedence in the inspected source; real-world occurrence unknown.
- **failedApproach:** Unconditionally promoting a secondary cleanup error over an already-active primary read failure.
- **correction:** [`345e6f8`](https://github.com/m-shogo/memories-project/commit/345e6f8fbcc67235b97b28d0cd6a2d1c9a8618c8) checks `sys.exc_info()` in `finally`; it preserves the active primary error and still rejects standalone cleanup failure.
- **recurrenceGuard:** The existing CI-reached `validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py` now injects `os.fdopen` OSError plus close-after-effect OSError against an isolated authority; checks the exact private-safe `Fail`, no descriptor leak, unchanged fixture bytes, and canonical contract/status byte-and-mode identity.
- **retryCondition:** Revisit only if the reader/cleanup semantics or CI evidence changes. Do not retry unchanged MinIO HTTP 401, workflow permission, production evidence or promotion blockers.

## Material success

- **outcome:** The primary unreadable-authority failure remains authoritative across secondary descriptor cleanup errors; standalone cleanup failures remain fail-closed.
- **evidence:** Exact-source [Backup Restore Drill Preflight Reconcile Negative #41332879149](https://github.com/m-shogo/memories-project/actions/runs/41332879149) and [Backup Restore Drill Preflight #41332879170](https://github.com/m-shogo/memories-project/actions/runs/41332879170) completed SUCCESS at code HEAD `345e6f8`. These are synthetic validator outcomes, not production restore evidence.
- **whySafe:** Only the preflight reader and an already CI-invoked synthetic negative were changed. No production authority, registry, workflow permissions, recovery objective or promotion path was modified.
- **reusableMechanism:** When closing owned descriptors in `finally`, preserve an active primary failure while failing closed on cleanup-only errors; inject both faults and verify exact diagnostic and resource ownership.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain non-resurrection `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`. Registered/semantically eligible generations 0/0, approved current recovery objectives 0, executable reviewed requests 0, request-bound evidence 0, complete typed eight-domain coverage 0, final candidates 0. Only unsuperseded semantically eligible generations from distinct environments plus an explicitly human-approved current recovery objective can enter preflight; reviewed requests are planning authority only, new recovery evidence must be bound to a current executable reviewed request, final candidates require all existing gates and independent typed eight-domain review, and human production promotion remains separate and nonautomatic.

## Next safe target

Audit drill-generation eligibility binding's atomic writer FD ownership and secondary cleanup precedence using its existing CI-reached isolated negative suite. Do not mutate production or planning registries.
