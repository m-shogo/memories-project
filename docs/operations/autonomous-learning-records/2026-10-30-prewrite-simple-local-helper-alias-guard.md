# Supplemental OPS learning — simple module-local helper alias prewrite guard (2026-10-30)

Append-only supplemental operational learning governed by `contracts/operations/autonomous-learning-system.json`; canonical learning blob remains unchanged and is not fully retrievable through the existing large-blob connector. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human-promotion evidence.

## Material failure — prospective indirect eager local helper call

- **symptom:** A Python candidate could define a local function that rebinds `main`, assign it to a simple module-level alias, then eagerly call the alias or apply it as a decorator. The prior direct-helper inventory rejected `mutate()` but not `alias = mutate; alias()`, allowing the same side effect through one indirection.
- **evidence:** At parent `de931e983e482e97b0573f9037634eb674bc89a7`, the prewrite AST guard inventoried only top-level function names. Isolated Python executions demonstrated that a simple alias call and alias decorator both replaced `main` with `None` before the exact entrypoint guard. This is a prospective static validator gap, not a production incident.
- **rootCauseOrUnknown:** Verified absence of simple module-level assignment alias propagation. Dynamic aliases through containers, conditional assignments, reflective lookup and full transitive Python call graphs remain unproven.
- **failedApproach:** Treating a direct function-name inventory as complete eager-call protection when a simple alias can invoke the same local helper.
- **correction:** [`894e9035`](https://github.com/m-shogo/memories-project/commit/894e903528e962e6f003c1573f9e93b58c1e699a) propagates local helper identity through bounded, source-ordered top-level `Assign` and `AnnAssign` name aliases, then applies the existing direct-call and name-only decorator guards to those aliases.
- **recurrenceGuard:** Four executable negative candidates cover direct alias, annotated alias, source-ordered chained alias and decorator alias. Two positive controls allow an uninvoked alias and a deferred alias call inside another function.
- **retryCondition:** Legitimate eager helper alias use requires reviewed callable semantics, source-identity checks, paired positive/negative fixtures, exact-source CI and protected authority comparison. Do not treat this as complete indirect dispatch proof or retry unchanged MinIO 401, workflow-write permission, canonical large-blob transfer or human approval blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41052298085](https://github.com/m-shogo/memories-project/actions/runs/41052298085) completed **SUCCESS** for exact source `894e903528e962e6f003c1573f9e93b58c1e699a`.
- **evidence:** Logs show append-only PASS, learning contract PASS, **547 canonical fail-closed cases**, **195 fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and clean/read-only completion. Six new nested prewrite controls execute inside the positive validator and do not increase the printed 547.
- **whySafe:** Only the CI-reachable read-only Python validator changed; no workflow YAML, Go production code, credentials, traffic, environment generation, objective, drill request, request-bound evidence, typed eight-domain non-resurrection, independent review or promotion authority changed.
- **reusableMechanism:** Resolve simple source-ordered local callable aliases conservatively and prove both eager rejection and deferred/unused acceptance. Do not promote partial alias tracking to full transitive dependency proof.
- **protectedAuthorityCheck:** All ten protected blobs matched from `de931e98` to `894e9035`: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, plus six environment-generation/objective/drill-request/recovery-evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0; no current approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, independent review, final candidate or human promotion.

## Next safe target

Audit decorator replacement of the canonical `main` callable itself, then continue read-only Go/Python transitive trigger coverage and the known MinIO-independent focused Go CI gap. Workflow edits remain permission-scoped.
