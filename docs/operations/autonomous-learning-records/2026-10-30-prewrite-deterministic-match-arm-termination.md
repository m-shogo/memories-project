# Supplemental OPS learning — deterministic eager match-arm termination (2026-10-30)

Append-only operational learning only. Canonical authority `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure / prospective static guard gap

- **symptom:** A candidate prewrite Python source could retain its exact canonical `__main__` guard yet terminate in the first deterministic module-level `match` arm before that guard.
- **evidence:** At source `a26b4b3fb35f8ecbdbdf9bd2afa83e50d5e35f0b`, `eager_direct_termination` handled classes, selected literal-boolean branches, entered with-bodies, nonempty literal loops, try/finally and direct header/RHS termination, but had no `ast.Match` case handling. This was a prospective source-order coverage gap, not an observed production incident.
- **rootCauseOrUnknown:** Verified omission of the first provably matching unguarded `ast.Match` case from the bounded AST source-order classifier. General match control flow and arbitrary side effects remain unknown.
- **failedApproach:** Treating the existing eager statement classifier and a syntactically preserved main guard as exhaustive reachability proof.
- **correction:** [`212c420b`](https://github.com/m-shogo/memories-project/commit/212c420b797677ae97519b2bf2a471cdaa2bd396) rejects direct terminating statements in a first unguarded wildcard, literal-equal or singleton-equal match arm. Three exact-diagnostic negatives and three safe unmatched/guarded/deferred positives were added to the CI-reachable prewrite self-test.
- **recurrenceGuard:** The self-test must reject deterministic first-arm `sys.exit`, `raise SystemExit`, and `os.abort`, while retaining positives for a nonmatching literal, a false guard, and a deferred function. This is a conservative bounded syntactic check, not general Python execution-graph proof.
- **retryCondition:** Revisit only if reviewed match semantics, the first-arm classifier or independently reproduced positives/negatives change; require exact-source CI and protected-authority verification. Do not retry unchanged MinIO 401, workflow-write permission, large canonical-learning transport or human-promotion blockers.

## Material success / verified safe scope

- **outcome:** [Autonomous Learning Guard #41065489514](https://github.com/m-shogo/memories-project/actions/runs/41065489514) completed **SUCCESS** on exact source `212c420b797677ae97519b2bf2a471cdaa2bd396`.
- **evidence:** Job `124095578017` completed SUCCESS. Logs show append-only PASS, autonomous learning contract PASS, 547 canonical fail-closed negative cases, 195 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document PASS and clean/read-only validation. The six new nested prewrite fixtures are not separately counted in the 547 printed cases.
- **whySafe:** The code commit changed only `scripts/validate-autonomous-learning-system.py` (+34 lines), a read-only CI-reachable validator. No workflow YAML, production service, credentials, traffic, recovery evidence, generation/objective/drill authority, typed eight-domain coverage or promotion record was modified.
- **reusableMechanism:** For source-order proof, classify only a provably entered first match arm, reject direct terminators, and preserve paired nonmatching/guarded/deferred positive controls.
- **protectedAuthorityCheck:** Exact-source compare `a26b4b3f...212c420b` shows only the validator changed. All ten protected authority blobs remain unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, recovery objective registry `f4d74f33`, reviewed drill request registry `acebcd02`, generation recovery evidence registry `ae7e57ef`, typed non-resurrection registry `26bb1cc7`, human promotion registry `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED` with registered/eligible generations 0/0 and no human-approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, independent review or separate human promotion.

## Next safe target

Audit direct eager termination in a `match` subject or a provably selected arm guard; correct the wildcard fixture to use a bound subject. Keep Go-source-triggered pre-MinIO Focused Upload Route Test and complete Go/Python transitive CI closure explicitly unproven until a separately executable, permission-approved path exists.
