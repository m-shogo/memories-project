# Supplemental OPS learning — Upload Route runtime input path-alias closure (2026-10-30)

Append-only supplemental history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. Learning is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective symlink input alias

- **Symptom:** The reviewed Upload Route direct Python/operability data inputs could be replaced with symlink aliases while preserving the same path-set inventory and `is_file()` checks. Reviewed workflow YAML sources could likewise be read through a symlink before semantic validation.
- **Observed evidence:** The existing read-only dependency audit called `require_unaliased_go_path` for Go files and selected Python scripts, but twelve direct metrics/rate-limit/observability/operability input files were checked only with `is_file()`. Both Upload Route workflow sources and the Autonomous Learning Guard source were read without the same path-alias check. This is a prospective source-identity gap, not observed production tampering.
- **Verified root cause:** `Path.is_file()` follows symlinks and does not prove that the reviewed repository-relative path resolves to the same path without aliases.
- **Failed approach:** Treating path existence and a stable set of relative path names as proof of source identity.
- **Correction / executable recurrence guard:** [`34a80976`](https://github.com/m-shogo/memories-project/commit/34a80976aa57d578bb66afd51d40a2124b6d8393) reuses the existing fail-closed `require_unaliased_go_path` helper for all twelve direct data inputs, both actual workflow YAML sources and the Autonomous Learning Guard source before reading them. A new JSON-data symlink negative confirms the helper rejects non-Go file aliases. Only the CI-reachable read-only negative validator changed (+23/-4 lines).
- **Retry condition:** Any legitimate path relocation requires review of actual file and parent directory identity, updated complete input/trigger inventory, executable negative fixtures, exact-source CI and protected-authority verification. Do not weaken alias rejection to accommodate unknown external data.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40948180847](https://github.com/m-shogo/memories-project/actions/runs/40948180847) **SUCCESS** on exact source `34a80976aa57d578bb66afd51d40a2124b6d8393`. Logs confirm append-only and contract PASS, 201 printed canonical negatives, 74 fanout synthetic, entry-document PASS, 1,186 helper-ancestor negative mutations and read-only completion. The additional JSON symlink negative is nested and not separately included in the printed 201.
- **Why safe:** Only existing CI-reachable read-only validation changed; no workflow YAML, production service, traffic, credentials, readiness, recovery evidence, generation/objective, drill, typed eight-domain records, independent review or human promotion was altered.
- **Reusable mechanism:** Require no-alias path identity for all reviewed direct runtime inputs, not just source code, and validate before opening any workflow or data file.
- **Protected-authority check:** Compare shows only `scripts/validate-autonomous-learning-system-negative.py` modified. Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remain unchanged. `productionDecision=NO_GO`; registered/eligible generations 0/0, no human-approved current objective, executable reviewed request, request-bound evidence, final candidate or human promotion.

## Next safe target

Complete exact shell-body identity for the remaining Upload Route executable steps: Publisher source-SHA capture, dependency installation and focused Go regression execution. Keep actual workflow YAML unchanged; the 109 reviewed inputs and 81 uncovered trigger inputs per workflow remain lower bounds, not full closure.
