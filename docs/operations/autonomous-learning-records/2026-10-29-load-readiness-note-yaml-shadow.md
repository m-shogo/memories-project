# Supplemental OPS learning — load readiness note CI YAML shadows (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, reviewed drill authority, credentials, traffic, readiness or human promotion.

## Material failure / recurrence prevention
- **Symptom:** Load readiness note publisher/independent CI validator pinned event trigger paths and reviewed Git blob identity but did not independently classify YAML root/permission shadows. Static coverage gap, not observed production bypass.
- **Observed evidence:** `load_readiness_validate_trigger_matrix` checked event topology and source digests rejected changed bytes, but `on :`/`jobs :` root shadows and quoted/spaced `contents` overrides lacked exact semantic diagnostics.
- **Verified root cause:** Source-byte identity and visible permission tokens do not independently prove unique effective YAML mapping and read-only permission leaves.
- **Failed approach:** Relying on generic Git blob drift for semantic YAML shadow detection.
- **Correction / executable recurrence guard:** [c95e8586](https://github.com/m-shogo/memories-project/commit/c95e858674e4e780ff0a5e5505dcceee802bd0ba) adds publisher/independent root and read-only permission checks plus twelve exact-diagnostic negative fixtures (eight root, four permission), retaining event/identity/runtime/source checks.
- **Retry condition:** Reassess on reviewed YAML topology/permission changes or demonstrated new bypass; do not retry unchanged MinIO 401, canonical learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** GitHub compare `4c71b66d...c95e8586` shows only CI-reachable read-only validator changed (+75 lines, 0 deletions). Before writing, both reviewed workflow root permissions were independently confirmed `contents: read`. [Load Readiness Note Source Negative #40744838841](https://github.com/m-shogo/memories-project/actions/runs/40744838841) was QUEUED when observed; CI SUCCESS is not claimed.
- **Why safe:** No workflow, production status, protected registry, evidence, credential, traffic or promotion authority changed.
- **Reusable mechanism:** Require exact semantic YAML root/permission diagnostics independently of source SHA and executable runtime checks.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged after code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates remain zero. Human promotion remains separate/non-automatic.
- **Next safe target:** Audit load-missing and load-foundation source-negative YAML authority and verify exact-source CI.

## Exact-source CI confirmation for prior independent target
- [Deletion Worker Container Kill Recovery Diagnostic Source Negative #40744701888](https://github.com/m-shogo/memories-project/actions/runs/40744701888) completed SUCCESS at code `67b95b8a`; job log confirms fourteen exact-diagnostic YAML negatives and 23 policy source mutations. No production evidence was generated.
