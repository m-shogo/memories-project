# Supplemental OPS learning — recovery objective publisher source lease guard (2026-11-02)

Append-only operational learning under canonical history and mandatory autonomous-learning contract. This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — publisher job authority mismatch

- **symptom:** A new read-only publisher-coupling guard initially failed because it searched for a `validate` job rather than the actual `validate-and-publish` job.
- **evidence:** Exact-source [Recovery Objectives Reconcile Negative #41383233040](https://github.com/m-shogo/memories-project/actions/runs/41383233040) FAILED at `8218da96`; job `125078353112` printed `recovery objective publisher coupling unexpectedly absent`. The reviewed `.github/workflows/recovery-objectives-admission.yml` has a `validate-and-publish` job with `contents: write`, not `validate`.
- **rootCauseOrUnknown:** Verified incorrect job-key assumption in the new static guard, not an absent publisher trigger. No production failure or actual authority drift was observed.
- **failedApproach:** Reusing another workflow's publisher job name without checking the target workflow's exact YAML job key.
- **correction:** [`6a1c3488`](https://github.com/m-shogo/memories-project/commit/6a1c34880065028e57dc7796dccbf24ab882c649) binds the guard to `validate-and-publish`; initial guard was [`8218da96`](https://github.com/m-shogo/memories-project/commit/8218da96c23093ee020120bad1afb2740bf609a2).
- **recurrenceGuard:** `scripts/validate-memory-os-recovery-objectives-reconcile-workflow-negative.py` now checks the publisher's actual write-capable job, `push.paths` coupling, latest-source `SOURCE_SHA` guard and exit-75 stale refusal. It injects two negative mutations and allows removal of the publisher trigger as a safe decoupling. The script itself triggers only read-only Reconcile Negative CI.
- **retryCondition:** Revisit when recovery-objective publisher job keys, permissions, push paths, source lease, guarded publication or read-only CI changes. Do not retry unchanged workflow permission, large canonical blob transport, MinIO HTTP 401 or missing human evidence blockers.

## Material success

- **outcome:** [Recovery Objectives Reconcile Negative #41383304444](https://github.com/m-shogo/memories-project/actions/runs/41383304444) completed **SUCCESS** on exact source `6a1c34880065028e57dc7796dccbf24ab882c649`.
- **evidence:** Job `125078568880` logged `PASS: recovery objective publisher trigger coupling and source lease (2 negatives)`, `Recovery objective reconcile negative suite PASS`, and `production decision: NO_GO`.
- **whySafe:** Only the existing read-only workflow-negative validator changed. The file is in the read-only Reconcile Negative push trigger and absent from the write-capable Recovery Objectives Admission push trigger. No workflow authority, production evidence, objective registry, credential or traffic was modified.
- **reusableMechanism:** Inspect the exact target publisher job name before writing a static topology guard; validate both trigger coupling and stale-source rejection with deterministic negative mutations.
- **protectedAuthorityCheck:** Canonical learning blob `b809c69d`, learning contract `87712ea9`, production status `d677a1c9`, OPS-P0-007 snapshot `dbaa36b0`, environment generations `bfd1b045`, recovery objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed eight-domain coverage `26bb1cc7`, and promotion registry `99cb895f` remain unchanged from initial `so` `c6bcdb85`. `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`; registered and semantically eligible distinct environments 0/0, current approved objective 0, executable reviewed request 0, request-bound recovery 0, complete typed coverage 0 and final candidates 0. Human promotion remains separate/nonautomatic.

## Next safe target

Audit other publisher-free read-only negative suites and their full write-capable trigger topology. Do not modify production readiness or weaken OPS-P0-007 gates.
