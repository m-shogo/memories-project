# Supplemental OPS learning — generation evidence closed child targets (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or semantically eligible generation, recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — self-consistent unreviewed generation child

- **symptom:** The generation-evidence validator's child runner accepted a caller-supplied repository file and matching expected-relative path under any label. No malicious child execution was observed.
- **evidence:** At starting `so` HEAD `d9fcde0e`, `run_validator(path, expected_relative, label)` called `require_exact_repo_file` without a reviewed label/path pair allowlist; four production call sites used specific reviewed scripts.
- **rootCauseOrUnknown:** Verified child execution authorization gap: repository containment and caller-supplied path equality did not establish a reviewed executable target. Whether a real attacker could influence the helper arguments is unknown.
- **failedApproach:** Relying on a self-consistent caller-provided expected-relative path as the execution authorization boundary.
- **correction:** [`847381e4`](https://github.com/m-shogo/memories-project/commit/847381e49ce1e61b7890e5351009b74d92a68294) requires exact reviewed label/path/relative-path pairs for the negative admission, semantic negative admission, source-order and independent-review validators before subprocess execution.
- **recurrenceGuard:** The existing CI-reached generation-evidence load negative suite now proves all four reviewed targets still pass a mocked positive subprocess and rejects an unreviewed writer, cross-swapped labels and a mismatched expected-relative path without launching any child.
- **retryCondition:** Revisit only when an explicitly reviewed child target/label, executable-source loader, or CI-reached fixture changes. Do not retry unchanged MinIO HTTP 401, workflow permission or missing external production-evidence blockers.

## Material failure — stale synthetic transport label

- **symptom:** Exact-source [Generation Evidence Reconcile Negative #41350814894](https://github.com/m-shogo/memories-project/actions/runs/41350814894) FAILED after the new allowlist, despite the separate read-only workflow passing.
- **evidence:** Job `124980352372` traceback points to `validate-memory-os-backup-restore-generation-evidence-transport-negative.py` invoking the reviewed independent-review path with the stale label `independent review`, while the production call site uses `generation independent-review validator`. The failure was a domain `Fail: unreviewed generation evidence child validator`, not a production incident.
- **rootCauseOrUnknown:** Verified stale test-fixture label, not an unknown external blocker.
- **failedApproach:** Updating the production runner's reviewed label map without updating every existing synthetic invocation of that runner.
- **correction:** [`9ba9dc28`](https://github.com/m-shogo/memories-project/commit/9ba9dc2847531cffbf98c5e8c077bf126f26467c) updates both synthetic transport calls to the existing canonical production label.
- **recurrenceGuard:** The CI-reached transport suite now uses the same exact reviewed label as the production call site; the new load-negative positive/negative target matrix also enforces the closed target inventory.
- **retryCondition:** Retry only if the canonical reviewed label changes with corresponding contract and negative fixture updates, or if exact-source CI exposes a new failure. The unchanged stale-label call is not retried.

## Material success

- **outcome:** Generation-evidence child validation now rejects unreviewed or label-swapped repository executables before launching subprocesses, while all four reviewed targets remain admitted.
- **evidence:** Exact-source [Generation Evidence Readonly #41350814794](https://github.com/m-shogo/memories-project/actions/runs/41350814794) completed **SUCCESS** on code HEAD `847381e4`; job `124980351791` logs `PASS: generation evidence child validator reviewed label/path allowlist`, `Generation evidence unreadable/escaped-authority negative suite PASS`, and `production decision: NO_GO`. After the fixture correction, exact-source [Generation Evidence Reconcile Negative #41350892479](https://github.com/m-shogo/memories-project/actions/runs/41350892479) completed **SUCCESS** on `9ba9dc28`; job `124980585295` logs `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. These are synthetic CI checks, not production recovery or current-source Go test evidence.
- **whySafe:** Only the existing generation-evidence validator and two CI-reached synthetic negative suites changed. Reviewed production child scripts and all production authorities were left untouched. Positive targets were exercised without granting new execution authority.
- **reusableMechanism:** Pair an exact reviewed (label, path, expected-relative) map with canonical file identity and a no-subprocess negative canary; update all pre-existing synthetic callers to the canonical label before declaring CI success.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs remained unchanged through `9ba9dc28` and the subsequent code HEAD `ff1f1d56`: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain non-resurrection `26bb1cc7`, human promotion review `99cb895f`. Registered generations and semantically preflight-eligible unsuperseded generations from distinct environments remain distinct. Preflight still requires an explicitly human-approved current recovery objective. Reviewed requests remain planning-only, new recovery evidence requires a current executable reviewed request, final candidates require complete typed eight-domain coverage plus independent review, and human production promotion remains separate and non-automatic.

## Next safe target

Complete the separate private child-result transport guard's exact-source CI, then audit remaining generation-evidence child script pathname TOCTOU without changing protected production authorities.
