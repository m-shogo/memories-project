# Supplemental OPS learning — admission-chain reconcile job authority (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production-equivalent generation or recovery evidence, backup/restore, RPO/RTO/skew, drill, credentials, traffic, readiness, or human production-promotion authority.

## Material guard gap / failure learning
- **Symptom:** Existing admission-chain reconcile CI source validator had event/root/permission semantic negatives but did not independently reject duplicate YAML job mappings or nested job-level permission and execution overrides. This was a static guard gap, not observed unauthorized recovery execution.
- **Observed evidence:** Reviewed workflow `.github/workflows/backup-restore-admission-chain-reconcile-negative.yml` has exactly one `negative` job, `runs-on: ubuntu-latest`, `timeout-minutes: 5`, `steps`, and inherits root `contents: read`; prior validator had nine YAML negatives but no nested job inventory.
- **Verified root cause:** A root read-only permission check and full Git blob pin cannot independently prove unique effective YAML job identity or forbid job-level shadow keys.
- **Failed approach:** Depending solely on source digest mismatch for nested YAML job/permission changes, without a dedicated semantic diagnostic.
- **Correction / executable recurrence guard:** [2a8b2f86](https://github.com/m-shogo/memories-project/commit/2a8b2f8625d7b22e0635a53387be84b10b089f02) pins the sole job identity and exact job-key sequence. Nine in-memory exact-diagnostic negatives reject duplicate/spaced/quoted jobs, plain/spaced/quoted job permissions, a bypass condition, a spaced timeout shadow, and job continuation override; total YAML negatives increase 9 to 18.
- **Retry condition:** Revisit only on a reviewed job topology/permission change or newly demonstrated bypass. Do not repeat unchanged canonical-learning transfer, workflow write permission, MinIO 401 or human-approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Admission Chain Reconcile Negative #40774439694](https://github.com/m-shogo/memories-project/actions/runs/40774439694) completed SUCCESS on exact source `2a8b2f8625d7b22e0635a53387be84b10b089f02`. Job log confirms 18 exact-diagnostic YAML negatives, 48 trigger removals, one shortened inventory, 18 semantic plus two blob-only source negatives.
- **Why safe:** Only the existing read-only, PR/push CI-reachable Python validator changed (+40/-3). No workflow, production status, registry, evidence, credential, traffic or promotion authority was written.
- **Reusable mechanism:** Enumerate reviewed YAML job mapping and allowed job keys, then inject synthetic job/permission shadows and require exact semantic rejection before the existing source SHA check.
- **Protected-authority check:** Commit compare shows only the validator changed; production-operability-status blob `3956bb805ee124ca7baf594ba05bcb0d986783b4` still states `productionDecision=NO_GO`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. Recovery evidence, drill-request and typed non-resurrection registries remain empty; learning is never admission/promotion evidence.
- **Next safe target:** Audit Backup Restore Contracts CI for the same independently unguarded nested job authority; distinguish targeted CI from the full admission chain.
