# Supplemental OPS learning — recovery objective temporary descriptor identity (2026-11-02)

Append-only learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. It is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** Recovery-objective atomic writer previously trusted `tempfile.mkstemp`'s returned descriptor without checking its exact type, sign or binding to the staged regular file. A forged boolean descriptor could be treated as integer and passed to `os.fchmod` or cleanup `os.close`, risking unrelated descriptors.
- **evidence:** Prior `scripts/reconcile-memory-os-recovery-objectives.py::write_text` assigned `descriptor, temp_name = tempfile.mkstemp(...)` and immediately called `os.fchmod(descriptor, mode)`. The existing cleanup negative checked only ordinary `fchmod`/`fdopen` failures, not malformed acquisition. No real compromised `mkstemp` result was observed.
- **rootCauseOrUnknown:** Verified source-level unchecked ownership and FD-to-path identity assumption. Actual malicious descriptor substitution is unknown.
- **failedApproach:** Assuming every integer-like returned FD belongs to the staged file and is safe to close on failure.
- **correction:** [`c65a8143`](https://github.com/m-shogo/memories-project/commit/c65a814325634363888fa43dacb6bfbab3567979) accepts only an exact nonnegative integer FD, canonical staged filename under the expected parent, and matching regular unique-inode `fstat`/`lstat` identities before transferring descriptor ownership. [`9651c326`](https://github.com/m-shogo/memories-project/commit/9651c326966bd37d3657aafb0a35321cd604b76d) adds forged boolean, negative and unrelated-regular-descriptor negatives.
- **recurrenceGuard:** The read-only exact-source `recovery-objectives-reconcile-negative.yml` executes `prove_atomic_temp_descriptor_identity`. It verifies private fail-closed rejection, unowned unrelated FD remains open, canary bytes unchanged, original authority bytes/mode unchanged and no staged temporary residue.
- **retryCondition:** Revisit when `mkstemp`, FD ownership, temp filename verification, cleanup or exact-source CI changes. Do not retry unchanged MinIO 401, workflow permissions, canonical large-blob transport or absent human evidence blockers.

## Material success

- **outcome:** Exact-source [Recovery Objectives Reconcile Negative #41377013254](https://github.com/m-shogo/memories-project/actions/runs/41377013254) completed **SUCCESS** on `9651c326966bd37d3657aafb0a35321cd604b76d`. [Recovery Objectives Admission #41377013322](https://github.com/m-shogo/memories-project/actions/runs/41377013322) also **SUCCESS** on the same HEAD. Code-only [Reconcile Negative #41376985486](https://github.com/m-shogo/memories-project/actions/runs/41376985486) and [Admission #41376985456](https://github.com/m-shogo/memories-project/actions/runs/41376985456) were **SUCCESS** on `c65a8143`.
- **evidence:** Job `125059345626` logged `PASS: recovery objective atomic temporary FD ownership and inode identity`, `Recovery objective reconcile negative suite PASS` and `production decision: NO_GO`.
- **whySafe:** Only a bounded staging FD ownership check and disposable synthetic negative fixtures changed. No production authority, generation, recovery objective, drill, traffic, credential, readiness or promotion record was intentionally written.
- **reusableMechanism:** Establish ownership only after exact type and file identity checks; do not close unverified descriptors, and verify an unrelated live FD survives negative execution.
- **protectedAuthorityCheck:** Production status blob prefix `d677a1c9`, OPS-P0-007 snapshot `dbaa36b0`, environment generations `bfd1b045`, approved objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, human promotion review `99cb895f`, and learning contract `87712ea9` remained unchanged after code/test commits. `productionDecision=NO_GO`, separate registered vs unsuperseded semantically eligible distinct environments, current human-approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review and separate nonautomatic human promotion remain mandatory.

## Next safe target

Pin atomic stage/replacement/cleanup to an owned parent-directory FD and add an exact replacement-boundary parent swap negative. The existing precommit path check and descriptor identity guard do not close the final path race. Do not create synthetic production-equivalent recovery evidence or promote readiness.
