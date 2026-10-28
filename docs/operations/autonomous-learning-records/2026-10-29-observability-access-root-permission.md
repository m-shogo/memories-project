# Supplemental OPS learning — observability access CI YAML shadow guard (2026-10-29)

Append-only supplemental learning only; never canonical learning authority, production/backup/restore/RPO/RTO/skew evidence, drill authority, credentials, traffic, readiness or human promotion authority.

## Material failure / recurrence prevention
- **Symptom:** Observability access publisher and independent CI had exact PR/push event matrices and reviewed Git blob pins but lacked independent effective YAML root and permission shadow diagnostics. This is a static coverage gap, not an observed production bypass.
- **Observed evidence:** `observability_validate_trigger_matrix` checked ordered event paths; `blob` checked whole source. Neither independently diagnosed `on :` / `jobs :` root shadows or quoted/spaced `contents` leaves.
- **Verified root cause:** Full-source digest and event-header equality cannot alone prove the exclusive effective YAML root mapping or read-only root permission.
- **Failed approach:** Relying only on reviewed SHA and visible `contents: read` tokens for semantic YAML authority.
- **Correction / executable recurrence guard:** [63050a0b](https://github.com/m-shogo/memories-project/commit/63050a0b4285c6c0267c2bddd45aff0bbe17a041) adds exact root/permission validation and 12 synthetic exact-diagnostic negatives (8 root, 4 permission) to the existing read-only CI source-negative validator. Existing event, source, shell identity and bounded CAS/no-op checks remain.
- **Retry condition:** Revisit only on reviewed YAML topology changes or a demonstrated new shadow bypass. Do not retry unchanged MinIO HTTP 401, canonical learning transfer, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Observability Access Source Negative #40739667358](https://github.com/m-shogo/memories-project/actions/runs/40739667358) completed **SUCCESS** on exact code `63050a0b4285c6c0267c2bddd45aff0bbe17a041`; job log confirms 12 new YAML negatives, 28 trigger omissions, 16 additions, 4 shortened inventories, 3 topology, 12 source, 14 identity and 5 CAS/no-op cases passing.
- **Why safe:** Only an existing CI-reachable read-only Python validator changed (+81 lines, -0). No reviewed workflow, protected contract, registry, production evidence, credentials, traffic or promotion authority was changed.
- **Reusable mechanism:** Add effective YAML root/permission checks to exact event-matrix validation, with synthetic shadows requiring specific rejection diagnostics while retaining full blob and executable runtime proofs.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged. `productionDecision=NO_GO`; registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records, final recovery candidates and human promotion approvals remain zero. Learning cannot satisfy any production or recovery gate.
- **Next safe target:** Audit live-load writer/PR/independent CI source boundaries, including their distinct reviewed root permission policies.
