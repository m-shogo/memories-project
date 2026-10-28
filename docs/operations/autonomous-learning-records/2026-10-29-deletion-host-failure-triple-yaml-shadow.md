# Supplemental OPS learning — deletion host-failure triple CI YAML shadows (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, reviewed drill authority, credentials, traffic, readiness or human promotion.

## Material failure / recurrence prevention
- **Symptom:** Host-failure publisher, independent source-negative and permission-negative CI workflows had reviewed Git blob and event/permission token guards but lacked a shared independent semantic root/permission shadow diagnostic across all three authorities. Static coverage gap, not observed production bypass.
- **Observed evidence:** `validate`, `validate_trigger_matrix` and `validate_permission` enforced source inventories and whole Git blob identity; `on :`/`jobs :` root shadows and spaced/quoted `contents` overrides had no mutation-specific semantic diagnostic across all three workflows.
- **Verified root cause:** Byte identity and visible read-only tokens do not independently establish unique effective YAML root mapping and permission authority for each workflow.
- **Failed approach:** Relying solely on generic full-source digest mismatch and token presence for effective YAML mapping semantics.
- **Correction / executable recurrence guard:** [15aac39f](https://github.com/m-shogo/memories-project/commit/15aac39f926f699cf403b631cafcec9708961cc5) adds exact root and read-only permission checks across all three workflows plus eighteen exact-diagnostic negative fixtures (twelve root, six permission). Existing event, permission-validator, runtime, writer and reconcile tests remain.
- **Retry condition:** Reassess on reviewed YAML topology/permission changes or demonstrated new bypass; do not retry unchanged MinIO 401, canonical learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** GitHub compare `c40ff7b6...15aac39f` confirms only the CI-reachable read-only validator changed (+75 lines, 0 deletions). Before writing, all three reviewed workflows had root `contents: read`, with publisher/permission workflows using `concurrency` and independent workflow not. Exact-source CI had not yet been observed at record creation; no SUCCESS is claimed.
- **Why safe:** No workflow, production status, protected registry, evidence, credential, traffic or promotion authority changed.
- **Reusable mechanism:** Validate all CI authorities in the same trust chain, including the separate permission-negative workflow, using mutation-specific semantic YAML diagnostics independently of reviewed Git blob identity.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged after code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates remain zero. Human promotion remains separate/non-automatic.
- **Next safe target:** Verify host-failure exact-source CI and audit remaining CI source-negative mapping gaps.

## Exact-source CI confirmation for prior independent target
- [Reconcile Backup Restore Source Negative #40745277311](https://github.com/m-shogo/memories-project/actions/runs/40745277311) completed SUCCESS at code `d09df056`; job log confirms twelve exact-diagnostic YAML negatives, 38 event removals, sixteen additions, two shortened inventories, sixteen runtime branch/event cases, 29 semantic and five blob-only source negatives. No production evidence was generated. Publisher/Full Admission Chain status is tracked separately.
