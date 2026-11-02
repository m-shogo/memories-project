# Supplemental OPS learning — history-validator direct trigger gap (2026-11-02)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection coverage, independent review, final candidate or human promotion authority.

## Material scoped trigger blocker

- **symptom:** The `Autonomous Learning Guard` invokes the supplemental append-only history validator indirectly, but its Push/PR path filters do not directly include the validator's own Python source. A source-only change to that validator therefore has no demonstrated exact-source trigger through this particular read-only workflow.
- **observed evidence:** Reviewed `.github/workflows/autonomous-learning-guard.yml` blob `732d664f` does not list `scripts/validate-autonomous-learning-records-history.py`. The invoked `scripts/validate-memory-os-entry-docs.py` reads and executes/checks the supplemental history validator at blob `4856da4d`. Both source files and the workflow were read at the same `so` state. This is **scoped** to the learning guard; no repository-wide no-trigger claim is made.
- **verified root cause or unknown:** Direct event-path coverage and runtime invocation are separate conditions. Direct coverage is absent in this workflow. Alternate workflows, branch rulesets, and manual dispatch for a validator-only change are not proven by this scoped read.
- **failed approach:** Assuming that a script called transitively by a CI step is automatically in that workflow's source-change path filters.
- **correction:** Do not change the supplemental-history validator under the unchanged workflow-write permission blocker. Preserve this scoped trigger finding and continue safe independent read-only tests. This is not a claim of complete CI coverage.
- **recurrence guard:** Before any future history-validator edit, require an independently authorized exact-source read-only trigger for its path, or a separately reviewed equivalent execution route, and prove event/branch/job/permission semantics plus destructive overwrite/delete/rename negatives. Reuse the existing 2026-10-31 supplemental learning trigger-coverage blocker rather than retrying unchanged permissions.
- **retry condition:** Workflow-write authorization or an independently reviewed alternative trigger must materially change; otherwise no repeated permission attempt.

## Material safe audit success

- **outcome:** The specific transitive-validator trigger asymmetry was identified without touching any validator, workflow or protected production authority.
- **evidence:** Read-only GitHub file inspections of the workflow, entry-docs validator and supplemental-history validator. No new CI run or runtime event-delivery proof is attributed to this audit.
- **why safe:** No code or workflow execution, publisher, credential, production evidence, traffic, readiness, generation/objective, drill or human promotion was changed.
- **reusable mechanism:** Compare both the path filters of the owning workflow and its actual transitive validator call graph before claiming exact-source CI reachability.
- **protected authority check:** Ten protected blob SHA prefixes remained unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`.

## Next safe target

Confirm the corrected aggregate exact-source read-only CI, then continue inspecting independent validators and permission-safe source trigger coverage. Keep `productionDecision=NO_GO` and human promotion review separate.
