# Supplemental OPS learning — saturation source SHA provenance exact-source CI closeout (2026-11-02)

Append-only subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Synthetic tests and CI are **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection coverage, independent review, final candidate, or human promotion authority.

## Material success

- **outcome:** Corrected original-run SHA provenance guard on code HEAD [`7157d6db`](https://github.com/m-shogo/memories-project/commit/7157d6dbe790f63a975113fa0444641834e047f9) passed its exact-source read-only workflow.
- **observed evidence:** [Autonomous Learning Guard #41452152725](https://github.com/m-shogo/memories-project/actions/runs/41452152725) completed `SUCCESS` with matching `head_sha=7157d6dbe790f63a975113fa0444641834e047f9`. The source-derived local semantic control accepted the reviewed saturation publisher and rejected eight SHA-rebinding/removal mutants. Prior CI [#41451915606](https://github.com/m-shogo/memories-project/actions/runs/41451915606) and [#41452104661](https://github.com/m-shogo/memories-project/actions/runs/41452104661) completed `FAILURE`, not success; their separate failure record explains the 10-vs-12-space and substring-overlap errors.
- **why safe:** The only executable code change was to `scripts/validate-autonomous-learning-system-negative.py`; the read-only CI workflow runs `contents: read` with credentials disabled at checkout. No write-capable publisher workflow or real source-bound evidence was modified or executed.
- **reusable mechanism:** Bind `source_sha` to the original `GITHUB_SHA`, reject later reassignment and dynamic shell rebinding, enforce post-rebase guard adjacency, and use complete-line indentation comparisons. Require an exact-source CI success after mutation controls and after correcting fixture mistakes.
- **protected authority check:** Re-read of `so` after the successful code commit confirmed unchanged protected blob SHA prefixes: production status `d677a1c9` (`NO_GO`), OPS-P0-007 `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, contract `87712ea9`.

## Scope and next safe target

The later read-only learning CI source-binding and three-soak critical-path inventory code commits require their own exact-source CI results; this earlier success is not a substitute. The three soak publishers still lack an executable post-rebase source/ancestry guard. The unchanged workflow-write permission blocker was not retried. Keep `productionDecision=NO_GO` and separate human promotion review.
