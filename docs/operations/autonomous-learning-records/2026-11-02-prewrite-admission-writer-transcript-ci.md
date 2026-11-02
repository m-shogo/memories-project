# Supplemental OPS learning — Admission Chain writer exact prewrite transcript (2026-11-02)

Append-only subordinate record to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under mandatory `contracts/operations/autonomous-learning-system.json`. Synthetic tests and learning do not satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion gates.

## Material failure / underconstrained proof

- **symptom:** The Admission Chain writer prewrite regression check verified a blocked risk, numeric count and Admission Chain membership without requiring that the CLI actually audited the requested transport path or emitted an exact refusal transcript. No unsafe write was observed.
- **evidence:** The preceding `scripts/validate-autonomous-learning-system-negative.py` used `actual_workflows`, `reports` and `exact_count` but did not compare the path header or complete stdout for the two real transport script paths. The prewrite CLI itself emits a deterministic header, risk/count, workflow identities and refusal advisory.
- **rootCauseOrUnknown:** Verified gap in the negative verifier's evidence reconciliation, not a verified failure of the underlying workflow matcher.
- **failedApproach:** Treating a blocked writer verdict and count parity as proof of exact requested-path classification.
- **correction:** [`4a131912`](https://github.com/m-shogo/memories-project/commit/4a1319129cd6fef6c48e2b8501d847ed442c6a0b) binds each transport path to the exact expected CLI transcript and sorted unique workflow identity set.
- **recurrenceGuard:** The independent read-only Autonomous Learning Guard now fails closed on wrong-path output, extra/missing stdout, incorrect refusal advisory, duplicate/reordered workflows, or count drift for both transport paths.
- **retryCondition:** Revisit only if prewrite CLI output grammar, Admission Chain trigger paths, reviewed writer identity or exact-source CI changes. Do not retry unchanged external-evidence or MinIO blockers.

## Observed success

- **outcome:** Exact-source [Autonomous Learning Guard #41431216038](https://github.com/m-shogo/memories-project/actions/runs/41431216038) completed SUCCESS on `4a1319129cd6fef6c48e2b8501d847ed442c6a0b`.
- **evidence:** GitHub Actions reported completed/success for the exact commit; the only changed file was `scripts/validate-autonomous-learning-system-negative.py`. No production evidence or live drill was generated.
- **whySafe:** This was a read-only negative verifier change; writer workflows, permissions, production registries, credentials and promotion authority were not edited.
- **reusableMechanism:** Require path identity, complete output grammar, exact count and unique ordered workflow identities together; a single risk string is not a proof.
- **protectedAuthorityCheck:** Postchange nine checked blob SHAs remained fixed: production status `d677a1c9` (`NO_GO`), generations `bfd1b045`, objectives `f4d74f33`, requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. No human promotion authority is claimed.

## Next safe target

Finish exact-source validation of the shared-entrypoint transcript check, then inspect the strict prewrite auditor's exact-path/advisory evidence without weakening writer-CAS refusal.
