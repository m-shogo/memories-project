# Supplemental OPS learning — drill JSON invalid acquired descriptor guard (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or semantically eligible generation, recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** Both independent drill-request JSON readers assigned an unchecked `os.open` return value to an owned FD variable before `os.fstat` and eventual `os.close`. A substituted boolean or other invalid return could be interpreted as a descriptor or accidentally close an unrelated FD. No real OS open returned such a value and no production incident was observed.
- **evidence:** At `so` HEAD `0f090e15`, `scripts/validate-memory-os-backup-restore-drill-request.py` and `scripts/reconcile-memory-os-backup-restore-drill-request.py` used `fd = os.open(...)` without checking `type(fd) is int and fd >= 0` before ownership and cleanup.
- **rootCauseOrUnknown:** Verified acquired-descriptor ownership boundary gap. External transport substitution or exploitation is unknown.
- **failedApproach:** Assuming any Python object returned by `os.open` is a valid owned integer descriptor; `bool` is an `int` subclass but is not an acceptable FD.
- **correction:** [`80f2e57b`](https://github.com/m-shogo/memories-project/commit/80f2e57b333134e69afac5ea9d7b75add465ff12) validates the exact integer nonnegative descriptor before assigning it to the owned `fd` variable in both readers.
- **recurrenceGuard:** The existing CI-reached drill-request load-negative suite now injects `True`, `False`, `-1` and `None` into each reader's open path, asserts exact fixed-class rejection and spies on `fstat` and `close` so an invalid acquired value cannot reach inspection or cleanup. Canonical positive controls and prior link/mode/mutation/close-fault negatives remain active.
- **retryCondition:** Revisit only when reviewed descriptor-acquisition logic, fixture transport or exact-source CI changes. Do not retry unchanged MinIO HTTP 401, workflow-write permission or missing external/human evidence blockers.

## Material success

- **outcome:** Invalid and boolean acquired FD values are rejected before ownership or cleanup in both readers; normal file reads still succeed.
- **evidence:** Exact-source [Unreadable Authority Negatives #41354395504](https://github.com/m-shogo/memories-project/actions/runs/41354395504) completed **SUCCESS** on `80f2e57b`; job `124991245874` logs `PASS: actual drill request JSON reader positive, invalid-FD, mode/link, mutation and close-fault negatives`, `PASS: drill reconcile reader positive, invalid-FD, mode/link, mutation and close-fault negatives`, `Drill-request unreadable/escaped-authority negative suite PASS`, and `production decision: NO_GO`. Exact-source [Drill Request Admission #41354395468](https://github.com/m-shogo/memories-project/actions/runs/41354395468) also completed **SUCCESS**. This is synthetic Python CI, not production recovery or a current-source focused Go test.
- **whySafe:** Only the two existing planning readers and their CI-reached negative suite changed. No reviewed workflow, protected production authority, credentials, traffic, generation/objective/request/evidence registry or human promotion was modified.
- **reusableMechanism:** Validate the exact acquired FD type and range before declaring ownership, then test invalid returns with guarded `fstat`/`close` spies to prevent unintended descriptor effects.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`. Registered and unsuperseded semantically eligible generations from distinct environments remain distinct; preflight requires a current explicitly human-approved recovery objective; reviewed requests are planning-only; new recovery evidence requires a current executable reviewed request; final candidates require typed eight-domain coverage and independent review; human promotion remains separate and non-automatic.

## Next safe target

Audit invalid `os.read` result types and EOF/short-read semantics in both bounded JSON readers, reusing the existing private CI negative suite and preserving all production authorities.
