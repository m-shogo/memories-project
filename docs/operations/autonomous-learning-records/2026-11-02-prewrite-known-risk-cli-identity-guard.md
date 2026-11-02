# Supplemental OPS learning — prewrite known-risk CLI inventory and transcript identity (2026-11-02)

Append-only record subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This learning and synthetic CI are **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate, or human promotion evidence.

## Material failure / code-level gap

- **symptom:** The known-external-dependency prewrite CLI check could accept a duplicated/reordered workflow list whose count still matched the printed total, or a correct count/risk for a different audited path with unreviewed extra stdout lines. No actual production incident or malicious CLI transcript was observed.
- **evidence:** Before `9ff29e57`, `scripts/validate-autonomous-learning-system-negative.py` checked only exit code, stderr, one parsed count, list length and one known workflow identity for `scripts/validate-memory-os-rate-limit-operations-source-negative.py`. Adjacent entrypoint/strict audit checks already required sorted unique identities, but this known-risk check did not. `scripts/audit-memory-os-workflow-trigger-fanout.py` prints a deterministic path header, risk/count, ordered workflow list and refusal advisory.
- **rootCauseOrUnknown:** Verified underconstrained verifier, not a verified unsafe repository write.
- **failedApproach:** Treating count parity plus one known identity as complete workflow-inventory/path evidence.
- **correction:** [`9ff29e57`](https://github.com/m-shogo/memories-project/commit/9ff29e579282e97663dd28cd5a2f305ff22a35e6) requires sorted unique identities; [`033fbcd0`](https://github.com/m-shogo/memories-project/commit/033fbcd00f707ff0df69da2e02f0915882df9f54) requires the exact audited path, risk/count, all workflow rows and refusal advisory with no extra lines.
- **recurrenceGuard:** Existing read-only Autonomous Learning negative suite now fails closed if the real known-risk CLI inventory is duplicated, reordered, path-substituted or transcript-extended; the workflow's exact-source clean-checkout, append-only and helper-ancestor steps remain mandatory.
- **retryCondition:** Revisit only if the prewrite CLI output grammar, known external-dependency workflow triggers, path identity, or exact-source CI changes. Do not retry unchanged MinIO HTTP 401, large canonical-learning blob retrieval or absent human production evidence.

## Observed material success

- **outcome:** Two exact-source read-only Autonomous Learning Guard runs completed SUCCESS.
- **evidence:** [Run #41430893558](https://github.com/m-shogo/memories-project/actions/runs/41430893558) on `9ff29e579282e97663dd28cd5a2f305ff22a35e6` and [run #41431096135](https://github.com/m-shogo/memories-project/actions/runs/41431096135) on `033fbcd00f707ff0df69da2e02f0915882df9f54` both had successful exact-clean-source, append-only authority, learning-contract/executable-negative, helper-ancestor reachability and read-only execution job steps. This is CI outcome evidence only.
- **whySafe:** Commits changed only the read-only negative test file; no workflow permissions, publisher, registry, production authority, credentials, traffic or promotion path was edited.
- **reusableMechanism:** Verify the *entire* deterministic CLI transcript and exact workflow identity set, not just a matching count or risk label, when auditing a path before an autonomous write.
- **protectedAuthorityCheck:** After the changes, nine explicitly checked authority blob SHAs remained unchanged: production status `d677a1c9` (`productionDecision=NO_GO`), environment generations `bfd1b045`, recovery objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. No production-equivalent generation, objective, request-bound evidence, eight-domain coverage or human promotion authority was created or inferred.

## Next independent safe target

Confirm exact-source CI for the Admission Chain writer transcript check, then apply equivalent exact-path/refusal checks to the shared entrypoint/strict prewrite audit where independently read-only CI is reachable.
