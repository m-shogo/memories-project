# Supplemental OPS learning — prewrite fanout misses Admission Chain writer classification (2026-11-02)

Append-only learning under canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved objective, reviewed request, request-bound recovery evidence, typed eight-domain coverage, independent review, final candidate or human production-promotion authority.

## Material failure / newly verified classifier gap

- **symptom:** An existing prewrite trigger fanout auditor can label a bounded workflow match as `BOUNDED_DIRECT_MATCH_ONLY` even when it includes the write-capable Backup Restore Admission Chain, because this writer is absent from its explicit known-writer set. A prior task also proposed inventing a new guard before locating the already implemented auditor.
- **evidence:** `scripts/audit-memory-os-workflow-trigger-fanout.py` defines `KNOWN_WRITER_CAS_WORKFLOWS` without `.github/workflows/backup-restore-admission-chain.yml`. Its `classify(matches)` returns `BLOCKED_KNOWN_WRITER_CAS` only for set membership, then `BOUNDED_DIRECT_MATCH_ONLY` when fanout is at most 12 and no other known blocker matches. The Admission Chain's `scripts/*backup*.py` push/PR path filter matches both newly changed transport negative harnesses, and its push `validate-and-publish` job has `contents: write` and Git push logic. This is a verified source-level classification gap; no exact-source invocation of the prewrite CLI on those two paths was executed in this run.
- **rootCauseOrUnknown:** Verified incomplete `KNOWN_WRITER_CAS_WORKFLOWS` inventory, plus an incomplete initial search of existing prewrite scripts. Whether other workflows outside the 48 scoped backup/restore/OPS workflows match these paths is not established by that scoped audit.
- **failedApproach:** Trusting bounded direct workflow count as evidence of no write capability; searching only the target negative workflow and named generation-evidence publisher; proposing a duplicate standalone trigger checker without first discovering `scripts/audit-memory-os-workflow-trigger-fanout.py`.
- **correction:** Reuse the existing fail-closed auditor rather than duplicating it. Treat `BOUNDED_DIRECT_MATCH_ONLY` as **not** a permission or transitive reachability proof, as the script itself documents. Hold further `scripts/*backup*.py` writes. Next code change should add Admission Chain to its known writer inventory and negative assertions that both transport script paths are blocked, but only after safe exact-source read-only CI reachability for the auditor change is confirmed.
- **recurrenceGuard:** Existing auditor already has conservative YAML glob parsing, verified workflow-source bytes, bounded fanout and negative fixtures. The **missing executable guard** is a regression assertion for Admission Chain writer coupling in `classify`; not yet implemented. Before any write, run/verify the existing auditor against the exact candidate path and inspect the matched workflows' effective permissions and source guards; never treat a bounded result as authorization.
- **retryCondition:** Revisit classifier code only after a safe, exact-source, independently read-only CI trigger for `scripts/audit-memory-os-workflow-trigger-fanout.py` (and its negative tests) is verified. Do not change the known-writer inventory without CI reachability; do not repeat unchanged production-evidence, MinIO HTTP 401 or canonical large-blob blockers.

## Bounded workflow audit and tool failure

- **outcome:** Read-only inspection of all 48 workflow files in the backup/restore, recovery-objectives, OPS-P0-007 and autonomous-learning scope found the broad `scripts/*backup*.py` writer coupling in Admission Chain. The Generation Evidence Reconcile Negative workflow explicitly runs the two transport harnesses with `contents: read`, while Admission Chain separately grants write.
- **evidence:** GitHub `so` tree and 48 fetched workflow sources; scope is explicitly 48 of 221 `.github/workflows/*.yml` files, **not** a complete repository-wide trigger proof.
- **whySafe:** All inspection calls were GET/read-only, with no CI dispatch, workflow edit, production evidence mutation, or credential/traffic action.
- **reusableMechanism:** Bounded source inventory and explicit per-workflow permission/path matching, followed by the existing prewrite CLI's full workflow-tree audit in an exact checkout when available.
- **protectedAuthorityCheck:** Git blob identities unchanged after source and append-only learning commits: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. Registered/semantically eligible generations 0/0; approved current objective, executable reviewed request, request-bound recovery evidence, complete typed coverage, final candidate and human promotion review all 0.

### Scoped tool failure and correction

- **symptom:** One attempted 48-way connector batch was rejected by the per-call tool limit.
- **evidence:** The orchestration returned `Code Mode exceeded the maximum number of tool calls` without yielding the requested workflow audit.
- **rootCauseOrUnknown:** Verified excessive calls within one orchestration, not a repository or GitHub CI failure.
- **failedApproach:** Launching 48 file reads in a single orchestration.
- **correction:** Split the exact 48 paths into five batches of at most 10 reads; all returned source results.
- **recurrenceGuard:** Keep each connector orchestration below the observed tool-call ceiling and reconcile the full requested path inventory across bounded batches.
- **retryCondition:** Retry the larger batch only if the orchestration limit is demonstrably raised; otherwise continue bounded batching.

## Next safe target

Establish exact-source read-only CI reachability for the existing prewrite auditor, then add Admission Chain to the known writer CAS set with a negative test proving both transport paths are blocked. Do not weaken OPS-P0-007 or turn learning/synthetic CI into production evidence.
