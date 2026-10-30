# Supplemental OPS learning — inherited Git configuration source guard (2026-10-30)

Append-only supplemental learning only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure — inherited Git config changes read-only source authority or blocks

- **symptom:** Strict prewrite Git-index inspection previously rejected alternate index/worktree and tracing environments, but inherited `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT` and `GIT_CONFIG_KEY_/VALUE_` could still alter Git configuration source/semantics. A config path pointing to a named pipe can hang a nominally read-only Git query.
- **evidence:** In a disposable Git repository, `GIT_CONFIG_GLOBAL` pointed at a file containing `core.ignorecase=true` and `git config --get core.ignorecase` returned `true`. A separate `GIT_CONFIG_GLOBAL` FIFO caused `git ls-files --stage` to exceed a 2-second timeout, while the same command without the override returned. These are observed local prewrite-control risks, not production incidents.
- **rootCauseOrUnknown:** Verified: inherited Git config environment can select unreviewed configuration sources before the strict audit's own read-only commands.
- **failedApproach:** Treating `GIT_INDEX_FILE/GIT_DIR/GIT_WORK_TREE/GIT_COMMON_DIR` and `GIT_TRACE*` guards as sufficient environment closure.
- **correction:** [`cd59eda5`](https://github.com/m-shogo/memories-project/commit/cd59eda5ae2d5b7c419153f213c8e7008e412c8f) rejects the listed Git config environment selectors and `GIT_CONFIG_KEY_/VALUE_` prefixes before invoking Git.
- **recurrenceGuard:** [`1c350e88`](https://github.com/m-shogo/memories-project/commit/1c350e88f32a64322e0760ace58a769291c7c640) adds a real-Git config override control, six exact-diagnostic CLI negatives and a disposable FIFO CLI negative with a 2-second bound. The guard must reject before opening the FIFO.
- **retryCondition:** An explicitly reviewed configuration override requires bounded config-source identity, no-block/no-write tests, exact-source CI and protected-authority verification. This does not claim complete Git config-file provenance or external module closure; do not retry unchanged workflow-write, MinIO, canonical large-file transfer or human-promotion blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41026600475](https://github.com/m-shogo/memories-project/actions/runs/41026600475) completed **SUCCESS** on exact source `1c350e88f32a64322e0760ace58a769291c7c640`.
- **evidence:** Job logs confirm append-only and learning contract PASS, 509 canonical fail-closed negatives, 193 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only checks PASS. Config/FIFO controls are nested and not separately counted in 509.
- **whySafe:** Only the read-only prewrite auditor (+8 lines) and CI-reachable negative validator (+36 lines) changed. The override file and FIFO are disposable local test fixtures; no workflow YAML, production runtime, credential, traffic, recovery, generation, objective, typed eight-domain review or human promotion authority changed.
- **reusableMechanism:** Treat configuration-source overrides as input authority, independently of checkout/index and trace-file side effects. Pair an actual override control with exact CLI rejection and a bounded FIFO no-hang negative.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and separate approved objective, executable reviewed request, request-bound evidence, typed eight-domain coverage, independent review and human-promotion gates unmet.

## Next safe target

Finish exact-source CI for the Go Skip receiver/method-value inventory and persist the resulting lesson. Continue Go-only pre-MinIO focused CI and complete transitive Go/Python input closure; no workflow YAML or external MinIO retries without changed preconditions.
