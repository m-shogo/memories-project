# Supplemental OPS learning — prewrite CLI exception closure and Git tree schema (2026-11-03)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is synthetic execution learning only, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or semantically eligible generation, human-approved objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human production-promotion evidence.

## Material failure 1 — enumerated unexpected CLI exceptions are not closed

- **symptom:** An unreviewed prewrite audit exception class such as `AttributeError`, `KeyError`, `AssertionError` or plain `Exception` could escape the CLI as a traceback with private source information.
- **evidence:** Before [ea2802df](https://github.com/m-shogo/memories-project/commit/ea2802dfb15b763c77b84ddbda2c5fed113fb7f3), the CLI caught `AuditFailure` separately but redacted only `(OSError, UnicodeError, ValueError, TypeError, RuntimeError)`. The other four exception classes were not caught. This is a source-observed disclosure risk, not an observed production leak.
- **rootCauseOrUnknown:** Verified omission inherent to the enumerated exception tuple. Whether any real private exception escaped outside synthetic testing is unknown.
- **failedApproach:** Repeatedly appending known exception subclasses to an incomplete tuple while leaving the generic unreviewed exception path open.
- **correction:** [ea2802df](https://github.com/m-shogo/memories-project/commit/ea2802dfb15b763c77b84ddbda2c5fed113fb7f3) keeps reviewed `AuditFailure` diagnostics in the first handler and maps all other ordinary `Exception` subclasses to the existing fixed, private-safe failure text and nonzero exit.
- **recurrenceGuard:** Four new real-CLI `runpy` canary injections in the existing CI-reachable negative suite cover `AttributeError`, `KeyError`, `AssertionError` and base `Exception`; the previous reviewed-domain positive control remains. Each injection must be observed, exit 1, emit no stdout, match exact fixed stderr and leak no canary.
- **retryCondition:** Revisit only when the CLI handler ordering, exception taxonomy, actual source-inspection call or CI negative entrypoint changes; do not reintroduce enumerated-only catch without equivalent exhaustive proof.

## Material failure 2 — Git tree creation argument schema mismatch

- **symptom:** The first atomic Git tree staging attempt failed before any branch update.
- **evidence:** `create_tree` rejected `base_tree_sha` because the caller supplied the entire `commit.tree` object `{sha,url}` instead of the required SHA string. The connector returned an explicit schema validation error; the `so` ref had not been updated.
- **rootCauseOrUnknown:** Verified incorrect field extraction in the orchestration call; not a repository or production failure.
- **failedApproach:** Passing the Git commit's tree object directly to a scalar `base_tree_sha` argument.
- **correction:** The successful retry extracted `commit.tree.sha` and used a non-force expected-head lease to advance `so` atomically.
- **recurrenceGuard:** Treat GitHub REST response objects and connector write arguments as separate schemas; assert `typeof tree.sha === "string"` before creating a tree, then verify current `so` again before the commit/ref CAS.
- **retryCondition:** Retry only after correcting the object-to-SHA extraction; this changed precondition was satisfied on the subsequent successful write.

## Material success — observed repository write and static authority check

- **outcome:** [ea2802df](https://github.com/m-shogo/memories-project/commit/ea2802dfb15b763c77b84ddbda2c5fed113fb7f3) advanced `so` from `51233024` through a non-force expected-head ref update; exactly the prewrite audit and its existing negative suite were changed.
- **evidence:** Connector returned successful ref update, the branch was independently re-read at `ea2802df`, both new blob SHAs were recorded, and all ten protected authority blob SHAs matched the prewrite baseline. Exact-source [Autonomous Learning Guard #41499117257](https://github.com/m-shogo/memories-project/actions/runs/41499117257) was **in progress** when this lesson was authored; no CI PASS is claimed here.
- **whySafe:** Only read-only prewrite CLI classification and synthetic negative tests changed. No writer workflow, generation, objective, reviewed drill request, evidence, credentials, traffic, readiness or promotion authority was written.
- **reusableMechanism:** Keep reviewed domain failures distinct from arbitrary unreviewed exceptions, require exact stderr and canary-free negative execution, and publish Git trees only with a verified scalar base tree SHA plus an expected-head lease.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs were unchanged: Production Status `d677a1c9` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. All generation/objective/evidence/final candidate counts remain zero. Learning never satisfies any production-equivalent gate and human promotion remains separate/non-automatic.

## Next safe target

Obtain the exact-source CI terminal result and independently audit unreviewed child-process stderr forwarding in the read-only entry-documents validator. Do not retry unchanged MinIO HTTP 401, workflow-write permission or missing human approval blockers.
