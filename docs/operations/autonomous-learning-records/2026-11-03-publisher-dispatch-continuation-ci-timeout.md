# Supplemental OPS learning — publisher dispatch continuation CI timeout (2026-11-03)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or semantically eligible environment generation, approved recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate, or human production-promotion evidence.

## Material failure

- **symptom:** Exact-source [Autonomous Learning Guard #41547085145](https://github.com/m-shogo/memories-project/actions/runs/41547085145) FAILED at the entrypoint-document validation step on commit [89bd4a10](https://github.com/m-shogo/memories-project/commit/89bd4a1050715ab936d6786e544481af8ae830ed).
- **evidence:** Job `125625189260` logged the standalone canonical contract PASS and `Autonomous learning negative validation PASS (642 fail-closed cases)`, followed by `ENTRYPOINT DOCUMENT VALIDATION FAILED - autonomous-learning guard timed out after 120s: scripts/validate-autonomous-learning-system-negative.py`. Append-only and clean-source checks passed before the failure; helper ancestor and final read-only checks were skipped.
- **rootCauseOrUnknown:** The nested entrypoint invocation has a fixed 120-second child budget and exceeded it. The new continuation-aware dispatch regex and five additional synthetic mutations increased work on an already close-to-budget negative suite; the precise contribution of runner variability versus redundant full-source rescans is **unknown**. No production or publisher failure was observed.
- **failedApproach:** Rebuilding a dictionary and rescanning all 120 unchanged publisher source files for each of 25+ synthetic mutation/control fixtures after the complete baseline had already been checked. Do not simply rerun the same unchanged slow approach.
- **correction:** [bef88c06](https://github.com/m-shogo/memories-project/commit/bef88c062b75859f449d7c38d5c7b87a87d31d85) retains the exact complete 120-file baseline check, then scans only the one intentionally mutated target in each synthetic fixture. This preserves detection semantics because the other 119 source strings are immutable and already verified. Exact-source follow-up CI was queued at record creation; success is **not** asserted here.
- **recurrenceGuard:** Keep complete baseline inventory plus target-only synthetic checks and the unchanged 120-second nested CI budget; require both direct and nested negative-suite PASS, helper ancestor and final read-only steps before treating the change as validated.
- **retryCondition:** Re-evaluate only on the new optimized exact source and its CI outcome; if still over budget, measure independent runtime and optimize deterministic fixture work without weakening fail-closed cases or extending timeout as a substitute for diagnosis.

## Observed safe boundary

- **outcome:** The timeout was detected before any production evidence/readiness change, and the source-level mutation coverage was retained while removing redundant repeated work.
- **evidence:** Commits `89bd4a10` and `bef88c06` each modify only `scripts/validate-autonomous-learning-system-negative.py`; CI #41547085145 was read-only and failed closed. No writer workflow was dispatched by this validation.
- **whySafe:** Only a CI-reachable read-only negative test changed; no workflow, publisher, protected contract, production evidence, credential, traffic or promotion source was modified.
- **reusableMechanism:** Verify immutable full inventory once, then apply target-scoped mutations and benign controls; preserve explicit runtime budgets and exact-source CI.
- **protectedAuthorityCheck:** After `bef88c06`, all ten protected blob SHAs remained unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, recovery objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory learning contract `87712ea9`. Registered/eligible generations 0/0; current approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain final candidate and human promotion absent.

## Next safe target

Verify optimized exact-source CI. If successful, inspect additional shell continuation positions in repo-qualified Actions dispatch with bounded source-negative mutations. Do not retry unchanged workflow-write permission, MinIO HTTP 401, or missing human authority blockers.
