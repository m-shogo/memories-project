# Supplemental OPS learning — environment review-independence job permissions (2026-10-29)

Append-only supplemental learning only. Never canonical learning, production evidence, recovery generation/objective/drill proof, backup/restore, RPO/RTO/skew, typed eight-domain non-resurrection evidence, credentials, traffic, readiness or promotion authority.

## Material gap / executable recurrence prevention

- **Symptom:** The environment review-independence CI source validator pinned root read-only YAML, reviewed blob and event paths, but did not independently verify PR and publisher job identity, event conditions or their distinct job-level permission scopes. This is a static admission gap, not observed production misuse.
- **Observed evidence:** Reviewed workflow Git blob `56d15ffd78c816ccecd0ff27c9e159f78c913bf4` has `validate-pr` with `contents: read` and `validate-and-publish` with `contents: write`, each with explicit event-scoped `if`, `runs-on`, `timeout-minutes: 8`, `steps`. Prior YAML semantic negatives numbered nine and covered only event/root/root-permission shadows.
- **Verified root cause / failed approach:** Root `contents: read` and a standalone `contents: write` token do not prove that write permission is confined to the push/dispatch publisher or that PR cannot inherit a job-level escalation. A whole-source SHA rejection is not an independent semantic diagnostic.
- **Correction / executable guard:** [3c0810ad](https://github.com/m-shogo/memories-project/commit/3c0810adc0c09c9445087fe96c97f90495862483) pins both job IDs, exact event conditions, job-key inventories and separate permission leaves. Twenty new in-memory exact-diagnostic negatives cover duplicate/spaced/quoted job mappings, plain/spaced/quoted late job permission shadows, direct PR/publisher scope mutations, quoted/spaced permission leaves and event-condition bypasses. Total YAML negatives increased from nine to twenty-nine.
- **Retry condition:** Reassess only after independently reviewed job/permission/event topology changes or a demonstrated bypass. Do not retry unchanged MinIO 401, canonical-learning transfer, supplemental workflow-write permission or human approval blockers.

## Material pre-write tooling failure and correction

- **Symptom/evidence:** The first pre-write verification attempt stopped with `TypeError: Cannot read properties of undefined (reading 'split')` before any GitHub write.
- **Verified root cause:** A JavaScript helper used `.split(delimiter, 1)[1]`, incorrectly treating JavaScript's second argument as Python's `maxsplit`; JavaScript instead limits the returned array to one element.
- **Failed approach:** Reusing Python-style split semantics in the JavaScript pre-write canonical job-section check.
- **Correction / recurrence guard:** Re-read the unchanged branch and target, used full JavaScript `.split(delimiter)` for the two known job boundaries, asserted exact job IDs, key order and scoped permission leaves before calling GitHub update. The successful write and CI followed this check.
- **Retry condition:** Only rerun pre-write preparation after fixing the delimiter handling and re-reading latest branch/file; do not retry the failed JavaScript expression unchanged.

## Material success / protected authority

- **Outcome/evidence:** [Production Equivalent Environment Review Independence #40771031871](https://github.com/m-shogo/memories-project/actions/runs/40771031871) completed SUCCESS for exact source `3c0810adc0c09c9445087fe96c97f90495862483`. Publisher job log confirms twenty-nine YAML exact-diagnostic negatives, twenty-one semantic anchor and two blob-only negatives, and validation exit code zero. The PR job was skipped on this push, as intended.
- **Why safe:** Only the existing CI-reachable Python source validator changed (+86/-2). No reviewed workflow, actual environment generation, objective, recovery evidence, credential, traffic, readiness or human promotion authority changed; all negatives are synthetic.
- **Reusable mechanism:** Enforce the effective nested job mapping, exact event admission condition and permission scope per job; allow explicitly reviewed publisher write permission while rejecting PR escalation or publisher authority drift.
- **Protected-authority check:** Repository compare `35121719` → `3c0810ad` showed only the validator file changed. Learning contract Git blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged; `productionDecision=NO_GO` and empty generation/evidence registries remain. No typed eight-domain coverage, final recovery candidate or human promotion was admitted.
- **Next safe target:** Audit recovery objectives reconcile source CI for independent nested job and permission shadows, while preserving strict OPS-P0-007 eligibility and separate human promotion gates.
