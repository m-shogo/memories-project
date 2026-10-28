# Supplemental OPS learning — deletion lease recovery CI YAML shadows (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, reviewed drill authority, credentials, traffic, readiness or human promotion.

## Material failure / recurrence prevention
- **Symptom:** Lease recovery publisher/independent CI source-negative validator verified exact event triggers and full Git blob identity but lacked a separate YAML root/permission shadow diagnostic. Static coverage gap, not observed production bypass.
- **Observed evidence:** `validate_trigger_reachability` verified publisher and independent event path inventories; reviewed source blobs were pinned. Trailing `on :`/`jobs :` root shadows and quoted/spaced `contents` leaves were previously classified only as generic source drift.
- **Verified root cause:** Complete byte identity and token membership do not independently prove the effective YAML mapping has unique root and permission authority.
- **Failed approach:** Relying on a Git blob mismatch as the only explanation for semantically meaningful YAML shadow mutations.
- **Correction / executable recurrence guard:** [c4696386](https://github.com/m-shogo/memories-project/commit/c469638654210a31fd07b489e1fee8313cb3f102) adds explicit publisher/independent root/permission validation and twelve exact-diagnostic negative fixtures (eight root, four permission), preserving event inventory, runtime, publisher CAS and source digest checks.
- **Retry condition:** Reassess on reviewed YAML topology change or demonstrated new shadow bypass; do not retry unchanged MinIO 401, canonical learning transfer, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** GitHub compare `00f10d9c...c4696386` shows only existing CI-reachable read-only validator changed (+76 lines, 0 deletions). Reviewed publisher root order is `name/on/permissions/concurrency/jobs`; independent is `name/on/permissions/jobs`; both have a single root `contents: read` leaf. Exact-source CI was not yet available when recorded; no SUCCESS claim is made here.
- **Why safe:** No reviewed workflow, production status, registry, recovery evidence, credential, traffic or promotion authority changed.
- **Reusable mechanism:** Exact YAML root/permission semantic diagnostics plus in-memory negative mutations, independent of existing full-source SHA and branch/CAS proof.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged after the code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates remain zero. Human promotion remains separate/non-automatic.
- **Next safe target:** Continue deletion mutation-evidence and lease diagnostic source-negative YAML semantic guard audit without editing protected authorities.

## Exact-source CI confirmation for prior independent target
- [Deletion Container-Kill Authority Source Negative #40743405736](https://github.com/m-shogo/memories-project/actions/runs/40743405736) completed SUCCESS at code `b0504986`; job log confirms twelve exact-diagnostic YAML negatives, 38 trigger omissions, sixteen additions, four shortened inventories, three topology negatives, fourteen publisher source mutations, fourteen identity-runtime cases and five publisher CAS/no-op cases. No production evidence was generated. This append-only observation closes the earlier pending CI record.
