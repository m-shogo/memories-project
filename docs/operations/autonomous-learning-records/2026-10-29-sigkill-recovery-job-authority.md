# Supplemental OPS learning — worker SIGKILL recovery nested job authority (2026-10-29)

Append-only supplemental learning only; not canonical learning, production-equivalent recovery, backup/restore, RPO/RTO/skew, drill authority, credentials, traffic, readiness or human promotion evidence.

## Material static gap / executable prevention

- **Symptom:** The worker SIGKILL recovery source-negative validator pinned event triggers, YAML roots/permissions, reviewed Git blobs and runtime diagnostics, but lacked independent nested job mapping, inherited permission and shadow-key negative proof. This was a static guard gap, not observed unauthorized SIGKILL recovery or production evidence.
- **Observed evidence:** Reviewed publisher blob `1ae00600d8ccbe1e9c70ad6d2bbfb6212e729313` contains `prove` (inherited root write, timeout 25, PostgreSQL service). Reviewed independent blob `f569abd277f668a4ea2e7af62b4b1d24e9a17a08` contains `source-negative` (explicit read, PR/push so condition, timeout 5). The old validator had no job-level semantic negative suite.
- **Verified root cause:** Whole-source blob equality and root YAML permission checks do not independently demonstrate unique effective nested job identity, inherited write scope or explicit read-only job scope.
- **Failed approach:** Assuming root permission and digest checks alone supply distinct job-level semantic evidence; adding unreviewed job permission overrides or conditions would require separate detection.
- **Correction / executable recurrence guard:** [Code `875ed8a0`](https://github.com/m-shogo/memories-project/commit/875ed8a0cc26d8119a6da85ab4401fb71941a056) reuses the already CI-validated container-kill job guard with the reviewed identical job topology, adding **24 exact-diagnostic in-memory negatives** for duplicate/quoted/spaced mappings, runner/timeout/steps/services shadows, continuation override, inherited permission overrides and independent condition/permission shadows.
- **Retry condition:** Revisit only if reviewed job topology/permissions change or a demonstrated bypass arises. Do not retry unchanged PostgreSQL client-major, MinIO 401, canonical-learning transport or human-approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [SIGKILL Recovery Diagnostic Source Negative #40793306554](https://github.com/m-shogo/memories-project/actions/runs/40793306554) completed **SUCCESS** on exact source `875ed8a0`. Logs confirm 24 new exact-diagnostic job negatives, 14 root/permission negatives, 34 trigger omissions, 12 additions, three shortened inventories, 12 runtime identity cases, 23 source mutations, seven diagnostic-writer cases, eight atomic rollback cases and strict JSON/path negatives passing. Output explicitly states `production evidence generated: false; production decision changed: false`.
- **Why safe:** Only the existing independently CI-reachable read-only Python validator changed; reviewed workflows, registry, production evidence, credentials, traffic, readiness and human promotion were untouched. Mutations were in-memory.
- **Reusable mechanism:** Reuse a proven semantic job guard only after verifying the exact reviewed publisher/independent job topology and permissions; keep the full Git blob as a separate source seal.
- **Protected-authority check:** Production status blob `3956bb805ee124ca7baf594ba05bcb0d986783b4` remains `productionDecision=NO_GO`; canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628` and learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. No production-equivalent generation, approved objective, executable reviewed drill, typed eight-domain record, independent final review or human promotion is asserted.
- **Next safe target:** Audit deletion pre-fence upload diagnostic source-negative nested job authority and its existing mutation diagnostics.
