# Supplemental OPS learning — deletion container-kill authority nested jobs (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production deletion/recovery evidence, backup/restore, RPO/RTO/skew, reviewed drill, credentials, traffic, readiness or human promotion.

## Material static gap / executable recurrence prevention

- **Symptom:** Deletion container-kill authority source-negative CI pinned reviewed Git blobs, event/root permissions and CAS/runtime source identity, but lacked independently tested nested job mapping, inherited PR-read and job-level write shadows. Static CI-admission gap only, not observed unauthorized deletion evidence.
- **Observed evidence:** Publisher blob `3284fc4bd9626bcac46a88b6c571d9db01dd3cf2` has `validate` (PR base so, inherited root read, timeout 10) and `reconcile` (push/dispatch so, explicit write, timeout 10); independent blob `3a3549fce360edc9a72c558a02a13db7cdf09d60` has `source-negative` (explicit read, timeout 5).
- **Verified root cause:** Root permissions and whole-source Git blob equality cannot independently demonstrate unique nested jobs, inherited PR read-only authority, publisher write isolation or fail-closed YAML shadows.
- **Failed approach:** Treating all publisher jobs as explicitly permission-scoped or relying on root/digest guards alone; this publisher's PR validation inherits read-only root permission while the reconcile job explicitly elevates to write.
- **Correction / executable recurrence guard:** [Code `75492880`](https://github.com/m-shogo/memories-project/commit/754928804c2a624a0431b92c06c0767570b4c5c4) adds a dedicated read-only nested job guard with **36 exact-diagnostic in-memory negatives** (12 per job). It pins job mappings, PR/push conditions, timeout, runner, steps, inherited-read scope and explicit write/read leaves; rejects duplicate/quoted/spaced mappings, condition/permission shadows, continuation override, permission escalation and unexpected environment.
- **Retry condition:** Revisit only if reviewed job topology, permission inheritance, PR scope or a new bypass changes. Do not retry unchanged PostgreSQL client-major, MinIO 401, canonical learning transfer or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Deletion Container-Kill Authority Source Negative #40794364059](https://github.com/m-shogo/memories-project/actions/runs/40794364059) completed **SUCCESS** on exact code `75492880`. Logs confirm 36 new nested job negatives, 12 root/permission negatives, 38 trigger omissions, 16 additions, four shortened inventories, three event topology negatives, 14 publisher source mutations, PR/writer runtime, five CAS/no-op cases and local atomic/cross-publisher checks passing. Output explicitly states `production evidence generated: false`.
- **Why safe:** Only the independently CI-reachable read-only Python validator changed; in-memory fixtures did not alter reviewed workflows, contracts, registries, evidence, credentials, traffic, readiness or promotion authority.
- **Reusable mechanism:** Distinguish inherited root-read validation from explicit job-write reconciliation and independent job-read authority; require exact-diagnostic semantic negatives before whole-file Git blob checks.
- **Protected-authority check:** Production status blob `3ab8092c7e3fec2b48d62fb2728f024151f610c5` remains `productionDecision=NO_GO`; canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628` and learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. No production-equivalent generation, approved objective, executable reviewed drill, complete typed eight-domain non-resurrection evidence, independent final review or human promotion is asserted.
- **Next safe target:** Audit deletion SIGKILL authority source-negative job boundaries while leaving unchanged external blockers isolated.
