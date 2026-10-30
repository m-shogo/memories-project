# Supplemental OPS learning — inherited Git tracing cannot write during prewrite audit (2026-10-30)

Append-only supplemental learning only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract is `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human-promotion evidence.

## Material failure — read-only Git command with an inherited trace destination

- **symptom:** The strict prewrite Git-index identity audit uses read-only `rev-parse`, `ls-files` and `diff` commands, yet inherited `GIT_TRACE*` environment variables can cause those commands to create or append trace files outside the checkout. This is a prospective read-only boundary gap, not an observed production incident.
- **evidence:** A disposable Git repository reproduced a nonempty trace file after `GIT_TRACE=/tmp/... git -c core.fsmonitor=false rev-parse --show-toplevel`. Independent disposable controls confirmed `GIT_TRACE`, `GIT_TRACE2_EVENT` and `GIT_TRACE2_PERF` each write nonempty files from a read-only `rev-parse`.
- **rootCauseOrUnknown:** Verified: disabling `core.fsmonitor` prevents that hook but does not suppress Git's separate inherited trace-file output.
- **failedApproach:** Assuming read-only Git subcommands plus `-c core.fsmonitor=false` guaranteed a no-write audit under arbitrary inherited Git environment variables.
- **correction:** [`34429b3b`](https://github.com/m-shogo/memories-project/commit/34429b3b459172fa869bea46efe7d28445f9f283) rejects every inherited `GIT_TRACE*` key before the first strict-index Git command, with a distinct exact diagnostic.
- **recurrenceGuard:** [`3750dda3`](https://github.com/m-shogo/memories-project/commit/3750dda330291cf2c24833811c69853b1ee0e21c) adds three real-Git control writes into disposable files, deletes each marker, then invokes the actual strict CLI with the same environment and requires rejection **without recreating** the marker.
- **retryCondition:** A legitimate traced audit requires a reviewed nonwriting trace destination or isolated trace transport plus a deterministic no-write negative/positive, exact-source CI and protected-authority verification. Do not retry unchanged workflow-write permission, MinIO HTTP 401, canonical large-file transport or human-promotion blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41025694920](https://github.com/m-shogo/memories-project/actions/runs/41025694920) completed **SUCCESS** on exact source `3750dda330291cf2c24833811c69853b1ee0e21c`.
- **evidence:** CI job logs show append-only PASS, learning contract PASS, 509 canonical fail-closed negatives, 193 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only validation PASS. The three trace controls are nested negatives and are not separately included in the printed 509.
- **whySafe:** Only the existing read-only prewrite auditor (+4 lines) and CI-reachable negative validator (+23 lines) changed. Trace writes in the control are confined to disposable test paths, removed before each actual guard invocation. No workflow YAML, Go runtime, production evidence, credentials, traffic, recovery, objective, generation, typed eight-domain review or promotion authority changed.
- **reusableMechanism:** Treat inherited tracing as a separate execution side-effect channel; prove the control write with real Git and prove the guarded command never recreates it. Retain the independent fsmonitor and clean-filter protections.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remain unchanged: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, approved recovery objective, executable reviewed drill request, request-bound recovery evidence, complete typed eight-domain coverage, final candidate and separate human promotion absent. Learning cannot satisfy any of these gates.

## Next safe target

Continue read-only Go/Python complete transitive input closure and Go-only pre-MinIO focused test CI reachability. Workflow trigger changes require changed permission/approval and complete coverage proof; do not retry unchanged external blockers.
