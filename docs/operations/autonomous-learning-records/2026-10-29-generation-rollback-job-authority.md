# Supplemental OPS learning — generation rollback diagnostics job authority (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production evidence, recovery generation/objective/drill authority, typed eight-domain non-resurrection evidence, credentials, traffic, readiness or promotion.

## Material failure / recurrence prevention

- **Symptom:** The generation rollback diagnostics negative CI validator pinned the exact event header, root YAML mapping, root `contents: read` and complete workflow blob but did not independently reject duplicate job mappings or job-level write permission shadows. This is a static guard gap, not observed production or recovery failure.
- **Observed evidence:** Reviewed rollback diagnostics workflow Git blob `79ad7da92fc35fdec16f69e9b7b432ba669ad886` contains one `validate` job inheriting root read-only permissions, with only `runs-on: ubuntu-latest` and `steps` as job-level keys. Prior YAML semantic negative inventory had nine cases.
- **Verified root cause:** Root permission and exact source identity do not independently prove unique nested job identity or the absence of job-scoped privilege escalation.
- **Failed approach:** Relying on whole-source digest or root permission checks as the only protection for job-level YAML semantics.
- **Correction / recurrence guard:** [fc0dffec](https://github.com/m-shogo/memories-project/commit/fc0dffec47e5e2302798cb18fd3fd7629b3f728b) pins the sole job mapping and exact allowed job keys; adds six exact-diagnostic synthetic negatives for duplicate/spaced/quoted `validate` job mapping and plain/spaced/quoted `contents: write` job permission injection. YAML negatives increase from nine to fifteen.
- **Retry condition:** Reassess after independently reviewed job topology/permission changes or a newly demonstrated bypass. Unchanged MinIO 401, canonical-learning transfer, supplemental workflow-write permission and human promotion blockers are not retryable by this guard.

## Material success / protected authority

- **Outcome/evidence:** [Generation Evidence Rollback Diagnostics Negative #40770775147](https://github.com/m-shogo/memories-project/actions/runs/40770775147) completed SUCCESS for exact source `fc0dffec47e5e2302798cb18fd3fd7629b3f728b`. CI job log confirms fifteen YAML exact-diagnostic negatives and nineteen semantic anchor plus two blob-only negatives. Compare `ab317631` → `fc0dffec` changed only the existing CI-reachable validator (+34/-2).
- **Why safe:** Reviewed workflow, source SHA/branch guards, protected production/OPS-P0-007 contracts, registries, recovery evidence, credentials, traffic and human promotion were not modified; all mutation probes are synthetic.
- **Reusable mechanism:** Enumerate exact job mappings and top-level job keys independently of root YAML, prove shadow/privilege rejection with diagnostic-specific negatives, retain whole-source blob and trigger reachability checks.
- **Protected-authority check:** `autonomous-learning-system.json` Git blob remains `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`; production status remains `NO_GO`, generation and generation-evidence registries remain empty. No objective, executable reviewed request, typed eight-domain record, independent final candidate review or human promotion was fabricated or promoted. Supplemental learning cannot satisfy any admission/readiness gate.
- **Next safe target:** Audit environment review-independence publisher/PR job-level permission separation and shadow keys without changing its reviewed workflow or human promotion authority.
