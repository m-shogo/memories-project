# Supplemental OPS learning — eager module attribute/namespace main-shadow guard (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under mandatory `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure / prospective alias-based module shadow

- **Symptom:** A candidate can rebind a module's `main` through `module.main = ...`, `namespace["main"] = ...`, `setattr(module, "main", ...)` or `delattr(module, "main")` without a lexical `Name(main, Store/Del)` node or a direct `globals()` call.
- **Observed evidence:** The previous prewrite guard rejected direct reflective namespace functions and eager lambda calls, but did not recognize attribute/subscript assignments or `setattr`/`delattr` targeting the `main` name. These are prospective semantic false-green paths; no production incident was observed.
- **Verified root cause:** Binding identity cannot be inferred solely from lexical `Name` nodes or direct namespace calls when aliases/attributes are permitted.
- **Failed approach:** Treating direct `globals`/`vars`/`exec` checks as sufficient coverage of module alias-based mutation.
- **Correction / executable recurrence guard:** [`11f5b1d6`](https://github.com/m-shogo/memories-project/commit/11f5b1d63be46a107be90538e516ab086a032eb4) conservatively rejects eager attribute `main` Store/Del, subscript literal `"main"` Store/Del, and `setattr`/`delattr` calls with literal second argument `"main"`. Four negative mutations prove each form; one positive control preserves function-local attribute use. This is conservative and may reject benign module-scope dictionary keys; it does **not** prove full reflection, alias propagation or dynamic-import closure.
- **Retry condition:** Any legitimate module-level attribute or namespace mutation requires reviewed binding evidence, exact-source CI, fresh HEAD/blob CAS and protected-authority verification. Do not retry unchanged MinIO 401, workflow-write permission, canonical learning large-file append or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40958454229](https://github.com/m-shogo/memories-project/actions/runs/40958454229) completed **SUCCESS** on exact source `11f5b1d63be46a107be90538e516ab086a032eb4`. The code commit modified only `scripts/validate-autonomous-learning-system.py` (+25/-0 lines); all learning contract, executable negative, helper-ancestor, append-only and clean read-only CI steps succeeded.
- **Why safe:** The guard only analyzes disposable Python ASTs and never executes the candidate. No workflow YAML, Go service, credentials, traffic, production data, recovery evidence, generation, objective, drill, typed eight-domain, independent review or promotion authority changed.
- **Reusable mechanism:** Explicitly enumerate alias/attribute mutation patterns that bypass lexical binding checks; use isolated negatives and a deferred-scope positive to prevent both false acceptance and over-rejection.
- **Protected-authority check:** Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, mandatory contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and reviewed generation/objective/evidence/promotion registry blobs remain unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, zero registered/semantically eligible generations and no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Review module-scope comprehension side effects and dynamic alias propagation only with bounded negative/positive fixtures. The Go-only source-change CI trigger gap and external MinIO 401 remain separate unresolved blockers; do not claim full Upload Route dependency closure or production readiness.
