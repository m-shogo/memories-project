# Supplemental OPS learning — generation reconciler pinned source close-fault CI (2026-11-02)

Append-only record under canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Learning and synthetic CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered generation, approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material regression risk / failure mode

- **symptom:** The independently read-only generation-evidence reconciler's pinned source importer lacked an executable check for private descriptor-close exceptions with and without an original source-read failure.
- **evidence:** At `so` HEAD `1925453004cfc74efa167079dfcccbe19d6af046`, `pinned_reconciler_source` used a primary-error-preserving owned-FD cleanup loop but its negative harness only covered malformed FD acquisitions and source read failures separately. No real OS close failure or production impact was observed.
- **rootCauseOrUnknown:** Verified missing double-fault negative coverage in this distinct source importer; actual OS failure occurrence unknown.
- **failedApproach:** Assuming similar coverage in generation-binding/evidence transport loaders or source-level cleanup structure alone proves the reconciler's separate boundary.
- **correction:** [`ba7d3451`](https://github.com/m-shogo/memories-project/commit/ba7d3451a9eb432e3b429935fddd89599b3fda01) adds close-then-raise private `ValueError` cases for the no-primary and premature-EOF-primary paths in `prove_pinned_reconciler_import`.
- **recurrenceGuard:** Both cases assert exact private domain errors, no canary leakage, suppressed context for the no-primary case, all three real owned descriptors closed, and restoration of monkeypatched `os.close` and `os.read`. Existing positive import, invalid-FD, early EOF, nonbytes, over-budget, hardlink and parent-swap negatives remain.
- **retryCondition:** Revisit only if reconciler source FD ownership, cleanup classification, exact-source CI or source fixture changes. Do not retry unchanged MinIO 401, write-capable publisher, canonical learning large-blob retrieval or missing human evidence.

## Observed material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41419318313](https://github.com/m-shogo/memories-project/actions/runs/41419318313) completed **SUCCESS** on `ba7d3451a9eb432e3b429935fddd89599b3fda01`.
- **evidence:** Job `125190779076` logged `PASS: generation reconciler negative classifier private exception redaction`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. The new close-fault cases execute before those summaries. GitHub diff changed only the read-only generation reconciler negative harness.
- **whySafe:** The harness runs in `contents: read` exact-source CI, not production recovery execution; it changes no canonical registry, evidence, credential, traffic or readiness.
- **reusableMechanism:** Test an owned descriptor that closes and then reports an injected fault, with/without a primary source-read rejection; preserve the primary, normalize otherwise private close errors and count all owned closures.
- **protectedAuthorityCheck:** After the code commit, ten protected Git blob identities were unchanged: production status `d677a1c9` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed request registry `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection registry `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, learning contract `87712ea9`. Registered/semantically eligible generations 0/0; current approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage and final candidates 0. Human production promotion remains separate/nonautomatic.

## Next safe target

Confirm the substituted-child cleanup negative covers both an intentional identity rejection and a concurrent primary body failure, then audit the fixture manager's non-OS exception redaction without broad catches that mask fixed-domain `Fail`.
