# Supplemental OPS learning — bounded descriptor-pinned workflow source reads (2026-10-30)

Append-only learning, not canonical production evidence. `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. This record must never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure — prospective unbounded workflow source read

- **symptom:** The prewrite auditor checked a workflow's size with `Path.stat()` but later used unbounded `read_text()` or `read_bytes()`. If a file changed or was swapped between the preflight and read, a stale size check could not cap bytes read; a FIFO swap could block a path-based open.
- **evidence:** Source review of `scripts/audit-memory-os-workflow-trigger-fanout.py` found both unbounded readers after the size checks. A disposable local descriptor prototype exercised regular, oversized, FIFO, symlink and hardlink cases (5/5 controls). No observed production incident or malicious checkout was claimed.
- **rootCauseOrUnknown:** Verified check-then-read separation without a descriptor-bound byte limit; exact exploitability depends on concurrent filesystem mutation and is not asserted as observed.
- **failedApproach:** Treating `Path.is_file()` and `Path.stat().st_size` as sufficient guarantees for a later path-based unbounded read.
- **correction:** [3cfead7d](https://github.com/m-shogo/memories-project/commit/3cfead7d58055005831a2ca7d4002b22e4966b02) introduces `read_workflow_bytes_bounded` with nonblocking/no-follow flags when supported, descriptor `fstat` regular-file and link checks, a 256 KiB + 1 read ceiling, post-read descriptor/path identity and size/mtime checks, and reuse by strict Git-index and ordinary direct-match paths.
- **recurrenceGuard:** The CI-bound self-test exercises direct descriptor positive plus oversized, FIFO, symlink and hardlink negatives in strict/non-strict modes; the independent real CLI rejects a FIFO workflow leaf within a bounded timeout. Strict Git mode still parses only the same verified bytes compared to the index blob.
- **retryCondition:** Revisit on a verified descriptor/close fault, platform-specific no-follow limitation, source-identity race or changed workflow source grammar. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical learning transport or human-promotion blockers.

## Material success — exact-source CI

- **outcome:** [Autonomous Learning Guard #41033573858](https://github.com/m-shogo/memories-project/actions/runs/41033573858) completed **SUCCESS** on exact source `3cfead7d58055005831a2ca7d4002b22e4966b02`.
- **evidence:** Job logs confirm append-only, learning contract, executable negatives, entry-document, helper ancestor and read-only checks PASS. Counts: 509 canonical fail-closed negatives, 195 fanout synthetic cases, 1,186 helper-ancestor mutations, 52 source-negative workflows, 63 direct Python commands and 204 reachability fixtures. New descriptor/CLI controls execute inside existing suites but are not separately included in the printed 509.
- **whySafe:** Only existing read-only Python auditor and CI-reachable negative harness changed. Tests use disposable filesystem fixtures; no workflow YAML, production traffic, credential, backup/restore, generation, objective, drill, recovery evidence, non-resurrection record, independent review or promotion authority was modified.
- **reusableMechanism:** Bind filesystem source reads to a single regular-file descriptor, enforce a hard byte ceiling after open, and compare descriptor/path identity before accepting a source snapshot. Continue to distinguish local source snapshot safety from Git object provenance and complete transitive CI reachability.
- **protectedAuthorityCheck:** Ten protected blob SHAs were unchanged after the code commit: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0 and no approved recovery objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain record, final candidate or separate human promotion.

## Next safe target

Read-only audit of residual checkout identity and source-race boundaries, especially descriptor-close behavior and inherited Git object-store environment. Independently, Go-only Upload Route test CI still lacks proven pre-MinIO execution and complete Go/Python transitive trigger closure; do not change workflow YAML without verified authority.
