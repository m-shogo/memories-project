# Supplemental OPS learning — prewrite workflow-directory nested Git checkout (2026-10-30)

Append-only supplemental history only; canonical authority `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory contract `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective nested workflow source checkout

- **Symptom:** A workflow YAML under `.github/workflows` could belong to a nested Git checkout with its own `.git` metadata, yet the prewrite direct matcher previously accepted its workflow-source identity. This is a prospective read-only audit boundary, not an observed production incident.
- **Observed evidence:** Before `3ecbddae`, the matcher rejected workflow symlinks, hardlinks, submodule configuration, nested target Git metadata and nested repository roots, but did not check `.github/.git` or `.github/workflows/.git`. Disposable fixtures with gitdir-file markers exercise both locations.
- **Verified root cause:** Target-path Git ownership checks do not cover the separately enumerated workflow-source tree.
- **Failed approach:** Assuming a non-symlinked `.github/workflows` directory belongs to the parent checkout without checking nested Git metadata.
- **Correction:** [`3ecbddae`](https://github.com/m-shogo/memories-project/commit/3ecbddae411fbc2b661676bac7d78e94c224c2b8) rejects `.git` metadata under `.github` or `.github/workflows` before enumerating workflow sources.
- **Executable recurrence guard:** The read-only fanout self-test and actual CLI negative validator require exact `workflow directory nested Git checkout` diagnostics for both nested locations, with a positive fixture allowing only the repository root's own `.git`.
- **Retry condition:** An intentional nested workflow checkout requires reviewed Git index/worktree ownership, exact-source binding, positive/negative CLI controls, exact-source CI and protected-authority verification. Unchanged MinIO 401, workflow-write permission, canonical learning transfer and human-promotion blockers are not retried.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40991874264](https://github.com/m-shogo/memories-project/actions/runs/40991874264) completed **SUCCESS** on exact code SHA `3ecbddae411fbc2b661676bac7d78e94c224c2b8`. Logs confirm append-only PASS, learning contract PASS, 411 canonical fail-closed negatives, 104 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document PASS and read-only completion.
- **Why safe:** Only two read-only Python validators changed; the paired negative-validator edit triggered exact-source CI. No production implementation, workflow YAML, credentials, traffic, readiness, generation/objective, drill, recovery evidence, typed eight-domain review or promotion authority changed.
- **Reusable mechanism:** Verify Git ownership boundaries independently for the target path, repository root and workflow-source directory. These are conservative metadata guards, not a complete Git index or transitive Go/Python dependency proof.
- **Protected-authority check:** The exact code diff changes only `scripts/audit-memory-os-workflow-trigger-fanout.py` and `scripts/validate-autonomous-learning-system-negative.py`. Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, and all six protected registries remain unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED` with zero registered/eligible generations and no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Limits and next safe target

The `Autonomous Learning Guard` push/PR paths still omit the audit script itself, so guard-only edits are not guaranteed to trigger it. The Go-only Upload Route CI still starts the external Quay MinIO image before focused tests. Next: review complete Go/Python input closure and CI path-filter coverage, then add a permission-authorized MinIO-independent focused Go test entrypoint only after the actual workflow authority changes.
