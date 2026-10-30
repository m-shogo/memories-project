# Supplemental OPS learning — prewrite target symlink aliases (2026-10-30)

Append-only supplemental history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy: `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective target alias bypass

- **Symptom:** The prewrite workflow fanout audit checked the workflow directory and workflow files for symlinks, but not the repository-relative target path being audited. A symlinked leaf or ancestor could make the displayed path identity differ from the underlying target. This was a prospective prewrite safety gap, not an observed production mutation.
- **Observed evidence:** Source review of the previous `matching_workflows` showed `validate_relative_path` followed immediately by checks of `.github/workflows`, with no symlink check for `repo_root / relative`. The new tests construct both a symlinked target file and a symlinked parent directory, plus a missing prospective file positive control.
- **Verified root cause:** Workflow-source symlink protection does not establish the identity of the separate requested target path.
- **Failed approach:** Inferring safe target-path identity from a valid relative string and a nonsymlinked workflow directory.
- **Correction / executable recurrence guard:** [`7e260d12`](https://github.com/m-shogo/memories-project/commit/7e260d12cc29a82ea69851d637f88c8e82f1f516) rejects symlinked target leaves and ancestors before matching workflows, while retaining support for absent prospective target files. The self-test checks one missing-target positive and two alias negatives; the actual CLI verifies both alias negatives with exact stderr, exit status and no stdout.
- **Retry condition:** Any legitimate symlink-path exception requires reviewed target identity/escape semantics, exact CLI positive/negative controls, exact-source CI and protected-authority verification. Do not retry unchanged MinIO 401, workflow-write permission, canonical learning transport or human-promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40989086832](https://github.com/m-shogo/memories-project/actions/runs/40989086832) completed **SUCCESS** for exact code source `7e260d12cc29a82ea69851d637f88c8e82f1f516`. Logs confirm append-only PASS, learning contract PASS, **410 fail-closed negatives**, **103 prewrite fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and read-only completion.
- **Why safe:** Only two CI-reachable read-only Python validators changed. No workflow YAML, production service, credentials, traffic, readiness, generation/objective, drill, recovery evidence, typed eight-domain record, independent review or human promotion was changed.
- **Reusable mechanism:** Validate both the authority being inspected and the requested target's complete ancestor chain for symlink aliases; do not force target existence for prospective changes.
- **Protected-authority check:** Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, and generation/objective/drill/evidence/non-resurrection/promotion registries remain unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0; no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Limits and next safe target

The audit remains a conservative direct trigger approximation, not proof of transitive Go/Python dependency closure. Upload Route Go-only focused tests still lack a verified MinIO-independent workflow path; workflow write permission and external MinIO 401 remain scoped blockers. Next: audit target-path hardlink and checkout identity boundaries, then revisit a CI-reachable Go-source focused test route without relaxing OPS-P0-007 or human promotion gates.
