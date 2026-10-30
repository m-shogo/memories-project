# Supplemental OPS learning — reflective exit guard and first-diagnostic recovery (2026-10-30)

Append-only supplemental learning only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure A — prospective reflective early-termination bypass

- **Symptom:** An entrypoint with the canonical live guard AST could invoke `getattr(os, "abort")()`, `getattr(sys, "exit")(0)` or `builtins.getattr(builtins, "quit")(0)` before reaching the guard. A dynamic attribute name could also conceal a termination callable.
- **Observed evidence:** At source `80adc3e1f9c4785d83e74c7e295a5c744f36dbf4`, `can_terminate_before_guard` handled direct qualified and module-dictionary termination calls, but did not inspect a nested `getattr` invocation returning the callee. This was a prospective static gap; no production or CI bypass was observed.
- **Verified root cause:** The early-termination detector omitted the `ast.Call(func=ast.Call(...getattr...))` callee form.
- **Failed approach:** Treating direct attribute/dictionary checks as complete early-termination reachability proof.
- **Correction / executable recurrence guard:** [`7f98eaad`](https://github.com/m-shogo/memories-project/commit/7f98eaad87371ae34ac1938aedce939949640fae) adds a bounded reflective-call detector for reviewed module names and terminating/dynamic attribute keys, plus module-level and pre-learning-guard negatives and deferred/benign positives.
- **Retry condition:** Revisit only with reviewed execution-order and alias evidence and changed preconditions; the guard is lexical, not complete Python alias closure.

## Material failure B — wrong first-diagnostic expectation

- **Symptom:** [Autonomous Learning Guard #40979270476](https://github.com/m-shogo/memories-project/actions/runs/40979270476) FAILED on `7f98eaad` for the `module early dynamic-reflective-os` fixture.
- **Observed evidence:** Expected `learning CI entrypoint module terminates before live main guard`, but the actual first diagnostic was `learning CI entrypoint main binding is shadowed by module control flow`. The existing eager `module_scope_rebinds` guard already rejects `getattr(os, method)()` at module scope because the attribute name is dynamic.
- **Verified root cause:** The new negative tested a later termination detector with a payload already rejected by an earlier, stronger dynamic-lookup guard. The diagnostic mismatch was in fixture placement, not missing termination rejection.
- **Failed approach:** Reusing the same dynamic reflective payload at module scope and inside `main()` while expecting both to exercise the new termination detector.
- **Correction:** [`b4b3e20b`](https://github.com/m-shogo/memories-project/commit/b4b3e20b49ee8fedd7afd2533982ef66e5ce1ef4) removes only the redundant module-scope dynamic fixture, retains the pre-learning-guard dynamic fixture and preserves exact first-failure diagnostics. No guard logic or protected authority was weakened.
- **Executable recurrence guard:** Exact diagnostic classification remains mandatory; the 7 surviving new fail-closed fixtures exercise distinct reachable checks, while three new positive controls preserve deferred and benign reflective lookups.
- **Retry condition:** Add a module-level dynamic reflective termination case only if the earlier module-binding guard changes under explicit review and the new first-failure order is proven; do not rerun the unchanged failed fixture.

## Material success

- **Observed outcome/evidence:** Corrected exact-source [Autonomous Learning Guard #40979398569](https://github.com/m-shogo/memories-project/actions/runs/40979398569) completed **SUCCESS** on `b4b3e20b49ee8fedd7afd2533982ef66e5ce1ef4`. Logs show append-only PASS, learning contract PASS, **345 canonical fail-closed negatives** (up from 338), 74 fanout synthetic cases, entry-docs guard PASS, 1,186 helper-ancestor negatives and clean read-only execution PASS.
- **Why safe:** Only the two read-only learning validators changed. The dangerous reflective payloads are rejected in disposable CI fixtures without being executed. No workflow YAML, Go service, credential, traffic, recovery evidence, readiness or promotion authority was changed.
- **Reusable mechanism:** Guard both direct and nested reflective termination calls, preserve first-diagnostic ordering and remove a redundant fixture rather than loosening a valid earlier guard.
- **Protected-authority check:** Ten protected blobs remain unchanged across the code changes: canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, current production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective `f4d74f333a4884f9aba2284a31ac011aae8b71bd`, drill request `acebcd02de9d4ec44891e70ff00b6898174451dd`, generation evidence `ae7e57efce7ca21d546c1cb336d3ee7bb7ebf93a`, typed non-resurrection `26bb1cc70c64ab3dfa09bee011545a52d46afc00`, promotion review `99cb895fbefb5b459d461926851186dbed742f88`. Production remains `NO_GO`, OPS-P0-007 remains `PREREQUISITES_BLOCKED`, and generation/objective/request/evidence/non-resurrection/promotion registries remain empty.
- **Limits:** Canonical learning's full approximately 4.17 MB body is not transportable through the current connector; its blob identity remains fixed. This is not a full production admission chain or a complete alias-closure proof.

## Next safe target

Prioritize the MinIO-independent Go-only Focused Upload Route Test CI path and exact Go/Python transitive dependency/trigger closure once workflow-write permission or other prerequisites change. Do not retry unchanged MinIO HTTP 401, canonical learning large-append transport or human approval blockers.
