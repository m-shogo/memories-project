# Supplemental OPS learning — eager match subject and selected guard termination (2026-10-30)

Append-only supplemental operational history only. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure / prospective reachability gap

- **symptom:** Even after deterministic first-arm checking, a prewrite candidate could preserve the exact `__main__` guard while terminating earlier in the eagerly evaluated `match` subject or the guard of a provably matching first arm.
- **evidence:** At `2a2f0467add6998cfecc2165bcbeca9c340097f9`, the bounded `ast.Match` classifier checked only an unguarded first arm's body. It did not inspect a direct terminating subject call or a first certain-match guard call. This was a prospective static gap, not observed production execution.
- **rootCauseOrUnknown:** Verified AST evaluation-order omission. Subject evaluation precedes patterns; a guard executes on a matching pattern even if the body does not. Arbitrary nested expressions and general Python control flow remain explicitly unproven.
- **failedApproach:** Treating a checked first-arm body as complete reachability proof for the whole match statement.
- **correction:** [`fa8d9d5b`](https://github.com/m-shogo/memories-project/commit/fa8d9d5b7edb9df1435274f9a30ddad31a5fb019) checks direct subject calls and direct guards on a provably matching first arm, with two new exact-diagnostic negatives and one unmatched-guard positive. The prior wildcard negative now uses a bound string subject rather than an undefined name, preventing a misleading NameError-only demonstration.
- **recurrenceGuard:** CI-reachable `prove_prewrite_python_negatives` rejects direct `sys.exit` in a match subject and direct `os.abort` in a selected guard while accepting an unselected guard. A bound-subject wildcard test proves the intended body boundary. No candidate fixture is executed.
- **retryCondition:** Revisit only for a changed reviewed match evaluation model or a demonstrated positive/negative regression; require exact-source CI, paired controls and protected-authority verification. Unchanged MinIO 401, workflow-write permission, canonical learning transport and human-promotion blockers remain ineligible for retry.

## Material success and authority preservation

- **outcome:** [Autonomous Learning Guard #41066185898](https://github.com/m-shogo/memories-project/actions/runs/41066185898) completed **SUCCESS** on exact source `fa8d9d5b7edb9df1435274f9a30ddad31a5fb019`.
- **evidence:** GitHub Actions validate job `124098081159` completed SUCCESS. Logs confirm append-only PASS, learning contract PASS, 547 canonical fail-closed negatives, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document PASS, and clean/read-only execution. The added prewrite fixtures are nested self-tests and not separately included in the printed 547.
- **whySafe:** Only the CI-reachable read-only Python validator changed (+23/-4 lines). No workflow, production service, credentials, traffic, generation/objective, drill, backup/restore, request-bound evidence, typed eight-domain, independent-review or promotion authority changed.
- **reusableMechanism:** Bind reachability checks to the exact evaluation order of subjects, patterns, guards and bodies; use a guaranteed-match first case, and pair selected/unselected negative and positive controls.
- **protectedAuthorityCheck:** Exact-source compare `2a2f0467...fa8d9d5b` changed only `scripts/validate-autonomous-learning-system.py`. All ten protected blob SHAs remain unchanged: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, recovery objective registry `f4d74f33`, reviewed drill request registry `acebcd02`, generation recovery evidence registry `ae7e57ef`, typed non-resurrection registry `26bb1cc7`, human promotion review registry `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, no approved objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain record, independent review or separate human promotion.

## Next safe target

Read-only audit of group-writable canonical authority files and existing negative-test coverage before any additional permission guard. Keep Go-only pre-MinIO focused CI and complete Go/Python transitive trigger closure explicitly unproven until permissions and external dependencies permit independent validation.
