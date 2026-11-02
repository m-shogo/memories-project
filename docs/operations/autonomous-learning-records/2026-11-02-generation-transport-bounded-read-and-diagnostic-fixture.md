# Supplemental OPS learning — bounded generation transport reads and exact diagnostic fixture (2026-11-02)

Append-only history governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This record and all referenced synthetic CI are **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, approved objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate, or human promotion authority.

## Material failure — generation-evidence transport fixture diagnostic drift

- **symptom:** The new generation-evidence pinned-source fragmented-read/EOF/nonbytes negative test failed exact-source CI.
- **evidence:** At code HEAD [`438b9d69`](https://github.com/m-shogo/memories-project/commit/438b9d69238cdec317f4ebde818446ba559922f1), [Generation Evidence Reconcile Negative #41398060264](https://github.com/m-shogo/memories-project/actions/runs/41398060264), job `125123617371`, failed with `GENERATION EVIDENCE TRANSPORT NEGATIVE FAILED: generation transport nonbytes read wrong rejection`. The actual reader raises `generation evidence transport validator read type invalid`; the new fixture incorrectly expected `generation evidence transport validator source read type invalid`. The real reader already rejected nonbytes; no production incident was observed.
- **rootCauseOrUnknown:** Verified fixture diagnostic-string mismatch (spurious `source` token), not a verified source-reader bypass. Runtime incident/exploitation unknown.
- **failedApproach:** Writing an expected error string from inference rather than reading the exact domain failure string from the target function; the mismatch caused a false negative despite fail-closed behavior.
- **correction:** [`7bfea0c2`](https://github.com/m-shogo/memories-project/commit/7bfea0c2097bdf60a77849f33bc9c37b66ba6bd1) changes only the fixture expectation to the actual reader diagnostic; it does **not** weaken the check or catch a broader exception.
- **recurrenceGuard:** Exact-string assertion remains executable in the independently read-only transport negative suite, alongside fragmented positive reads, premature EOF and nonbytes rejection. Future fixtures must extract the exact diagnostic from the corresponding reader before committing.
- **retryCondition:** Revisit if reader diagnostics, pinned-source read implementation, or exact-source CI reachability changes. Do not repeat unchanged canonical 4.17 MB learning blob upload, Quay MinIO 401, publisher-coupled writer edits or absent human evidence.

## Material success — generation-evidence transport corrected

- **outcome:** [Generation Evidence Reconcile Negative #41398715566](https://github.com/m-shogo/memories-project/actions/runs/41398715566) completed **SUCCESS** on exact code HEAD `7bfea0c2097bdf60a77849f33bc9c37b66ba6bd1`; job `125125622427` logged `PASS: generation transport pinned importer rejects invalid FDs, EOF, nonbytes, hardlink and swap; fragmented read works`, `Memory OS generation-evidence execution transport negative PASS`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`.
- **evidence:** Exact-source GitHub Actions run conclusion and job output, committed one-line diagnostic correction; synthetic CI only.
- **whySafe:** Only a read-only Negative Suite file changed. The publisher trigger excludes it; fixtures are disposable and the protected authorities are unchanged.
- **reusableMechanism:** Use the actual reader's exact diagnostic as fixture authority, test fragmented positive reads plus bounded EOF/type failures, and require a specific failure class rather than accepting any exception.
- **protectedAuthorityCheck:** Post-code Git blob SHAs unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, request-bound evidence registry `ae7e57ef`, typed non-resurrection registry `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory learning contract `87712ea9`. All generation/objective/request/evidence/coverage/candidate counts remain zero.

## Material success — independent generation-binding transport coverage

- **outcome:** [`73fddcf2`](https://github.com/m-shogo/memories-project/commit/73fddcf2926b95a7087f7b272bcdb4008569344f) adds a fragmented-read positive control and fail-closed premature EOF, nonbytes and private `OSError` read negatives. [Generation Evidence Reconcile Negative #41398818334](https://github.com/m-shogo/memories-project/actions/runs/41398818334) completed **SUCCESS** on that exact HEAD; job `125125919478` logged `PASS: generation-binding transport pinned importer rejects EOF, nonbytes and private read failures; fragmented read works`, `Memory OS generation-binding loader transport negative PASS`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`.
- **evidence:** GitHub Actions exact-source run conclusion, job logs, source diff. Synthetic CI only; no live recovery was executed.
- **whySafe:** Only the read-only generation-binding transport negative script changed; the production publisher's trigger list excludes it. The private canary is never accepted or surfaced, injected `os.read` is restored after every case, and no authority registry was modified.
- **reusableMechanism:** Deterministic three-byte fragmented read, early EOF, nonbytes return and private read exception fixtures with exact failure assertions and `__suppress_context__` for private `OSError`.
- **protectedAuthorityCheck:** Same ten protected Git blob SHAs unchanged after `73fddcf2`; registered/semantically eligible generations `0/0`, approved current objective `0`, executable reviewed request `0`, request-bound evidence `0`, complete typed eight-domain coverage `0`, final candidate `0`. Human promotion remains separate and nonautomatic.

## Next safe target

Exercise equivalent fragmented positive reads, early EOF, nonbytes and private read `OSError` rejection in the independent generation-evidence registry-transaction pinned writer-import negative harness. Do not change publisher-coupled writer code without independent read-only exact-source coverage.
