# Supplemental OPS learning — wildcard import prewrite main binding guard (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective unbounded import namespace

- **Symptom:** A module-level `from package import *` could introduce or replace a `main` binding without an explicit `main` alias in the AST. The previous prewrite import visitor compared only explicit import names, so a star import was admitted even though its runtime export set was unbounded.
- **Observed evidence:** The prewrite import guard at source `078fc9a44ac976cbbdfeaeb6d045b19a093d68c2` compared `alias.name` to `main`; `ast.ImportFrom(names=[alias(name="*")])` does not match. Python compilation accepts module-level `from math import *`. This is a prospective static guard gap, not evidence that a real imported module has shadowed `main`.
- **Verified root cause:** Exact alias-name matching cannot establish the binding set of a wildcard import.
- **Failed approach:** Treating `ImportFrom` with `*` as harmless merely because its AST contains no literal `main` name.
- **Correction:** [`c38ad676`](https://github.com/m-shogo/memories-project/commit/c38ad676cd3b668323af34efbf5ba9111c4f817c) rejects module-level wildcard imports conservatively while preserving class-local scope handling and explicit safe imports.
- **Executable recurrence guard:** One new isolated negative requires the exact `main binding shadowed` diagnostic for a module-level wildcard import. One positive control admits `from math import sqrt`. The conservative rejection does not claim that `math` itself exports `main`.
- **Retry condition:** Revisit only with a reviewed, deterministic import export-set proof and matching positive/negative fixtures, or if Python import semantics change. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical large-file append or human promotion blockers.

## Material success

- **Outcome/evidence:** [Autonomous Learning Guard #40960828658](https://github.com/m-shogo/memories-project/actions/runs/40960828658) completed **SUCCESS** for exact source `c38ad676cd3b668323af34efbf5ba9111c4f817c`. Its append-only, learning contract/negative, entrypoint, helper-ancestor and read-only checks succeeded. The code commit changed only `scripts/validate-autonomous-learning-system.py` (+9/-2 lines).
- **Why safe:** The guard performs read-only Python AST analysis and does not import the candidate module or modify a workflow, service, credential, traffic, recovery, generation, objective, drill, typed eight-domain, review or promotion authority.
- **Reusable mechanism:** Reject unbounded namespace imports in authority-sensitive static validation, and pair conservative negatives with explicit-import positive controls.
- **Protected-authority check:** The code commit left canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation registry `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective registry `f4d74f333a4884f9aba2284a31ac011aae8b71bd` and promotion review registry `99cb895fbefb5b459d461926851186dbed742f88` unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED` with zero registered/eligible generations and no approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Inspect function parameter and return annotation evaluation in the prewrite AST guard. Preserve the separate unresolved Go-only CI trigger reachability and incomplete Upload Route dependency closure.
