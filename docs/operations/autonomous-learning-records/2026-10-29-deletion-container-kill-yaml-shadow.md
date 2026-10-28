# Supplemental OPS learning — deletion container-kill CI YAML shadows (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, reviewed drill authority, credentials, traffic, readiness or human promotion.

## Material failure / recurrence prevention
- **Symptom:** The container-kill publisher and independent source-negative CI validator pinned exact event triggers and full Git blob identity but did not separately diagnose YAML root and permission shadows. Static coverage gap, not an observed production bypass.
- **Observed evidence:** `container_kill_validate_trigger_matrix` compared reviewed event path matrices; `reviewed_source` rejected any blob change, but no semantic guard classified trailing `on :`/`jobs :` root mapping or quoted/spaced `contents` leaf overrides.
- **Verified root cause:** Complete source identity does not independently establish effective YAML root mapping or unique read-only permission leaves.
- **Failed approach:** Using only generic source digest rejection for semantically distinct YAML mapping bypasses.
- **Correction / executable recurrence guard:** [b0504986](https://github.com/m-shogo/memories-project/commit/b05049866cc1625e1c0ecef0b54de7f4a39cd7f2) adds `validate_yaml_root_permission` and twelve exact-diagnostic negative fixtures (eight root shadows, four permission shadows) to the existing CI-reachable validator. Event inventory, reviewed Git blobs, identity, runtime and CAS proofs remain.
- **Retry condition:** Reassess on reviewed YAML root/permission topology changes or a newly demonstrated bypass. Do not retry unchanged MinIO 401, canonical learning transfer, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** GitHub compare `d078a1ff...b0504986` confirms only the read-only validator changed (+76 lines, 0 deletions). Separate source inspection at `b0504986` verified publisher root order `name/on/permissions/concurrency/jobs` and independent `name/on/permissions/jobs` with a single root `contents: read` leaf. [Deletion Container-Kill Authority Source Negative #40743405736](https://github.com/m-shogo/memories-project/actions/runs/40743405736) was IN_PROGRESS when checked; do not infer CI SUCCESS.
- **Why safe:** No reviewed workflow, production status, recovery evidence, registry, objective, generation, credential, traffic or promotion authority changed.
- **Reusable mechanism:** Test exact effective YAML root/permission semantics with mutation-specific diagnostics, independent of whole-source SHA and executable CAS/identity proofs.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning Git blob SHAs unchanged after the code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates remain zero. Human promotion is separate/non-automatic.
- **Next safe target:** Continue with deletion lease-recovery source-negative CI validators, reusing existing semantic guard patterns without changing protected authorities.

## Exact-source CI observations closing earlier pending records
- [Review Source Order Readonly #40743071402](https://github.com/m-shogo/memories-project/actions/runs/40743071402) completed SUCCESS at code `5c198170`; job log proves nine exact-diagnostic YAML negatives, 40 trigger omissions, eight additions, one shortened inventory, six branch-runtime cases, 20 semantic and two blob-only source negatives, with canonical byte/mode postcondition successful. This closes the earlier pending-CI note without editing that append-only record.
- [Advanced Deletion Evidence Source Negative #40743309047](https://github.com/m-shogo/memories-project/actions/runs/40743309047) completed SUCCESS at code `4503d68e`; job log proves twelve exact-diagnostic YAML negatives, 40 trigger omissions, sixteen additions, two shortened inventories, three topology negatives, fourteen source mutations, fourteen identity runtime cases and five publisher CAS/no-op cases. No production evidence was generated.
