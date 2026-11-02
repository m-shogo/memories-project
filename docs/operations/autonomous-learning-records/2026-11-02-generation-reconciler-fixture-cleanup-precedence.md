# Supplemental OPS learning — generation reconcile fixture cleanup precedence (2026-11-02)

Append-only learning governed by canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Neither this record nor any synthetic CI may satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved recovery objective, executable reviewed drill request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure / latent secondary-cleanup override

- **symptom:** A secondary `shutil.rmtree` or descriptor-close exception in the independent generation reconcile fixture could replace the original negative-test failure, and a private cleanup exception could escape into CI logs.
- **evidence:** At `so` HEAD `c94c4898f1f851ad09abca492758cba2f4460013`, `_pinned_temporary_directory` performed unguarded `os.stat`/`require`/`shutil.rmtree` in its `finally` after `yield`, and an unguarded `os.close(fd)` in the outer `finally`. No actual CI double fault or secret disclosure was observed; the source-level failure mode was verified by exception-flow review. Prior OPS learning already established primary-error precedence for other atomic cleanup boundaries.
- **rootCauseOrUnknown:** Verified unguarded secondary cleanup exceptions in this independent fixture manager; actual runtime occurrence unknown.
- **failedApproach:** Treating cleanup as infallible and relying on the original failure to survive a second exception raised in `finally`.
- **correction:** [`183f2efd`](https://github.com/m-shogo/memories-project/commit/183f2efd5d22510ea3ba3c25584cc8fe67f4aa8c) preserves an existing primary exception and normalizes otherwise-unhandled child or descriptor cleanup errors to fixed private domain messages.
- **recurrenceGuard:** An executable two-case double-fault test injects `ValueError("PRIVATE_GENERATION_FIXTURE_SECONDARY_CLEANUP_CANARY")` from `shutil.rmtree`, both with and without a primary `Fail`. It asserts the exact primary or redacted cleanup failure, excludes the canary, restores the original cleanup function, and removes synthetic residue. The test is invoked before parent-swap negatives.
- **retryCondition:** Revisit on cleanup flow, error-classification, fixture finalizer behavior or exact-source read-only CI changes. Do not retry unchanged Quay MinIO 401, publisher-coupled writer changes, canonical learning large-blob transport or absent human evidence.

## Observed code-change outcome

- **outcome:** `183f2efd` was committed to `so`; GitHub diff and readback confirm the new primary-error preservation and executable negative test.
- **evidence:** Commit diff, source readback, branch-head comparison and protected Git blob reads. GitHub's available status response remained empty; **no exact-source CI SUCCESS is claimed**.
- **whySafe:** Only the independent read-only Negative Suite changed; no production publisher trigger, production authority, evidence registry or readiness decision was altered.
- **reusableMechanism:** Capture primary exception presence before cleanup, redact secondary failures when no primary exists, preserve primary exceptions when both fail, and test deterministic double faults with a private canary and explicit fixture cleanup.
- **protectedAuthorityCheck:** Verified unchanged Git blobs for production status `d677a1c9` (`productionDecision=NO_GO`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, canonical learning `b809c69d` and mandatory contract `87712ea9`. OPS-P0-007 remains blocked by absent real human-approved objectives and qualifying recovery evidence; human production promotion is separate/nonautomatic.

## Next safe target

Obtain exact-source read-only Negative Suite outcomes for the accumulated harness commits, especially `183f2efd`. If the suite fails, append the observed failure and correct it before extending this cleanup boundary further. Otherwise inspect the remaining independently read-only validators; do not weaken production-promotion gates.
