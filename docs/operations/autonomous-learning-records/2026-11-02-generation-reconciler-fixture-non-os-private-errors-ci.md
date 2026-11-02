# Supplemental OPS learning — generation reconcile fixture non-OS private error redaction (2026-11-02)

Append-only learning subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Learning and synthetic CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure mode / verified coverage gap

- **symptom:** The independently read-only generation-evidence reconcile fixture manager redacted `OSError` at root/ancestor acquisition and child creation but allowed private `ValueError` or `TypeError` from those same boundaries to escape unclassified.
- **evidence:** Before [`d09dec01`](https://github.com/m-shogo/memories-project/commit/d09dec0191c6e1dafd2ea070d149abccfbe7cd2f), both fixture operation handlers used `except OSError`, while the private canary negative injected only `OSError`. No actual private data leak or production incident was observed. Earlier learning had explicitly warned that a broad `except Exception` masked an intended fixed-domain child-identity rejection.
- **rootCauseOrUnknown:** Verified incomplete exception-type normalization and regression coverage for Python syscall wrapper `ValueError`/`TypeError`; actual occurrence unknown.
- **failedApproach:** Assuming `OSError` alone covers every private fixture acquisition/mkdir failure, or applying an undifferentiated broad catch that would repeat the known fixed-domain `Fail` masking bug.
- **correction:** `d09dec01` catches only `(OSError, ValueError, TypeError)` at root-open and outer fixture-operation boundaries, retaining all fixed-domain `Fail` rejections. The negative injects each type at root open, ancestor open and child mkdir.
- **recurrenceGuard:** Nine deterministic canary cases require exact private domain errors, `__suppress_context__`, no canary leakage and no residual fixture child; monkeypatches are restored. The existing substituted-child identity, primary double-fault, invalid-FD, safety-flag and parent-swap negatives remain.
- **retryCondition:** Revisit on fixture operation exception classification, private diagnostics, cleanup ownership or exact-source CI regression. Do not retry unchanged Quay MinIO 401, publisher-coupled writer, canonical learning large-blob retrieval or absent human evidence.

## Observed material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41419906839](https://github.com/m-shogo/memories-project/actions/runs/41419906839) completed **SUCCESS** on `d09dec0191c6e1dafd2ea070d149abccfbe7cd2f`.
- **evidence:** Job `125192679090` logged `PASS: generation reconcile fixture private OS/value/type errors redacted`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. The commit changed only the independent reconcile-negative script.
- **whySafe:** Only the synthetic read-only fixture guard changed; no publisher, production authority, recovery evidence, credential, traffic or readiness state was changed.
- **reusableMechanism:** Normalize a bounded set of expected Python syscall exceptions without catching the already-sanitized domain exception; inject private canaries at distinct acquisition and creation boundaries, checking exact redaction and cleanup.
- **protectedAuthorityCheck:** Ten protected Git blob identities unchanged after code commit: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, learning contract `87712ea9`. Registered/semantically eligible generations remain 0/0; approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage and final candidates all 0. Human promotion remains separate/nonautomatic.

## Next safe target

Verify the independently read-only reconciler, generation-evidence transport and generation-binding transport pinned-source reader `ValueError`/`TypeError` canary negatives on their exact-source CI.
