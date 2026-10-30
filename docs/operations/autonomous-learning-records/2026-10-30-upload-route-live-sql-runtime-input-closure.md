# Supplemental OPS learning — Upload Route Go live SQL runtime input lower bound (2026-10-30)

Append-only supplemental learning only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human-promotion gates.

## Material failure A — runtime SQL dependencies omitted from compile-input lower bound

- **symptom:** The Upload Route static Go/Python input inventory pinned 109 compile/direct validator inputs but omitted eleven SQL migration files loaded at runtime by the selected Go HTTP live-test helper. Both reviewed Upload Route Push/PR workflow path filters omit those eleven `infra/postgresql/security/*.sql` files. A SQL-only change therefore lacks proven focused-test trigger reachability.
- **evidence:** Read-only inspection of `services/import-api/internal/httpserver/server_live_test.go` found one `os.ReadFile(filepath.Join("..", "..", "..", "..", "infra", "postgresql", "security", name))` loop with exactly eleven ordered migration names. The latest Git tree contains all eleven SQL blobs. The preexisting 109-path inventory and 81-path uncovered set did not mention `infra/postgresql/security`.
- **rootCauseOrUnknown:** Verified: the import-graph inventory models compile-time Go imports and selected Python validator inputs, not the live Go helper's runtime file reads. Full transitive runtime closure remains unproven.
- **failedApproach:** Treating the 109 direct/compile input set as though it already covered every input consumed by the focused Go live test.
- **correction:** [`c9c1ed4c`](https://github.com/m-shogo/memories-project/commit/c9c1ed4c237f56f1831bd15facdbae4b3d13469f) adds a separate exact eleven-file runtime SQL migration input inventory, pins the Go loop's names/order/read expression, validates regular unaliased source paths, and adds mutation/missing-file negatives.
- **recurrenceGuard:** A deterministic SHA-256 identity of the eleven relative paths, actual Go loop fingerprint, disposable positive/missing-file negative and real Push/PR trigger-gap set check. The eleven missing trigger paths are explicitly retained as a **blocker**, not silently counted as covered.
- **retryCondition:** Workflow trigger changes require newly available permission and a reviewed complete input/trigger closure; SQL content identity changes require a separately reviewed blob guard. Do not retry unchanged Quay MinIO HTTP 401 or human-promotion blockers.

## Material failure B — extra stdout violated the exact CI diagnostic contract

- **symptom:** Initial [CI #41027502262](https://github.com/m-shogo/memories-project/actions/runs/41027502262) was **FAILED** before executing new negatives.
- **evidence:** The job log showed `RuntimeError: unreviewed learning negative stdout` from `require_reviewed_learning_negative_stdout`. The new SQL-gap `print(...)` introduced a second stdout call, while the existing contract permits exactly one canonical PASS classifier.
- **rootCauseOrUnknown:** Verified: the strict AST-based stdout inventory rejected the added diagnostic, independent of SQL path semantics.
- **failedApproach:** Adding informative stdout to a negative suite with a deliberately pinned single-line stdout authority.
- **correction:** [`7dd0f08c`](https://github.com/m-shogo/memories-project/commit/7dd0f08c3fa6aaaae348061ee2834ac7b258f5ff) removes the extra stdout and uses a fail-closed check that the eleven current SQL migration paths remain missing from both workflow trigger sets until an explicit reviewed reconciliation.
- **recurrenceGuard:** Existing `require_reviewed_learning_negative_stdout` remains unchanged and executable, rejecting any unreviewed stdout additions. The actual workflow path audit rejects unreviewed changes to the known SQL trigger gap.
- **retryCondition:** Only change the negative suite's stdout contract with an independently reviewed diagnostic protocol and exact-source CI; do not repeat ad hoc debug printing.

## Material success

- **outcome:** [Autonomous Learning Guard #41027599801](https://github.com/m-shogo/memories-project/actions/runs/41027599801) completed **SUCCESS** on exact source `7dd0f08c3fa6aaaae348061ee2834ac7b258f5ff`.
- **evidence:** Job logs confirm append-only and learning contract PASS, 509 canonical fail-closed negatives, 193 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only checks PASS. The new SQL runtime-input controls run as nested checks, not additional printed canonical negatives.
- **whySafe:** Only the CI-reachable read-only negative validator changed; no SQL migration contents, Go production/test source, workflow YAML, credentials, traffic, recovery, generation, objective, typed eight-domain review or human-promotion authority changed.
- **reusableMechanism:** Distinguish compile-time import closure from runtime file-read closure; pin actual runtime input names/order and path identity, then explicitly classify trigger gaps without using learning records as readiness evidence or weakening exact CI diagnostics.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, human-approved objective, executable reviewed request, request-bound evidence, typed eight-domain coverage, independent review and human promotion absent.

## Next safe target

Pin the eleven runtime SQL blob contents in the CI-bound read-only validator, while keeping the separate 109 compile-input inventory and eleven trigger gaps explicit. Continue Go-only pre-MinIO focused CI and complete transitive Go/Python dependency closure; do not alter workflow YAML without authority.
