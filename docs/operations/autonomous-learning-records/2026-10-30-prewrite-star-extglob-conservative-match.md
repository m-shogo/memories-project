# Supplemental OPS learning — conservative star-extglob workflow path matching (2026-10-30)

Append-only operational learning only. The canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. **No learning record can satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, or human-promotion gates.**

## Material failure — prospective direct-trigger undercount

- **symptom:** The read-only prewrite workflow path auditor could report zero direct push/PR matches for an unreviewed star-prefixed parenthesized glob such as `scripts/*(a).py`, even though its parser already conservatively rejected other extended glob prefixes.
- **evidence:** Python `fnmatch.fnmatchcase("scripts/a.py", "scripts/*(a).py")` returned false, and the existing regex `[@+?!]\\(` did not recognize `*(`. This is an observed lexical compatibility gap, **not proof that GitHub accepts this exact extglob** and not a production incident. GitHub's workflow path-filter syntax is a separate grammar from Python `fnmatch`.
- **rootCauseOrUnknown:** Verified missing `*` prefix in the scanner's conservative extended-glob detection. Exact GitHub runtime interpretation of this spelling is not independently established; the safe response is over-approximation.
- **failedApproach:** Using Python `fnmatch` to prove non-match for unreviewed parenthesized glob syntax.
- **correction:** [a22012c8](https://github.com/m-shogo/memories-project/commit/a22012c8aca2b1ca1a238778b1b5cb7ff8d7a6ca) expands the conservative detector to `[*@+?!]\\(`, adds a star-extglob synthetic match and a literal-parenthesis control, and exercises the actual strict CLI with exact matched-workflow identity.
- **recurrenceGuard:** CI-reachable negative harness invokes the real auditor and requires one matching workflow for the ambiguous star-extglob source, while the self-test pins the two new fixture identities and retains the unrelated literal-parenthesis non-match.
- **retryCondition:** Narrow the over-approximation only after a reviewed GitHub-compatible glob engine and actual positive/negative semantics are established. Do not retry unchanged workflow-write permissions, external MinIO HTTP 401, canonical learning transport or human-promotion blockers.

## Material success — exact-source CI and protected authority

- **outcome:** [Autonomous Learning Guard #41032850716](https://github.com/m-shogo/memories-project/actions/runs/41032850716) completed **SUCCESS** on exact code source `a22012c8aca2b1ca1a238778b1b5cb7ff8d7a6ca`.
- **evidence:** Job logs show 509 canonical fail-closed negatives, **195** prewrite fanout synthetic cases (193 before this change), 1,186 helper-ancestor negatives, 52 source-negative workflows, 63 direct Python commands and 204 execution-path fixtures. Append-only, contract, entry-document and read-only checks PASS. The new strict real-CLI fixture is executed but not separately included in the printed 509.
- **whySafe:** Only the read-only workflow path auditor and its existing CI-reachable negative validator changed. No workflow YAML, production service, credentials, traffic, backup/restore, generation/objective/drill/evidence/non-resurrection/review or promotion authority was modified.
- **reusableMechanism:** Unsupported cross-engine pattern grammar must be conservatively classified as possible direct fanout, backed by an exact real-CLI match identity and a control that ordinary literals remain non-matches. Direct trigger matches alone are not transitive CI closure or write authorization.
- **protectedAuthorityCheck:** All ten protected blob SHAs remained unchanged after the code commit: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, no approved recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or separate human promotion.

## Next safe target

Audit source-byte bounded reads and source-identity race windows in the prewrite workflow matcher. Preserve existing CI trigger limitations: modifying the standalone audit script alone does not automatically trigger Autonomous Learning Guard. The Go-only focused Upload Route pre-MinIO CI and complete Go/Python transitive dependency closure remain unproven.
