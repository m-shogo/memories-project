# Supplemental OPS learning — Python prewrite entry-name binding guard (2026-10-30)

Append-only supplemental operational learning governed by `contracts/operations/autonomous-learning-system.json`. The canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains unchanged and cannot be fully retrieved through the existing large-blob transport. This record is **never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective module-import execution of main

- **symptom:** A candidate Python module with the exact `if __name__ == "__main__": raise SystemExit(main())` guard can assign `__name__ = "__main__"` at module scope and thereby execute `main` even when imported under a different name. The existing prewrite guard protected the `main` binding, not the `__name__` value that controls the entrypoint predicate.
- **evidence:** At parent `277e4df2fcd5037c155c41c4acb414c91c930a55`, the AST checker rejected module-level Store/Del, imports and class/function rebinding for `main` only. An isolated Python execution of a candidate with module-level `__name__` assignment under `{"__name__": "imported_module"}` raised `SystemExit(0)` from the canonical main guard. This is a prospective source validation failure, not an observed production incident.
- **rootCauseOrUnknown:** Verified missing direct `__name__` binding protection. Indirect reflective rebinding and arbitrary dynamic import behavior remain unproven.
- **failedApproach:** Treating the exact guard AST as sufficient without protecting its `__name__` predicate binding.
- **correction:** [`9cde447e`](https://github.com/m-shogo/memories-project/commit/9cde447eff5deed1dc17fde52555fb3e381188dc) extends the bounded prewrite AST check to reject module-scope `__name__` Store/Del, import aliases, class/function definitions and direct global/subscript binding. The existing fail-closed main-binding diagnostic is intentionally reused to preserve prior negative expectations.
- **recurrenceGuard:** Five executable negative candidates cover assignment, deletion, import alias, class and function rebinding of `__name__`; two positive controls preserve deferred function-local and class-local `__name__` variables. No candidate is executed by the prewrite validator.
- **retryCondition:** Legitimate entrypoint semantics changes require a separately reviewed guard contract, fresh baseline digest, positive/negative cases, exact-source CI and protected-authority comparison. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical full-blob transport or human promotion blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41051726504](https://github.com/m-shogo/memories-project/actions/runs/41051726504) completed **SUCCESS** on exact source `9cde447eff5deed1dc17fde52555fb3e381188dc`.
- **evidence:** CI logs confirm append-only PASS, learning contract PASS, **547 canonical fail-closed cases**, **195 fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and clean/read-only completion. The seven new nested prewrite fixtures run inside the positive validator and do not increase the printed 547 count.
- **whySafe:** The code commit changed only the CI-reachable read-only Python validator; tests use isolated strings and Python AST compilation, not production execution. No workflow YAML, production code, credentials, traffic, generation, objective, drill request, recovery evidence, typed eight-domain record, independent review or promotion authority changed.
- **reusableMechanism:** Validate the predicate binding controlling the entrypoint guard, not just the existence of the guard and the callable it invokes. Retain distinct positive tests for deferred/local namespaces.
- **protectedAuthorityCheck:** All ten protected blobs matched from `277e4df2` to `9cde447e`: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill-request/recovery-evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0; no human-approved current objective, executable reviewed request, request-bound recovery, complete typed eight-domain coverage, independent review, final candidate or promotion.

## Next safe target

Audit simple module-local helper aliases and remaining indirect-call limitations with bounded AST negative fixtures. Separately continue the Go/Python transitive input and Push/PR trigger-closure audit; MinIO-independent focused Go CI remains unproven and workflow edits remain permission-scoped.
