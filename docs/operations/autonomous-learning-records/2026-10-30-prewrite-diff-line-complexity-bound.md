# Supplemental OPS learning — bounded prewrite diff-line complexity (2026-10-30)

Append-only supplemental learning only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure / prospective resource-exhaustion false assurance

- **Symptom:** A syntactically valid generated Python input below the existing 512 KiB byte ceiling can still contain thousands of repeated lines and cause disproportionate CPU work in the prewrite `difflib.SequenceMatcher(autojunk=False)` comparison.
- **Observed evidence:** The prewrite validator previously limited bytes and changed-line budget but did not limit the number of source lines before AST parsing and line-diff matching. The checked-in 201,688-byte negative validator has 3,566 lines; the existing 149,386-byte CI entrypoint has 2,780 lines. No actual CI timeout was observed from this issue; it is a prospective complexity guard gap.
- **Verified root cause:** The byte ceiling bounds input size but not the worst-case number of line tokens or repeated-token comparisons in `SequenceMatcher`.
- **Failed approach:** Assuming a 512 KiB input limit and a post-comparison diff budget sufficiently bound comparison cost.
- **Correction / executable recurrence guard:** [`5705ba04`](https://github.com/m-shogo/memories-project/commit/5705ba043f7f154abb389ede3b15d3555443d885) adds a **4,096-line maximum per baseline/candidate** before parsing or comparing. Two isolated negatives verify candidate and baseline rejection, while the real 3,566-line and 2,780-line positive controls remain admissible. This is a bounded input limit, **not** a formal worst-case runtime proof for every admissible input.
- **Retry condition:** Increase the line ceiling only after reviewing actual script sizes, a deterministic adversarial runtime budget, exact-source CI and protected-authority invariants. Do not retry unchanged Quay MinIO 401, workflow-write permission, canonical learning large-file append or human-promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40956535816](https://github.com/m-shogo/memories-project/actions/runs/40956535816) completed **SUCCESS** on exact source `5705ba043f7f154abb389ede3b15d3555443d885`. The source commit modified only `scripts/validate-autonomous-learning-system.py` (+11/-0 lines); CI completed its learning contract, executable negatives, append-only, helper ancestor and read-only steps successfully.
- **Why safe:** Only a read-only prewrite validation path changed; no workflow trigger, Go service, MinIO, credential, production data, traffic, readiness, generation/objective, recovery evidence, typed eight-domain, independent review or promotion authority was changed.
- **Reusable mechanism:** Apply a conservative token-count ceiling before potentially superlinear comparison, in addition to byte and final diff budgets; test both baseline and candidate rejection independently.
- **Protected-authority check:** The mandatory learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remain unchanged; reviewed generation, objective, recovery evidence and promotion registry blob identities also match the prior baseline. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, zero registered/semantically eligible generations and no approved objective, executable reviewed request, request-bound evidence, typed eight-domain record, final candidate or human promotion.

## Next independent safe target

Add a compile-only prewrite check: Python `ast.parse` can accept module-level `return`, `break` or `nonlocal` that `compile` rejects. Prove the distinction with isolated negatives, without executing candidate code.
