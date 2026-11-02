# Supplemental OPS learning — generation-binding transport oversized read guard (2026-11-02)

Append-only learning governed by canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Neither this record nor synthetic CI can satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure / latent nonterminating read budget

- **symptom:** The independent generation-binding transport negative harness could loop without reaching its final source-size check if a faulty/mock `os.read` returned more bytes than requested.
- **evidence:** At `so` HEAD `db8189ebfdd664f0dc09fb7a28727c1ded0dd0ea`, `pinned_validator_source` used `remaining = MAX_VALIDATOR_SOURCE_BYTES + 1`, `while remaining:` and `remaining -= len(chunk)` without a per-chunk upper bound. A response of `MAX + 2` makes `remaining == -1`, still truthy. This was identified by source/arithmetic review, **not** an observed CI hang. Existing tests covered fragmented reads, EOF, nonbytes and private OSError but not oversized responses.
- **rootCauseOrUnknown:** Verified missing `len(chunk) <= remaining` check before decrement; real OS over-read occurrence unknown.
- **failedApproach:** Relying on the final `len(source) <= MAX` check, which an over-budget mocked response could prevent the loop from reaching. Prior generation reconciler learning documented the same class; the new negative was added only alongside the correction.
- **correction:** [`219f984b`](https://github.com/m-shogo/memories-project/commit/219f984b56c39a4b606ae0ac029b57969fb2b002) adds the per-chunk budget check before append/decrement and a deterministic oversized-response negative with the existing private domain error.
- **recurrenceGuard:** The existing pinned transport suite now exercises both legitimate fragmented reads and oversized mocked responses, with exact expected error classification and restoration of `os.read`.
- **retryCondition:** Check exact-source read-only Negative Suite CI when observable; if a failure occurs, append its actual evidence and correct it before retry. Do not retry unchanged external evidence or publisher-coupled blockers.

## Observed code-change outcome

- **outcome:** `219f984b` was committed to `so`; GitHub diff confirms only the independent generation-binding transport negative harness changed.
- **evidence:** Commit diff, exact branch comparison and protected Git blob checks. The read-only generation-evidence reconcile negative workflow includes this script in its push trigger; the publisher excludes it. GitHub commit-status returned no checks; **no exact-source CI SUCCESS is claimed**.
- **whySafe:** No production authority, publisher, credential, traffic, evidence registry or readiness state was changed; the new guard only constrains synthetic transport test behavior.
- **reusableMechanism:** Bound every individual read by the remaining byte budget before updating counters, and pair the guard with an over-budget negative that cannot hang.
- **protectedAuthorityCheck:** Verified unchanged Git blobs for production status `d677a1c9` (`productionDecision=NO_GO`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, canonical learning `b809c69d`, mandatory contract `87712ea9`. OPS-P0-007 production-equivalent prerequisites and separate human promotion remain unsatisfied.

## Next safe target

Obtain exact-source CI for the independent generation-binding transport and generation reconciler Negative Suites. Recovery Objectives has a similar reader budget issue but its negative script also triggers a write-capable Admission workflow; defer that scope until a separate read-only execution boundary is established.
