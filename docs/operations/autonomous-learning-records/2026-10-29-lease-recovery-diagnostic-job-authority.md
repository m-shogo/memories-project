# Supplemental OPS learning — deletion lease-recovery diagnostic nested job authority (2026-10-29)

Append-only supplemental learning only, never canonical learning, production-equivalent recovery evidence, backup/restore, RPO/RTO/skew, reviewed drill, credentials, traffic, readiness or human promotion.

## Material static gap / executable recurrence prevention

- **Symptom:** Lease-recovery diagnostic source-negative CI pinned reviewed Git blobs, exact triggers, root permissions and runtime identity but lacked independent nested job mapping, service and permission-shadow negatives. Static admission-guard gap only, not observed unauthorized lease recovery or production evidence.
- **Observed evidence:** Publisher blob `12129252904c15d5a9c335fd0b529319d1f0b71a` has `prove` (inherited root write, timeout 25, PostgreSQL service); independent blob `f76d9a92924355358d005d5b49c73d30c4be4b3b` has `source-negative` (explicit read, PR/push so, timeout 5).
- **Verified root cause:** Root permission and whole-source Git blob checks cannot independently demonstrate unique effective nested job identity, inherited publisher write scope or independent read-only permission.
- **Failed approach:** Treating root permission and digest equality as sufficient nested job semantic proof, or assuming the publisher declares a job-level permission when it actually inherits root write.
- **Correction / executable recurrence guard:** [Code `f1330964`](https://github.com/m-shogo/memories-project/commit/f1330964716ba807c15c2b02f23e5a2c7092cdc4) reuses the CI-proven guard after verifying matching reviewed job topology, adding **24 exact-diagnostic in-memory negatives** for duplicate/quoted/spaced mappings, runner/timeout/steps/services shadows, continuation override, inherited permission overrides and independent condition/permission shadows.
- **Retry condition:** Revisit only if reviewed job topology, inherited permissions or an observed bypass changes. Do not retry unchanged PostgreSQL client-major, MinIO 401, canonical learning transport or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Lease Recovery Diagnostic Source Negative #40794086438](https://github.com/m-shogo/memories-project/actions/runs/40794086438) completed **SUCCESS** on exact source `f1330964`. Logs show 24 new exact-diagnostic job negatives, 14 root/permission negatives, 33 trigger omissions, 12 additions, three shortened inventories, 12 runtime identity cases, 23 policy source negatives, seven diagnostic-writer cases, eight atomic rollback cases and strict result checks passing. Output explicitly states `production evidence generated: false; production decision changed: false`.
- **Why safe:** Only the existing independently CI-reachable read-only Python validator changed. All mutations were in-memory; reviewed workflows, production contracts, registries, evidence, credentials, traffic, readiness and human promotion were untouched.
- **Reusable mechanism:** Match reviewed inherited-write and explicit-read job topology before reusing semantic guard fixtures, and retain the whole-source Git blob as an independent seal.
- **Protected-authority check:** Current production status blob `3ab8092c7e3fec2b48d62fb2728f024151f610c5` remains `productionDecision=NO_GO`; canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628` and learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. No production-equivalent generation, approved objective, executable reviewed request, typed eight-domain non-resurrection evidence, independent final review or human promotion is asserted.
- **Next safe target:** Audit deletion lease-recovery authority source-negative publisher/independent jobs without changing OPS-P0-007 or retrying the PostgreSQL client-major blocker.
