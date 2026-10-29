# Supplemental OPS learning — closed-world contract negative proofs (2026-10-30)

Append-only supplemental history only; canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under mandatory `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — unproven new schema branches

- **Symptom:** The newly added exact contract key-set and purpose checks could later be deleted, weakened, or reject for an unrelated reason while the old negative suite continued to pass.
- **Observed evidence:** After [`bb0ac8fc`](https://github.com/m-shogo/memories-project/commit/bb0ac8fcce181f715901e232146a21f203e2990e), the positive validator enforced a closed-world schema but the existing 201 canonical negative cases had no isolated unknown-field or changed-purpose mutations.
- **Verified root cause:** A passing positive baseline does not prove rejection behavior for a newly added fail-closed branch.
- **Failed approach:** Treating new positive schema assertions as fully regression-protected without dedicated negative cases.
- **Correction / executable recurrence guard:** [`c056b64f`](https://github.com/m-shogo/memories-project/commit/c056b64f963f2c6fef670d4f3f5703cdcc534ae6) adds five isolated canonical mutations and exact expected diagnostics for: extra top-level `productionDecision=GO`, missing purpose, changed purpose, extra permissive rule and extra protected-invariant key. The canonical negative count increases from 201 to **206**. Only `scripts/validate-autonomous-learning-system-negative.py` changed (+20 lines).
- **Retry condition:** Any schema extension must update the mandatory contract and both positive and negative validators under explicit review, exact-source CI, append-only learning and protected-authority verification. Never treat an extra permissive field as promotion approval.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40952774850](https://github.com/m-shogo/memories-project/actions/runs/40952774850) completed **SUCCESS** on exact source `c056b64f963f2c6fef670d4f3f5703cdcc534ae6`. Logs show positive contract PASS, append-only PASS, **206** canonical fail-closed cases, 1,186 helper-ancestor negative mutations and read-only completion.
- **Why safe:** The new cases mutate only disposable learning-contract fixtures, not the protected real contract, and enforce exact diagnostics rather than arbitrary failures. No production source, workflow, evidence, credentials, traffic, readiness, generation/objective, eight-domain, review or promotion changed.
- **Reusable mechanism:** Every new fail-closed schema rule gets a separate negative mutation bound to its canonical diagnostic, including explicit misleading `GO` field injection.
- **Protected-authority check:** Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no approved recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Audit remaining autonomous-learning contract fields for semantic shadows not captured by the new closed-world schema, and investigate a permission-safe source-change-triggered path for the Upload Route Go test guards. Do not retry unchanged MinIO 401 or workflow-write permission blockers.
