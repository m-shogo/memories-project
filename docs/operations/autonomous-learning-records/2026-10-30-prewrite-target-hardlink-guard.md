# Supplemental OPS learning — prewrite target hardlink aliases (2026-10-30)

Append-only supplemental history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective hardlink target alias

- **Symptom:** After symlink protections, a regular target file with multiple hardlink directory entries could still alias a file outside the requested repository-relative path. The prewrite audit would treat it as an independent target identity. This was a prospective local prewrite alias risk, not an observed production incident.
- **Observed evidence:** The prior `matching_workflows` rejected symlinked leaves and ancestors but did not inspect the regular target's link count. A local same-filesystem hardlink fixture has `st_nlink` greater than one; a missing prospective target remains allowable.
- **Verified root cause:** Symlink checks alone do not detect regular-file inode aliases.
- **Failed approach:** Treating `Path.is_symlink() == False` as proof that the target has a unique file identity.
- **Correction / executable recurrence guard:** [`1a8ab00c`](https://github.com/m-shogo/memories-project/commit/1a8ab00cc3039a67b03185b4f84367ab8461f7f0) rejects existing regular target files whose link count is not one, with both in-process and actual CLI hardlink negatives. Symlink leaf/ancestor negatives and the missing-target positive remain intact.
- **Retry condition:** A legitimate hardlink exception requires reviewed inode/link-count semantics, explicit alias safety proof, positive/negative CLI tests, exact-source CI and protected-authority verification. Do not retry unchanged external MinIO 401, workflow-write permission, canonical learning transfer or human-promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40989422254](https://github.com/m-shogo/memories-project/actions/runs/40989422254) completed **SUCCESS** for exact code source `1a8ab00cc3039a67b03185b4f84367ab8461f7f0`. Logs confirm append-only PASS, learning contract PASS, **411 fail-closed negatives**, **104 prewrite fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and read-only completion.
- **Why safe:** Only two CI-reachable read-only Python validators changed. No actual workflow, production code, credentials, traffic, readiness, generation/objective, drill, recovery evidence, typed eight-domain record, independent review or human promotion changed.
- **Reusable mechanism:** Verify both symlink and regular-file inode alias properties before relying on a prewrite target path identity; allow absent prospective targets without inventing a file.
- **Protected-authority check:** Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, and generation/objective/drill/evidence/non-resurrection/promotion registries remain unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Limits and next safe target

Direct trigger matching is not a complete Go/Python transitive CI dependency proof. The Go-only Upload Route focused-test path remains MinIO-coupled and workflow writes remain permission-scoped. Next: audit prewrite target-path Git submodule and repository-root identity boundaries, or establish an authorized MinIO-independent focused Go test workflow once its actual permissions and dependency closure are proven.
