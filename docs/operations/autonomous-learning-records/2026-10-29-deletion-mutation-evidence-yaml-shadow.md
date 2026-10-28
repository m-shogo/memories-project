# Supplemental OPS learning — deletion mutation evidence CI YAML shadows (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, reviewed drill authority, credentials, traffic, readiness or human promotion.

## Material failure / recurrence prevention
- **Symptom:** Deletion mutation-evidence publisher/independent CI source-negative validator pinned event path inventory and complete Git blob identity but did not separately diagnose YAML root and permission shadow keys. Static coverage gap only, not an observed production bypass.
- **Observed evidence:** `validate_trigger_reachability` rejected event inventory drift; `reviewed_source` rejected blob mismatch. Trailing `on :`/`jobs :` mappings and quoted/spaced `contents` leaves had no dedicated semantic diagnostic.
- **Verified root cause:** Source-byte identity and visible read-only tokens do not independently prove effective YAML root mapping and permission uniqueness.
- **Failed approach:** Treating a generic Git blob mismatch as sufficient semantic proof for YAML shadows.
- **Correction / executable recurrence guard:** [2535afe9](https://github.com/m-shogo/memories-project/commit/2535afe9a0cdc8b57ef4288f0695dce1d3a4f8ce) adds explicit root/permission validation and twelve exact-diagnostic negative fixtures (eight root, four permission) across publisher and independent CI, preserving existing event inventory, identity runtime, source digest and CAS checks.
- **Retry condition:** Reassess on reviewed YAML topology change or a demonstrated new shadow bypass; do not retry unchanged MinIO 401, canonical learning transfer, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** GitHub compare `18232e24...2535afe9` confirms only the CI-reachable read-only validator changed (+76 lines, 0 deletions). Reviewed publisher root order `name/on/permissions/concurrency/jobs` and independent `name/on/permissions/jobs` both have a sole root `contents: read` leaf. Exact-source CI had not yet been observed at record creation; no CI success is claimed here.
- **Why safe:** No publisher workflow, protected registry, production evidence, credential, traffic or promotion authority changed.
- **Reusable mechanism:** Require effective YAML root/permission uniqueness with mutation-specific diagnostics independently of source SHA and executable branch/CAS proofs.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning Git blob SHAs unchanged after code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates remain zero. Human promotion remains separate/non-automatic.
- **Next safe target:** Continue deletion lease diagnostics and pre-fence source-negative YAML authority audit.

## Exact-source CI confirmation for prior independent target
- [Deletion Lease Recovery Authority Source Negative #40743524427](https://github.com/m-shogo/memories-project/actions/runs/40743524427) completed SUCCESS at code `c4696386`; job log proves twelve exact-diagnostic YAML negatives, two reviewed Git blob negatives, fourteen publisher source mutations, fourteen identity runtime cases and five publisher CAS/no-op cases. No production evidence was generated. This append-only observation closes the earlier pending CI record.
