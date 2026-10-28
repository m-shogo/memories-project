# Supplemental OPS learning — worker container-kill recovery CI YAML shadows (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, reviewed drill authority, credentials, traffic, readiness or human promotion.

## Material failure / recurrence prevention
- **Symptom:** Worker container-kill recovery publisher/independent CI validator pinned exact event triggers and reviewed Git blob identity but did not independently classify YAML root/permission shadows. Static coverage gap, not observed production bypass.
- **Observed evidence:** `validate_trigger_reachability` checked event topology and source digests rejected changed bytes, but `on :`/`jobs :` root shadows and spaced/quoted `contents` overrides had no exact semantic diagnostic.
- **Verified root cause:** Whole-source identity and visible permission tokens cannot independently prove unique effective YAML root mapping and permission leaf authority.
- **Failed approach:** Relying solely on a generic Git blob mismatch to reject semantic YAML shadows.
- **Correction / executable recurrence guard:** [67b95b8a](https://github.com/m-shogo/memories-project/commit/67b95b8a67ca3bb1ea3efa936b7d47dcadb78404) adds explicit publisher-write/independent-read root/permission checks and fourteen exact-diagnostic negatives (eight root, four shadow leaves, two direct permission replacements), preserving event/identity/runtime/source checks.
- **Retry condition:** Reassess on reviewed YAML topology/permission changes or demonstrated new bypass; do not retry unchanged MinIO 401, canonical learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** GitHub compare `fc7b7067...67b95b8a` confirms only CI-reachable read-only validator changed (+80 lines, 0 deletions). Before writing, reviewed publisher `contents: write` and independent `contents: read` root leaves were independently verified. Exact-source CI was not yet observed at record creation; no SUCCESS is claimed.
- **Why safe:** No workflow, production status, protected registry, evidence, credential, traffic or promotion authority changed.
- **Reusable mechanism:** Match exact semantic negative fixtures to each workflow's reviewed root permission, independent of full-source SHA and runtime checks.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged after code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates remain zero. Human promotion remains separate/non-automatic.
- **Next safe target:** Audit deletion worker host-failure source-negative CI and reconcile independent permission boundary.

## Exact-source CI confirmation for prior independent target
- [Deletion Worker SIGKILL Recovery Diagnostic Source Negative #40744611004](https://github.com/m-shogo/memories-project/actions/runs/40744611004) completed SUCCESS at code `8ead7bde`; job log proves fourteen exact-diagnostic YAML negatives, 34 trigger omissions, twelve additions, three shortened inventory negatives, 23 policy mutations and seven writer redaction/atomic runtime cases. No production evidence was generated.
