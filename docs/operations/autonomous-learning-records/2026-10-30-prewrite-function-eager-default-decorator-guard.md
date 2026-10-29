# Supplemental OPS learning — eager function decorator/default prewrite guard (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure / prospective eager definition side effect

- **Symptom:** A module-level function or async-function body is deferred, but its decorators and positional/keyword default expressions execute immediately. The previous prewrite traversal skipped all `FunctionDef`/`AsyncFunctionDef` children and could miss a decorator/default that mutates `main`.
- **Observed evidence:** Four isolated Python AST/compile controls confirmed valid candidate syntax for eager `globals()` decorator, positional default, keyword-only default, and async-function default expressions. The prior helper returned without inspecting any of these eager expression positions. No production execution incident was observed.
- **Verified root cause:** Deferred function body semantics were incorrectly applied to eager definition-time decorator/default expressions.
- **Failed approach:** Treating every child of a function definition as deferred and safe to skip.
- **Correction / executable recurrence guard:** [`c76575ed`](https://github.com/m-shogo/memories-project/commit/c76575ed387ad3adc13fcd47e6c60ed10054a167) inspects decorators, positional defaults and non-null keyword defaults for both synchronous and asynchronous definitions, while still skipping deferred bodies. Four isolated negatives prove eager reflection rejection and a benign default-argument positive remains admissible. Annotation evaluation and arbitrary indirect calls are not claimed as fully modeled.
- **Retry condition:** Changes to function-definition eager/deferred scope analysis require paired positive/negative fixtures, exact-source CI, fresh HEAD/blob CAS and protected-authority verification. Do not retry unchanged MinIO 401, workflow-write permission, canonical learning large-file append or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40959045316](https://github.com/m-shogo/memories-project/actions/runs/40959045316) completed **SUCCESS** on exact source `c76575ed387ad3adc13fcd47e6c60ed10054a167`. The code commit modified only `scripts/validate-autonomous-learning-system.py` (+20/-0 lines); learning contract, executable negative, helper-ancestor, append-only and clean read-only CI steps succeeded.
- **Why safe:** Only a read-only prewrite AST check changed. No workflow YAML, Go service, credentials, traffic, production data, recovery evidence, generation, objective, drill, typed eight-domain, independent review or promotion authority changed.
- **Reusable mechanism:** Separate deferred function bodies from eager definition-time expressions and test each distinct eager position.
- **Protected-authority check:** Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, mandatory contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and reviewed generation/objective/evidence/promotion registry blobs remain unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0 and no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Audit eager class decorators/bases/class-body reflective expressions and function annotation semantics without falsely rejecting ordinary class-local `main` bindings. Preserve the known Go-only CI trigger gap and external MinIO blocker.
