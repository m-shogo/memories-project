# Supplemental OPS learning — atomic inventory triple CI YAML authority (2026-10-29)

Append-only supplemental learning only; never canonical learning, production/recovery evidence, approved objectives, executable reviewed drills, typed eight-domain records, credentials, traffic, readiness or human promotion.

## Material failure / recurrence prevention
- **Symptom:** Atomic inventory source guard pinned publisher, independent and replacement workflow blobs and visible read-only permission tokens but lacked independent effective YAML event/root/permission shadow checks. This was a static coverage gap, not an observed atomic-write or production bypass.
- **Observed evidence:** `validate` and `validate_replacement` authenticated source blobs, branch/SHA checks and visible permission tokens; extra events and shadow mappings previously depended on whole-source digest rejection.
- **Verified root cause:** Git blob identity and visible tokens alone do not independently prove unique effective YAML mapping or intended semantic diagnostic.
- **Failed approach:** Treating any digest mismatch as sufficient event/permission shadow regression proof.
- **Correction / executable recurrence guard:** [3f9eb070](https://github.com/m-shogo/memories-project/commit/3f9eb0704847d1d1fd63ba1dd841e965454d214d) binds publisher push/PR/dispatch, independent PR/push and replacement PR/push event topology, root-key order and root read-only permissions. Twenty-seven exact-diagnostic negatives (nine per workflow) reject extra event, six root shadows and two permission shadows per source. Existing blob, runtime, replacement and atomic rollback guards remain.
- **Retry condition:** Revalidate on reviewed workflow topology or validator changes, or a newly demonstrated semantic bypass. Do not retry unchanged canonical learning transfer, workflow-write permissions, Quay MinIO HTTP 401 or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Atomic Write Source Negative #40736639449](https://github.com/m-shogo/memories-project/actions/runs/40736639449) and [Atomic Write Negative #40736639423](https://github.com/m-shogo/memories-project/actions/runs/40736639423) both completed SUCCESS on exact source `3f9eb070`. Logs confirm 27 YAML exact-diagnostic negatives, 14 branch + 14 SHA source runtime cases, seven branch + seven SHA replacement runtime cases, 20 source negatives and ten replacement negatives.
- **Why safe:** Only an existing CI-executed read-only source validator changed; reviewed workflows, production/recovery evidence, credentials, traffic and human promotion were untouched.
- **Reusable mechanism:** Bind effective YAML event/root/permission semantics for all three related CI workflows and prove diagnostic-specific negative rejection independently of pinned blobs.
- **Protected-authority check:** Twelve protected production/recovery contracts, registries and canonical-learning Git blob SHAs matched baseline after code commit. `productionDecision=NO_GO`; OPS-P0-007 blocking; no registered/semantically eligible generations, approved objectives, executable reviewed requests, complete typed eight-domain records or final candidates. Human promotion remains separate/non-automatic; learning cannot satisfy production readiness.
- **Concurrency guard:** Both current-source CI runs were terminal SUCCESS before this nonurgent Learning append. Existing stale-source CAS must not be bypassed or rerun unchanged.
- **Next safe target:** Audit remaining atomic/reconcile source-negative workflow YAML mappings and job-level shadow permissions, while preserving source reachability and production authorities.
