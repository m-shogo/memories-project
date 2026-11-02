# Supplemental OPS learning — entry-docs child stderr, prewrite budget and writer fanout (2026-11-03)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This synthetic operational lesson is **never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered/semantically eligible generation, human-approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure 1 — existing high-risk prewrite trigger guard was not enforced before a write

- **symptom:** A read-only source hardening change to `scripts/validate-memory-os-entry-docs.py` unexpectedly started eight workflows, including write-capable reconciler jobs.
- **evidence:** [9ede0485](https://github.com/m-shogo/memories-project/commit/9ede0485f3ed03bb3b5cb35b3aea774abbd0c3af) triggered [Autonomous Learning Guard #41499773021](https://github.com/m-shogo/memories-project/actions/runs/41499773021) plus Reconcile Backup Restore Policy, Reconcile Metrics Authority, Reconcile Observability Access Policy, Reconcile Rate-Limit Operations Policy, Rate-Limit Operation Evidence, Diagnose Metrics Alerting and Operability Contracts. The existing prewrite fanout self-test independently classifies this exact path as `BLOCKED_KNOWN_WRITER_CAS`, with nine direct workflow matches including a PR-only workflow. Several triggered writer workflows use `contents: write` and `git push`. This was not a production promotion.
- **rootCauseOrUnknown:** Verified execution-process error: the existing canonical prewrite fanout risk classification was not applied as a blocking precondition before the write. The repository already contained the executable guard.
- **failedApproach:** Treating a validator file as read-only in effect while ignoring its CI path-triggered writer fanout.
- **correction:** Stop further direct changes to this high-fanout file except the bounded repair required by the failing exact-source CI. Reuse the existing `audit-memory-os-workflow-trigger-fanout.py --path ... --require-direct-push-pr-match` guard and its `BLOCKED_KNOWN_WRITER_CAS` classification; select independent read-only negative-suite files for future guard work.
- **recurrenceGuard:** Before **every** proposed write, check exact path against the existing prewrite fanout authority, inspect both direct and transitive writer triggers, and reject `BLOCKED_*` without an explicitly changed and reviewed retry precondition. The canonical prewrite audit already contains executable source-derived writer CAS negatives; do not invent a weaker duplicate.
- **retryCondition:** Revisit this path only for a proven broken-source repair, or after reviewed workflow trigger topology and permission changes make the prewrite classifier return an authorized safe result. Do not repeat the high-fanout write merely to add another negative.

## Material failure 2 — oversized real-entrypoint prewrite fixture

- **symptom:** The first [Autonomous Learning Guard #41499773021](https://github.com/m-shogo/memories-project/actions/runs/41499773021) failed on the real-entrypoint prewrite CLI positive control; downstream writer reconciler validation also failed.
- **evidence:** Job `125463992126` logged `RuntimeError: prewrite CLI real-entrypoint positive control failed`. Independent exact-source counts show the entry-docs file grew from 4,095 newline-split lines to 4,119, crossing the reviewed `PREWRITE_MAX_SOURCE_LINES=4096` bound. The negative suite's actual CLI positive test uses the real entry-docs source.
- **rootCauseOrUnknown:** Verified excess line count from the newly introduced helper and its canary tests; no production runtime incident was observed.
- **failedApproach:** Adding a standalone helper and synthetic tests directly into a large source that is already near its prewrite line-count ceiling.
- **correction:** [9634bc4d](https://github.com/m-shogo/memories-project/commit/9634bc4d8e80b69cf7faff52424af099bf9dbd4e) restored the original source topology and replaced the unreviewed `fanout_result.stderr[:300]` forwarding with a fixed diagnostic, leaving the source at 4,094 newline-split lines. This bounded repair was necessary because the preceding commit broke CI.
- **recurrenceGuard:** Preserve the actual real-entrypoint prewrite CLI positive control and its 4,096-line limit. Move new redaction negatives to the independent CI-reachable negative suite, not the high-fanout entry-docs source.
- **retryCondition:** Only revisit the line budget after a reviewed change to the canonical prewrite contract or a real source-size requirement; do not weaken the limit to fit a convenience helper.

## Material failure 3 — negative mutation must remain executable

- **symptom:** Source review found that initial synthetic stderr mutants removed an entire `if` block header and could fail only due an orphaned `else`, rather than the intended diagnostic leak.
- **evidence:** [fd52de5a](https://github.com/m-shogo/memories-project/commit/fd52de5a7f94f2ff0ff1c16e765f32ddbc331867) introduced the source-negative guard; its first mutation construction replaced the two-line `if`+append anchor with a bare append statement. This was a verified fixture construction defect, not an observed CI failure.
- **rootCauseOrUnknown:** Verified replacement span accidentally included the control-flow header.
- **failedApproach:** Counting a parser rejection as proof that a private stderr diagnostic was rejected.
- **correction:** [cecab29b](https://github.com/m-shogo/memories-project/commit/cecab29ba57e43f4bb9a886e2245bf1c10ce4f3a) preserves the `if` header for ordinary mutants, compiles each mutant before applying the AST semantic guard, and fails on a no-op or invalid fixture.
- **recurrenceGuard:** Six synthetic AST negatives now target leaked stderr suffix, direct stderr, reversed exit condition, removed failure, changed diagnostic and additional stderr output. Every mutant must compile, differ from source and be rejected by the intended guard.
- **retryCondition:** Revisit only on actual entry-docs failure-branch topology or negative-fixture semantics changes.

## Observed repair success and protected authority

- **outcome:** [Autonomous Learning Guard #41500176955](https://github.com/m-shogo/memories-project/actions/runs/41500176955) completed **SUCCESS** on exact repaired source `9634bc4d`. Job `125465329540` recorded 616 direct and independently nested canonical negative cases PASS, 195 prewrite fanout synthetic cases PASS, entrypoint-document PASS and append-only/read-only validation. The subsequent AST guard commits `fd52de5a` and `cecab29b` had no terminal CI result at this record's creation; do not treat them as CI PASS.
- **evidence:** The repaired entry-docs source has 4,094 newline-split lines and no `fanout_result.stderr[:300]` expression. GitHub branch and blob reads confirmed the fixed source; the CI run above confirms the prewrite budget and full existing negative suite.
- **whySafe:** The repaired diagnostic is fixed-domain and does not reflect private child stderr. No production-equivalent evidence or promotion authority was written. The **trigger fanout itself was not an approved safe write route**; that separate process failure remains recorded rather than hidden by green CI.
- **reusableMechanism:** Keep error redaction inside an existing line budget, validate actual CLI positive controls, use separate executable AST negatives, and treat CI writer fanout as a prewrite authority gate.
- **protectedAuthorityCheck:** Ten protected blobs remained unchanged across these changes: Production Status `d677a1c9` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory learning contract `87712ea9`. No registered or semantically eligible generation, approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion exists.

## Next safe target

Verify exact-source terminal CI for `cecab29b`, inspect writer workflow outcomes and any authority drift, and restrict subsequent changes to independently read-only paths. Do not retry unchanged MinIO HTTP 401 or missing human production-evidence/approval blockers.
