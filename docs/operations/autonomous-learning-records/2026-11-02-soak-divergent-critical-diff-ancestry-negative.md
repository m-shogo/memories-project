# Supplemental OPS learning — divergent soak source ancestry despite clean critical diff (2026-11-02)

Append-only subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Synthetic local Git proof is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate, or human promotion authority.

## Material scoped failure mode

- **symptom:** A critical-path `git diff --quiet "$SOURCE_SHA" origin/so -- ...` may return success when `origin/so` was force-replaced with unrelated history containing identical critical file bytes. Therefore a clean diff does not prove that the original source commit is an ancestor of the publication target. No actual divergent publisher run was observed.
- **evidence:** Local isolated bare-Git prototype produced `diff_status=0` and `merge-base --is-ancestor status=1` after a synthetic orphan-history force update. GitHub source review found one critical-path diff followed by rebase in each of `sustained-local-soak.yml`, `sustained-local-soak-parallel-request.yml`, and `sustained-local-soak-parallel-v2.yml`. The previously reviewed controlled saturation workflow separately checks ancestry.
- **rootCauseOrUnknown:** Verified Git DAG semantics: content equality is independent of commit ancestry. Whether remote force updates are possible in the deployed permission/protection configuration, or cause actual stale publication, is unknown.
- **failedApproach:** Treating a critical-path diff against remote source as sufficient ancestry proof. In the first local fixture prototype, `git rm -qr .` also failed because orphan checkout left files staged in the index; the fixture needed a forced removal.
- **correction:** [f97e0da4](https://github.com/m-shogo/memories-project/commit/f97e0da411c22eec40c5dadc661b78efb6da214a) adds a source-scoped, local-only synthetic Git fixture to the existing read-only negative suite. It proves the normal positive ancestry case, creates unrelated history with identical critical bytes, and verifies that diff returns 0 while the ancestry check returns 1. The fixture uses `git rm -qrf -- .` for the orphan-index state and never pushes any evidence/result commit.
- **recurrenceGuard:** Exact-source negative test rejects unexpected source inventory drift, malformed Git subprocess status, a missing divergent-history distinction, and incorrect LF fixture bytes. Its ancestry result is diagnostic only; it cannot authorize production, readiness, or writer publication.
- **retryCondition:** Modify write-capable soak publishers only after separately reviewed ancestry/source-lease semantics, workflow permissions, bounded reconcile, and independent read-only CI. Revisit this fixture if source paths, Git DAG semantics, or exact-source CI outcomes change.

## Observed safe progress

- **outcome:** Local isolated Git prototype passed after the orphan-index correction. GitHub code diff and source re-read confirmed a single-file change to `scripts/validate-autonomous-learning-system-negative.py`. Exact-source Autonomous Learning Guard [#41439796022](https://github.com/m-shogo/memories-project/actions/runs/41439796022) was still in progress when this record was authored; it is **not** claimed as SUCCESS.
- **evidence:** The prototype observed `diff=0` and `ancestor=1` on unrelated synthetic history, and `ancestor=0` on the positive baseline. The committed fixture uses temporary local repositories and does not execute the three publisher workflows.
- **whySafe:** The only changed code is an independent read-only negative test. No production-equivalent evidence, credential, traffic, readiness, promotion authority, write-capable workflow or real remote branch was modified by the fixture.
- **reusableMechanism:** Test source-commit ancestry independently of critical-file equality, including divergent remote history with unchanged critical bytes. Distinguish proof of a potential guard need from proof of real exploitability.
- **protectedAuthorityCheck:** Prewrite and post-code review found unchanged production status blob `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, and mandatory contract `87712ea9`.

## Next safe target

Confirm exact-source CI for the divergent-history fixture and separately review post-rebase source ancestry/critical checks for all three soak publisher paths. Do not retry unchanged external MinIO or write-capable permission blockers. Keep `productionDecision=NO_GO` and human promotion authority separate.
