# Supplemental OPS learning — Upload Route focused skip inventory and CI trigger reachability (2026-10-30)

Append-only supplemental history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective unreviewed skip site

- **Symptom:** A third `t.Skip` could be added to an unrelated function in a selected Go test source file while both previously guarded helper conditions remain unchanged. A focused test could then transitively skip without the two named-helper guards rejecting the new site.
- **Observed evidence:** Read-only review of all 24 HTTP server `*_test.go` files identified opt-in skip paths in several tests outside the focused selector. Of the two source files containing the four selected tests, `route_authority_test.go` has zero direct `t.Skip` sites and `server_live_test.go` has exactly two, both reviewed individually. This is a prospective drift risk, not observed production execution.
- **Verified root cause:** Per-helper guards establish the identity of known skip sites, not completeness of the selected source-file skip-site inventory.
- **Failed approach:** Inferring no additional skip sites from successful checks of the two known helpers.
- **Correction / executable recurrence guard:** [`4aae0558`](https://github.com/m-shogo/memories-project/commit/4aae0558ed8365ac7a2522a5ef7b3bed5b1ba092) adds a read-only exact skip-site count guard (0/2) for the two focused test files. Three nested negatives reject an added route skip, an unrelated live-file skip, and a removed password skip. It is lexical and does not establish a complete transitive call graph.
- **Retry condition:** Any legitimate skip addition/removal requires review of selected test execution, conditional helper preconditions, exact-source CI and protected authorities. Do not narrow the Upload Route triggers on the basis of this inventory.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40951903025](https://github.com/m-shogo/memories-project/actions/runs/40951903025) completed **SUCCESS** on exact source `4aae0558ed8365ac7a2522a5ef7b3bed5b1ba092`. Logs show append-only PASS, 201 printed fail-closed cases, 1,186 helper-ancestor negative mutations, and successful read-only completion. The three new nested skip negatives are not included in the printed 201.
- **Why safe:** Only the read-only negative validator changed (+38 lines). No Go source, workflow YAML, production evidence, traffic, credentials, generation/objective, recovery, eight-domain, review or promotion authority changed.
- **Reusable mechanism:** Pair known-helper precondition guards with an independent selected-file skip-site inventory; keep static inspection distinct from actual integration execution.
- **Protected-authority check:** Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remain unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and all separate objective/request/evidence/eight-domain/review/promotion gates unsatisfied.

## Newly discovered scoped blocker — source-change trigger reachability

- **Symptom:** A Go-only edit to either selected test source file does not itself trigger `Autonomous Learning Guard`, even though the new checks run when its Python negative validator changes.
- **Observed evidence:** The current `.github/workflows/autonomous-learning-guard.yml` push/PR path filters include `scripts/validate-autonomous-learning-system-negative.py` but do not include `services/import-api/internal/httpserver/**`. The Upload Route workflows do include the Go directory, but do not invoke the new Python negative validator; their known Quay MinIO HTTP 401 occurs before their own rollback validation. Therefore **exact-source CI success here proves guard execution on validator changes, not automatic enforcement on Go-only drift**.
- **Verified root cause:** The guard's source dependencies and its workflow trigger path filter are not aligned. This is separate from the previously known incomplete Go/Python transitive input closure.
- **Failed approach:** Treating CI execution on a validator-only commit as proof that the guard runs on every change to its guarded source files.
- **Correction / recurrence guard:** Record this coverage limitation explicitly; retain the existing source-drift checks and avoid false claims of automatic enforcement. No workflow YAML was changed because the previously recorded workflow-write permission blocker has not changed. The next safe work is a read-only audit of an existing authorized CI entrypoint that already triggers on `services/import-api/**` and can execute these checks before external MinIO setup, or a separately approved workflow-trigger correction.
- **Retry condition:** Retry workflow edits only after the required workflow-write permission/approval is actually available, or use an independently verified CI-reachable entrypoint without changing protected workflow authority. Do not retry the unchanged MinIO 401.

## Next safe target

Find a source-change-triggered, pre-MinIO, permission-safe execution path for focused Go test discoverability and skip checks. The 109 reviewed static inputs and at least 81 uncovered Upload Route trigger inputs per workflow remain lower bounds; complete transitive closure is not proven.
