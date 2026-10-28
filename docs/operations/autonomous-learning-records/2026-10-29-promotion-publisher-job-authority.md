# Supplemental OPS learning — human promotion publisher/independent job authority (2026-10-29)

Append-only supplemental learning only; never canonical learning, human promotion approval, production/recovery evidence, RPO/RTO/skew, reviewed drill, credentials, traffic or readiness.

## Material gap / recurrence prevention

- **Symptom:** Human promotion publisher/independent CI checked exact Git blobs, event topology, YAML roots and root permission leaves, but not independently the effective job mapping and job-scoped permission leaves. Static guard gap, not observed human-promotion bypass.
- **Observed evidence:** The reviewed publisher has `validate-pr` with `contents: read` and `validate-and-publish` with `contents: write`; the independent source-admission job has `contents: read`. Prior eighteen YAML negatives covered event/root/permission shadows only.
- **Verified root cause:** Root-level `contents: read` and byte identity do not independently prove that only the reviewed job can write or that a quoted/spaced duplicate job cannot override the mapping.
- **Failed approach:** Assuming all jobs inherit root read-only authority, or treating complete Git blob drift as a specific job/permission semantic diagnostic.
- **Correction / executable recurrence guard:** [Code commit e569583a](https://github.com/m-shogo/memories-project/commit/e569583a9e174feff0911563168f7aa9433ee35d) adds exact job identity and role-specific permission validation and twelve in-memory exact-diagnostic job/permission negatives (publisher eight, independent four), increasing the YAML negative population from eighteen to thirty.
- **Retry condition:** Revisit only after reviewed promotion publisher/independent job topology, permission semantics, or a demonstrated new bypass changes. Do not retry unchanged MinIO 401, canonical-learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Backup Restore Promotion Review Source Negative #40753781163](https://github.com/m-shogo/memories-project/actions/runs/40753781163) completed **SUCCESS** on exact code `e569583a9e174feff0911563168f7aa9433ee35d`. Logs confirm thirty exact-diagnostic YAML negatives, 82 trigger removals, sixteen additions, two shortened inventories, twelve branch cases, four writer-event cases, sixteen SHA cases, five diagnostic/atomic cases, and existing 25+2 publisher and 11+2 independent source negatives.
- **Why safe:** Only the existing CI-reachable read-only source-negative validator changed; the actual promotion workflow, registry, reviewed requests, generation/evidence contracts and human authority were untouched.
- **Reusable mechanism:** Enforce writer and read-only job permissions separately and test duplicate job mappings and quoted/spaced permission overrides with exact failure diagnostics, preserving event and source integrity checks.
- **Protected-authority check:** Git tree comparison after the code commit found no drift across 127 protected contract/backup-evidence/canonical-learning blobs. `productionDecision=NO_GO`; no learning satisfies semantically eligible generation, human-approved objective, executable reviewed request, typed eight-domain non-resurrection, independent review or human promotion gates.
- **Next safe target:** Audit other OPS-P0-007 publisher/independent job mappings and check Full Admission Chain independently of source-negative CI.
