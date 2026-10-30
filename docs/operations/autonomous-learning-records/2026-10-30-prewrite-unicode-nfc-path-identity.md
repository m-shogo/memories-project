# Supplemental OPS learning — Unicode NFC prewrite path identity (2026-10-30)

Append-only supplemental learning governed by `contracts/operations/autonomous-learning-system.json`. Canonical authority `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains blob-SHA verified but unavailable through the large-blob text transport. **Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure / static alias gap

- **symptom:** The prewrite path grammar accepted decomposed Unicode source names such as `docs/cafe\u0301.md` and `docs/ハ\u309aス.md`, which have canonically equivalent NFC spellings. Workflow glob matching could be evaluated against a spelling different from the checkout filesystem's canonical representation.
- **evidence:** Run-start `7d2a0617` and post-Win32 source `a7586aa9` checked control categories, separators, Git metadata and Win32 aliases but had no Unicode normalization check. This is a potential static source-identity gap, **not** an observed production incident.
- **rootCauseOrUnknown:** Verified missing canonical-normalization check in `validate_relative_path`; platform-specific normalization of a particular actual checkout was not observed.
- **failedApproach:** Treating all visible Unicode spellings as distinct repository-relative source identities.
- **correction:** [`e9a5c808`](https://github.com/m-shogo/memories-project/commit/e9a5c8084715ecfaa72fb4392a12fe51cf6c4f86) requires `unicodedata.normalize("NFC", relative) == relative`. [`00556bf4`](https://github.com/m-shogo/memories-project/commit/00556bf4d13a3084b453c5bdafa8c72c22b37603) adds exact real-CLI negative controls.
- **recurrenceGuard:** Two synthetic negatives and two actual CLI negatives require exit 1, exact diagnostic and empty stdout; NFC-composed Latin/Japanese and existing ordinary paths remain positives. Exact-source fail-closed count **469 → 471** and fanout synthetic count **159 → 161**.
- **retryCondition:** Any exception requires platform-aware, checkout-specific normalization and root-containment proof with positive/negative real-CLI tests. Do not retry unchanged external MinIO, workflow write, canonical-learning transfer or human-approval blockers.

## Material success / authority check

- **outcome:** Exact-source [Autonomous Learning Guard #41013836778](https://github.com/m-shogo/memories-project/actions/runs/41013836778) completed **SUCCESS** for `00556bf4d13a3084b453c5bdafa8c72c22b37603`.
- **evidence:** CI job log shows append-only PASS, contract PASS, **471** canonical fail-closed negatives, **161** fanout synthetic cases, **1,186** helper-ancestor negative mutations, entry-document PASS and clean read-only completion.
- **whySafe:** Only read-only prewrite auditor and its CI-reachable negative suite were changed; no workflow, production runtime, recovery evidence, registry, credential, traffic, readiness or promotion mutation.
- **reusableMechanism:** Validate canonical Unicode path identity before filesystem reads or workflow-trigger fanout; preserve explicit composed positives and decomposed negatives.
- **protectedAuthorityCheck:** The ten protected authority blob SHAs remained equal to run-start `7d2a0617` after the code and CLI-negative commits, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and no approval or recovery gate satisfaction.
- **limits / nextSafeTarget:** NFC validation is not full Git index/checkout identity or a proof of transitive dependency and trigger closure. Review DOS 8.3 short-name alias handling separately; keep human production promotion non-automatic.
