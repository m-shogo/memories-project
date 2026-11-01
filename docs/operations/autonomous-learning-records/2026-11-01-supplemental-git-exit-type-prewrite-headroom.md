# Supplemental OPS learning — typed Git exit transport and prewrite headroom (2026-11-01)

Append-only operational learning governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound recovery evidence, typed eight-domain non-resurrection, independent-review, final-candidate or human-promotion evidence.

## Material failure A — Git history transport accepted non-integer exit codes

- **symptom:** The supplemental all-parent Git history wrapper could accept a synthetic boolean, float or string return code as a successful/allowed status, including `False == 0` and nonzero values when `allow_failure=True`. This is a verified validator transport gap, not an observed forged repository history.
- **evidence:** At `51058801`, `git()` used truthiness and equality on `result.returncode` without an exact integer type check. An isolated `subprocess.CompletedProcess` control showed `False`, `True`, `0.0`, `1.0`, `"0"` and `-9` accepted by the prior generic status checks under `allow_failure=True`; genuine `0` and `1` remained accepted.
- **rootCauseOrUnknown:** Verified Python equality/truthiness permits `bool` and numeric-equivalent non-integers; signal-terminated processes also must not become acceptable results under `allow_failure=True`.
- **failedApproach:** Treating `if result.returncode` and `result.returncode == 0` as sufficient proof of a genuine subprocess integer exit status.
- **correction:** [`2a49b0d4`](https://github.com/m-shogo/memories-project/commit/2a49b0d40059d51929e0028a5ceda1c58934e183) rejects non-`int` and negative return codes before other Git transport handling.
- **recurrenceGuard:** The real `--self-test` injects six invalid statuses and requires the exact `invalid supplemental Git exit status` reason; the existing CI-reachable entrypoint independently AST-binds the live top-level guard and rejects weakening of its predicate or diagnostic through source-negative mutations.
- **retryCondition:** Revisit if subprocess exit semantics, the Git wrapper, or source-negative AST binding changes. Do not repeat unchanged external MinIO, workflow permission or human evidence blockers.

## Material failure B — prewrite positive fixture exceeded the canonical entrypoint line budget

- **symptom:** Initial code HEAD `2a49b0d4` failed exact-source Autonomous Learning Guard and multiple dependent validators; the nested prewrite CLI real-entrypoint positive control failed.
- **evidence:** [Autonomous Learning Guard #41266842757](https://github.com/m-shogo/memories-project/actions/runs/41266842757) FAILED at learning negative validation. [Rate-Limit Operation Evidence #41266842687](https://github.com/m-shogo/memories-project/actions/runs/41266842687) also FAILED at the dependent entrypoint validator, reporting `prewrite CLI real-entrypoint positive control failed`. The entrypoint grew from 4,095 to 4,096 lines, while `PREWRITE_MAX_SOURCE_LINES=4096` and its real-entrypoint positive fixture appends one more line.
- **rootCauseOrUnknown:** Verified off-by-one headroom: the source itself fit the bound but the mandatory positive mutation did not. This was a CI test-fixture budget failure, not a production readiness failure.
- **failedApproach:** Checking only the unmodified entrypoint's line count instead of preserving one line for the canonical positive-control append.
- **correction:** [`b25d42f6`](https://github.com/m-shogo/memories-project/commit/b25d42f628ee77ad39604700c9441b06e631918b) condensed the new AST predicate onto an existing line, restoring 4,095 physical source lines without weakening the guard.
- **recurrenceGuard:** The existing nested real-entrypoint prewrite positive control fails closed if its appended-line candidate breaches the budget. Future edits must reserve one source line and run that positive, not only syntax or current-file size checks.
- **retryCondition:** Revisit when entrypoint layout or the prewrite candidate line budget changes; never bypass the positive control to silence an unrelated validator failure.

## Material success — exact-source recovery and protected authority

- **outcome:** The typed Git exit-status guard and its six executable negatives are CI-reachable, with the mandatory real-entrypoint positive restored.
- **evidence:** [Autonomous Learning Guard #41266967245](https://github.com/m-shogo/memories-project/actions/runs/41266967245) **SUCCESS** at exact corrected code HEAD `b25d42f6`. Logs verify canonical 601 fail-closed negatives, supplemental all-parent 39-fixture suite, 52 workflow / 63 Python command / 204 source-negative fixtures, 195 fanout synthetic cases, 1,186 helper-ancestor negatives, append-only, learning contract, entrypoint and read-only checks. [Operability Contracts #41266967246](https://github.com/m-shogo/memories-project/actions/runs/41266967246), [Reconcile Backup Restore Policy #41266967330](https://github.com/m-shogo/memories-project/actions/runs/41266967330) and [Rate-Limit Operation Evidence #41266967298](https://github.com/m-shogo/memories-project/actions/runs/41266967298) also completed **SUCCESS** on that code HEAD.
- **whySafe:** Only two read-only Python validators were modified; malformed process results are injected through isolated mocks, no Git history, workflow, production authority, credentials, traffic or evidence was fabricated or mutated.
- **reusableMechanism:** Require exact integer process statuses before truthiness/equality; bind both the executable test and live source AST; budget prewrite positive-control headroom rather than only current-file length.
- **protectedAuthorityCheck:** All ten protected Git blob identities remained unchanged at corrected code HEAD: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`. This new record is append-only and is not admitted as production evidence.

## Strict gates, scoped blockers and next safe target

`productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered / semantically preflight-eligible generations **0/0** and human-approved current recovery objectives **0**. Preflight still requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current objective. Reviewed drill requests are planning-only; new generation evidence requires a current executable reviewed request; final candidates need complete typed eight-domain non-resurrection coverage and independent review in addition to all generation/objective gates; human promotion is separate and non-automatic. No synthetic learning or test can satisfy these gates.

Unchanged blockers: Quay MinIO HTTP 401 prevents focused Go/HTTP tests in Upload Route, workflow-write permission and standalone supplemental-only CI triggers remain restricted, and production-equivalent evidence/human approval are absent. No unchanged blocker was manually retried.

**Next safe target:** Audit non-bytes `stdout`/`stderr` from Git transport and require deterministic typed rejection without increasing the 4,095-line entrypoint source budget; then examine independent pre-MinIO focused Go test reachability without editing blocked workflow authorities.
