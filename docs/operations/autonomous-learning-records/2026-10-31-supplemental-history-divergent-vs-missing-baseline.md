# Supplemental OPS learning — divergent versus unavailable Git history baseline (2026-10-31)

Append-only operational learning only. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, human-approved recovery objective, reviewed drill request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure class

- **symptom:** The supplemental all-parent history guard treated every nonzero `git merge-base --is-ancestor` exit as the same `baseline is not an ancestor` diagnostic, even when the baseline Git object was unavailable.
- **evidence:** Disposable Git reproduction observed exit **1** with empty stderr for an existing but unrelated root commit, versus exit **128** with `Not a valid commit name` for a syntactically valid, missing 40-hex baseline object. The old guard collapsed both cases.
- **rootCauseOrUnknown:** Verified: an unconditional truthiness check on `CompletedProcess.returncode` erased the distinction between an authoritative negative ancestry result and Git execution/object-availability failure. Future Git implementations may use other nonzero error codes; no specific code other than the documented fixture observation is assumed by the production guard.
- **failedApproach:** Treating any Git failure as proof that a reviewed immutable baseline exists but is unrelated to the checked-out history.
- **correction:** [1055d220](https://github.com/m-shogo/memories-project/commit/1055d220bf840dbfa8d7f4c62d5a76269e459f35) distinguishes exit 1 with empty stderr (not an ancestor) from any other nonzero or diagnostic-bearing result (ancestry inspection unavailable).
- **recurrenceGuard:** Two real disposable Git negative controls assert the cause-specific errors for a divergent orphan branch and a missing object. Each control independently checks the raw Git return code and stderr before invoking the guard; the independent CI entrypoint pins the exact **37-fixture** PASS format, up from 35.
- **retryCondition:** Revisit only after a reviewed Git ancestry error contract, immutable epoch, checkout topology or CI invocation changes. Do not repeat unchanged workflow-write permission, MinIO HTTP 401, canonical large-learning write, or human approval blockers.

## Material success

- **outcome:** Missing immutable baseline objects now fail closed with a distinct unavailable-inspection reason, while valid but unrelated baselines fail closed with the correct divergence reason.
- **evidence:** [Autonomous Learning Guard #41165761346](https://github.com/m-shogo/memories-project/actions/runs/41165761346) completed **SUCCESS** on exact code source `1055d220`. Job logs show 601 canonical fail-closed cases, **37 supplemental all-parent history fixtures**, 52 source-negative workflows / 63 Python commands / 204 semantic fixtures, 195 fanout synthetics, 1,186 helper-ancestor negatives, canonical append-only, entrypoint and clean/read-only PASS. [Operability Contracts #41165761456](https://github.com/m-shogo/memories-project/actions/runs/41165761456) also completed **SUCCESS** on the same SHA and independently printed the 37-fixture history proof.
- **whySafe:** Only two CI-executed read-only Python validators changed. Test Git repositories were temporary; no production/recovery registries, workflow YAML, external MinIO, credentials, traffic, human approvals or promotion were modified.
- **reusableMechanism:** Preserve semantic distinctions between a negative Git ancestry result and an unavailable/incomplete Git object graph; use actual Git subprocess fixtures plus cause-sensitive negative assertions and an independently pinned CI PASS string.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs were unchanged at the exact code HEAD: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, and all six generation/objective/drill-request/recovery-evidence/non-resurrection/promotion registries. Live `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound evidence 0, typed eight-domain records 0, final candidates 0. Human promotion remains separate and non-automatic.

## Next safe target

A shallow Git history can hide a restored mutation on a merged side branch even when the baseline is still an ancestor through the main branch. Reproduce and reject incomplete shallow history with a real multi-parent negative, without relaxing existing all-parent checks, CI deadlines or protected production gates.
