# Supplemental OPS learning — upload completion CI YAML shadow guard (2026-10-29)

Append-only supplemental learning only; not canonical `AUTONOMOUS-OPS-LEARNING.md`, production/backup/restore/RPO/RTO/skew evidence, drill authority, credentials, traffic, readiness or promotion authority.

## Material failure / recurrence prevention
- **Symptom:** The upload-completion-load publisher and independent source-negative validator enforced exact event-trigger inventories and reviewed Git blob identity, but did not independently diagnose effective YAML root/permission shadows. Static semantic gap only; no observed production bypass.
- **Observed evidence:** `upload_completion_validate_trigger_matrix` checked ordered PR/push/dispatch event headers, while `require_reviewed_source` checked full Git blob SHA. Neither had an exact diagnostic for `on :`, `jobs :`, `permissions :`, or quoted/spaced `contents` shadow mappings.
- **Verified root cause:** A reviewed source digest and event header do not independently prove effective root key exclusivity or read-only permission leaves.
- **Failed approach:** Depending only on source digest and visible `contents: read` token for YAML authority explanation.
- **Correction / executable recurrence guard:** [89812019](https://github.com/m-shogo/memories-project/commit/898120194012565f700a74f1542dfd1c2c068518) adds root/permission semantic checks and 12 synthetic mutations with exact expected diagnostics (8 root, 4 permission), retaining existing event, blob and runtime tests.
- **Retry condition:** Revisit on reviewed YAML topology changes or demonstrated new shadow bypass only. Do not retry unchanged MinIO HTTP 401, large canonical learning transfer, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Upload Completion Load Source Negative #40739540231](https://github.com/m-shogo/memories-project/actions/runs/40739540231) completed **SUCCESS** on exact code `898120194012565f700a74f1542dfd1c2c068518`; job log confirms 12 new exact-diagnostic YAML negatives, 26 omissions, 16 additions, 4 shortened inventories, 3 event topology, 2 blob, 13 source, and 14 runtime identity cases passing.
- **Why safe:** Only the existing read-only CI-reachable Python validator changed (+81 lines, -0). No reviewed workflow, contract, registry, evidence, credentials, traffic or promotion authority changed.
- **Reusable mechanism:** Layer effective root and permission YAML checks onto reviewed event matrices; use synthetic shadow mutations bound to their specific rejection diagnostic, while retaining whole-source SHA and runtime proofs.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged. `productionDecision=NO_GO`; zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records, final candidates or human promotion approvals. Learning is not production gate evidence.
- **Next safe target:** Audit observability and live-load source-negative CI validators for similar effective YAML shadow gaps without changing protected authorities.
