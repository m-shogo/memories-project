# Supplemental OPS learning — backup policy five-validator private transport (2026-11-01)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. **Not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, executable reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — five inherited unbounded backup policy child validators

- **symptom:** The backup/restore foundation reconciler ran five child validators with inherited Python/import, dynamic-loader and Git overrides, no timeout and inherited stdout/stderr. A child could return a false success before executing reviewed assertions.
- **evidence:** Source at `ab49a884` in `scripts/reconcile-memory-os-backup-restore.py` used `subprocess.run([sys.executable, str(path)], cwd=ROOT, check=False)`. Prior [child environment learning](2026-11-01-child-validator-environment-isolation.md) demonstrates a synthetic `PYTHONPATH` bypass. Actual runner compromise, leaked output or production manipulation are unknown.
- **rootCauseOrUnknown:** Verified implicit inherited environment, unbounded runtime and unfiltered output. Actual external adversarial control is unknown.
- **failedApproach:** Relying on the canonical validator inventory and a typed exit-zero check without child environment, timeout, output privacy or `CompletedProcess` type enforcement.
- **correction:** [`b6e2bc2f`](https://github.com/m-shogo/memories-project/commit/b6e2bc2fb7752c5ecb5d504c34a2ed8b15687386) restricts each child target to the reviewed five-validator inventory, filters `PYTHON*`, `LD_*`, `DYLD_*`, `GIT_*`, bounds runtime to 180 seconds, suppresses stdout/stderr, requires a real `CompletedProcess` and exact integer-zero, and converts transport faults to private domain failures.
- **recurrenceGuard:** Existing CI-reachable `scripts/validate-memory-os-backup-restore-reconcile-negative.py` now tests all five targets with six synthetic poisoned environment variables, benign canary preservation, exact child arguments, `1`/`False`/`None` rejection, four transport exceptions and unreviewed validator rejection. Code and negative test were committed atomically under expected-HEAD lease.
- **retryCondition:** Revisit only on changed reviewed validator inventory, runtime environment boundary, exact-source CI or publisher topology. Do not retry unchanged Quay MinIO HTTP 401, workflow permissions or human evidence blockers.

## Material success — source-local negative and validation checks passed

- **outcome:** All five backup policy validators now use bounded, isolated, private child execution; the existing backup foundation, rollback and OPS-P0-007 blocker logic remain unchanged.
- **evidence:** Exact-source [Reconcile Backup Restore Policy #41318250721](https://github.com/m-shogo/memories-project/actions/runs/41318250721) at `b6e2bc2f` completed its `Compile backup authority tools` and `Reconcile then validate status authority` steps **SUCCESS**. Its job log explicitly reports `PASS: backup policy five validators use isolated bounded private transport`, `Memory OS backup/restore policy reconcile negative suite PASS`, and `production decision: NO_GO`. [Backup and Restore Contracts #41318250716](https://github.com/m-shogo/memories-project/actions/runs/41318250716) completed **SUCCESS** on the same code SHA.
- **whySafe:** Git compare showed exactly the backup policy Python reconciler and its negative test changed. No protected production/evidence/promotion authority or reviewed workflow was modified. All tests used synthetic data, not real backup, restore, RPO/RTO, drill or production evidence.
- **reusableMechanism:** For each canonical validator child, enforce inventory membership, sanitized environment, bounded DEVNULL execution, strict result type and executable poisoned-environment/benign positive controls.
- **protectedAuthorityCheck:** Ten protected blob SHAs remained unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, environment generation registry `bfd1b045`, objective registry `f4d74f33`, drill request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion registry `99cb895f`. `productionDecision=NO_GO`. Registered versus semantically eligible generations remain distinct, preflight requires unsuperseded eligible distinct environments plus explicit current human-approved objective, reviewed requests remain planning-only until executable, evidence remains request-bound, typed eight-domain coverage and independent review remain mandatory, and human promotion is separate/nonautomatic.

## Material failure — publisher workflow cancelled after successful source-local validation

- **symptom:** The exact-source Reconcile Backup Restore Policy workflow was **CANCELLED** during `Commit reconciled status`, after its compilation and reconciliation/validation steps had passed.
- **evidence:** [#41318250721](https://github.com/m-shogo/memories-project/actions/runs/41318250721) logs show the negative suite PASS at 14:54:19Z, local policy/operability PASS through 14:55:42Z, then `The operation was canceled` at 14:56:40Z while a newer `so` branch state existed. No final publisher success was observed.
- **rootCauseOrUnknown:** Exact cancellation initiator **unknown**; concurrent branch advancement was observed, but the log does not prove whether concurrency policy, user action or another cause cancelled the run.
- **failedApproach:** Treating successful internal validation steps as a completed publisher run. Do not convert a cancelled run into CI SUCCESS or production evidence.
- **correction:** Preserve the source-local PASS and workflow cancellation as separate facts. Keep the publisher's bounded revalidation and expected-source checks; do not force stale publication.
- **recurrenceGuard:** Existing exact-source checkout, bounded reconcile and pre-publication source revalidation remain executable. Learning explicitly distinguishes source-local test success from final workflow completion.
- **retryCondition:** Inspect a naturally triggered new exact-source publisher run only after branch/source topology changes; do not manually retry an unchanged cancelled run or relax stale-source checks.

## Next safe target

Continue auditing remaining child-validator launch sites and establish a genuinely MinIO-independent focused Go test path only through approved CI authority. Do not weaken production evidence or human promotion gates.
