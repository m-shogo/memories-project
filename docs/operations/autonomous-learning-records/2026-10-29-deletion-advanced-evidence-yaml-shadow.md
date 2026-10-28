# Supplemental OPS learning — advanced deletion evidence CI YAML shadows (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, reviewed drill authority, credentials, traffic, readiness or human promotion.

## Material failure / recurrence prevention
- **Symptom:** The advanced deletion evidence publisher and independent source-negative validator checked exact event trigger inventories and reviewed Git blob identity but lacked an independent effective YAML root/permission shadow diagnostic. Static coverage gap only; no observed production bypass.
- **Observed evidence:** `validate_trigger_reachability` already rejected event header changes; `reviewed_source` pinned full workflow blobs. Neither independently classified trailing `on :`/`jobs :` root shadows or `contents : write`/`'contents': write` permission overrides.
- **Verified root cause:** A byte-identity mismatch is not a semantic test of effective root mapping and permissions; token presence alone does not prove uniqueness.
- **Failed approach:** Relying on reviewed Git blob drift for YAML mapping shadow detection.
- **Correction / executable recurrence guard:** [4503d68e](https://github.com/m-shogo/memories-project/commit/4503d68e737dc3a714b2e291db76c0973d27b64e) adds `validate_yaml_root_permission` and twelve exact-diagnostic negative fixtures (eight publisher/independent root shadows, four permission leaf shadows), retaining existing event topology, source digest, runtime and CAS proofs.
- **Retry condition:** Reassess only if reviewed YAML topology changes or another effective mapping bypass is demonstrated. Do not retry unchanged MinIO 401, canonical learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** GitHub compare `1e6ca5df...4503d68e` shows only the CI-reachable read-only validator changed (+76 lines, 0 deletions). At exact code SHA `4503d68e`, a separate deterministic source check confirmed publisher root order `name/on/permissions/concurrency/jobs`, independent `name/on/permissions/jobs`, and sole root `contents: read` leaves. [Advanced Deletion Evidence Source Negative #40743309047](https://github.com/m-shogo/memories-project/actions/runs/40743309047) was QUEUED when observed; CI success is not claimed in this record.
- **Why safe:** No publisher workflow, protected registry, production evidence, credentials, traffic or promotion authority changed.
- **Reusable mechanism:** Pin YAML effective root/permission topology with exact-diagnostic mutation fixtures alongside existing full-source SHA and executable branch/CAS checks.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged relative to the code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates remain zero. Human promotion is separate/non-automatic.
- **Next safe target:** Audit deletion container-kill and lease recovery source-negative validators for the same missing semantic guard without changing workflow authorities.
