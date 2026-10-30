# Supplemental OPS learning — prewrite nested repository root identity (2026-10-30)

Append-only supplemental history only; canonical authority `docs/operations/AUTONOMOUS-OPS-LEARNING.md`, mandatory contract `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective nested checkout root substitution

- **Symptom:** A caller could pass a subdirectory of another Git checkout as `--repo-root`, with its own copied `.github/workflows`, and receive a bounded direct-trigger result without proving checkout-root ownership. This is a prospective prewrite audit risk, not an observed production incident.
- **Observed evidence:** Before `cdaa559f`, the audit rejected symlink aliases, hardlinks, submodule configuration and target-path nested Git markers, but did not inspect Git metadata in ancestors above `repo_root`. A disposable fixture with `parent/.git` and `parent/repo/.github/workflows` reproduces the ambiguous root.
- **Verified root cause:** Target-path checks cannot prove that a caller-supplied repository root is not itself nested under another Git checkout.
- **Failed approach:** Treating an existing workflow directory under an arbitrary `--repo-root` as sufficient repository-root identity.
- **Correction:** [`cdaa559f`](https://github.com/m-shogo/memories-project/commit/cdaa559f5e3257980d4a41a5c5e76ac3678f00f6) conservatively rejects `.git` metadata in any ancestor above `repo_root`; the root's own `.git` remains allowed.
- **Executable recurrence guard:** The read-only self-test and actual CLI negative validator create a parent `.git` fixture and require the exact `prewrite repository root nested under Git checkout` rejection. The existing ordinary root `.git` positive, `.gitmodules` and nested target Git negatives remain intact.
- **Retry condition:** A legitimate nested checkout requires independently verified `git rev-parse --show-toplevel`, Gitlink ownership and checkout-root source binding, reviewed positive/negative fixtures, exact-source CI and protected-authority verification. Do not retry unchanged external MinIO, workflow-write permission, canonical learning transfer or human-promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40991575641](https://github.com/m-shogo/memories-project/actions/runs/40991575641) completed **SUCCESS** on exact code SHA `cdaa559f5e3257980d4a41a5c5e76ac3678f00f6`. Logs confirm append-only PASS, learning contract PASS, 411 canonical fail-closed negatives, 104 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document PASS and read-only completion.
- **Why safe:** Only two read-only Python validators changed. The negative validator is directly included in the existing CI trigger; no production, workflow YAML, credentials, traffic, readiness, generation/objective, drill, recovery evidence, typed eight-domain review or promotion authority changed.
- **Reusable mechanism:** Distinguish the legitimate root Git metadata from an ancestor checkout's metadata before accepting a direct-path audit. This remains a conservative source-path check, not full Git index or Go/Python transitive closure proof.
- **Protected-authority check:** The code commit changed only `scripts/audit-memory-os-workflow-trigger-fanout.py` and `scripts/validate-autonomous-learning-system-negative.py`; the previously verified protected 10 blob identities remain the reference: canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED`.

## Limits and next safe target

The direct `Autonomous Learning Guard` push/PR path filters still omit the audit script itself; the paired negative-validator modification ensured this exact-source CI ran. The Go-only Upload Route focused tests remain MinIO-coupled. Next: audit nested Git metadata on the workflow-directory side, then the reviewed Go/Python transitive trigger closure; workflow edits require changed permissions and complete CI reachability evidence.
