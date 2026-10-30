# Supplemental OPS learning — workflow ctime identity and Git no-system config (2026-10-30)

Append-only operational learning only. The canonical learning authority and mandatory contract are unchanged. **This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, approved-objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure risk A — same-size, restored-mtime workflow rewrite

- **symptom:** The bounded workflow reader compared descriptor size and mtime, and verified the final pathname inode, but did not compare ctime. A same-inode rewrite could restore mtime and retain size while changing source content during the read/identity boundary.
- **evidence:** Source inspection of `read_workflow_bytes_bounded` at `ed1cc70d` found size/mtime checks without ctime. This is a verified guard gap and a synthetic concurrency risk, **not** an observed production incident or proof of an actual successful bypass.
- **rootCauseOrUnknown:** Verified omission of `st_ctime_ns` from the descriptor and final path identity checks.
- **failedApproach:** Treating equal inode, byte count and restored mtime as sufficient evidence that a workflow source remained unchanged.
- **correction:** [`c248d15e`](https://github.com/m-shogo/memories-project/commit/c248d15ebefc86d9c331d5623e0f0828efede05f) compares ctime before/after the bounded descriptor read and at the final pathname lstat, while retaining the same verified byte buffer for matching.
- **recurrenceGuard:** A deterministic self-test injects changed ctime on the same inode while preserving size/mtime, and requires the exact `workflow source changed during read` rejection. The existing entry-document CI executes this self-test.
- **retryCondition:** Reconsider if supported filesystem timestamp semantics or source-snapshot logic changes. Do not claim this closes races after the final identity check.

## Material failure risk B — inherited Git configuration source suppression

- **symptom:** Strict Git checkout/index verification rejected several inherited configuration selectors, but did not reject `GIT_CONFIG_NOSYSTEM`, which changes whether system Git configuration participates.
- **evidence:** Source inspection of the environment guard at `ed1cc70d` showed the missing selector. No production incident was observed.
- **rootCauseOrUnknown:** Verified omission from the reviewed Git configuration environment inventory.
- **failedApproach:** Treating the existing `GIT_CONFIG_GLOBAL/SYSTEM/PARAMETERS/COUNT` and key/value prefix checks as complete configuration-source closure.
- **correction:** The same code commit rejects inherited `GIT_CONFIG_NOSYSTEM` before running any Git command.
- **recurrenceGuard:** The CI-reachable real CLI negative passes `GIT_CONFIG_NOSYSTEM=1`, requires exit 1 and the exact configuration-environment diagnostic, and increases the reviewed negative inventory by one.
- **retryCondition:** Any explicitly reviewed Git configuration exception needs source-identity evidence, bounded execution and exact-source CI; do not repeat unchanged permission, MinIO or human-approval blockers.

## Observed success and protected authority

- **outcome:** [Autonomous Learning Guard #41040213242](https://github.com/m-shogo/memories-project/actions/runs/41040213242) completed **SUCCESS** on exact code source `c248d15ebefc86d9c331d5623e0f0828efede05f`.
- **evidence:** CI job logs report 517 canonical fail-closed negatives, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, and PASS for append-only, learning contract, entry documents and read-only checks. The ctime fixture is part of the fanout self-test and is not separately counted among canonical negatives.
- **whySafe:** The code commit modified only two read-only Python validators; the ctime test uses an isolated temporary file and mocked lstat. No workflow YAML, production code, production evidence, credential, traffic, recovery, readiness or promotion authority was written.
- **reusableMechanism:** Compare stable descriptor and final path metadata including ctime, consume the same verified source bytes, and bind new inherited environment selectors to exact-diagnostic CLI negatives.
- **protectedAuthorityCheck:** The code commit's GitHub comparison lists only `scripts/audit-memory-os-workflow-trigger-fanout.py` and `scripts/validate-autonomous-learning-system-negative.py`; all other paths, including the ten protected authorities, are unchanged. Canonical learning blob `b809c69d`, contract `87712ea9`, production status `55b3e639` and OPS-P0-007 snapshot `dbaa36b0` remain unchanged. `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, approved objective 0, executable reviewed request 0, request-bound evidence 0, complete typed eight-domain record 0, final candidate 0 and separate human promotion unmet.

## Next independent safe target

Audit remaining source-identity boundaries and Go/Python transitive input closure without claiming workflow trigger completeness. The focused Upload Route Go regression remains downstream of MinIO in existing workflows; do not retry unchanged Quay 401, workflow-write permission, large canonical learning transport or human-promotion blockers. The learning-only HEAD is not itself proof of the full production admission chain.
