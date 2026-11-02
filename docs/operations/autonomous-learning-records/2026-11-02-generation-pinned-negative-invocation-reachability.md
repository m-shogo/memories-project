# Supplemental OPS learning — pinned negative invocation reachability (2026-11-02)

Append-only history under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, human-approved objective, executable reviewed request, request-bound evidence, typed eight-domain coverage, independent review, final candidate, or human-promotion evidence.

## Material failure / recurrence risk

- **symptom:** Three newly pinned executable-module importer negatives were CI-reachable but their `prove_pinned_*` function calls and definitions could be removed from their harnesses without the existing workflow-source AST guard noticing.
- **evidence:** At starting `so` HEAD `802b3007993e98829b9fcf26167970c6579e83bb`, `scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-workflow-negative.py::require_private_child_negative_reachable` enforced only the three earlier private child/import/path checks in the transport negative; no equivalent reachability check existed for the new transaction writer, evidence transport validator and binding transport validator pinned-source tests. This is a verified test-coverage weakness, not an observed production failure.
- **rootCauseOrUnknown:** Verified incomplete AST reachability inventory following the independent test additions; no evidence that any test was actually removed.
- **failedApproach:** Relying on an executable test file's presence and workflow invocation without guarding that its new security test is actually called from `main`.
- **correction:** [`3d9d2c2a`](https://github.com/m-shogo/memories-project/commit/3d9d2c2a15d7709c29583c849400eb61aa2ddcc1) adds an AST-based three-harness invocation/definition guard and runs it from the existing read-only workflow negative suite.
- **recurrenceGuard:** For each harness, remove the exact pinned-test call or rename its function definition and require a deterministic rejection with the expected diagnostic. The guard itself executes on every covered `so` source change. It checks call/definition reachability, not the semantic quality of the function body.
- **retryCondition:** Revisit when any pinned test is renamed, moved or replaced, when harness `main` execution changes, or when the read-only workflow's exact trigger inventory changes. Do not retry unchanged publisher-coupled writer changes, canonical large-blob transport, Quay MinIO HTTP 401, workflow permission or absent human evidence.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41394366109](https://github.com/m-shogo/memories-project/actions/runs/41394366109) completed **SUCCESS** at exact source `3d9d2c2a15d7709c29583c849400eb61aa2ddcc1`. The job log contains `PASS: generation evidence three pinned import negative invocations and definitions non-removable`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`. [Backup Restore Admission Chain #41394366372](https://github.com/m-shogo/memories-project/actions/runs/41394366372) also completed SUCCESS on the same source.
- **evidence:** Observed exact-source workflow conclusions and targeted job output. These are synthetic CI results only.
- **whySafe:** The only changed executable file was the read-only workflow negative script; its push trigger is independent of the production-capable Generation Evidence publisher. No production authority or evidence was modified.
- **reusableMechanism:** AST-enforce that security negatives are both defined and invoked from a real harness entrypoint, with deletion/rename mutations that must fail with exact diagnostics.
- **protectedAuthorityCheck:** Post-code `so` tree preserved production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion `99cb895f`, canonical learning `b809c69d` and learning contract `87712ea9` unchanged. Registered/semantically eligible generations remain 0/0; approved current objective, executable reviewed request, request-bound recovery, complete typed eight-domain coverage and final candidate remain 0. OPS-P0-007 preflight, independent review and separate nonautomatic human promotion remain mandatory.

## Next safe target

Audit the pinned importers' platform flag semantics (`O_NOFOLLOW` / `O_DIRECTORY`) and FD ownership with targeted negative fault injection; keep work on independently read-only CI-reachable paths, not publisher-coupled generation writer code.
