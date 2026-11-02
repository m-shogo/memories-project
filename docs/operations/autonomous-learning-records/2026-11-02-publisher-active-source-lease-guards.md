# Supplemental OPS learning — active publisher source-lease commands (2026-11-02)

Append-only learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — source-level command token masking

- **symptom:** Generation Evidence and Recovery Objectives publisher coupling checks accepted required source-lease/push tokens anywhere in YAML text, including shell comments, without confirming active command lines inside the reviewed write-capable job.
- **evidence:** Before [`56e3d8b4`](https://github.com/m-shogo/memories-project/commit/56e3d8b45383baeb30cc7d1921ab778626872ad3), `classify_generation_publisher_coupling` required token substring presence but not active `git fetch`, `exit 75`, `git push`, `revalidate_latest_authority` or `SOURCE_SHA` lines. Before [`60cf1eac`](https://github.com/m-shogo/memories-project/commit/60cf1eacd8bcfcf61df9024ae70157b04cb6879e), `classify_objective_publisher_coupling` similarly checked only token presence. No real commented-out publisher commands or production bypass were observed.
- **rootCauseOrUnknown:** Verified static scanner did not distinguish executable shell lines from comments; whether an adversary attempted such a bypass is explicitly unknown.
- **failedApproach:** Treating presence of source-lease tokens anywhere in a workflow as sufficient to authorize a write-capable publisher path.
- **correction:** [`56e3d8b4`](https://github.com/m-shogo/memories-project/commit/56e3d8b45383baeb30cc7d1921ab778626872ad3) checks active command lines inside the Generation Evidence `validate` job. [`60cf1eac`](https://github.com/m-shogo/memories-project/commit/60cf1eacd8bcfcf61df9024ae70157b04cb6879e) checks active fetch, stale-source comparison, exit-75 and push lines inside the Recovery Objectives `validate-and-publish` job.
- **recurrenceGuard:** Two independent publisher-free read-only suites inject commented-out fetch, push, stale-exit and source revalidation/guard cases. Both require non-inert mutations and reject a workflow that retains the same token text but no longer executes the reviewed authority commands. Generation Evidence now has 18 publisher semantic negatives; Recovery Objectives has 17.
- **retryCondition:** Revisit if publisher shell structure, job names, active source-lease commands, bounded retry, or read-only CI reachability changes. Do not repeat substring-only checks or unchanged workflow permission, MinIO HTTP 401, or missing human production evidence blockers.

## Material success — Generation Evidence

- **outcome:** [Generation Evidence Reconcile Negative #41389401082](https://github.com/m-shogo/memories-project/actions/runs/41389401082) completed **SUCCESS** on exact source `56e3d8b45383baeb30cc7d1921ab778626872ad3`.
- **evidence:** Job `125097239373` logged `PASS: generation evidence publisher active source lease and YAML shadow guards (18 negatives)`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`.
- **whySafe:** Only the existing publisher-free read-only source-negative script changed; actual publisher workflow, production evidence and protected authorities were not written.
- **reusableMechanism:** Bind source-lease requirements to active shell lines within the exact reviewed write-capable job and prove commented-command rejection using in-memory negative YAML.
- **protectedAuthorityCheck:** Protected authorities remained byte-identical to initial `so` `25ac906d`; `productionDecision=NO_GO`.

## Material success — Recovery Objectives

- **outcome:** [Recovery Objectives Reconcile Negative #41389625732](https://github.com/m-shogo/memories-project/actions/runs/41389625732) completed **SUCCESS** on exact source `60cf1eacd8bcfcf61df9024ae70157b04cb6879e`.
- **evidence:** Job `125097923051` logged `PASS: recovery objective publisher active source lease and YAML shadow guards (17 negatives)`, `Recovery objective reconcile negative suite PASS`, and `production decision: NO_GO`.
- **whySafe:** Only the existing publisher-free read-only workflow-negative script changed; no objective, registry, credential, traffic, readiness or promotion authority was written.
- **reusableMechanism:** Require active fetch, stale-source comparison, bounded exit-75 and push lines, rather than accepting their presence in comments.
- **protectedAuthorityCheck:** Canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `d677a1c9`, OPS-P0-007 snapshot `dbaa36b0`, generation `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, human promotion `99cb895f` remain unchanged. Registered/semantically eligible generations 0/0, approved current objective 0, executable reviewed request 0, request-bound evidence 0, complete typed coverage 0, final candidates 0. OPS-P0-007 prerequisites remain blocked and human promotion remains separate/nonautomatic.

## Next safe target

Audit other publisher-coupled workflows only when a distinct read-only CI-reachable guard is available; do not mutate a write-capable workflow to obtain CI. Generation Evidence atomic pathname staging/replacement remains a separate scoped risk and requires a reviewed execution plan before modification.
