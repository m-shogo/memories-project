# Supplemental OPS learning — local-scope prewrite positive controls (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory contract remains `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human-promotion evidence.

## Material failure / prospective over-rejection

- **Symptom:** A newly generalized module-shadow traversal could reject legitimate `main` variables that exist only inside deferred function bodies, class-local namespaces, lambda arguments or comprehension-local targets. Negative-only tests would not prove that valid scopes remain admissible.
- **Observed evidence:** The prior [`bd529ae3`](https://github.com/m-shogo/memories-project/commit/bd529ae392aff4b03b31dec686024eba459c69d5) added five eager-module shadow negatives and explicit exclusions, but no isolated positive controls for those exclusions.
- **Verified root cause:** Negative rejection fixtures alone cannot prove a guard's scope exclusions or prevent overbroad AST recursion from silently turning valid local bindings into failures.
- **Failed approach:** Treating a passing set of eager module-shadow negatives as sufficient scope correctness evidence.
- **Correction / executable recurrence guard:** [`5e5c3d29`](https://github.com/m-shogo/memories-project/commit/5e5c3d2936fe89a9162e1e36fc5fc34acf7d77fd) adds four independent in-process positive controls with exact (+2/-0 or +1/-0) prewrite diff results: function-local, class-local, lambda-parameter and comprehension-local `main`. All must pass the same real prewrite validator used by the negatives.
- **Retry condition:** Any change to AST traversal, deferred/eager scope rules, comprehension handling or prewrite diff matching requires both positive and negative controls, exact-source CI, fresh HEAD/blob CAS and protected-authority verification. Do not retry unchanged MinIO 401, workflow-write permission, canonical learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40957948692](https://github.com/m-shogo/memories-project/actions/runs/40957948692) completed **SUCCESS** on exact source `5e5c3d2936fe89a9162e1e36fc5fc34acf7d77fd`. The code commit changed only `scripts/validate-autonomous-learning-system.py` (+14/-0 lines); all learning contract, executable negative, helper-ancestor, append-only and read-only CI steps passed.
- **Why safe:** The controls parse and compare disposable source strings only. No workflow YAML, Go service, production data, credentials, traffic, recovery evidence, generation, objective, drill, typed eight-domain, independent review or promotion authority changed.
- **Reusable mechanism:** For every new fail-closed semantic rejection, pair a negative mutation with a nearby admissible positive control that proves intended scope boundaries.
- **Protected-authority check:** Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, mandatory contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and reviewed generation/objective/evidence/promotion registry blob identities remain unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, zero registered/semantically eligible generations and no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Fail closed on explicitly reflective module-level `globals`/`exec`/immediately invoked lambda writes in prewrite source, with exact negative controls. Preserve function-local legitimate uses and do not claim full reflective or dynamic import closure.
