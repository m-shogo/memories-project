# Supplemental OPS learning — backup restore policy CI YAML shadows (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, reviewed drill authority, credentials, traffic, readiness or human promotion.

## Material failure / recurrence prevention
- **Symptom:** Reconcile backup/restore policy publisher/independent CI validator pinned event triggers and reviewed Git blob identity but lacked separate YAML root/permission shadow diagnostics. Static coverage gap, not observed production bypass.
- **Observed evidence:** `validate_trigger_reachability` checked event topology and full-source digests rejected changed bytes, but `on :`/`jobs :` root shadows and quoted/spaced `contents` overrides had no exact semantic diagnostic.
- **Verified root cause:** Source-byte identity and visible read-only tokens cannot independently prove unique effective YAML mapping and permission leaf authority.
- **Failed approach:** Relying solely on generic Git blob drift to detect semantic YAML shadows.
- **Correction / executable recurrence guard:** [d09df056](https://github.com/m-shogo/memories-project/commit/d09df05683c3c39072dda993be4bdeda3b63bb83) adds publisher/independent root and read-only permission checks plus twelve exact-diagnostic negatives (eight root, four permission), preserving existing source admission and trigger/identity/runtime negatives.
- **Retry condition:** Reassess on reviewed YAML topology/permission changes or demonstrated new bypass; do not retry unchanged MinIO 401, canonical learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** GitHub compare `17ce9058...d09df056` shows only existing CI-reachable read-only validator changed (+75 lines, 0 deletions). Before writing, both reviewed workflow root permissions were independently confirmed `contents: read`. [Reconcile Backup Restore Policy #40745277324](https://github.com/m-shogo/memories-project/actions/runs/40745277324) was QUEUED when checked; no CI success is claimed.
- **Why safe:** No workflow, production status, protected registry, evidence, credential, traffic or promotion authority changed.
- **Reusable mechanism:** Assert exact YAML root/permission semantic diagnostics independently of full-source SHA and runtime checks.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged after code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates remain zero. Human promotion remains separate/non-automatic.
- **Next safe target:** Confirm independent source-negative CI and audit worker host-failure permission boundary.

## Exact-source CI confirmation for prior independent target
- [Rate Limit Distributed Runtime Source Negative #40745160648](https://github.com/m-shogo/memories-project/actions/runs/40745160648) completed SUCCESS at code `c49cf846`; job log confirms twelve exact-diagnostic YAML negatives, six branch/base, six SHA, twenty publisher/independent source mutations and eight redaction/atomic/symlink runtime cases. No production evidence was generated.
