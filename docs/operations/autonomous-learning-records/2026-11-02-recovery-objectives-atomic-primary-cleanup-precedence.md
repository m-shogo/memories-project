# Supplemental OPS learning — recovery-objective atomic cleanup precedence (2026-11-02)

Append-only learning governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved objective, executable reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate, or human-promotion evidence.

## Material failure

- **symptom:** A secondary failure closing or unlinking a temporary authority file in the recovery-objective reconciler could override the primary atomic-write failure class, obscuring the reason for failed publication. This is a verified source-level failure path, not a reported production incident.
- **evidence:** Before [2d7c9a83](https://github.com/m-shogo/memories-project/commit/2d7c9a83ba7751d091ba54fe30c085a306bc1f43), `scripts/reconcile-memory-os-recovery-objectives.py::write_text` unconditionally raised `recovery objective reconcile authority temporary cleanup failed` from its `finally` block even while an earlier `recovery objective reconcile authority atomic write failed` exception was propagating.
- **rootCauseOrUnknown:** Verified: `finally` cleanup error priority ignored whether the atomic-write body already failed. Whether any real runner experienced both failures is unknown.
- **failedApproach:** Unconditional secondary cleanup exception propagation; treating cleanup failures as more authoritative than the original write failure.
- **correction:** [2d7c9a83](https://github.com/m-shogo/memories-project/commit/2d7c9a83ba7751d091ba54fe30c085a306bc1f43) captures `sys.exc_info()` before cleanup, attempts all cleanup actions, and raises a standalone cleanup failure only when no primary exception is active.
- **recurrenceGuard:** [d2ab5f03](https://github.com/m-shogo/memories-project/commit/d2ab5f03a08b6b462783cdba695c37a91e9629b3) adds a CI-reachable negative fixture forcing both `os.replace` and temporary `os.unlink` to fail, requiring the primary private failure class to survive, then restores monkeypatches and removes disposable residue. Byte/mode identity of the fixture authority is checked.
- **retryCondition:** Revalidate only if atomic write, cleanup, exception normalization, or exact-source negative CI changes. Do not retry unchanged MinIO 401, canonical large-blob append, workflow-write permissions, or missing human approval/evidence.

## Material success

- **outcome:** Exact-source [Recovery Objectives Reconcile Negative #41374288619](https://github.com/m-shogo/memories-project/actions/runs/41374288619) completed **SUCCESS** on `d2ab5f03a08b6b462783cdba695c37a91e9629b3`; prior code-only [#41374267060](https://github.com/m-shogo/memories-project/actions/runs/41374267060) also completed SUCCESS.
- **evidence:** GitHub Actions job `125051079834` reports `PASS: recovery objective atomic primary failure survives secondary cleanup fault`, `Recovery objective reconcile negative suite PASS`, and `production decision: NO_GO`.
- **whySafe:** The change preserves the existing atomic-write and rollback behavior, changes only exception precedence on a double-failure path, and tests only disposable fixture files. No production status or evidence was written by the code/test commits.
- **reusableMechanism:** Capture primary-exception presence before cleanup, attempt cleanup without hiding it, and require a deterministic two-fault negative control to prove error priority and fixture integrity.
- **protectedAuthorityCheck:** After the code/test commits, Production Status `d677a1c9`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objectives registry `f4d74f33`, drill registry `acebcd02`, evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review registry `99cb895f`, and learning contract `87712ea9` were unchanged. `productionDecision=NO_GO`, OPS-P0-007 remains blocked; distinct registered vs eligible unsuperseded environments, current human-approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review and separate human promotion remain mandatory.

## Next safe target

Audit the recovery-objective JSON authority reader's parent-directory TOCTOU and owned-FD boundary. Prefer a focused negative test and exact-source read-only CI; avoid unrelated production evidence or publisher changes.
