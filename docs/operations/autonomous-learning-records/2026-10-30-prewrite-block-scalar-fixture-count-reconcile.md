# Supplemental OPS learning — block scalar events and fixture-count reconciliation (2026-10-30)

Append-only supplemental history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure — prospective block-scalar event undercount

- **Symptom:** Valid YAML such as `on:\n  push`, `on:\n  "p\\u0075sh"`, and `on:\n  *events` could be treated as dispatch-only by the prewrite matcher. This is a prospective source-analysis defect, not an observed production incident.
- **Observed evidence:** PyYAML 6.0.3 parsed the three sample forms as scalar or aliased event values; the reviewed source only recognized block event mappings and sequences. Focused local regex controls covered scalar, escaped, alias, comment and blank-line variants.
- **Verified root cause:** The narrow event-map parser did not model scalar or alias values on the next indented row after `on:`, especially after comment-only headers.
- **Failed approach:** Assuming `on:` with no literal nested `push:` mapping is necessarily non-triggering.
- **Correction:** [`422fe088`](https://github.com/m-shogo/memories-project/commit/422fe0881485919074dee6970fb22003097dd4aa) adds conservative block-scalar/alias detection, retaining negative controls for dispatch-only mappings and lists.
- **Executable recurrence guard:** Ten ordered identity-pinned cases run through both the in-process self-test and actual prewrite CLI. Scalar dispatch-only values may be conservatively counted; this is not a production or workflow-dispatch assertion.
- **Retry condition:** Revisit only with a reviewed YAML semantics proof or an exact-source counterexample; never relax to a silent non-match for unrecognized event-value syntax.

## Material failure — fixture counts omitted newly executed controls

- **Symptom:** [CI #41002287200](https://github.com/m-shogo/memories-project/actions/runs/41002287200) reported 112 fanout synthetic cases and 419 canonical fail-closed negatives despite eight newly executed multiline-flow cases in each suite.
- **Observed evidence:** Both count expressions in the reviewed Python source omitted `len(multiline_flow_cases)`, although the test loops ran. This was a reporting/inventory defect, not evidence of missing execution.
- **Verified root cause:** Hand-maintained aggregate counts were not updated when a new fixture group was inserted.
- **Failed approach:** Appending executed fixture groups while leaving the synthetic/CLI total expressions unchanged.
- **Correction:** [`422fe088`](https://github.com/m-shogo/memories-project/commit/422fe0881485919074dee6970fb22003097dd4aa) adds both `len(multiline_flow_cases)` and `len(block_scalar_cases)` to the reported totals.
- **Executable recurrence guard:** Both suites preserve exact ordered fixture identities and execute actual CLI positive/negative cases; count expressions now enumerate the new groups. This is bounded correction, not a general proof that future unlisted groups cannot be omitted.
- **Retry condition:** If a future group is added, reconcile the executed group inventory and reported totals before accepting the CI count; do not equate a successful CI job with exact inventory accounting absent that reconciliation.

## Material success — corrected code and CI

- **Observed outcome/evidence:** Exact-source [Autonomous Learning Guard #41002576427](https://github.com/m-shogo/memories-project/actions/runs/41002576427) completed SUCCESS for `422fe0881485919074dee6970fb22003097dd4aa`. Job logs show 437 canonical fail-closed negatives, 130 fanout synthetic cases, 1,186 helper-ancestor negative mutations, learning contract, append-only, entry-doc and read-only PASS. The audited shared entrypoint still has nine direct workflow matches and is classified `BLOCKED_KNOWN_WRITER_CAS`.
- **Why safe:** The only code changes are read-only Python guard and test files. No workflow YAML, writer, credential, traffic, environment generation, recovery objective, reviewed drill request, production evidence, non-resurrection record or human promotion authority was created or modified.
- **Reusable mechanism:** Conservative block scalar/alias trigger matching plus paired real CLI/in-process fixtures and explicit aggregate count reconciliation, validated at an immutable exact source SHA.
- **Protected-authority check:** Git tree comparisons show all ten protected authority Blob SHAs unchanged from `e10e2710` through `422fe088`: production status `55b3e639`, canonical learning `b809c69d`, contract `87712ea9`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered and preflight-eligible generations remain 0/0, with no current approved recovery objective or separate human promotion decision.

## Limits and next safe target

The large canonical learning file remains inaccessible as full text through this connector; its SHA was read and unchanged, and these new records are supplemental append-only history, never production evidence. Full production admission chain on the eventual learning-only HEAD is not established by code-only CI. The next independent safe targets remain Go-only focused test reachability before MinIO startup and exact Go/Python transitive input/trigger closure. No unchanged external MinIO, workflow-write, large canonical learning or human-approval blocker was retried.
