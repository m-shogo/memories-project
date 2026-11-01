# Supplemental OPS learning — binding negative-suite child transport (2026-11-02)

Append-only operational learning subordinate to the canonical learning policy. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion evidence.

## Material failure

- **symptom:** The drill-generation binding validator's nested drill-request negative suite inherited interpreter/loader/Git environment, had no timeout, accepted loosely typed exit results, and could expose raw child output in errors.
- **evidence:** At starting HEAD `aa019603`, `run_negative_suite` used `subprocess.run` without `env` or `timeout`, captured stdout/stderr, and checked `completed.returncode == 0`, which also accepts `False`. Prior [child environment learning](2026-11-01-child-validator-environment-isolation.md) reproduced a synthetic PYTHONPATH early-success bypass; actual CI compromise or secret exposure is unknown.
- **rootCauseOrUnknown:** Verified implicit environment inheritance, unbounded execution, output capture and Python bool/int equality; real-world exploit unknown.
- **failedApproach:** Treating a canonical script pathname and numeric equality of exit code as sufficient child-execution evidence.
- **correction:** [`44b322fd`](https://github.com/m-shogo/memories-project/commit/44b322fd6b9ff910a2c3824c56ee87259ae60e7a) filters `PYTHON*`, `LD_*`, `DYLD_*`, `GIT_*`, enforces 120-second timeout, suppresses child output, rejects non-`CompletedProcess`/non-exact-integer-zero results and normalizes exceptions to private-safe `Fail`.
- **recurrenceGuard:** Existing CI-reached binding reconcile negative suite injects six poisoned environment keys plus a benign preserved key, checks exact child target, cwd, timeout, output suppression and env filtering; rejects `1`, `False`, `None`, OSError, ValueError, TypeError and TimeoutExpired without leaking a synthetic private marker.
- **retryCondition:** Revisit on reviewed child topology or environment/timeout contract change or exact-source CI regression. Do not retry unchanged MinIO HTTP 401, workflow permissions, external evidence or promotion blockers.

## Material success

- **outcome:** Nested negative-suite execution is bounded, environment-isolated and private, with strict typed success.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41333389469](https://github.com/m-shogo/memories-project/actions/runs/41333389469) completed SUCCESS at code HEAD `44b322fd`. This is CI validator evidence, not a reviewed drill, production restore or readiness.
- **whySafe:** Only the existing binding validator and its CI-reached synthetic negative suite changed; no protected authority, workflow permission, credential, traffic or human promotion changed.
- **reusableMechanism:** Bind canonical child target to filtered environment, DEVNULL, timeout, strict typed exit and injected poisoned-environment tests with a benign positive control.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound evidence 0, complete typed eight-domain coverage 0, final candidates 0. Preflight requires distinct unsuperseded semantically eligible generations and explicitly human-approved current objective; reviewed requests remain planning-only, recovery evidence is bound to a current executable reviewed request, final candidates require complete typed eight-domain coverage plus independent review, and human promotion is separate/nonautomatic.

## Next safe target

Audit the binding validator's module import boundary and subprocess identity guards for bypasses; investigate existing approved pre-MinIO Focused Go Test reachability without changing workflow permissions or inventing external evidence.
