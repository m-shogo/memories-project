# Supplemental OPS learning — appleauth compiled package peer and local import closure (2026-10-31)

Append-only operational learning only. Canonical learning and its mandatory contract remain unchanged. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material source-proof gap

- **symptom:** The fourth-hop Go edge guard bound `appleauth/login.go` and `appleauth/metered.go`, but did not ensure that every other non-test source in the imported `appleauth` package had a reviewed package identity and exact local import set, nor reject newly added package peers.
- **evidence:** The current `services/import-api/internal/appleauth` non-test Go inventory contains exactly seven files: `client_secret.go`, `jwks_client.go`, `login.go`, `metered.go`, `pgstores.go`, `token_client.go` and `verifier.go`. Parsed local imports are `login.go -> security`, `metered.go -> metrics, security`, and no local imports for the other five. The `httpapi/apple_handler.go -> appleauth` edge is already reviewed. Focused Upload Route Push/PR paths omit `appleauth/**`; the broad Import API security slice starts MinIO before Go tests.
- **rootCauseOrUnknown:** Verified omission in the scoped package-peer inventory and exact local import checks. This does not prove complete Go test compilation closure or independent pre-MinIO CI reachability.
- **failedApproach:** Treating two selected Go import edges as proof that the complete imported `appleauth` package's non-test peer inventory and local dependencies cannot drift.
- **correction:** [Code commit d40883a5](https://github.com/m-shogo/memories-project/commit/d40883a50b72ca18a9f797105b11d9d18eb345b9) adds an exact seven-file non-test inventory, package identity checks for each file, and exact parsed local import-set checks.
- **recurrenceGuard:** In-process negatives reject removed and added package peers, and inject an extra unreviewed `internal/reqid` import separately into each of the seven real sources. The parser must detect the unexpected compiled dependency. No extra subprocess was added; the 120-second nested guard deadline remains unchanged.
- **retryCondition:** A real addition, removal, rename, package declaration change or local import change requires review of the package inventory, transitive dependency closure and Push/PR trigger coverage, followed by exact-source direct/nested CI and protected-authority comparison. Do not repeat unchanged workflow permission, MinIO HTTP 401 or canonical full-text transport blockers.

## Material success and authority check

- **outcome:** The `appleauth` package's current seven non-test sources and all three local import edges are now bound to a CI-executed deterministic positive/negative source proof.
- **evidence:** Exact-source [Autonomous Learning Guard #41137507734](https://github.com/m-shogo/memories-project/actions/runs/41137507734) on `d40883a50b72ca18a9f797105b11d9d18eb345b9` completed **SUCCESS** on 2026-10-31 JST. Logs show append-only PASS, learning contract PASS, **601** direct and **601** independent nested fail-closed cases, 195 fanout synthetic, 1,186 helper ancestor negative mutations, 52-workflow/63-command/204-fixture source-negative reachability, entry-document PASS and clean/read-only completion. The new in-process negatives are inside the existing suite and are not separately added to its displayed count.
- **whySafe:** Only `scripts/validate-autonomous-learning-system-negative.py` changed (+63 lines). No Go runtime/test source, workflow YAML, MinIO, credentials, traffic, recovery evidence, objective/generation, review or promotion was changed.
- **reusableMechanism:** For an imported Go package, bind exact non-test source membership and parsed local import sets, not merely selected import edges; test both missing/extra peers and an unexpected local dependency without adding subprocesses.
- **protectedAuthorityCheck:** The one-file code diff leaves all ten protected authority blobs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 remains blocked, and no human promotion authority is present. Canonical learning blob identity was checked; full-text retrieval remains unavailable.

## Next safe target

Audit the `pgrepo`, `objectstore` and `previewcommit` packages imported by the focused HTTP live-test compilation path, with exact package-peer inventories and parsed local imports. Then continue Go/Python closure and event-trigger reconciliation without workflow YAML edits.
