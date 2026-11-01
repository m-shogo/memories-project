# Supplemental OPS learning — drill-request negative child isolation and stale CI refusal (2026-11-01)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. **Not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, executable reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, final-candidate or human-promotion evidence.

## Material failure — inherited environment and boolean false-success boundary

- **symptom:** Drill-request validation's negative child inherited Python/loader/Git overrides, and a boolean `False` return code could satisfy equality with integer zero.
- **evidence:** Initial source at `09d8aff2` in `scripts/validate-memory-os-backup-restore-drill-request.py` invoked `subprocess.run` without explicit `env` and used `completed.returncode == 0`. Prior [child environment learning](2026-11-01-child-validator-environment-isolation.md) documents a synthetic `PYTHONPATH` early-success bypass. Actual malicious runner environment is unknown.
- **rootCauseOrUnknown:** Verified implicit environment inheritance and Python boolean/integer equality semantics; actual compromise or production effect unknown.
- **failedApproach:** Treating canonical negative script path, bounded DEVNULL transport and a loose equality-zero check as sufficient proof of child execution.
- **correction:** [`ec9f0f29`](https://github.com/m-shogo/memories-project/commit/ec9f0f29972f0bc9b6fbf648c2e33e74fd9311a5) filters `PYTHON*`, `LD_*`, `DYLD_*`, `GIT_*`, requires a `CompletedProcess` and exact integer-zero, and maps OSError, ValueError, TypeError and TimeoutExpired to private failure classes.
- **recurrenceGuard:** Existing CI-reachable `scripts/validate-memory-os-backup-restore-drill-request-load-negative.py` now poisons six parent overrides, requires exact filtered child environment and preserved benign canary, rejects `1`, `False`, `None`, and checks four transport exceptions without private-marker disclosure. Code/test were published atomically with expected-HEAD lease.
- **retryCondition:** Revisit only if the reviewed child execution topology, runtime trust boundary or exact-source CI changes; do not retry unchanged Quay MinIO HTTP 401, workflow permissions or human evidence blockers.

## Material failure — correctly rejected stale publisher source

- **symptom:** [Backup Restore Drill Request Admission #41318349296](https://github.com/m-shogo/memories-project/actions/runs/41318349296) completed **FAILURE** on `ec9f0f29`, at the `Commit bounded drill planning authority` step with exit code 75.
- **evidence:** Exact job log reports `Drill request validation exit code: 0 (raw validator log suppressed)` after the compile and validator sequence, then `origin/so` moved from `ec9f0f29` to `31ca4abf` before the publisher's expected-source check. The job explicitly reported `Drill planning source HEAD changed during reconciliation; refusing stale derived authority.`
- **rootCauseOrUnknown:** Verified concurrent `so` advancement, not a validator assertion failure. The CI publisher correctly refused to commit derived authority from a stale source.
- **failedApproach:** Assuming a long-running publisher can still publish after unrelated branch advancement; **do not** bypass its exact-source guard or force a stale push.
- **correction:** No production/CI publisher change is warranted. Keep the existing fail-closed expected-source check; preserve this outcome and allow a future normal trigger on a genuinely changed source.
- **recurrenceGuard:** The existing publisher source-HEAD comparison and exit-75 rejection are executable stale-source guards; expected-HEAD CAS publication is used for independent code changes. The negative-suite local validation exit zero is **not** a full workflow SUCCESS.
- **retryCondition:** A new independently triggered publisher run may be assessed only on its own exact source when branch head remains stable through the source check. Do not manually repeat the unchanged stale run, remove the guard, or claim it was successful.

## Material success — source-local validation without authority promotion

- **outcome:** The negative-suite code and child environment isolation were published together; the publisher's local validation sequence reported exit code zero before correctly rejecting stale publication.
- **evidence:** [`ec9f0f29`](https://github.com/m-shogo/memories-project/commit/ec9f0f29972f0bc9b6fbf648c2e33e74fd9311a5) changed exactly two Python files. The exact-source job log above contains local validation exit zero, while the overall run is FAILED due to expected stale-source refusal.
- **whySafe:** No production authority was published by the failed publisher; code/test changes did not modify protected production, generation, objective, drill request, evidence, typed coverage or human promotion registries. Synthetic negative cases are not real drill/recovery evidence.
- **reusableMechanism:** Use poisoned-environment negatives and exact typed child exit checks, plus publisher expected-source validation to prevent stale derived authority from overwriting newer branch state.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs remained unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objective registry `f4d74f33`, drill request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion registry `99cb895f`. `productionDecision=NO_GO`. Registered versus semantically eligible generations, unsuperseded distinct environments, explicit current human-approved objective, executable reviewed request-bound recovery evidence, typed eight-domain coverage, independent review and separate human promotion remain mandatory.

## Next safe target

Inspect other child-validator transport gaps while preserving exact-source publisher stale-head guards. No production evidence or readiness may be inferred from this learning record.
