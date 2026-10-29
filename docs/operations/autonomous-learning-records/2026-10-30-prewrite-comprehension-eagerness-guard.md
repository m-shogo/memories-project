# Supplemental OPS learning — eager comprehension versus deferred generator prewrite guard (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure / prospective comprehension side effect

- **Symptom:** A module-level list/set/dict comprehension can eagerly invoke `globals()` or `vars()` to rebind `main`, while a generator expression evaluates its first iterable eagerly even though its body is deferred. The prior prewrite traversal skipped all comprehension and generator nodes.
- **Observed evidence:** The prior AST helper returned `False` for `ListComp`, `SetComp`, `DictComp` and `GeneratorExp`. Four isolated parse/compile controls demonstrated valid eager side-effect candidates: list/set/dict comprehension elements and a generator's outermost iterable. This was a prospective false-green risk, not a production incident.
- **Verified root cause:** Comprehension iteration targets are locally scoped, but that does not make all element/filter/iterable expressions deferred or side-effect-free.
- **Failed approach:** Treating all comprehensions and generator expressions as entirely local/deferred and skipping their AST children.
- **Correction / executable recurrence guard:** [`e2b4667d`](https://github.com/m-shogo/memories-project/commit/e2b4667da56a3b78c48319b01ae1ea85de73fed9) inspects eager list/set/dict element, key/value, iterable and filter expressions while ignoring local iteration targets; for generator expressions, it inspects only the eagerly evaluated outermost iterable. Four isolated negatives cover the eager reflection cases; a positive control preserves deferred generator-body reflection, and the existing comprehension-local `main` positive still passes. This is a conservative static boundary, not complete dynamic alias or import analysis.
- **Retry condition:** Any change to comprehension/generator eager/deferred evaluation handling requires paired negative and positive controls, fresh HEAD/blob CAS, exact-source CI and protected-authority verification. Do not retry unchanged MinIO 401, workflow-write permission, canonical learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40958714578](https://github.com/m-shogo/memories-project/actions/runs/40958714578) completed **SUCCESS** on exact source `e2b4667da56a3b78c48319b01ae1ea85de73fed9`. The code commit modified only `scripts/validate-autonomous-learning-system.py` (+28/-0 lines); all learning contract, executable negative, helper-ancestor, append-only and clean read-only CI steps succeeded.
- **Why safe:** The guard only parses/compiles disposable candidate source without executing it. No workflow YAML, Go source, production data, credentials, traffic, backup/recovery evidence, generation, objective, drill, typed eight-domain, independent review or promotion authority changed.
- **Reusable mechanism:** Analyze eager expression positions independently of lexical scope; avoid both missing eager side effects and rejecting deferred generator-body code.
- **Protected-authority check:** Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, mandatory contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and reviewed generation/objective/evidence/promotion registry blobs remain unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0 and no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Inspect the remaining module-level decorator/default-argument eager evaluation boundary and alias-based dynamic calls, with bounded positive/negative fixtures; keep Go-only CI trigger coverage and MinIO 401 as separate unchanged blockers.
