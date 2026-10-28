# Supplemental OPS learning — pre-fence upload diagnostic CI YAML shadows (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, reviewed drill authority, credentials, traffic, readiness or human promotion.

## Material failure / recurrence prevention
- **Symptom:** Pre-fence upload diagnostic publisher/independent CI validator pinned event paths and reviewed Git blob identity but did not independently classify YAML root/permission shadows. Static coverage gap, not an observed production bypass.
- **Observed evidence:** `prefence_upload_trigger_matrix` checked reviewed event topology; source digest checks rejected changed bytes but did not produce exact semantic diagnostics for `on :`/`jobs :` root shadows or quoted/spaced `contents` overrides.
- **Verified root cause:** Source-byte identity and visible permission tokens cannot independently prove unique effective YAML root mapping or permission leaves.
- **Failed approach:** Relying solely on a generic Git blob mismatch for YAML semantic shadow detection.
- **Correction / executable recurrence guard:** [dc095aed](https://github.com/m-shogo/memories-project/commit/dc095aed41a970bfe38e9815b10db8889d57de65) adds publisher-write/independent-read root/permission checks and fourteen exact-diagnostic negative fixtures (eight root, four permission shadows, two direct permission replacements), preserving event, runtime, CAS and source checks.
- **Retry condition:** Reassess on reviewed YAML topology or permission changes or demonstrated new bypass; do not retry unchanged MinIO 401, canonical learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** GitHub compare `c2e51ddb...dc095aed` confirms only the CI-reachable read-only validator changed (+80 lines, 0 deletions). Before writing, publisher root `contents: write` and independent root `contents: read` were verified against reviewed workflow blobs. Exact-source CI had not yet been observed at record creation; no SUCCESS claim is made.
- **Why safe:** The guard matches existing publisher writer authority without changing workflows, production status, registry, evidence, credentials, traffic or promotion.
- **Reusable mechanism:** Inspect per-workflow root permission before generating exact-diagnostic YAML negative fixtures, preserving distinct publisher/independent authority.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged after code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates remain zero. Human promotion remains separate/non-automatic.
- **Next safe target:** Audit remaining deletion worker failure source-negative CI and verify exact-source CI.

## Exact-source CI confirmation for prior independent target
- [Deletion Pre-Fence Mutation Diagnostic Source Negative #40744231275](https://github.com/m-shogo/memories-project/actions/runs/40744231275) completed SUCCESS at code `28019453`; job log confirms fourteen exact-diagnostic YAML negatives, 34 trigger omissions, twelve additions, three shortened inventories, three topology negatives, 26 policy mutations, seven writer, seven reconcile CAS, 23 strict JSON and 119 typed criteria runtime negatives. No production evidence was generated.
