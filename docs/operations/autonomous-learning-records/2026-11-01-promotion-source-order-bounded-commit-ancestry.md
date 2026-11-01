# Supplemental OPS learning — bounded human promotion Git commit/ancestry transport (2026-11-01)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — promotion commit and ancestry Git subprocesses lacked fail-closed bounds

- **symptom:** Human promotion source-order `commit_exists` and `is_ancestor` launched Git without a per-process timeout, captured stdout/stderr unnecessarily and treated bool return codes as numeric 0/1. A stalled subprocess could delay admission and a synthetic `True` return code could be interpreted as non-ancestry instead of invalid transport.
- **evidence:** At source blob `a9faba93`, both calls used `stdout=subprocess.PIPE`, `stderr=subprocess.PIPE`, no timeout and equality comparisons without exact `int` type. No real hang, secret leak or forged promotion was observed.
- **rootCauseOrUnknown:** Verified missing timeout/private-output and strict exit-type validation in two separate promotion chronology Git consumers. Actual adversarial control is unknown.
- **failedApproach:** Relying on workflow-level timeout, inherited Git process behavior and downstream review chronology checks as substitutes for bounded, fail-closed subprocess transport.
- **correction:** [`a32163f7`](https://github.com/m-shogo/memories-project/commit/a32163f7a02f63a01d9dcca19b1dcb23bd69a2ab) adds 20-second timeouts, suppresses both output streams, rejects OSError/TimeoutExpired with fixed diagnostics, and requires exact `int` exit status for commit existence and ancestry 0/1. The pinned executable, sanitized environment and source-before-review semantics remain intact.
- **recurrenceGuard:** The existing CI-invoked `--self-test` now exercises actual commit and ancestry consumers with three positive controls (commit exists, ancestor, non-ancestor) and eight nonzero/bool/timeout/unavailable/other-exit negatives. The mock asserts pinned command shape, timeout, suppressed streams, sanitized environment, fixed nonprivate error classes and 11-call multiplicity.
- **retryCondition:** Revisit on Git transport, reviewed promotion chronology or CI changes, or exact-source regression. Do not retry unchanged external MinIO HTTP 401, workflow-write permission or human production evidence blockers.

## Material success — exact-source promotion CI

- **outcome:** Human promotion source-order commit-existence and ancestry subprocesses are bounded, redacted and fail-closed on invalid transport.
- **evidence:** [Backup Restore Promotion Review Source Order #41311956689](https://github.com/m-shogo/memories-project/actions/runs/41311956689) and [Backup Restore Promotion Review #41311956973](https://github.com/m-shogo/memories-project/actions/runs/41311956973) completed **SUCCESS** at exact code HEAD `a32163f7a02f63a01d9dcca19b1dcb23bd69a2ab`. These are CI validator outcomes, not actual human review or production readiness.
- **whySafe:** Only the read-only Python validator changed. All synthetic subprocess controls are isolated and do not create or alter production evidence, reviews, generations, objectives, requests, credentials, traffic, readiness or promotion.
- **reusableMechanism:** Treat subprocess exit-code type, bounded timeout and child-output privacy as explicit transport authority for each Git consumer; require positive, negative and fixed-diagnostic checks in the existing CI path.
- **protectedAuthorityCheck:** Ten protected blobs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, approved objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion registry `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED`. Preflight requires unsuperseded semantically eligible generations from distinct environments and a current explicitly human-approved recovery objective; reviewed drill requests are planning-only; new evidence remains bound to a current executable reviewed request; final candidates require complete typed eight-domain coverage and independent review; human promotion remains separate/nonautomatic.

## Next safe target

Bound the promotion source-order creation-blob read by first checking its committed size, then verifying exact bytes. The independent real pre-MinIO Focused Go Test execution path remains unresolved.
