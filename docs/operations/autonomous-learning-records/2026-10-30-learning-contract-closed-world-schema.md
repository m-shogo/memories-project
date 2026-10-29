# Supplemental OPS learning — closed-world autonomous learning contract schema (2026-10-30)

Append-only supplemental history only. Canonical learning authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy is `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective unknown-key semantic shadow

- **Symptom:** The learning contract could gain a new permissive top-level, rule, or protected-invariant key, or its human-readable purpose could be rewritten, while all previously mandatory true fields and schemaVersion still passed validation.
- **Observed evidence:** Read-only audit of `scripts/validate-autonomous-learning-system.py` found exact checks for required fields, required true rules, protected invariants and bound paths, but no exact key-set check and no purpose-value check. The current contract contains exactly 11 top-level fields, 10 rules, and 3 protected invariants. This is a prospective authority ambiguity, not observed malicious contract data.
- **Verified root cause:** Presence/value checks alone do not reject extra semantic authority fields, which can create contradictory interpretation or shadow a reviewed rule.
- **Failed approach:** Assuming a fixed schemaVersion and required-field validation implied a closed-world schema.
- **Correction / executable recurrence guard:** [`bb0ac8fc`](https://github.com/m-shogo/memories-project/commit/bb0ac8fcce181f715901e232146a21f203e2990e) adds exact top-level, rules and protected-invariant key-set checks, plus exact purpose-text validation to the canonical read-only positive validator. Only `scripts/validate-autonomous-learning-system.py` changed (+16 lines); the protected contract itself did not change.
- **Retry condition:** Any legitimate learning schema extension requires explicit contract-policy review, matching validator update, dedicated negative controls, exact-source CI and protected-authority verification. Do not add permissive keys as an undocumented compatibility path.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40952522108](https://github.com/m-shogo/memories-project/actions/runs/40952522108) completed **SUCCESS** on exact source `bb0ac8fcce181f715901e232146a21f203e2990e`. Logs confirm positive learning contract PASS, append-only PASS, 201 existing canonical negatives, 1,186 helper-ancestor negative mutations and read-only completion.
- **Why safe:** The change is a read-only validator, without modifying the learning contract, canonical learning, production status, workflow YAML, traffic, credentials, recovery evidence, generation/objective, typed eight-domain coverage, independent review or human promotion.
- **Reusable mechanism:** Reject unknown semantic keys independently of required-value checks; treat human-readable purpose as part of the reviewed authority, not a free-form override.
- **Protected-authority check:** Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, and all independent objective/request/evidence/eight-domain/review/promotion gates remain unsatisfied.

## Next safe target

Add dedicated canonical negative fixtures for extra top-level/rule/protected-invariant fields, missing or changed purpose, with exact diagnostics. This will prove each new closed-world branch fails for its intended reason rather than relying on the positive baseline alone.
