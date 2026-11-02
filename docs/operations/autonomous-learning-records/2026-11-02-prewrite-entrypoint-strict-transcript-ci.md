# Supplemental OPS learning — shared entrypoint and strict prewrite CLI transcript CI (2026-11-02)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Neither learning nor synthetic CI constitutes production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure / verifier gap

- **symptom:** The shared entrypoint and strict prewrite source CLI regressions reconciled count, selected identities and risk/exit code, but could accept a correct risk/count for the wrong audited path or an incomplete/extended stdout transcript. No unsafe production action was observed.
- **evidence:** Before `1b0c4678`, `scripts/validate-autonomous-learning-system-negative.py` verified entrypoint identity set, count and risk but not the exact path header or refusal/advisory. Before `69574f9f`, the strict source audit similarly verified count, identity order and risk/exit code but not the complete transcript. `scripts/audit-memory-os-workflow-trigger-fanout.py` emits a deterministic path header, risk/count, workflow identities and risk-specific advisory.
- **rootCauseOrUnknown:** Verified verifier incompleteness; whether an adversarial CLI would have substituted output is unknown and not claimed.
- **failedApproach:** Count and risk parity without exact audited path and complete output grammar.
- **correction:** [`1b0c4678`](https://github.com/m-shogo/memories-project/commit/1b0c46782c9e919961b9e86ed2319793000e973d) adds complete entrypoint transcript reconciliation; [`69574f9f`](https://github.com/m-shogo/memories-project/commit/69574f9fa471078faeef0d98e675f83212649e10) adds exact strict source path and risk-specific advisory reconciliation.
- **recurrenceGuard:** The read-only negative suite now rejects missing/extra CLI lines, wrong audited path, duplicate or reordered workflow identities, mismatched risk/count and changed advisory in the reviewed prewrite checks.
- **retryCondition:** Revisit only when CLI grammar, direct trigger matching, audited paths, or exact-source CI changes. Do not repeat unchanged canonical-learning retrieval, MinIO HTTP 401 or human-evidence blockers.

## Observed successes

- **outcome:** Both exact-source read-only Autonomous Learning Guard runs completed SUCCESS.
- **evidence:** [Run #41431829469](https://github.com/m-shogo/memories-project/actions/runs/41431829469) on `1b0c46782c9e919961b9e86ed2319793000e973d` and [run #41431952725](https://github.com/m-shogo/memories-project/actions/runs/41431952725) on `69574f9fa471078faeef0d98e675f83212649e10` completed/success. Both changed only `scripts/validate-autonomous-learning-system-negative.py`.
- **whySafe:** Tests are read-only, exact-source GitHub Actions checks; no publisher workflow, protected registry, credentials, traffic, readiness or human promotion authority was changed.
- **reusableMechanism:** Bind every risk-classification assertion to exact source path, deterministic transcript, sorted unique workflow identities, and refusal/advisory semantics.
- **protectedAuthorityCheck:** Nine checked protected Git blobs stayed unchanged: production status `d677a1c9` (`productionDecision=NO_GO`), environment generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. No OPS-P0-007 gate was promoted.

## Next safe target

Develop an independent source-derived, read-only workflow writer-permission inventory guard for the scoped nine unclassified write-capable workflows documented separately. Preserve direct-trigger versus effective-permission distinction, and require exact-source negative CI before any publisher-coupled write.
