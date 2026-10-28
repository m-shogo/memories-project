# Supplemental OPS learning — compatibility diagnostic CI YAML shadow guard (2026-10-29)

Append-only supplemental learning only; not canonical `AUTONOMOUS-OPS-LEARNING.md`, production evidence, backup/restore, RPO/RTO/skew, drill, credentials, traffic, readiness or promotion authority.

## Material failure / recurrence guard
- **Symptom:** The compatibility diagnostic publisher and independent source-negative CI checked exact PR/push event headers and Git blob hashes but did not independently reject effective YAML root or permission shadow mappings. This is a static semantic gap, not observed production bypass.
- **Observed evidence:** `compat_validate_trigger_matrix` compared ordered event sections, and `blob` compared reviewed source identity. Neither emitted a specific semantic diagnostic for trailing `on :` / `jobs :` or quoted/spaced `contents` mapping.
- **Verified root cause:** Event-path equality and full-source SHA checks do not independently establish effective root mapping and read-only permissions.
- **Failed approach:** Treating the visible `permissions: contents: read` token and source digest as sufficient semantic validation of the YAML permission boundary.
- **Correction / executable recurrence guard:** [a9c0d8b7](https://github.com/m-shogo/memories-project/commit/a9c0d8b7defcefeaa2de0e3cbff0b3316a9de611) extends the existing read-only `scripts/validate-memory-os-compatibility-diagnostic-source-negative.py` with exact root and permission leaf checks plus 12 in-memory mutations requiring their specific diagnostics (8 root, 4 permission). Existing event, blob, atomic redaction, symlink and runtime negative proofs are retained.
- **Retry condition:** Revisit only on reviewed YAML root/permission topology changes or demonstrated new shadow bypass. Do not retry unchanged MinIO HTTP 401, large canonical learning transfer, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Compatibility Diagnostic Source Negative #40739389172](https://github.com/m-shogo/memories-project/actions/runs/40739389172) executed on exact code `a9c0d8b7defcefeaa2de0e3cbff0b3316a9de611`. Its source-negative job completed **SUCCESS**: 12 new exact-diagnostic YAML negatives, 24 trigger omissions, 16 additions, 4 shortened inventories, 3 topology, 23 source, 12 identity, 7 atomic/redaction/symlink and secret-output suppression checks all passed.
- **Why safe:** Only one existing CI-reachable Python source-negative validator changed (+75 lines, -0). No workflow, protected contract, registry, production evidence, credentials, traffic or promotion authority was changed.
- **Reusable mechanism:** Layer semantic YAML root/permission checks and exact-diagnostic synthetic negatives onto existing reviewed event matrices and executable atomic/privacy tests, retaining independent source blob verification.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged. `productionDecision=NO_GO`; zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records, final candidates or human promotion approvals. Learning cannot satisfy production or recovery gates.
- **Next safe target:** Inspect other read-only source-negative CI validators for missing effective YAML or shell execution authority without changing protected files.
