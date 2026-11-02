# Supplemental OPS learning — 221-workflow source-derived lexical writer guard (2026-11-02)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is diagnostic source evidence, not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material inventory gap / executable correction

- **symptom:** A seven-entry named writer-CAS classifier omitted many workflows with lexical write/push signals. A 40-source sample had found 37 unclassified; a full source read expanded the scoped observation.
- **evidence:** At immutable `so` commit `84c8b665`, all 221 `.github/workflows` sources were fetched. Exactly 104 contained a `contents: write` line or `git push` token (in this snapshot all 104 had both); seven are named writer-CAS and one is known external-blocked, leaving 96 unclassified lexical signals. This is **not** effective YAML permission, trigger-overlap or workflow-call proof.
- **rootCauseOrUnknown:** Verified incomplete finite name classifier; semantic permission resolution and actual write reachability remain unknown.
- **failedApproach:** Treating a bounded name list or direct trigger count as a complete writer-permission inventory.
- **correction:** [`554cd0ee`](https://github.com/m-shogo/memories-project/commit/554cd0ee4a0cf8eea8b90545c79156e886ba7d8d) adds `prove_source_derived_writer_inventory` to the existing read-only negative suite. It consumes the audited prewrite module's Git-index-verified, bounded, descriptor-checked workflow bytes; requires all 221 workflow sources and the exact sorted 104-name lexical writer inventory; reconciles seven known writer-CAS, one external-blocked and 96 unclassified signal names. No source is classified as authorized by absence of a marker.
- **recurrenceGuard:** Six executable membership mutations reject omitted, added, substituted, duplicated, reordered and wrong-type inventory entries. Diagnostic risk checks preserve `BLOCKED_UNREVIEWED_WRITER_SIGNAL` for unclassified names and `UNKNOWN_NOT_AUTHORIZED` for no observed lexical signal. Existing `Autonomous Learning Guard` invokes the negative suite on exact clean `so` source.
- **retryCondition:** Update the exact inventory only after reviewing changed workflow source identity and CI reachability. Do not treat the inventory as a permission grant or production evidence.

## Material implementation failure / immediate correction

- **symptom:** The first generated Python raw-string regex contained double-escaped `\\s` and `\\b`, which would miss ordinary lexical writer markers.
- **evidence:** GitHub source re-read after `554cd0ee` showed `r"(?m)^\\\\s*contents..."` and `r"\\\\bgit..."` in the generated source. The initial CI [#41436241471](https://github.com/m-shogo/memories-project/actions/runs/41436241471) had started but no runtime outcome was claimed at correction time.
- **rootCauseOrUnknown:** Verified JavaScript-to-Python raw-string escaping error during source generation, not a verified malicious workflow or production defect.
- **failedApproach:** Generating raw Python regex strings with a second backslash-escaping layer and trusting visual intent without re-reading exact source.
- **correction:** [`01d5fcaa`](https://github.com/m-shogo/memories-project/commit/01d5fcaaf1615ac04db2546b435a733f47bf2974) fixes the regex spelling and adds executable positive/negative marker fixtures. Isolated Python regex checks matched both positive fixtures and rejected the read-only fixture.
- **recurrenceGuard:** Source re-read plus executable `has_writer_signal` controls now detect recurrence of double-escaped raw patterns before accepting the full inventory.
- **retryCondition:** Revisit only if marker grammar changes or exact-source CI exposes another verified discrepancy; do not repeat the known double-escaping pattern.

## Observed safe progress

- **outcome:** Both code commits and exact diffs were verified; the corrected exact-source [Autonomous Learning Guard #41436284979](https://github.com/m-shogo/memories-project/actions/runs/41436284979) was queued when this record was written, so full CI SUCCESS is **not** claimed.
- **evidence:** GitHub diff of `554cd0ee...01d5fcaa` shows only the negative suite's regex/fixtures changed. All 104 reviewed names are sorted and unique; source-derived inventory compares exact names, not just a count.
- **whySafe:** Read-only negative suite and diagnostic classification only; no workflow permission, publisher, protected registry, production evidence, credential, traffic, readiness or promotion change.
- **reusableMechanism:** Snapshot all workflow sources through a verified Git-index reader, pin a source-derived diagnostic name inventory, mutation-test membership and signal extraction, and explicitly keep `UNKNOWN` distinct from `SAFE`.
- **protectedAuthorityCheck:** Production `d677a1c9` (`NO_GO`), OPS-P0-007 `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d` and mandatory contract `87712ea9` remained outside the changed diff.

## Next safe target

Obtain exact-source CI outcomes for the corrected inventory and separately reviewed transcript tests. Then audit job-level YAML permissions and source-lease semantics for unclassified workflows without changing publisher paths or allowing lexical signals to promote readiness.
