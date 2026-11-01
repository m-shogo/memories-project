# Supplemental OPS learning — reject unreviewed admission-chain post-validators (2026-11-01)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. **Not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, executable reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, final-candidate or human-promotion evidence.

## Material failure — admission-chain post-validator fallback accepted any repository file

- **symptom:** The admission-chain `run_validator` recognized the two canonical validator paths but fell back to `require_repo_file` for any other repository file, allowing an unreviewed script target if invoked through that helper.
- **evidence:** Source at `55909b26` in `scripts/reconcile-memory-os-backup-restore-admission-chain.py` had an `else: require_repo_file(path, f"{label} validator missing")` branch. Existing production call sites supplied canonical paths, so this is a verified helper trust-boundary gap, **not** an observed production bypass.
- **rootCauseOrUnknown:** Verified overly broad repository-containment fallback instead of a closed canonical post-validator allowlist. Whether an attacker could reach that helper with an arbitrary target in the reviewed workflow is unknown.
- **failedApproach:** Treating any repository-contained file as a reviewed post-validation executable.
- **correction:** [`a38b2e63`](https://github.com/m-shogo/memories-project/commit/a38b2e63d31a4d44fc4730b919a0027f87651225) rejects the fallback with the fixed class `unreviewed admission-chain post-reconcile validator`, retaining both canonical positive targets.
- **recurrenceGuard:** Existing CI-reachable `scripts/validate-memory-os-backup-restore-admission-chain-reconcile-negative.py` now calls the actual helper with the canonical contract path as an unreviewed executable and requires the exact fail-closed class. Previous two-target poisoned-environment, bounded private output, typed exit and transport exception negatives remain active. Code/test were published atomically under expected-HEAD CAS.
- **retryCondition:** Revisit only if a human-reviewed new post-validator target is explicitly added with its own canonical relative path and negative coverage, or exact-source CI changes. Do not retry unchanged MinIO, workflow permission or production evidence blockers.

## Material success — canonical post-validator allowlist verified

- **outcome:** Admission-chain post-validation accepts only the two reviewed validator targets and rejects an arbitrary repository-contained file before launching a child.
- **evidence:** Exact-source [Backup Restore Admission Chain Reconcile Negative #41318938099](https://github.com/m-shogo/memories-project/actions/runs/41318938099) completed **SUCCESS** on `a38b2e63`; [Backup Restore Helper Ancestor Reachability #41318938066](https://github.com/m-shogo/memories-project/actions/runs/41318938066) also completed **SUCCESS**. Other workflows were pending/running at record time.
- **whySafe:** Git compare shows only the existing admission-chain reconciler and its CI-reachable negative test changed. No protected contract, production status, generation/objective/request/evidence/typed/promotion registry, workflow, credential or traffic was modified. The test's unreviewed path is a synthetic negative and not production evidence.
- **reusableMechanism:** Prefer exact reviewed executable allowlists over generic repository containment for child validation. Add an explicit unreviewed-but-repository-contained negative in the existing CI test.
- **protectedAuthorityCheck:** Ten protected blob SHAs remained unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objective registry `f4d74f33`, drill request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion registry `99cb895f`. `productionDecision=NO_GO`. Registered and semantically eligible generations remain distinct; preflight requires unsuperseded eligible distinct environments and an explicitly current human-approved recovery objective; reviewed requests are planning-only until executable; recovery evidence stays request-bound; complete typed eight-domain coverage and independent review are mandatory; human promotion remains separate/nonautomatic.

## Next safe target

Audit remaining helper child-executable allowlists for repository-contained fallback paths, without altering production evidence, human authority or CI workflow permissions.
