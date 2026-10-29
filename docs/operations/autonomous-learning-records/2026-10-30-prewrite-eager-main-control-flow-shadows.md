# Supplemental OPS learning — eager module control-flow main-shadow guard (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under mandatory `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure / prospective nested module binding

- **Symptom:** The earlier direct-binding guard rejected `main = ...` at module scope but could still accept a candidate with a module-level `if`, `for`, `with`, `try/except` or `match` that binds `main` before the canonical `__main__` invocation.
- **Observed evidence:** The previous guard iterated `tree.body` and inspected only direct assignment/import/class statements. Isolated Python AST/compile controls confirmed all five nested binding fixtures are syntactically compilable, so the compile-only guard cannot detect this semantic shadow.
- **Verified root cause:** Direct top-level statement inspection does not traverse eager control-flow binding targets and capture-pattern names.
- **Failed approach:** Treating rejection of direct module assignment/import/class shadows as proof against eager nested module binding.
- **Correction / executable recurrence guard:** [`bd529ae3`](https://github.com/m-shogo/memories-project/commit/bd529ae392aff4b03b31dec686024eba459c69d5) replaces the direct-only check with a bounded AST traversal of eager module statements. It rejects store/delete `main` names, import aliases, `except` bindings, `match` captures and nested function/class definitions named `main`, while skipping deferred function/lambda bodies and comprehension-local targets. Five isolated negatives cover conditional assignment, for-loop target, with-as binding, except-as binding and match capture. This does **not** prove arbitrary reflective writes, import hooks or immediately invoked lambda side effects.
- **Retry condition:** Legitimate module binding changes require a reviewed execution graph, exact source/HEAD and blob CAS, prewrite checks, exact-source CI and protected-authority review. Do not retry unchanged MinIO 401, workflow-write permission, canonical learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40957661547](https://github.com/m-shogo/memories-project/actions/runs/40957661547) completed **SUCCESS** on exact source `bd529ae392aff4b03b31dec686024eba459c69d5`. Its code commit modified only `scripts/validate-autonomous-learning-system.py` (+43/-22 lines); all learning contract, executable negative, helper-ancestor, append-only and clean read-only CI steps succeeded.
- **Why safe:** The guard examines disposable source ASTs without executing candidate code. No workflow YAML, Go service, production evidence, credentials, traffic, recovery data, generation, objective, drill, typed non-resurrection, independent review or promotion authority changed.
- **Reusable mechanism:** Differentiate module-level eager control-flow bindings from deferred function/class-local/comprehension scopes; verify each distinct binding form with a compilable negative mutation.
- **Protected-authority check:** Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, mandatory contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and reviewed generation/objective/evidence/promotion registry blobs remain unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, no approved objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Prove the new scope exclusions with independent positive controls (function-local and comprehension-local `main` must not be treated as module shadows), then audit the still-unproven reflective/IIFE boundary without weakening existing guards.
