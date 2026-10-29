# Supplemental OPS learning — CI entrypoint eager dynamic import/runpy and first-diagnostic recovery (2026-10-30)

Append-only supplemental history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory execution policy remains `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound evidence, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure — unreviewed eager module execution

- **Symptom:** The CI entrypoint binding guard could admit an eager `__import__`, `importlib.import_module`, `runpy.run_path` or `runpy.run_module` call before the canonical main dispatch even though imported code may mutate the protected `main` or `validate_learning_guards` binding without a lexical store in the current file.
- **Observed evidence:** At reviewed `626f34eb7d570685755039a54ecb06adbf6d60c5`, `module_scope_rebinds` checked direct imports, namespace mutations and reflection but omitted those four dynamic execution calls. No actual production execution or namespace-mutation incident was observed.
- **Verified root cause:** The entrypoint visitor's bounded call inventory omitted dynamic module execution, although the separate prewrite visitor already rejected these forms.
- **Failed approach:** Assuming a lexical protected-name binding scan was sufficient proof that an eager module call cannot rebind a guard.
- **Correction / executable recurrence guard:** [`de477586`](https://github.com/m-shogo/memories-project/commit/de477586d90f60989fc30272082461bd577dfe1b) conservatively rejects the four eager call forms in the CI entrypoint visitor. [`e0374c27`](https://github.com/m-shogo/memories-project/commit/e0374c274c20288c206fc9591ed2807dbd61b95e) adds eight isolated exact-diagnostic negatives (four forms, two protected binding labels). Deferred function bodies remain outside eager module execution analysis. This is lexical coverage, not complete import alias/transitive dependency closure.
- **Retry condition:** Revisit only with reviewed import/runtime semantics and paired eager/deferred controls, exact-source CI, and protected-authority verification. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permissions, canonical 4.17 MB append transport, or human promotion blockers.

## Material failure — first-diagnostic expectation mismatch

- **Symptom:** The first CI run for the eight new negatives failed even though the new visitor rejected the mutation.
- **Observed evidence:** [Autonomous Learning Guard #40964231755](https://github.com/m-shogo/memories-project/actions/runs/40964231755) FAILED at `dynamic learning guard eager-builtin-import`: expected `learning guard binding is shadowed by module control flow`, observed `main binding is shadowed by module control flow`.
- **Verified root cause:** The visitor checks the `main` binding before `validate_learning_guards`; eager dynamic module execution conservatively threatens both, so the first canonical failure is always the `main` diagnostic. The new negative classifier reused the general guard-specific expectation.
- **Failed approach:** Expecting a second binding's diagnostic when a shared-risk operation is already rejected at the first binding.
- **Correction / executable recurrence guard:** [`4df8c992`](https://github.com/m-shogo/memories-project/commit/4df8c9923b6288766aedf0a65f8a875772b2e89f) binds the eager dynamic-import cases to the exact first `main` shadow diagnostic. The existing single-line stderr and exact diagnostic validator prevents accidental acceptance of an unrelated failure.
- **Retry condition:** Only change diagnostic ordering with an explicit source-order review and paired first-failure negative updates; never loosen to substring matching.

## Material success

- **Outcome/evidence:** [Autonomous Learning Guard #40964060716](https://github.com/m-shogo/memories-project/actions/runs/40964060716) SUCCESS on the visitor change. [Autonomous Learning Guard #40964354164](https://github.com/m-shogo/memories-project/actions/runs/40964354164) SUCCESS on exact negative/fix source `4df8c9923b6288766aedf0a65f8a875772b2e89f`: **226 fail-closed canonical cases**, 74 fanout synthetic cases, 1,186 helper-ancestor negative mutations, append-only, entry-document and clean read-only checks passed.
- **Why safe:** Only read-only learning validators changed; no workflows, service code, production evidence, credentials, traffic, generation/objective, reviewed request, request-bound recovery, typed eight-domain records, independent review or promotion authority changed.
- **Reusable mechanism:** Apply the same conservative eager-module-execution boundary to both prewrite and CI entrypoint checks; bind negatives to the earliest expected canonical rejection rather than a later conceptual target.
- **Protected-authority check:** Ten protected blob SHAs remained unchanged: canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective `f4d74f333a4884f9aba2284a31ac011aae8b71bd`, drill request `acebcd02de9d4ec44891e70ff00b6898174451dd`, generation evidence `ae7e57efce7ca21d546c1cb336d3ee7bb7ebf93a`, typed non-resurrection `26bb1cc70c64ab3dfa09bee011545a52d46afc00`, promotion review `99cb895fbefb5b459d461926851186dbed742f88`. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; zero registered/eligible generations, approved current objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records, final recovery candidates or human promotion.

## Next safe target

Review direct-name imports (`from importlib import import_module`, `from runpy import run_module`) and other bounded eager dynamic execution aliases with negative and deferred-scope positive controls. Independently preserve the unresolved Go-only pre-MinIO CI reachability and complete Upload Route transitive dependency closure as blockers; do not narrow workflow triggers.
