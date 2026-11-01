# Supplemental OPS learning — drill-request post-validator child environment (2026-11-01)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. **Not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, request-bound recovery, typed eight-domain non-resurrection, independent-review or promotion evidence.

## Material failure — inherited environment at drill-request post-validation boundary

- **symptom:** Two post-reconcile drill-request child validators inherited unfiltered Python, dynamic-loader and Git override environment variables.
- **evidence:** Source at initial `so` HEAD `be3d855a` called `subprocess.run([sys.executable, str(path)], ...)` without `env=` in `scripts/reconcile-memory-os-backup-restore-drill-request.py`. Prior [child-validator environment learning](2026-11-01-child-validator-environment-isolation.md) documents an isolated synthetic `PYTHONPATH` interpreter bypass, not actual runner compromise. This is a verified source-level boundary omission; actual malicious control of runner environment is unknown.
- **rootCauseOrUnknown:** Verified implicit inheritance from the parent `os.environ` into the two child processes. External adversary control and actual CI compromise remain unknown.
- **failedApproach:** Relying on a canonical script path, bounded timeout, DEVNULL output and strict exit code without an explicit reviewed child environment.
- **correction:** [`2c81f037`](https://github.com/m-shogo/memories-project/commit/2c81f0378f47dffc2f487f55b6581f470df80211) supplies a filtered `env` excluding `PYTHON*`, `LD_*`, `DYLD_*` and `GIT_*` for both drill-request post-validators.
- **recurrenceGuard:** The existing CI-reachable `scripts/validate-memory-os-backup-restore-drill-request-reconcile-negative.py` injects six synthetic override variables, requires their absence, asserts exact environment equality, and checks preservation of a benign canary for both validators. Existing positive, nonzero, boolean-return, timeout and exception controls remain active.
- **retryCondition:** Reassess only if the reviewed child invocation topology, runtime/loader trust boundary, or exact-source negative/CI outcome changes. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permissions or human-evidence blockers.

## Material success — drill-request post-validation isolation

- **outcome:** Both reviewed drill-request post-validators now receive an explicit filtered environment while preserving timeout, output suppression and return-code strictness.
- **evidence:** Exact-source [Backup Restore Drill Request Reconcile Rollback #41315454011](https://github.com/m-shogo/memories-project/actions/runs/41315454011) completed **SUCCESS** at `2c81f037`; other triggered workflows were still running at observation time and are not claimed successful.
- **whySafe:** The atomic code/negative commit modified only two Python files; no production registry, OPS-P0-007 evidence, objective, generation, credential, workflow or promotion authority was written. The injected values are synthetic test inputs.
- **reusableMechanism:** Keep code and executable negative test in one expected-HEAD Git-tree commit; inject poisoned parent environment and a benign canary, assert the exact child environment, and retain strict bounded transport and private diagnostics.
- **protectedAuthorityCheck:** The two-file Git compare at `2c81f037` excludes all ten protected authorities. Canonical learning blob `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, and promotion registry `99cb895f` remain protected. `productionDecision=NO_GO`; registered/semantically eligible generations `0/0`, approved current objectives `0`, executable requests `0`. All independent recovery evidence, typed eight-domain coverage, independent review and explicit human promotion remain separate, unsatisfied gates.

## Next safe target

Audit generation-evidence post-reconcile subprocess transport for the same inherited-environment boundary plus unbounded execution and raw diagnostic disclosure. Preserve current human-only production promotion.
