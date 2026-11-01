# Supplemental OPS learning — review source-order Git executable isolation (2026-11-01)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure 1 — source-order chronology still resolved Git from inherited PATH

- **symptom:** The review source-order validator's `git_output`, creation-blob size/read, commit-existence and ancestry calls used bare `git` without sanitized subprocess environments. A PATH-first executable could forge a valid-looking creation commit or ancestry status even while the existing timeout, output-size and fixed-diagnostic checks passed.
- **evidence:** Source blob `23c49724` had five `["git", ...]` call sites and five `cwd=ROOT` subprocess invocations with no explicit `env`. Existing independent-review negative fixtures expected the same bare executable. No real forged review, altered chronology or compromised runner was observed.
- **rootCauseOrUnknown:** Verified inherited executable-resolution and loader/Git override trust boundary. Actual adversarial control remains unknown.
- **failedApproach:** Assuming bounded, redacted Git transport and exact commit syntax also protected executable identity and environment. This is a separate source-order consumer and does not inherit protections from sibling material-delta or independent-review validators.
- **correction:** Atomic commit [`195137ca`](https://github.com/m-shogo/memories-project/commit/195137ca262cafdbe6ab751bd08bca323e9dcab7) pins `/usr/bin/git` for all five calls, strips inherited `GIT_*`, `LD_*`, `DYLD_*`, and explicitly disables replace objects and system/global Git config. The original two-creation-commit bound, exact blob size/bytes, 20-second timeout, chronological ordering, private diagnostics and fail-closed ancestry semantics remain intact.
- **recurrenceGuard:** The existing CI-reachable independent-review negative suite checks the pinned executable and sanitized transport for history, creation blob, commit existence and ancestry. A disposable PATH decoy must first produce a forged 40-hex creation SHA, while the real reader rejects the nonexistent synthetic review for the exact expected reason. A mocked `GIT_DIR`/`LD_PRELOAD`/`DYLD_INSERT_LIBRARIES` control proves environment filtering. The source and negative suite were committed together with a non-forced expected-HEAD lease.
- **retryCondition:** Revisit if reviewed Git executable location, chronology/creation policy, subprocess transport or source-order workflow changes, or exact-source CI regresses. Do not retry unchanged external MinIO HTTP 401, workflow permission or human evidence blockers.

## Material failure 2 — prewrite source-segment boundary was too broad

- **symptom:** The first attempted construction of the negative-suite patch aborted before creating any Git object because a segment scanner found the wrong next `def` token.
- **evidence:** The prewrite exact-occurrence check reported `segment occurrence def prove_source_order_bounded_commit_checks` for the intended `calls.append(args[1])` insertion. No repository write occurred in that attempt.
- **rootCauseOrUnknown:** Verified string search for `def ` also matched a nested function declaration inside the selected top-level function.
- **failedApproach:** Using an unanchored function-boundary token when patching a nested-function test.
- **correction:** Re-read latest `so` and both targets; constrain the next boundary to newline plus top-level `def `, then re-run exact source occurrence and fixture-escape checks before atomic publication.
- **recurrenceGuard:** Prewrite segment multiplicity and expected Git-call/env-call counts must pass before any Git blob/tree/ref mutation. The corrected construction found five trusted calls, five sanitized environments and five negative expectations.
- **retryCondition:** Revisit only when source nesting or function structure changes; never reuse the unanchored scanner for nested-function fixtures.

## Material success — exact-source negative and contract CI

- **outcome:** All five review source-order Git calls now have pinned executable identity and sanitized environment, with executable PATH-decoy and callsite negatives.
- **evidence:** [Backup Restore Generation Independent Review Negative #41311601862](https://github.com/m-shogo/memories-project/actions/runs/41311601862) and [Backup and Restore Contracts #41311601867](https://github.com/m-shogo/memories-project/actions/runs/41311601867) completed **SUCCESS** at exact code HEAD `195137ca262cafdbe6ab751bd08bca323e9dcab7`. Other concurrent workflows must be assessed separately; this success is not a production recovery or human review.
- **whySafe:** Only two read-only Python files changed. Synthetic review/decoy controls do not create or alter generations, objectives, requests, evidence, credentials, traffic, typed eight-domain records, independent review, readiness or promotion.
- **reusableMechanism:** Extend existing actual-reader negative fixtures, require a working spoof positive control and exact-reason rejection, preserve chronology and append-only semantics, and atomically commit interdependent source/negative updates with expected-HEAD CAS.
- **protectedAuthorityCheck:** Ten protected blobs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, approved objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion registry `99cb895f`. `productionDecision=NO_GO` and OPS-P0-007 `PREREQUISITES_BLOCKED` remain. Preflight still requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current recovery objective; reviewed requests remain planning-only; new evidence remains bound to a current executable reviewed request; final candidates need complete typed eight-domain coverage and independent review; human promotion is separate/nonautomatic.

## Next safe target

Audit the distinct promotion-review source-order Git transport and its existing negatives. Keep the independent real pre-MinIO Focused Go Test path as an unresolved separate target.
