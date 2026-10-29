# Supplemental OPS learning — Upload Route step order and source-output binding (2026-10-30)

Append-only supplemental learning/history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy is `contracts/operations/autonomous-learning-system.json`. This record never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, human-approved objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or promotion.

## Material failure — prospective step-order bypass

- **Symptom:** An Upload Route workflow could reorder, remove, duplicate or rename steps, or move the Publisher's `id: source` to another step while retaining the same ten direct Python/Go command strings and three action identities. The source SHA CAS could then bind a different step output.
- **Observed evidence:** Read-only inspection found 14 ordered Publisher steps and 13 ordered PR steps, with 11 shared core steps. The Publisher has one `id: source` bound to `Capture validation source`; PR has no step `id`. Previous guards checked action identities, command ordering, run-key counts and working-directory bindings but not the complete ordered step list or `id` placement. No production drift was observed.
- **Verified root cause:** Ordered direct command lists and action identities do not establish the full workflow step graph or the binding of a referenced step output.
- **Failed approach:** Inferring the entire step graph from partial action/command inventories.
- **Correction / executable recurrence guard:** [`e2b5001c`](https://github.com/m-shogo/memories-project/commit/e2b5001ca5ce0643801978f973689a2fc6fbe7ef) adds a CI-reachable read-only exact ordered step-name check, `steps` mapping cardinality and source-output `id` placement checks, with two positive and twelve negative controls. Only `scripts/validate-autonomous-learning-system-negative.py` changed (+79 lines).
- **Retry condition:** A legitimate step graph change requires explicit review of execution order, CAS/source binding, Go/Python dependencies, event coverage, updated deterministic negatives, exact-source CI and protected-authority verification. Do not retry unchanged external-evidence or permission blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40946732251](https://github.com/m-shogo/memories-project/actions/runs/40946732251) **SUCCESS** on exact source `e2b5001ca5ce0643801978f973689a2fc6fbe7ef`. Logs confirm append-only and contract PASS, 201 printed canonical negatives, 74 fanout synthetic, entry-document PASS and 1,186 helper-ancestor negative mutations. The twelve nested step-order negatives are additional to the printed 201.
- **Why safe:** Only an existing CI-reachable read-only validator changed; no workflow YAML, production source, traffic, credentials, readiness, recovery evidence, registries, drill or human promotion was altered.
- **Reusable mechanism:** Pin ordered step identities and output-ID placement independently of action refs, runtime commands, run-key counts and working-directory mappings.
- **Protected-authority check:** Compare confirms one modified read-only validator. Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remain unchanged. `productionDecision=NO_GO`; registered/eligible generations remain 0/0 and separate objective/request/evidence/eight-domain/independent-review/human-promotion gates remain unsatisfied.

## Next safe target

Pin Upload Route local PostgreSQL/S3 job environment, service ports and health configuration, and step-specific source SHA environment bindings so a changed test target cannot silently redirect toward external or production systems. Keep workflow YAML unchanged.
