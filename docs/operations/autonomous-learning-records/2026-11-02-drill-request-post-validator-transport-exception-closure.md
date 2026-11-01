# Supplemental OPS learning — drill request post-validator malformed transport exceptions (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery-objective, request-bound recovery, typed eight-domain non-resurrection, independent-review or promotion evidence.

## Material failure — malformed subprocess transport errors could bypass private diagnostic class

- **symptom:** The drill-request reconciler post-validator caught `OSError` and `TimeoutExpired` but allowed `TypeError` and `ValueError` from `subprocess.run` to escape as raw exceptions.
- **evidence:** Reviewed `scripts/reconcile-memory-os-backup-restore-drill-request.py` at pre-change `8123014d7c390e13c83bb3e3f430aed356ca91e6`; the original `except (OSError, subprocess.TimeoutExpired)` omitted these two error classes. This is a verified source-level error-class gap, not evidence of actual CI compromise.
- **rootCauseOrUnknown:** Verified incomplete exception normalization at the subprocess boundary. Whether malformed transport inputs ever occurred on a real runner is unknown.
- **failedApproach:** Treating timeouts and OS errors as the only transport failures while requiring class-only private diagnostics.
- **correction:** [`fbac067d`](https://github.com/m-shogo/memories-project/commit/fbac067d15b37ceec99c22482721bf5d530cbbcc) adds `TypeError` and `ValueError` to the fail-closed, output-withheld exception class.
- **recurrenceGuard:** The existing CI-reachable drill-request reconcile negative suite now injects synthetic `ValueError` and `TypeError` for both reviewed child validators and asserts the exact privacy-safe `Fail` message. Existing positive, nonzero, boolean status, `OSError`, timeout, target allowlist, environment and output privacy checks remain active.
- **retryCondition:** Revisit only if the subprocess transport, reviewed child target topology or exact-source CI outcome changes. Do not replay unchanged external credential, MinIO, permission or human-evidence blockers.

## Material success — private transport exception closure

- **outcome:** Both reviewed post-validator invocations normalize malformed transport exceptions without exposing synthetic private exception text.
- **evidence:** Exact-source [Backup Restore Drill Request Reconcile Rollback #41355676024](https://github.com/m-shogo/memories-project/actions/runs/41355676024) completed **SUCCESS** at `fbac067d15b37ceec99c22482721bf5d530cbbcc`. Other workflows were still pending/in progress at observation and are not claimed successful.
- **whySafe:** The atomic two-file code/test commit changed only the reconciler and its negative suite; no authority or evidence file was modified. Tests use synthetic error strings and the reviewed child allowlist remains unchanged.
- **reusableMechanism:** Normalize transport-level `OSError`, `ValueError`, `TypeError`, and `TimeoutExpired` into a stable private failure class; exercise every class in the existing exact-source CI-reachable negative suite.
- **protectedAuthorityCheck:** The exact Git compare lists only the two code/test paths. The ten protected blobs remain unchanged: learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, and promotion review `99cb895f`. `productionDecision=NO_GO`; no human promotion authorization was supplied.

## Next safe target

Audit the remaining pathname re-open between post-validator identity verification and child execution. Prefer executing pinned reviewed source bytes, with a negative test proving that a replaced pathname cannot become the executed child. Preserve all OPS-P0-007 and human promotion gates.
