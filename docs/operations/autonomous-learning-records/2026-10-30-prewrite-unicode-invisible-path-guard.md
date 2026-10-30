# Supplemental OPS learning — invisible Unicode prewrite paths (2026-10-30)

Append-only supplemental learning only; canonical authority `docs/operations/AUTONOMOUS-OPS-LEARNING.md`, mandatory contract `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed executable request, request-bound recovery, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure — prospective path-identity ambiguity

- **Symptom:** The prewrite workflow-fanout CLI accepted repository-relative paths containing invisible Unicode format controls or non-ASCII line separators. Such input could make a displayed file identity differ from the bytes being audited. This is a prospective review/diagnostic ambiguity, not an observed production change.
- **Observed evidence:** The prior `validate_relative_path` rejected ASCII/C1 control code points but did not check Unicode category `Cf`, `Cs`, `Zl` or `Zp`. Python `unicodedata.category` classifies U+202E as `Cf`, U+200D as `Cf`, and U+2028 as `Zl`; ordinary Japanese characters remain printable letters.
- **Verified root cause:** A numeric C0/C1-only filter does not cover non-ASCII invisible formatting or line separators.
- **Failed approach:** Treating rejection of tabs, NUL, DEL and C1 controls as complete protection against visually ambiguous repository paths.
- **Correction / executable recurrence guard:** [`7dcc5b8f`](https://github.com/m-shogo/memories-project/commit/7dcc5b8fb78a1156babc80c08bc7b8b7e7ccc4be) extends the read-only prewrite path validator to reject Unicode categories `Cf`, `Cs`, `Zl`, `Zp`. Three new internal and real CLI negative controls reject bidi override, zero-width joiner and Unicode line separator. A positive control keeps `docs/日本語.md` valid. Existing control-character negatives remain intact.
- **Retry condition:** A legitimate Unicode path policy change requires reviewed byte-level path semantics, positive international filename controls, exact CLI negatives, exact-source CI and protected-authority verification. Do not retry unchanged MinIO 401, workflow-write permission, canonical large-learning transfer or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40988477575](https://github.com/m-shogo/memories-project/actions/runs/40988477575) completed **SUCCESS** on exact code source `7dcc5b8fb78a1156babc80c08bc7b8b7e7ccc4be`. Logs confirm append-only PASS, learning contract PASS, **404 fail-closed negatives**, **96 prewrite fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and final read-only success.
- **Why safe:** Only two CI-reachable read-only Python validators changed. No real workflow, production service, credentials, traffic, readiness, generation/objective, reviewed request, recovery evidence, typed eight-domain record, independent review or promotion gate was changed.
- **Reusable mechanism:** Validate Unicode character categories at an untrusted path boundary, while retaining explicit international filename positive controls.
- **Protected-authority check:** Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, and generation/objective/drill/evidence/non-resurrection/promotion registries remain unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0; no approved recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Limits and next safe target

Direct workflow matching remains an over-approximation, not a transitive CI proof. Upload Route Go-only MinIO-independent focused-test execution remains unresolved because workflow source writes are permission-scoped and the current job starts MinIO first. Next: investigate Unicode YAML source line-separator ambiguity in the prewrite audit and the Go/Python trigger closure without changing production gates or blocked workflow YAML.
