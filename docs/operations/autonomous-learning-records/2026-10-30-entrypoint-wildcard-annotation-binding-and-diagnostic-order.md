# Supplemental OPS learning — CI entrypoint wildcard/annotation binding and first-failure diagnostic (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective CI entrypoint binding bypass

- **Symptom:** The bound learning CI entrypoint could introduce a module-level wildcard import or a definition-time annotation that changes `main` or `validate_learning_guards` without being rejected by its original `module_scope_rebinds` AST scan.
- **Observed evidence:** The prior scan inspected explicit import names and function defaults/decorators, but omitted `ImportFrom(name="*")` and parameter/return annotations. The reviewed CI entrypoint currently has no such unreviewed mutation; this is prospective static guard coverage, not observed production execution.
- **Verified root cause:** The binding guard did not model an unbounded import export set or the full definition-time expression inventory.
- **Failed approach:** Treating explicit import aliases and function defaults/decorators as exhaustive binding sources.
- **Correction / executable recurrence guard:** [`f9b306c8`](https://github.com/m-shogo/memories-project/commit/f9b306c8a57ade606b6d9a60602007523720d35f) conservatively inspects wildcard imports and function parameter/return annotations for both protected CI bindings, and treats decorator-lambda named-expression bindings as lambda-local. [`54c05600`](https://github.com/m-shogo/memories-project/commit/54c05600c08add6ff1ebeddf30b7bed020343945) adds six canonical negative mutations (wildcard, parameter annotation, return annotation for each protected symbol) and two positive controls for lambda-local decorator bindings.
- **Retry condition:** Revisit on changed CI entrypoint, import or annotation semantics, with exact-source negative diagnostics and protected-authority verification. Do not retry unchanged workflow-write, MinIO HTTP 401, large canonical-learning append or human promotion blockers.

## Material failure — strict negative diagnostic ordering

- **Symptom:** The first CI after adding the six negatives FAILED even though the positive validator correctly rejected the wildcard import.
- **Observed evidence:** [Autonomous Learning Guard #40961724170](https://github.com/m-shogo/memories-project/actions/runs/40961724170) on `54c05600c08add6ff1ebeddf30b7bed020343945` failed in `Validate learning contract and executable negatives`. The `dynamic learning guard wildcard-import` case expected a learning-guard shadow diagnostic but observed the canonical `main binding is shadowed by module control flow` diagnostic.
- **Verified root cause:** A wildcard import's unknown export set can shadow both protected names; the canonical validator checks `main` first. The negative classifier assumed the case label alone determined the first failing authority.
- **Failed approach:** Using the guard-labelled diagnostic for a mutation that independently violates the earlier main-binding check.
- **Correction:** [`7047c310`](https://github.com/m-shogo/memories-project/commit/7047c310ffff3ebe29054b9bc2c93503ef165c9d) binds this exact case to the observed main-first diagnostic. It does not loosen canonical rejection or permit arbitrary diagnostics.
- **Executable recurrence guard:** The existing exact-diagnostic negative case remains active and must reject with the first canonical failure; the classifier no longer mistakes a correct earlier rejection for a failed guard.
- **Retry condition:** Change this expectation only if the validator's reviewed check ordering or wildcard import semantics legitimately change. Do not rerun the unchanged failed source.

## Material success

- **Outcome/evidence:** [Autonomous Learning Guard #40961448676](https://github.com/m-shogo/memories-project/actions/runs/40961448676) completed SUCCESS for the positive validator commit. Corrected exact-source [Autonomous Learning Guard #40962051193](https://github.com/m-shogo/memories-project/actions/runs/40962051193) completed **SUCCESS** for `7047c310ffff3ebe29054b9bc2c93503ef165c9d`. Logs show **212 canonical fail-closed negatives** (up from 206), 1,186 helper-ancestor mutations, append-only, entry-document and read-only checks passing.
- **Why safe:** Only the read-only learning validator and its isolated negative suite changed. No workflow YAML, service, production evidence, credential, traffic, generation, objective, reviewed request, recovery evidence, typed eight-domain, independent review or promotion authority changed.
- **Reusable mechanism:** Validate multiple protected bindings with exact first-failure diagnostics rather than relying on a mutation label; preserve explicit positive controls for lexical local scopes.
- **Protected-authority check:** The code commits preserved canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective `f4d74f333a4884f9aba2284a31ac011aae8b71bd`, drill request `acebcd02de9d4ec44891e70ff00b6898174451dd`, generation evidence `ae7e57efce7ca21d546c1cb336d3ee7bb7ebf93a`, non-resurrection `26bb1cc70c64ab3dfa09bee011545a52d46afc00` and promotion review `99cb895fbefb5b459d461926851186dbed742f88` unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Review direct module attribute rebinding in the learning CI entrypoint AST guard, then return to the independent Go-only CI source-trigger reachability blocker. Do not infer complete Upload Route transitive dependency closure from static inventory.
