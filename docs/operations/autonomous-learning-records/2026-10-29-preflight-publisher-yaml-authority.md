# Supplemental OPS learning — preflight publisher/independent source CI YAML authority (2026-10-29)

Append-only supplemental learning only; not the canonical `AUTONOMOUS-OPS-LEARNING.md`, production evidence, recovery objectives, drill execution authority, generation eligibility, readiness, credential, traffic or human promotion authority.

## Material failure / recurrence prevention
- **Symptom:** The preflight publisher/independent source-negative validator pinned reviewed Git blob SHAs and event-path anchors but did not independently reject extra YAML event types, root shadow keys or overriding permission leaves. This is a static semantic coverage gap, not an observed production bypass.
- **Observed evidence:** `validate_guard_trigger_reachability` checked exact PR/push paths only; `MAIN_REQUIRED` and `GUARD_REQUIRED` checked visible tokens and blob identity. No separate effective YAML root/event/permission mapping proof existed.
- **Verified root cause:** A complete source digest rejects unreviewed bytes but cannot explain whether an added `issues` event, quoted/spaced root key or `contents : write` is semantically unsafe.
- **Failed approach:** Relying on visible read-only tokens and source digest as the sole rejection for YAML mapping shadows.
- **Correction / executable recurrence guard:** [942c927e](https://github.com/m-shogo/memories-project/commit/942c927e91efb08709b77aef020e05d0a47fea31) adds exact event-key order, root-key and permission-leaf checks to the existing CI-reachable read-only source-negative validator, with 18 in-memory exact-diagnostic negatives (two extra events, twelve root shadows, four permission shadows across publisher/independent).
- **Retry condition:** Reassess after a reviewed event/root/permission topology change or demonstrated new YAML bypass. Do not retry unchanged MinIO HTTP 401, large canonical learning transfer, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Preflight Source Negative #40724700230](https://github.com/m-shogo/memories-project/actions/runs/40724700230) completed SUCCESS on exact source `942c927e`. Logs show 18 exact-diagnostic YAML negatives, 6 trigger removals, 8 additions, one shortened inventory, 12 PR/push runtime cases, four writer event cases, 24 SHA runtime cases, four CAS runtime cases, five diagnostic cases, and existing publisher/independent source mutation suites passing.
- **Why safe:** Only a pre-existing read-only Python validator changed (+89/-0). Reviewed workflow, preflight contract, environment generation registry, objective registry, drill registry and production authorities remained unchanged; no production-shaped evidence was created.
- **Reusable mechanism:** Compare YAML event keys, root mapping and permission leaves against reviewed topology; exercise synthetic shadow mutations and require their specific semantic diagnostics while retaining full-source digest and source/branch runtime proofs.
- **Protected-authority check:** Nine production/OPS-P0-007/registry/learning-contract blob SHAs and canonical learning blob unchanged after code commit. `productionDecision=NO_GO`; registered/semantically eligible generations, approved objectives and executable reviewed requests remain zero; no production-ready or human-promotion authority was created.
- **Next safe target:** Audit preflight generation-eligibility consistency and admission-chain source-negative validators for missing event/root/permission semantic proofs without changing any production or workflow authority.
