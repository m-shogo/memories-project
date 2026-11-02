# Supplemental OPS learning — recovery objective parent swap before atomic commit (2026-11-02)

Append-only learning governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate, or human promotion evidence.

## Material failure / residual gap

- **symptom:** The recovery-objective writer's temporary staging, replacement and cleanup still use pathname-based `tempfile.mkstemp`, `os.replace` and `os.unlink`. A parent directory swap during staging could make the pathname-based cleanup miss the original staged temporary file. The current precommit guard rejects the changed parent before replacement but does not close the final race after that check.
- **evidence:** `scripts/reconcile-memory-os-recovery-objectives.py::write_text` currently stages and replaces by path. [`33075815`](https://github.com/m-shogo/memories-project/commit/3307581558e011a306fcd145bb381a0a80ee572d) adds a disposable negative that renames the parent and substitutes a symlink immediately after `os.fsync`, then checks that `os.replace` is never reached. No real malicious parent swap was observed.
- **rootCauseOrUnknown:** Verified source-level mutable-path cleanup and final check-to-replace gap. Real exploitability, attacker presence, and actual production impact are unknown; the negative exercises only the precommit rejection boundary.
- **failedApproach:** Relying on a precommit path identity check as if it also pinned later replacement and cleanup. This approach is explicitly incomplete, not retried as full TOCTOU closure.
- **correction:** Added `prove_atomic_parent_swap_before_commit` with an isolated authority fixture, a moved original parent, a canary symlink parent, a forbidden replacement spy, and deterministic restoration of the fixture and staged temporary residue. No production writer semantics changed in this test-only commit.
- **recurrenceGuard:** Exact-source read-only `recovery-objectives-reconcile-negative.yml` requires parent-swap refusal before replacement, unchanged reviewed/canary bytes, restored paths and no final fixture residue. A later directory-FD-bound stage/replace/cleanup guard remains necessary.
- **retryCondition:** Implement the remaining final-race and cleanup closure only after reviewing existing FD-pinned writers and tests, using a new negative that swaps the parent exactly at the commit boundary; do not claim this test closes that race. Do not retry unchanged MinIO 401, workflow-write, canonical large-blob or absent human-evidence blockers.

## Material success

- **outcome:** Exact-source [Recovery Objectives Reconcile Negative #41376858449](https://github.com/m-shogo/memories-project/actions/runs/41376858449) **SUCCESS** on `3307581558e011a306fcd145bb381a0a80ee572d`. [Recovery Objectives Admission #41376858387](https://github.com/m-shogo/memories-project/actions/runs/41376858387) also **SUCCESS** on the same SHA.
- **evidence:** CI job `125058880087` logged `PASS: recovery objective atomic parent swap before commit refuses replace`, `Recovery objective reconcile negative suite PASS`, and `production decision: NO_GO`.
- **whySafe:** Only the synthetic negative suite changed; it uses a temporary copied authority tree and restores its moved directory, symlink, and staged temporary file. It does not generate real objectives or recovery evidence, touch production traffic, or promote readiness.
- **reusableMechanism:** Intercept `os.fsync` at the exact staging boundary to mutate a disposable parent path, forbid replacement with a spy, then assert unchanged trusted and canary bytes and restored fixture state.
- **protectedAuthorityCheck:** After the test commit, GitHub blob prefixes remained production status `d677a1c9`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objectives registry `f4d74f33`, drill registry `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`, and learning contract `87712ea9`. Production remains `NO_GO`; distinct unsuperseded semantically eligible environments, current explicitly human-approved objective, executable reviewed drill request, request-bound recovery evidence, complete typed eight-domain coverage, independent review, and separate nonautomatic human promotion remain mandatory.

## Next safe target

Design and validate parent-directory-FD-bound staging/replacement/cleanup that preserves the primary atomic error and rollback behavior, then add an exact commit-boundary parent swap negative. Do not treat the present precommit guard as complete.
