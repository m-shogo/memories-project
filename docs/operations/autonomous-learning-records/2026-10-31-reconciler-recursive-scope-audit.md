# Supplemental OPS learning — bounded audit of reconciler recursive scopes (2026-10-31)

Append-only operational learning only. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material tool failure

- **symptom:** A single source-inspection orchestration requested 24 GitHub file reads and failed before returning its results.
- **evidence:** The connector reported `Code Mode exceeded the maximum number of tool calls`. No repository write was requested by that failed orchestration, and the branch was subsequently read independently.
- **rootCauseOrUnknown:** Verified: the attempted batch exceeded the execution's available tool-call budget. The exact connector-side maximum and whether partial reads completed are unknown; no partial result was treated as verified.
- **failedApproach:** Unbounded multi-file fetch orchestration for a large reconciler inventory.
- **correction:** Reduced to bounded batches of eight file reads, each with per-file result/error handling and source-only extraction of traversal calls.
- **recurrenceGuard:** Cap similar source-audit batches at eight calls and emit the paths inspected, rather than assuming a failed large batch completed. Keep all Git writes separate from read-audit batches.
- **retryCondition:** Revisit the batch limit only after documented connector capacity changes; otherwise use the proven eight-at-a-time pattern. Do not retry unchanged external MinIO HTTP 401, workflow-write permission or human approval blockers.

## Material safe audit success

- **outcome:** Completed a read-only source survey of all **91** `scripts/reconcile-memory-os-*.py` files present on branch `so`. The Upload Route reconciler was the only reviewed script with a broad `Path.rglob("*")` authority scan. The other 90 did not contain the surveyed broad recursive traversal patterns.
- **evidence:** The 91-file inventory came from the exact Git tree; each file was fetched in bounded batches and scanned for `rglob(`, `os.walk`, `Path.walk`, `glob(`, and related broad docs-rewrite/snapshot patterns. Three limited `glob` cases were separately inspected: `reconcile-memory-os-incident-human-tabletops.py` enumerates `LEDGER.glob("IR-DRILL-*.json")`, `reconcile-memory-os-migration-recovery-result-orphans.py` enumerates `RESULT_ROOT.glob("mig_*.json")`, and `reconcile-memory-os-sustained-local-soak-status.py` enumerates `RESULT_DIR.glob(RESULT_GLOB)`. None of those observed glob expressions targets append-only learning. This is a **source-pattern audit**, not a formal proof against dynamic imports, indirect helpers, runtime path aliasing or every possible write.
- **whySafe:** Read-only GitHub source inspection only; no reconciler was executed against real authority, and no production/recovery registry, credentials, traffic, readiness, promotion or historical learning file was mutated.
- **reusableMechanism:** First inventory every script from the current Git tree; batch bounded reads; distinguish broad recursive authority rewrites from narrowly scoped evidence/ledger enumeration; inspect each exceptional glob in context. Escalate to AST/dataflow or runtime sandbox proof only when a new write-bearing traversal is found.
- **protectedAuthorityCheck:** The ten protected authority blob SHAs were unchanged at the prior code-success HEAD `9ff46b4a` and the subsequent append-only learning HEAD `ac64fe14`; canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, and six protected generation/objective/request/evidence/non-resurrection/promotion registries remained unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0 and all human-approved objective, executable reviewed request, request-bound evidence, typed eight-domain coverage, final candidate and promotion gates unfulfilled.
- **CI limitation:** No code changed in this audit, and supplemental learning-only commits are not independently proven to trigger a Push/PR learning guard. The last code HEAD `9ff46b4a` has [exact-source Autonomous Learning Guard SUCCESS #41168310972](https://github.com/m-shogo/memories-project/actions/runs/41168310972); no CI success is asserted for this record-only commit.

## Next safe target

Review bounded rollback/restore paths for symlink and concurrent-write protection, and audit whether any non-`reconcile-memory-os-*.py` writer can indirectly rewrite append-only learning. Keep the separate MinIO and supplemental-learning Push/PR workflow blockers scoped and unchanged.
