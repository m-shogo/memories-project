# Supplemental OPS learning — function annotation eager-expression prewrite guard (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective annotation-time main mutation

- **Symptom:** Python function parameter/return annotation expressions can execute at definition time under non-postponed annotation semantics. The previous prewrite AST guard checked function decorators and defaults but omitted annotation expressions, allowing a candidate annotation to mutate module `main` without rejection.
- **Observed evidence:** At source `1f213587523f601b0cb5bf912605bc8f288c9203`, the `FunctionDef`/ `AsyncFunctionDef` eager list contained decorators, positional defaults and keyword-only defaults only. Isolated Python compilation accepted positional, keyword-only, return and async-function annotation expressions calling `globals().__setitem__("main", None)`. This is a prospective static gap, not observed production execution.
- **Verified root cause:** The eager-expression inventory excluded function annotations.
- **Failed approach:** Treating annotation AST nodes as unconditionally deferred, or assuming decorator/default checks cover all definition-time expressions.
- **Correction:** [`f2041401`](https://github.com/m-shogo/memories-project/commit/f2041401bae8c4a78bf3d5837c46645874c53c7f) includes positional-only, positional, keyword-only, vararg, kwarg and return annotations in the conservative prewrite eager-expression scan. Postponed annotation evaluation (for example via `from __future__ import annotations`) is intentionally over-approximated rather than used to admit a potentially ambiguous source.
- **Executable recurrence guard:** Four new isolated negatives reject parameter, return, keyword-only and async-function annotation reflection; one positive control admits ordinary `int`/`str` annotations. These run within the existing CI-reachable learning validator.
- **Retry condition:** Revisit if the reviewed Python runtime or annotation evaluation semantics change, using both eager and postponed positive/negative fixtures and exact-source CI. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permission, canonical large-file append or human promotion blockers.

## Material success

- **Outcome/evidence:** [Autonomous Learning Guard #40961112290](https://github.com/m-shogo/memories-project/actions/runs/40961112290) completed **SUCCESS** on exact source `f2041401bae8c4a78bf3d5837c46645874c53c7f`. The code commit changed only `scripts/validate-autonomous-learning-system.py` (+22/-0 lines), with append-only, learning contract/negative, entry-document, helper-ancestor and clean-source/read-only steps passing. These isolated static cases do not constitute production runtime evidence.
- **Why safe:** No workflow YAML, service code, credential, traffic, production evidence, generation/objective, reviewed request, request-bound recovery, typed eight-domain, independent review or human promotion authority was modified.
- **Reusable mechanism:** Inventory every definition-time expression position explicitly and conservatively over-approximate version-dependent semantics; preserve ordinary type-annotation positive controls.
- **Protected-authority check:** The code diff preserved canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation registry `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective registry `f4d74f333a4884f9aba2284a31ac011aae8b71bd` and promotion registry `99cb895fbefb5b459d461926851186dbed742f88` unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED` with zero registered/eligible generations, no approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Audit Python prewrite control-flow guards for exact target source reachability and Go-only CI trigger coverage separately. Do not narrow Upload Route triggers before the full Go/Python transitive dependency closure is proven.
