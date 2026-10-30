# Supplemental OPS learning — eager local helper and decorator prewrite guard (2026-10-30)

Append-only supplemental operational learning governed by `contracts/operations/autonomous-learning-system.json`; canonical learning history remains unchanged and is not fully retrievable through the existing large-blob connector. **Not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective false-green prewrite

- **symptom:** A bounded Python candidate with exactly one `def main` and the exact `if __name__ == "__main__"` guard could define a helper that rebinds `main` and invoke it at module scope, or apply the helper as a decorator. The existing deferred-function-body exception allowed the eager side effect to escape lexical main-binding checks. This is a static validator gap, not a production incident.
- **evidence:** At parent `30514a3938a5eea0c5a8419b4d7e1c44670918e4`, `module_shadows_main` skipped function bodies and did not classify direct calls or name-only decorators referring to module-local helper functions. Two isolated Python executions confirmed that `mutate()` and `@decorate` can each replace the module's `main` binding with `None` before the canonical guard.
- **rootCauseOrUnknown:** Verified missing eager invocation/decorator binding in the bounded AST check. Complete alias closure, indirect calls and arbitrary dynamic dispatch remain explicitly unproven.
- **failedApproach:** Assuming that skipping a deferred function body is safe without checking whether its callable is eagerly invoked or used as a decorator in module execution.
- **correction:** [`d4172ae5`](https://github.com/m-shogo/memories-project/commit/d4172ae512b246de139339c0bc6304d0f68189af) inventories top-level local helper definitions (excluding the canonical `main` guard call), conservatively rejects their eager direct calls and name-only decorator application.
- **recurrenceGuard:** Two executable prewrite negatives require `main binding shadowed` for an eager local helper call and an eager local decorator; a positive control preserves deferred local helper calls inside another function. Existing baseline/candidate digest, AST compilation, diff budgets and entrypoint guard checks remain.
- **retryCondition:** Revisit when a reviewed legitimate eager helper/decorator is required, with an explicit safe-call authority, negative and positive fixtures, exact-source CI and protected blob comparison. Do not claim complete indirect-call proof or retry unchanged workflow-write, MinIO 401, canonical large-file transport or human-promotion blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41051044792](https://github.com/m-shogo/memories-project/actions/runs/41051044792) completed **SUCCESS** for exact source `d4172ae512b246de139339c0bc6304d0f68189af`.
- **evidence:** Job logs show append-only PASS, learning contract PASS, **547 fail-closed cases**, **195 fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and clean/read-only completion. The three new nested prewrite fixtures execute inside the positive validator and do not increment the printed 547.
- **whySafe:** The code commit changed only the CI-reachable read-only `scripts/validate-autonomous-learning-system.py` (+24 lines). No workflow YAML, production code, traffic, credentials, environment generations, approved objectives, recovery requests/evidence, typed non-resurrection records, independent review or promotion authority changed.
- **reusableMechanism:** Combine lexical deferred-body handling with a conservative module-local eager-call/decorator inventory; test both rejection and deferred positive behavior.
- **protectedAuthorityCheck:** All ten protected blobs matched between `30514a39` and `d4172ae5`: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, plus six generation/objective/drill-request/recovery-evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0, and all separate human objective, request, recovery, eight-domain, independent review and promotion gates remain unsatisfied.

## Next safe target

Audit module-level `__name__` rebinding and simple local-helper aliases against the exact main-guard semantics, without asserting complete Python dynamic dispatch. Independently pursue Go/Python transitive CI trigger closure and a MinIO-independent focused Upload Route test path only after workflow permissions and source reachability are verified.
