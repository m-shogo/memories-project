# Supplemental OPS learning — unnamed YAML step boundary negatives (2026-11-02)

Append-only subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Synthetic workflow parsing is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material scoped failure mode

- **symptom:** A rebase-to-push inventory that treats only `- name:` as a YAML step boundary can incorrectly accept a push in a later unnamed `- run:` or `- uses:` step as part of the earlier shell process.
- **evidence:** The prior read-only classifier at `344e09db` used `^      - name:\s` as its step delimiter. GitHub Actions step items can be written without a `name` key. Local regex prototype verified `- run:`, `- uses:` and `- id:` were not recognized by the previous pattern. No real stale publisher run was observed.
- **rootCauseOrUnknown:** Verified overly narrow lexical step-boundary matcher. Full YAML/shell control-flow proof and real publisher exploitability remain unknown.
- **failedApproach:** Treating a named-step-only marker as a complete YAML shell-process boundary.
- **correction:** [`7e55ff0e`](https://github.com/m-shogo/memories-project/commit/7e55ff0e1d318c9316139e9e3086851513586bf3) recognizes a six-space YAML sequence item with a literal key, covering named and unnamed steps. It adds two cross-step push negatives (`- run:` and `- uses:`) and a valid unnamed same-step positive.
- **recurrenceGuard:** The existing three soak publisher source inventories must retain their exact reviewed rebase/guard results; separate-step push fixtures now fail closed regardless of whether the next step has a name.
- **retryCondition:** Revisit on YAML nesting/topology changes or exact-source CI failure; do not claim that lexical step scoping alone proves publisher permission or source-lease correctness.

## Material safe progress

- **outcome:** One read-only negative-suite code commit was accepted on `so`. Local regex prototype distinguished named, unnamed and nested source lines. Exact-source [Autonomous Learning Guard #41444284838](https://github.com/m-shogo/memories-project/actions/runs/41444284838) was queued at record creation, not claimed as SUCCESS.
- **evidence:** Source re-read confirmed the generalized step-boundary regex and three new fixtures in `scripts/validate-autonomous-learning-system-negative.py`. No workflow or publisher code was changed.
- **whySafe:** The classifier only reads repository workflow text; its negative fixtures never execute a real publisher or contact GitHub remotes.
- **reusableMechanism:** Bind shell-process boundaries to YAML sequence structure rather than optional display-name fields, with both cross-boundary negatives and legitimate same-step positives.
- **protectedAuthorityCheck:** Post-code tree showed all ten protected blob SHAs unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, contract `87712ea9`.

## Next safe target

Confirm exact-source CI for unnamed-step negatives. Then audit multiline `git push` shell forms and the three unguarded soak publishers in an independent read-only path. Keep `productionDecision=NO_GO`.
