# Supplemental OPS learning — prewrite workflow source hardlink aliases (2026-10-30)

Append-only supplemental history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective workflow source hardlink alias

- **Symptom:** A workflow YAML leaf can be a regular hardlink to a source outside `.github/workflows`, while the prewrite fanout auditor previously treated it as an independent workflow source. This is a prospective alias risk, not a production incident.
- **Observed evidence:** Before `e9008813`, `matching_workflows` checked `workflow.is_symlink()`, file type and byte size but not `st_nlink`. A same-filesystem disposable hardlink fixture provides two directory entries for one inode.
- **Verified root cause:** Symlink-only workflow identity checks do not detect regular-file hardlink aliases.
- **Failed approach:** Treating a non-symlinked workflow leaf as proof of independent workflow-source identity.
- **Correction:** [`e9008813`](https://github.com/m-shogo/memories-project/commit/e9008813ae41a3ab441fe11ced1f7b62084ad8ed) rejects workflow source leaves with `st_nlink != 1` before reading their YAML.
- **Executable recurrence guard:** Both the fanout self-test and the CI-reachable learning negative validator now create disposable workflow-source hardlinks and require the exact fail-closed diagnostic `PREWRITE TRIGGER AUDIT FAILED: workflow source hardlink alias`. Existing missing prospective target, symlink and target-hardlink controls remain intact.
- **Retry condition:** An intentional workflow-source hardlink requires reviewed inode/alias semantics, a proof of repository ownership, explicit positive and negative CLI fixtures, exact-source CI and protected-authority verification. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical learning transfer or human-promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40991023830](https://github.com/m-shogo/memories-project/actions/runs/40991023830) completed **SUCCESS** on exact code SHA `e9008813ae41a3ab441fe11ced1f7b62084ad8ed`. Job logs confirm append-only PASS, contract PASS, 411 canonical fail-closed negatives, 104 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document PASS and read-only completion.
- **Why safe:** Only two read-only, CI-reachable Python validators changed; no workflow YAML, production code, traffic, credential, readiness or OPS-P0-007 evidence authority was modified.
- **Reusable mechanism:** Check regular-file link count for both prospective target and enumerated workflow source before trusting direct-path trigger audit identities; keep CLI rejection deterministic.
- **Protected-authority check:** Compared the one-commit diff with the starting tree: only `scripts/audit-memory-os-workflow-trigger-fanout.py` and `scripts/validate-autonomous-learning-system-negative.py` changed. Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and the six protected generation/objective/drill/evidence/non-resurrection/promotion registries are unchanged. `productionDecision=NO_GO`; no evidence or human promotion is inferred from this learning record.

## Limit and next safe target

Workflow hardlink identity is not a complete Gitlink/submodule or Go/Python transitive dependency proof. Next: fail-closed submodule metadata and nested Git checkout boundaries, with disposable CLI negatives; do not change workflow triggers without verified permission and full CI reachability.
