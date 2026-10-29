# Supplemental OPS learning — eager decorator lambdas versus deferred lambda scope (2026-10-30)

Append-only supplemental history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective eager decorator bypass

- **Symptom:** A lambda used as a function/class decorator executes when the decorated definition is created, but a bare lambda remains deferred. The prewrite visitor skipped all lambda bodies, so a decorator lambda could mutate module `main` without a rejected static shadow. Treating all lambda bodies as eager would incorrectly reject legitimate deferred lambdas.
- **Observed evidence:** At reviewed source `a1c1c6a566672dafaf3d3930ac8b6713d0db7d34`, `module_shadows_main` traversed decorators but immediately returned false for every `ast.Lambda`; no decorator-lambda negative or deferred-lambda-`main` positive control was present. Isolated Python compilation confirmed the decorated function/class forms are syntactically valid. This was a prospective guard gap, not a production incident.
- **Verified root cause:** The visitor modeled lambda deferral without the eager invocation semantics of the decorator application position.
- **Failed approach:** Reusing the bare-lambda deferred-body rule for decorator lambdas, or indiscriminately traversing deferred lambda bodies.
- **Correction:** [`6f1d55d2`](https://github.com/m-shogo/memories-project/commit/6f1d55d236b33a76e41e6315900ce49f68b7c787) inspects decorator-lambda bodies for function, async-function and class definitions with lambda-local lexical bindings.
- **Executable recurrence guard:** Three new isolated negatives reject function, class and class-method decorator lambda reflection; two positive controls admit a deferred lambda that mentions module `main` and a decorator lambda that binds its own local `main`.
- **Retry condition:** Revisit if decorator AST handling or Python lambda scope semantics change, with paired positive/negative cases, exact-source CI and protected-authority checks. Do not retry unchanged workflow-write permission, MinIO HTTP 401, large canonical-learning append or human promotion blockers.

## Material success

- **Outcome/evidence:** [Autonomous Learning Guard #40960476702](https://github.com/m-shogo/memories-project/actions/runs/40960476702) completed **SUCCESS** on exact code source `6f1d55d236b33a76e41e6315900ce49f68b7c787`. The commit changed only `scripts/validate-autonomous-learning-system.py` (+19/-0 lines), and the CI contract/negative, append-only, helper-ancestor, entry-document and clean read-only steps succeeded. These five isolated controls do not constitute production runtime evidence.
- **Why safe:** Only a read-only AST guard changed; no workflow, Go source, credential, traffic, recovery, generation, objective, drill, typed eight-domain, independent review or promotion authority was modified.
- **Reusable mechanism:** Distinguish an expression's evaluation position from the expression's own deferred semantics, and separately preserve local lexical binding rules.
- **Protected-authority check:** The code diff left canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation registry `bfd1b04561a257d1a288bd127572bdad762bfae5`, recovery objective registry `f4d74f333a4884f9aba2284a31ac011aae8b71bd` and promotion review registry `99cb895fbefb5b459d461926851186dbed742f88` unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Inspect module-level wildcard imports and function annotations as additional eager prewrite surfaces, while keeping the known Go-only source-trigger gap and incomplete Upload Route dependency closure explicit.
