# Supplemental OPS learning — qualified dynamic code/import execution and first-diagnostic reconciliation (2026-10-30)

Append-only supplemental learning only; canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md`, mandatory policy is `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure A — prospective qualified execution bypass

- **Symptom:** Eager `builtins.__import__("math")`, `builtins.exec("pass")`, `builtins.eval("1")` and reflective `getattr(builtins, "exec")` / `getattr(builtins, "eval")` could execute code without triggering the earlier module-scope lexical check. An eager literal `exec("pass")` was also accepted by the CI entrypoint guard, although arbitrary literals may import or modify global state.
- **Observed evidence:** Before [`75fdb3b8`](https://github.com/m-shogo/memories-project/commit/75fdb3b8164ac680e9fc308e5fd1fa511fbbcc1d), the attribute execution set omitted `__import__`, `exec` and `eval`, the reflective set omitted `exec`/`eval`, and the direct `exec`/`eval` check exempted constant strings not containing the protected binding name. The actual bound CI entrypoint had no such new eager call; this was a prospective static guard gap.
- **Verified root cause:** Qualified builtins calls and apparently harmless constant dynamic-code strings were excluded from the reviewed eager-execution surface.
- **Failed approach:** Treating a constant code string or unqualified import/exec checks as sufficient proof of no module namespace side effects.
- **Correction / executable recurrence guard:** The positive validator now rejects eager qualified import, exec, eval, direct exec/eval and reflective exec/eval. Seven mutation payloads are bound to the reviewed CI inventory, exercised for both protected bindings, plus seven real prewrite CLI negatives and in-process negatives. Two deferred-function positives preserve local scope.
- **Retry condition:** Permit reviewed dynamic code only after explicit semantic proof and updated exact-negative/CLI controls; never treat an unreviewed constant code string as inherently safe.

## Material failure B — overly broad inventory selector

- **Symptom:** [Autonomous Learning Guard #40975691700](https://github.com/m-shogo/memories-project/actions/runs/40975691700) FAILED on `75fdb3b8` with `reviewed reflective CI negative inventory drift`.
- **Observed evidence:** The new `kind.endswith("-import")` selector also included the pre-existing `eager-builtin-import` case, which was not a member of `REVIEWED_REFLECTIVE_EXECUTION`. An explicit prewrite source comparison found **27 selected** versus **26 reviewed**, with exactly one extra: `eager-builtin-import`.
- **Verified root cause:** A suffix-based selector conflated the new `eager-qualified-import` with an unrelated existing negative.
- **Failed approach:** Extending an identity-bound fixture inventory using a broad suffix instead of an exact reviewed kind.
- **Correction / executable recurrence guard:** [`08a120aa`](https://github.com/m-shogo/memories-project/commit/08a120aabc81183a09c935150f38dd39f9c2e50f) restricts the new import selection to `kind == "eager-qualified-import"`. A deterministic prewrite set comparison confirmed 26 selected/26 reviewed with no extra or missing cases.
- **Retry condition:** Expand the selector only after checking exact selected/expected tuple sets and negative inventory controls; do not rerun the unchanged failed source.

## Material failure C — canonical first-failure diagnostic changed

- **Symptom:** [Autonomous Learning Guard #40975789667](https://github.com/m-shogo/memories-project/actions/runs/40975789667) FAILED on `08a120aa` for `dynamic learning guard exec`.
- **Observed evidence:** The exact diagnostic expected a learning-guard binding shadow, but the positive validator now correctly rejected the same eager `exec` as a **main** binding shadow first.
- **Verified root cause:** Making eager direct `exec` unconditionally fail closed changed the first checked protected binding, while the older negative classifier retained the previous later diagnostic.
- **Failed approach:** Reusing the earlier guard-labelled diagnostic after changing main-binding rejection semantics.
- **Correction / executable recurrence guard:** [`42ef0abc`](https://github.com/m-shogo/memories-project/commit/42ef0abc85c507beb3db51e41bb405f864b18432) changes only the exact `dynamic learning guard exec` classifier to the observed main-first rejection, preserving strict diagnostic equality for all other cases.
- **Retry condition:** Change first-failure expectations only when canonical check order or explicitly reviewed semantics changes, with an exact-source CI confirmation.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40975918451](https://github.com/m-shogo/memories-project/actions/runs/40975918451) completed **SUCCESS** on exact source `42ef0abc85c507beb3db51e41bb405f864b18432`. Logs show append-only PASS, learning contract PASS, **310 fail-closed cases** (up from 289), prewrite fanout 74 synthetic cases, entry-document PASS, 1,186 helper-ancestor negative mutations and read-only execution PASS.
- **Why safe:** Only the two read-only learning validators changed; no workflow YAML, production service, credential, traffic, evidence, recovery or promotion authority was modified.
- **Reusable mechanism:** Reject dynamic code execution at module scope even for constant strings; treat qualified builtin execution as code execution; bind new cases to exact reviewed payloads and actual CLI rejection, and align first-failure diagnostics without weakening rejection.
- **Protected-authority check:** Ten protected Git blobs are unchanged: canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective `f4d74f333a4884f9aba2284a31ac011aae8b71bd`, drill request `acebcd02de9d4ec44891e70ff00b6898174451dd`, generation evidence `ae7e57efce7ca21d546c1cb336d3ee7bb7ebf93a`, typed non-resurrection `26bb1cc70c64ab3dfa09bee011545a52d46afc00`, and promotion review `99cb895fbefb5b459d461926851186dbed742f88`. Actual registries remain empty; OPS-P0-007 `PREREQUISITES_BLOCKED`, `productionDecision=NO_GO`.
- **Limitations:** These are bounded lexical controls, not complete dynamic Python alias resolution or a production admission chain. The canonical learning full 4.17 MB transport remains blocked.

## Next safe target

Prioritize Go-only CI source-trigger reachability and a complete Go/Python transitive Upload Route input closure. Avoid the unchanged MinIO HTTP 401, workflow-write permissions, canonical-learning transport and human approval blockers; do not narrow triggers without complete dependency proof.
