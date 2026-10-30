# Supplemental OPS learning — parsed Go imports of compiled httpapi peers (2026-10-31)

Append-only supplemental learning only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy is `contracts/operations/autonomous-learning-system.json`. This cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective/request, typed eight-domain non-resurrection, independent-review or human-promotion gates.

## Material static-proof gap

- **symptom:** The scoped Upload Route CI classification verified five non-test `httpapi` peer package declarations but did not bind their actual compiled import edges. Quoted path text in comments could otherwise be mistaken for an executable peer dependency in a future source-only proof.
- **evidence:** Current peer source reads show `apple_handler.go -> appleauth`, `apply_handler.go -> apply/security`, `fence_error.go -> epochguard`, and `preview_handler.go -> previewread/security`. Each of these six reviewed quoted import anchors occurs exactly once. The focused Upload Route Push/PR workflows trigger on `httpserver/**` and `httpapi/upload_handler.go`, not these peer source paths. The broad Import API Security Slice matches `services/import-api/**` but starts MinIO before Go tests. This is a scoped static-proof omission, not a production failure or proof that no other workflow matches.
- **rootCauseOrUnknown:** Verified scoped graph gap: package declaration identity does not establish the transitive imports of other compiled package files.
- **failedApproach:** Assuming a directly triggered `upload_handler.go` and verified `package httpapi` peer declarations prove the complete imported package closure.
- **correction:** [Code commit 8db2998c](https://github.com/m-shogo/memories-project/commit/8db2998cbcde3232bfd0dc54e47fc448e792f148) adds parsed import-edge checks for the six peer edges inside the existing CI-bound read-only validator.
- **recurrenceGuard:** Six deterministic comment-spoof negatives replace each executable import with an unreviewed path while leaving the old quoted path in a comment. Each must fail the parsed edge check; current source files are positives. No extra subprocesses or workflow edits were introduced.
- **retryCondition:** Any legitimate peer import, package or source-path change requires reviewed transitive graph and Push/PR trigger reconciliation, negative/positive controls, exact-source CI and protected-authority parity. Do not repeat unchanged MinIO HTTP 401, workflow-write or canonical learning full-file transport blockers.

## Observed bounded success and CI boundary

- **outcome/evidence:** Only `scripts/validate-autonomous-learning-system-negative.py` changed (+31 lines), published to `so` at `8db2998c` with a CAS ref update. Six current import anchors and package identities were verified read-only before the write. **Exact-source CI outcome for this commit remains unconfirmed** at record creation.
- **whySafe:** No Go production/test code, workflow YAML, external MinIO, credential, traffic, production readiness, recovery generation/objective/request/evidence, typed eight-domain review or promotion was modified or executed.
- **reusableMechanism:** Bind each compiled peer import to a parsed source edge and a spoof-negative, then classify actual workflow path triggers separately from source graph reachability.
- **protectedAuthorityCheck:** Ten protected authority blobs matched the parent: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, and no human-approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review, final candidate or human promotion.

## Next safe target

Observe the exact-source Autonomous Learning Guard run to terminal state and append a separate verified CI proof. Continue the imported `appleauth`, `apply` and `previewread` source and Push/PR trigger closure audit without treating the MinIO-first broad workflow as independent pre-MinIO regression evidence.
