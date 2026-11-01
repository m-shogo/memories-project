# Supplemental OPS learning — binding reconcile primary error and rollback double-fault (2026-11-02)

Append-only operational learning subordinate to canonical policy. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final-candidate or human-promotion evidence.

## Material failure

- **symptom:** A secondary rollback failure could hide the primary binding post-validation or atomic-write failure.
- **evidence:** At starting HEAD `2930c2ad`, `_reconcile` caught `Exception` and attempted rollback, but only handled `OSError` from the rollback. The newly hardened `atomic_write_text` returns a fixed-class `Fail`, so an unsuccessful rollback could replace the primary failure without an explicit incomplete-rollback diagnostic. The isolated negative injects both failures. No real production rollback failure or corruption was observed.
- **rootCauseOrUnknown:** Verified mismatch between rollback's `except OSError` and writer's `Fail` contract; real-world occurrence unknown.
- **failedApproach:** Handling only raw `OSError` during rollback while a reviewed writer now normalizes its failures to `Fail`.
- **correction:** [`70983bae`](https://github.com/m-shogo/memories-project/commit/70983baec2dc289ebc42a16c47cb2ea757018963) handles secondary rollback exceptions explicitly, marks rollback incomplete using fixed-class type diagnostics, and retains the original primary exception in the causal chain.
- **recurrenceGuard:** Existing CI-reached binding reconcile negative suite injects a post-write validator rejection and a failed second rollback write against an isolated contract. It asserts both attempts occurred, the primary exception is preserved, private exception messages are withheld, and the synthetic fixture is restored byte-for-byte with its mode and no leftover temp. Canonical contract and drill registry remain unchanged.
- **retryCondition:** Revisit on a reviewed rollback/writer exception-contract change or exact-source CI regression. Do not retry unchanged MinIO HTTP 401, workflow permissions, external evidence or human-promotion blockers.

## Material success

- **outcome:** The binding reconciler explicitly rejects incomplete rollback while preserving its original validation failure.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41333109710](https://github.com/m-shogo/memories-project/actions/runs/41333109710) completed SUCCESS at code HEAD `70983bae`. It validates the synthetic double-fault guard; it is not production recovery evidence.
- **whySafe:** Only the binding reconciler and existing CI-reached isolated negative suite changed; no production status, OPS-P0-007 snapshot, registry, workflow permission or human authority was changed.
- **reusableMechanism:** When transactional rollback fails, retain the original exception as cause, emit a bounded private-safe incomplete marker, test two fault injections and restore isolated fixtures.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound recovery evidence 0, complete typed eight-domain coverage 0, final candidates 0. Only unsuperseded semantically eligible generations from distinct environments plus a human-approved current objective enter preflight; reviewed requests are planning-only, new evidence is bound to a current executable reviewed request, final candidates require complete typed eight-domain coverage and independent review, and human promotion remains separate/nonautomatic.

## Next safe target

Audit the binding reconciler's planning-authority JSON loader for duplicate-key/nonfinite ambiguity and bounded reading; reuse existing CI-reached negative fixtures, without creating or changing planning/production evidence.
