# Supplemental OPS learning — Upload Route shared critical shell step identity (2026-10-30)

Append-only supplemental history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy: `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective shared shell-body drift

- **Symptom:** Both Upload Route Publisher and PR workflows could alter Go formatting/write scope, the idempotence check, rollback validation, reconcile invocation or metrics/observability execution while retaining their named step order, action refs and selected direct-command inventory.
- **Observed evidence:** Read-only inspection found five identical named shell step bodies in both workflows. The prior critical-body guard covered MinIO, source-integrity and writer/PR-final steps but not these shared formatting/reconcile/contract steps. This was a prospective execution-graph gap, not observed production behavior.
- **Verified root cause:** Partial critical-step fingerprints do not bind adjacent shell bodies that can mutate or validate the worktree.
- **Failed approach:** Assuming step identity and selected Python/Go commands fully protect all formatting, idempotence and reconcile shell behavior.
- **Correction / executable recurrence guard:** [`c0073b8c`](https://github.com/m-shogo/memories-project/commit/c0073b8cbff7294ce665dc9ec5ad101f6dd4e509) adds five shared reviewed SHA-256 step-body fingerprints to both event maps and six new mutation negatives per workflow (12 total). The existing unique-step extraction, real-source positive controls and diagnostic checks are reused. Only the CI-reachable read-only negative validator changed (+21 lines).
- **Retry condition:** A legitimate change to formatting, rollback, reconciliation, idempotence or metrics shell bodies requires explicit review of writer/CAS and Go/Python dependency effects, updated fingerprints and negatives, exact-source CI, and protected-authority verification. Do not treat source fingerprinting as complete transitive dependency or production readiness proof.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40947850166](https://github.com/m-shogo/memories-project/actions/runs/40947850166) **SUCCESS** on exact source `c0073b8cbff7294ce665dc9ec5ad101f6dd4e509`. Logs confirm append-only and contract PASS, 201 printed canonical fail-closed cases, 74 fanout synthetic, entry-document PASS, 1,186 helper-ancestor negative mutations and read-only completion. The twelve new nested shared-step negatives are not separately included in the printed 201.
- **Why safe:** No workflow YAML, production service, credentials, traffic, readiness, generation/objective, reviewed request, recovery evidence, typed eight-domain coverage, independent review or promotion was changed.
- **Reusable mechanism:** Use a shared digest map for identical Publisher/PR shell steps, with exact named-step extraction and per-event mutation controls, avoiding duplicated manually transcribed hashes.
- **Protected-authority check:** Compare shows only the read-only negative validator changed. Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` unchanged. `productionDecision=NO_GO`; registered/semantically eligible generations remain 0/0, with no current human-approved objective, executable reviewed request, request-bound evidence, final recovery candidate or human promotion.

## Next safe target

Reject symlink aliases for the twelve reviewed direct Python/operability input files and the reviewed workflow sources, reusing existing executable path-alias negatives. Keep workflow YAML and incomplete trigger coverage unchanged.
