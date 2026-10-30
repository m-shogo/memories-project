# Supplemental OPS learning — Go Skip receiver aliases and method values (2026-10-30)

Append-only supplemental learning only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract remains `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — receiver-specific Skip inventory

- **symptom:** The focused Go test and selected-file skip inventory recognized `t.Skip` variants but not an aliased receiver `alias := t; alias.Skip(...)` or a method value `skip := t.Skip; skip(...)`. Either can skip an otherwise selected Go test without adding a direct `t.Skip(...)` call counted by the previous inventory.
- **evidence:** A disposable Go 1.23.2 module with `TestAliasSkip` and `TestMethodValueSkip` completed both tests as **SKIP**. Read-only inspection of the two selected HTTP test files found exactly two existing `.Skip` references, both the reviewed `t.Skip` helper calls, and none in the two focused route tests.
- **rootCauseOrUnknown:** Verified: the earlier regex bound the receiver to the literal identifier `t` and required an immediate call after the method name; Go permits both receiver aliasing and method-value extraction.
- **failedApproach:** Treating a count of direct `t.Skip(...)` invocations as a complete source-level skip reference inventory.
- **correction:** [`2f36993a`](https://github.com/m-shogo/memories-project/commit/2f36993a22e6a3cc4ff39c0aabc7711e734c4cd6) conservatively matches any receiver's `.Skip/.Skipf/.SkipNow` selector, including whitespace/newline forms and method-value references, in selected test bodies and the selected-file skip inventory.
- **recurrenceGuard:** Four CI-bound negatives inject aliased receiver and method-value skips into a selected test and unrelated route-file helper; each must produce the existing exact focused-test or skip-inventory diagnostic. Existing 0/2 reviewed skip-reference counts remain positive controls.
- **retryCondition:** A legitimate new Skip reference requires reviewed conditional preconditions, exact source inventory, executable Go controls, exact-source CI and protected-authority verification. Reflection or dynamic control flow remains outside this lexical proof; do not infer full test execution.

## Material success

- **outcome:** [Autonomous Learning Guard #41026817397](https://github.com/m-shogo/memories-project/actions/runs/41026817397) completed **SUCCESS** on exact source `2f36993a22e6a3cc4ff39c0aabc7711e734c4cd6`.
- **evidence:** CI job logs show append-only/learning contract PASS, 509 canonical fail-closed negatives, 193 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only checks PASS. The four new nested Skip negatives are not separately counted in 509.
- **whySafe:** Only the CI-reachable read-only negative validator changed (+10/-2 lines). Go syntax controls used disposable modules; no Go production/test source, workflow YAML, credentials, traffic, evidence, recovery, generation, objective, eight-domain review or human promotion authority changed.
- **reusableMechanism:** Bind a safety-sensitive source inventory to semantic member references rather than one local receiver name; use executable Go controls for alias and method-value forms and keep the limitation of lexical analysis explicit.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and all separate approved objective, executable reviewed request, request-bound evidence, typed eight-domain coverage, independent review and human-promotion gates unsatisfied.

## Next safe target

Continue Go-only pre-MinIO focused test CI reachability and complete Go/Python transitive dependency closure. Do not change workflow triggers without permission and full input coverage, and do not retry unchanged Quay MinIO HTTP 401 or human promotion blockers.
