# Supplemental OPS learning — rate-limit operations CI YAML shadow guard (2026-10-29)

Append-only supplemental learning only; never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence. The canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`.

## Material failure / recurrence guard
- **Symptom:** The rate-limit operations publisher and independent source-negative CI had exact PR/push event-path inventories and Git blob pins but no independent effective YAML root/permission shadow diagnostic. This is a static semantic gap, not an observed production bypass.
- **Observed evidence:** `rate_ops_validate_trigger_matrix` compared ordered event sections, and `reviewed_source` compared whole Git blobs. Neither identified a trailing `on :` / `jobs :` mapping or quoted/spaced `contents` leaf as a distinct semantic failure.
- **Verified root cause:** Source digest and event-filter membership do not independently prove the exclusivity of root YAML keys or read-only permission leaves.
- **Failed approach:** Relying solely on the reviewed full-source digest and visible `permissions: contents: read` token to explain YAML authority.
- **Correction / executable recurrence guard:** [ba3793b7](https://github.com/m-shogo/memories-project/commit/ba3793b7a331daa648e7a7d6d3dab725ed2c5135) extends the existing read-only `scripts/validate-memory-os-rate-limit-operations-source-negative.py` with exact publisher/independent root mapping and permission leaf checks, plus 12 synthetic shadow fixtures requiring the specific diagnostic (8 root, 4 permission). Existing trigger, blob, runtime identity and bounded CAS tests remain intact.
- **Retry condition:** Reassess only when reviewed YAML topology changes or a new effective shadow bypass is demonstrated. Do not retry unchanged MinIO HTTP 401, large canonical learning transfer, workflow-write permission, or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Rate-Limit Operations Source Negative #40739227020](https://github.com/m-shogo/memories-project/actions/runs/40739227020) executed on exact code `ba3793b7a331daa648e7a7d6d3dab725ed2c5135`. Its source-negative job completed **SUCCESS** with 12 exact-diagnostic YAML negatives, 34 omission, 16 addition, 4 shortened inventory, 3 topology, 2 Git blob, 14 source, 14 branch/ref/SHA runtime and 5 CAS/no-op runtime cases passing.
- **Why safe:** Only the existing CI-reachable Python source-negative validator changed (+79 lines, -0). No reviewed workflow, production authority, credentials, traffic, evidence, generation, objective, drill, or promotion data changed.
- **Reusable mechanism:** Combine an exact event matrix with effective YAML root/permission checks and diagnostic-bound synthetic negative fixtures, retaining whole-source Git blob and executable runtime tests.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs remained unchanged. `productionDecision=NO_GO`, with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records and final recovery candidates. Human promotion remains separate and non-automatic.
- **Next safe target:** Audit other CI source-negative validators for unguarded YAML root/permission or executable shell bypasses, without changing protected authorities.
