# Supplemental OPS learning — prewrite fanout DOTALL blank-row and stdout contract recovery (2026-10-29)

Append-only supplemental learning only. Canonical authority `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract `contracts/operations/autonomous-learning-system.json`. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, recovery generation/objective, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure A — strict CI stdout contract

- **Symptom:** [Autonomous Learning Guard #40896728832](https://github.com/m-shogo/memories-project/actions/runs/40896728832) FAILED even though its negative validator returned exit 0 with 156 passing fail-closed cases.
- **Observed evidence:** The entrypoint reported `autonomous-learning guard missing verified PASS: scripts/validate-autonomous-learning-system-negative.py (exit 0)`. The new negative validator had printed a diagnostic sample before its final PASS marker.
- **Verified root cause:** `scripts/validate-memory-os-entry-docs.py` requires the child validator's entire stdout to be exactly the single canonical `Autonomous learning negative validation PASS (N fail-closed cases)` line; extra diagnostic stdout invalidates the success classifier.
- **Failed approach:** Printing diagnostic workflow names from the canonical negative-validator process while expecting the entrypoint to accept its final PASS line.
- **Correction / recurrence guard:** [`72ddf3ff`](https://github.com/m-shogo/memories-project/commit/72ddf3ff77f8ff8358de16fc7c7a75ff169769da) removed extra stdout but preserved the executable real-CLI count/identity check. The preexisting entrypoint exact-output classifier now enforces the boundary. [Autonomous Learning Guard #40896912435](https://github.com/m-shogo/memories-project/actions/runs/40896912435) completed SUCCESS.
- **Retry condition:** Add any future diagnostics through a separately authorized reporting channel, never through the exact-output guard stdout; test the complete entrypoint before declaring CI success.

## Material failure B — conservative fanout count inflation

- **Symptom:** After the ambiguity guard, the read-only fanout audit reported 151 possible operability matches and 68 possible rate-limit matches, up from 88 and 3 respectively. The added possible matches included unrelated source-negative workflows.
- **Observed evidence:** [CI #40895701639](https://github.com/m-shogo/memories-project/actions/runs/40895701639) and [CI #40896379162](https://github.com/m-shogo/memories-project/actions/runs/40896379162) logged 151/68. An isolated Python reproduction using a normal workflow event block with an unrelated `paths:` list and a blank line before the next event returned a false positive. The traced return occurred at `if not pattern: return True` with `row == ''`.
- **Verified root cause:** The old `(?ms)` path-list regex used DOTALL `.*`, greedily absorbing trailing blank lines. `splitlines()` then produced an empty row, which the new conservative parser classified as an ambiguous empty path. The false positives were not evidence of new GitHub Actions trigger reachability.
- **Failed approach:** Combining DOTALL wildcard list extraction with a fail-closed empty-row rule without distinguishing ordinary YAML blank lines from actual list entries.
- **Correction / executable recurrence guard:** [`35daee6d`](https://github.com/m-shogo/memories-project/commit/35daee6de1cfc8834eb090a28448f1f868eb1231) scans the bounded event tail line by line, ignores blank/comment rows, requires explicit list items, and rejects unreviewed trailing mappings. Three synthetic cases cover blank-after-unrelated, blank-within-matching and trailing mapping; two real CLI fixtures cover the blank-line boundary.
- **Retry condition:** Revisit parser scope only after a new concrete false-positive/false-negative fixture or reviewed workflow grammar change. Never narrow a production workflow trigger from a conservative prewrite estimate alone.

## Material success

- **Observed outcome / evidence:** [Autonomous Learning Guard #40897191458](https://github.com/m-shogo/memories-project/actions/runs/40897191458) completed SUCCESS on exact source `35daee6de1cfc8834eb090a28448f1f868eb1231`. Logs confirm **158** fail-closed learning negative cases, **27** prewrite fanout synthetic cases, entrypoint document validation PASS, clean-source/append-only checks PASS. The audited counts returned to **88** operability and **3** rate-limit possible direct matches.
- **Why safe:** All code changes were limited to the read-only prewrite auditor and CI-bound negative validator. No workflow trigger, MinIO external dependency, production authority, credentials, traffic, recovery evidence or human promotion was changed.
- **Reusable mechanism:** Diagnose unexpected conservative count changes with an isolated actual-source reproduction and line-level return evidence; require exact single-line success output when another guard verifies the child's stdout.
- **Protected-authority check:** Production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `NO_GO`; canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` are unchanged. No registered/eligible generations, human-approved current recovery objective, executable reviewed request, generation-bound evidence, complete typed eight-domain record, final candidate or human promotion was admitted.

## Next safe target

Audit `pull_request_target` direct event fanout separately from `pull_request`, with synthetic and actual CLI controls, while preserving the distinction between possible trigger reachability and production readiness.
