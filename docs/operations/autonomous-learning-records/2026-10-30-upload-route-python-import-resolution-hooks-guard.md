# Supplemental OPS learning — Python import resolution hook guard (2026-10-30)

Append-only supplemental history only; canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under `contracts/operations/autonomous-learning-system.json`. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure / static proof gap

- **Symptom:** A Python validator can change import resolution via `sys.path`, `sys.meta_path`, `sys.path_hooks` or `sys.path_importer_cache` while keeping the same direct import declaration SHA-256.
- **Observed evidence:** Prior AST guard rejected `sys.modules` and `from sys import modules` but not these four resolver surfaces. Read-only inspection of the four actual Upload Route Python validators found no such resolver access. This is a prospective import-resolution escape, not observed production drift.
- **Verified root cause:** Imported module-name identity does not prove import-resolution configuration is unchanged.
- **Failed approach:** Treating pinned import names and `sys.modules` reflection rejection as sufficient proof of stable module resolution.
- **Correction / executable recurrence guard:** [`42dc5330`](https://github.com/m-shogo/memories-project/commit/42dc5330e5365c35c823e78cfd9d7a51296ec835) extends the existing dynamic-dependency rejection to these four `sys` attributes and matching `from sys import ...` forms. Eight synthetic negatives cover direct mutations/access and imports; the existing benign `sys.stderr` positive control remains accepted.
- **Retry condition:** Review a legitimate import-hook change with explicit module resolution/dependency inventory, deterministic source baseline, exact-source CI and protected-authority check. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical large-learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40939804194](https://github.com/m-shogo/memories-project/actions/runs/40939804194) **SUCCESS** on exact source `42dc5330e5365c35c823e78cfd9d7a51296ec835`. Logs confirm contract PASS, 201 printed fail-closed cases, 74 fanout synthetic, 1186 helper-ancestor negatives, append-only, entry-document and read-only PASS. Eight new nested negatives are not separately counted in the printed 201.
- **Why safe:** Only the read-only negative validator changed (+12 net lines); no workflow, production source, credentials, traffic, generation/objective, reviewed requests, recovery evidence, typed eight-domain records, independent review or promotion changed.
- **Reusable mechanism:** Pin module import identity and import-resolution mechanism independently; preserve positive control for reviewed benign `sys` attributes.
- **Protected-authority check:** Post-code-commit canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and protected generation/objective/drill/evidence/non-resurrection/promotion registries remained unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations, approved current objectives, executable reviewed requests, generation evidence, complete typed eight-domain records, final candidates and human promotion remain zero. Preflight requires distinct unsuperseded semantically eligible environments and explicitly human-approved current objective; reviewed requests are planning-only, new evidence request-bound, independent review and promotion separate.

## Next safe target

Audit import resolution via Python environment variables, module `__path__`, and Go/Python toolchain input closure without changing Upload Route triggers. Keep the 109-input/81-uncovered-per-workflow inventory as a lower bound, not proof of complete closure.
