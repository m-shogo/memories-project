# Supplemental OPS learning — reject control-character prewrite fanout paths (2026-10-29)

Append-only supplemental learning only; canonical learning authority `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory contract `contracts/operations/autonomous-learning-system.json` remain separate. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent review or human-promotion evidence.

## Material failure / ambiguous path grammar

- **Symptom:** The prewrite fanout path validator rejected absolute paths, backslashes and unsafe dot segments but accepted control characters such as newline, tab, NUL, DEL and C1 controls in a repository-relative path. Such input can confuse logs, CLI boundaries or path identity assertions.
- **Observed evidence:** The original `validate_relative_path` predicate contained no control-character test. The reviewed path grammar allowed `scripts/a\nb.py` and `scripts/a\x00b.py` through its string-level checks. This was a static validation gap, not an observed malicious path or production incident.
- **Verified root cause:** Safety validation was limited to separators and path components, not the lexical character set of a prewrite audit argument.
- **Failed approach:** Assuming repository-relative shape alone was sufficient to make a path unambiguous for deterministic audit diagnostics.
- **Correction / executable recurrence guard:** [`5afe4a77`](https://github.com/m-shogo/memories-project/commit/5afe4a77591e1696a0b32b4451e001c01f3393b1) rejects C0/C1 control code points. Five in-process negatives cover newline, tab, NUL, DEL and U+0085; three actual CLI negatives require exact exit-1 diagnostics for newline, tab and DEL.
- **Retry condition:** Revisit only if supported Git path grammar or CLI encoding requirements change, with isolated positive/negative controls and exact-source CI. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical learning large-append transport or human-promotion blockers.

## Material success

- **Observed outcome / evidence:** [Autonomous Learning Guard #40898497037](https://github.com/m-shogo/memories-project/actions/runs/40898497037) completed SUCCESS on exact source `5afe4a77591e1696a0b32b4451e001c01f3393b1`. Logs confirm **165** fail-closed learning negatives, **38** prewrite fanout synthetic cases, entrypoint document validation PASS, clean-source/append-only checks PASS, and unchanged conservative direct match counts of 88 operability / 3 rate-limit.
- **Why safe:** Only the read-only prewrite auditor and CI-bound negative validator changed; no workflow YAML, external service, credentials, traffic, recovery evidence or promotion authority was modified.
- **Reusable mechanism:** Treat control-character path input as an explicit invalid class and verify the actual CLI's exit code and exact diagnostic, rather than trusting string-shape checks alone.
- **Protected-authority check:** Production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `NO_GO`; canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` are unchanged. No registered/eligible generation, human-approved objective, executable reviewed request, generation-bound evidence, complete typed eight-domain record, final candidate or human promotion was admitted.

## Next safe target

Bound per-workflow source bytes and invalid UTF-8 handling in the read-only fanout audit; preserve fail-closed diagnostics without modifying production workflow event filters.
