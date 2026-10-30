# Supplemental OPS learning — group-writable canonical learning authority guard (2026-10-30)

Append-only supplemental operational learning only. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure / prospective source-identity gap

- **symptom:** A canonical learning authority file could be group-writable (for example mode 0664), allowing another principal in the same group to mutate the file while existing guards rejected only world-writable mode 0002.
- **evidence:** At `7a584381caf75801b8cfef765bcf0a5b8c0be90e`, both the descriptor-pinned reader and the five-file authority validator checked `0o002` but not `0o020`. Existing negative cases used mode 0666, not 0664. This is a prospective local source-authority gap, not evidence of a real unauthorized write.
- **rootCauseOrUnknown:** Verified omission of group-write permission in canonical file checks. Group membership and actual cross-principal exploitability were not demonstrated and remain unknown.
- **failedApproach:** Treating rejection of world-writable files and inode/hardlink controls as proof of exclusive canonical file mutation authority.
- **correction:** [`239dcc99`](https://github.com/m-shogo/memories-project/commit/239dcc990609d09b69b21b2f8346026e9385f186) rejects group-writable canonical files in both descriptor-pinned read and five-file validator, while retaining the prior exact world-writable diagnostic. Five isolated CLI negatives, a descriptor negative and a group-read-only positive were added.
- **recurrenceGuard:** The CI-reachable negative harness now exercises mode 0664 on contract, canonical learning, positive validator, negative validator and entrypoint. The descriptor test rejects 0664 and accepts 0640. No production file permission is modified.
- **retryCondition:** Revisit only after reviewed group ownership and runner permission evidence demonstrate a legitimate required writable mode; require exact-source CI, negative/positive controls and protected-authority comparison. Do not retry unchanged MinIO 401, workflow-write permission, large canonical learning transfer or human-promotion blockers.

## Prewrite failure caught before publication

- **symptom:** An initial patch-construction preflight expected three instances of `st_mode & 0o002`, but the source contained five.
- **evidence:** The read-only exact-token inventory returned five occurrences, covering parent-directory policy, the five-file world-write policy and three descriptor checks. No Git object or branch ref was written during that aborted attempt.
- **rootCauseOrUnknown:** Verified overbroad token-replacement assumption; the descriptor checks were not the only uses of that literal.
- **failedApproach:** Blindly replacing every `st_mode & 0o002` with `0o022`, which would unintentionally change separate parent-directory and world-writable diagnostic policies.
- **correction:** Aborted and reconstructed the patch using three uniquely named `before`, `after` and `live` descriptor tokens plus a separate exact five-file check.
- **recurrenceGuard:** Prewrite exact occurrence counts must match reviewed targets; abort on ambiguity before Git blob creation. The final commit contains only the intended group-write changes.
- **retryCondition:** Change the inventory only if the source structure changes and every affected permission policy is reviewed independently.

## Material success / exact-source evidence

- **outcome:** [Autonomous Learning Guard #41067049859](https://github.com/m-shogo/memories-project/actions/runs/41067049859) completed **SUCCESS** on exact source `239dcc990609d09b69b21b2f8346026e9385f186`.
- **evidence:** Validate job `124101081641` completed SUCCESS. Logs show append-only PASS, contract PASS, **552 canonical fail-closed negatives** (up from 547), 195 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document PASS and clean/read-only execution. The descriptor negative and positive are additional nested checks, not separately included in the 552 count.
- **whySafe:** One atomic CAS-published commit changed only the CI-reachable read-only validator and negative suite (+37/-2 lines). The tests use disposable fixture files. No workflow YAML, production service, credentials, traffic, generation/objective/drill/restore, request-bound evidence, typed eight-domain, independent review or promotion authority changed.
- **reusableMechanism:** Distinguish file write authority from parent-directory write authority; reject group-writable canonical file modes with descriptor and full CLI negative controls, and use an atomic two-file Git tree/commit plus expected-head CAS publication.
- **protectedAuthorityCheck:** Exact-source compare `7a584381...239dcc99` changed only the two read-only Python validators. Ten protected blob SHAs remained unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, recovery objective registry `f4d74f33`, reviewed drill request registry `acebcd02`, generation recovery evidence registry `ae7e57ef`, typed non-resurrection registry `26bb1cc7`, human promotion review registry `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and all separate objective/request/evidence/eight-domain/review/promotion gates unsatisfied.

## Next safe target

Audit group-writable parent-directory permissions against actual checkout/runner modes before extending parent-path policy. Continue Go/Python complete transitive dependency and trigger-coverage investigation; do not claim Go-only pre-MinIO focused CI without a permission-approved, executable independent path.
