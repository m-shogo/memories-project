# Supplemental OPS learning — prewrite eager dynamic import and runpy boundary (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective unbounded module execution

- **Symptom:** A prewrite Python candidate can execute unreviewed import/module code at module or eager class-definition time using `__import__`, `importlib.import_module`, `runpy.run_path` or `runpy.run_module`. Such code can have namespace side effects without a direct lexical `main` store or `globals()` mutation in the candidate's own AST.
- **Observed evidence:** At reviewed source `354ade219dbafaaa96ab73de661bbeea0189111f`, the prewrite visitor rejected direct `globals/vars/locals/exec/eval` and explicit reflection but did not recognize these four dynamic import/execution call forms. No production or actual candidate execution incident was observed.
- **Verified root cause:** The existing static visitor covered direct reflection but not bounded lexical entrypoints for indirect module execution.
- **Failed approach:** Treating absence of a direct `main` mutation AST as proof that an eager import/runpy call cannot affect the module binding.
- **Correction / executable recurrence guard:** [`747a9b29`](https://github.com/m-shogo/memories-project/commit/747a9b292856af86d7ea9ba924e9b6a99cd34292) conservatively rejects eager `__import__` calls and attribute calls named `import_module`, `run_module` or `run_path`. Four isolated negative controls require the `main binding shadowed` diagnostic; a deferred function-local dynamic import remains a positive control.
- **Retry condition:** Legitimate eager dynamic import/runpy use requires independent review of execution effects and explicit source/dependency binding, then paired positive/negative controls, exact-source CI and protected-authority checks. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical large-file append or human promotion blockers.

## Material success

- **Outcome/evidence:** [Autonomous Learning Guard #40962971512](https://github.com/m-shogo/memories-project/actions/runs/40962971512) completed **SUCCESS** on exact source `747a9b292856af86d7ea9ba924e9b6a99cd34292`. The code commit changed only `scripts/validate-autonomous-learning-system.py` (+22/-0 lines), and the append-only, contract/negative, entry-document, helper-ancestor and clean read-only checks passed.
- **Why safe:** The candidate code is parsed/compiled but not executed; only a read-only AST guard and isolated fixtures changed. No workflow YAML, service code, production evidence, credentials, traffic, generation/objective, reviewed request, recovery, typed eight-domain, independent review or promotion authority changed.
- **Reusable mechanism:** Treat eager dynamic module execution as an explicit static-analysis uncertainty boundary; retain deferred-scope positives and do not claim complete dynamic import alias resolution.
- **Protected-authority check:** The code commit preserved canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective `f4d74f333a4884f9aba2284a31ac011aae8b71bd`, drill request `acebcd02de9d4ec44891e70ff00b6898174451dd`, generation evidence `ae7e57efce7ca21d546c1cb336d3ee7bb7ebf93a`, non-resurrection `26bb1cc70c64ab3dfa09bee011545a52d46afc00` and promotion review `99cb895fbefb5b459d461926851186dbed742f88` unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Audit the separate CI entrypoint binding guard for dynamic import/runpy side effects, with exact first-failure diagnostics and no false assertion of full transitive import closure. Preserve the Go-only CI trigger and MinIO blockers as scoped unresolved work.
