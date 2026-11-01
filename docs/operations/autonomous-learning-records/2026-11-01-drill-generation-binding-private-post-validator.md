# Supplemental OPS learning — drill-generation binding private post-validation (2026-11-01)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, executable reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, final-candidate or human-promotion evidence.

## Material failure — inherited, unbounded and raw-output semantic-binding post-validation

- **symptom:** The two drill-generation eligibility binding post-reconcile validators inherited Python/loader/Git overrides, had no timeout, and captured and re-emitted up to 9,000 characters of raw child output per stream on failure.
- **evidence:** Initial `so` at `d9dd785b` in `scripts/reconcile-memory-os-backup-restore-drill-generation-eligibility-binding.py` used `subprocess.run(..., text=True, stdout=PIPE, stderr=PIPE, check=False)` with no `env` or `timeout`. Prior [child environment learning](2026-11-01-child-validator-environment-isolation.md) reproduced a synthetic `PYTHONPATH` early-success bypass in isolation. Actual malicious runner influence and sensitive child output are **not observed**.
- **rootCauseOrUnknown:** Verified implicit parent environment inheritance, unlimited child execution and raw child-output exposure in error messages; actual external control or compromise remains unknown.
- **failedApproach:** Treating canonical script path, ordinary subprocess exit status and captured child diagnostics as sufficient without isolation, bounded execution and private failure classes.
- **correction:** [`7fbdea52`](https://github.com/m-shogo/memories-project/commit/7fbdea52063a910e5df11c1dd48bac665b7101ea) filters `PYTHON*`, `LD_*`, `DYLD_*`, `GIT_*` from the child environment, uses 120-second timeout, DEVNULL output and strict `CompletedProcess`/integer-zero acceptance. Process errors and timeout become class-only failures.
- **recurrenceGuard:** Existing CI-reachable `scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding-reconcile-negative.py` injects six synthetic override variables, requires exact child environment filtering and benign canary preservation, rejects `1`, `False`, `None`, and proves OSError, ValueError, TypeError and TimeoutExpired do not leak synthetic private details. Code and negative test were committed atomically under expected-HEAD lease.
- **retryCondition:** Revisit only on changed reviewed child topology, environment trust boundary, timeout policy or exact-source CI. Do not repeat unchanged Quay MinIO HTTP 401, workflow-write permission or human-evidence blockers.

## Material success — semantic binding transport guard verified

- **outcome:** Both semantic binding post-validators use bounded, isolated private transport while the original semantic eligibility logic and rollback authority remain intact.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41317792716](https://github.com/m-shogo/memories-project/actions/runs/41317792716) completed **SUCCESS** at `7fbdea52`. The workflow's `validate` job completed SUCCESS; the PR-only job was skipped for this push.
- **whySafe:** Git compare shows exactly two Python files changed, with no protected contract/registry, production status, credential, traffic, workflow or promotion mutation. The injected environment and subprocess results are synthetic test fixtures, not production evidence.
- **reusableMechanism:** Pair a canonical post-validator file check with an explicit filtered environment, bounded DEVNULL subprocess, strict typed exit result, poisoned-environment negative tests, benign-variable positive control and atomic code/test CAS publication.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs were unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, environment generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion registry `99cb895f`. `productionDecision=NO_GO` remains unchanged. Registered generations are not semantically eligible generations. Preflight requires unsuperseded eligible distinct-environment generations plus an explicitly human-approved current objective. Reviewed drill requests are planning authority only; executable request-bound recovery evidence, typed eight-domain coverage, independent review and human promotion remain separate mandatory gates.

## Next safe target

Audit the remaining generation-status and promotion-review subprocess boundaries for inherited overrides, unbounded execution and private diagnostics without altering reviewed workflows or any production authority.
