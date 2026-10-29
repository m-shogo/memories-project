# Supplemental OPS learning — deletion mutation-evidence nested job authority (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production deletion evidence, backup/restore, RPO/RTO/skew, reviewed drill, credentials, traffic, readiness or human promotion.

## Material static gap / executable recurrence prevention

- **Symptom:** The deletion mutation-evidence CI source validator pinned exact event/root/permission, reviewed Git blobs, CAS and runtime source identity, but lacked independent nested job mapping and job permission shadow tests. This was a static source-admission gap, not observed unauthorized evidence publication.
- **Observed evidence:** Publisher blob `a8f7e07803fdc88ce3183017d754986e0488bf57` has PR-only `validate-pr` (read, timeout 10, condition includes `github.base_ref == 'so'`) and `reconcile` (push/dispatch so, write, timeout 10). Independent blob `34127c6c007016ef570072c567c7f3144a9763ca` has `source-negative` (read, timeout 5). Previous validator lacked job-level exact-diagnostic fixtures.
- **Verified root cause:** Whole-source Git blob equality and root permission checks do not independently prove effective nested job uniqueness, publisher write isolation, PR base constraint or job-level permission leaves.
- **Failed approach:** Reusing another publisher's job schema without checking its PR base condition, job name and timeout would misclassify reviewed authority; relying on root permission and Git blob checks alone leaves no independent nested semantic proof.
- **Correction / executable recurrence guard:** [Code `19b165aa`](https://github.com/m-shogo/memories-project/commit/19b165aa4933ff3c3cd9a3134fb3b60ab861ba8d) adapts the CI-proven dependency job guard to the exact reviewed `validate-pr`/`reconcile`/`source-negative` schema, including PR base condition and publisher timeout 10. Adds **36 in-memory exact-diagnostic negatives** (12 per job) for duplicate/quoted/spaced mappings, condition/permission/runner/timeout/steps shadows, continuation override and direct/spaced/quoted permission changes.
- **Retry condition:** Revisit only if reviewed job topology, PR base scope, permissions or a new bypass changes. Do not retry unchanged PostgreSQL client-major, MinIO 401, canonical-learning transport or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Deletion Mutation Evidence Source Negative #40793659739](https://github.com/m-shogo/memories-project/actions/runs/40793659739) completed **SUCCESS** on exact code `19b165aa`. Logs confirm 36 new job negatives, 12 YAML root/permission negatives, 36 trigger omissions, 16 additions, two shortened inventories, three event topology negatives, 14 publisher source mutations, six PR and eight writer runtime cases, five publisher CAS/no-op cases, plus atomic rollback proof. Output explicitly states `production evidence generated: false`.
- **Why safe:** Only the existing independently CI-reachable read-only Python validator changed. In-memory mutations never wrote production contracts, registries, evidence, credentials, traffic, readiness or human promotion authority.
- **Reusable mechanism:** Reuse a proven semantic job guard only after verifying exact job name, PR base condition, timeout and read/write permission scope; preserve whole-source Git blob checks independently.
- **Protected-authority check:** Production status blob `3956bb805ee124ca7baf594ba05bcb0d986783b4` remains `productionDecision=NO_GO`; canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628` and learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. No production-equivalent generation, approved objective, executable reviewed request, typed eight-domain non-resurrection record, independent final review or human promotion is asserted.
- **Next safe target:** Audit deletion advanced-evidence source-negative job authority; avoid unchanged external blockers.
