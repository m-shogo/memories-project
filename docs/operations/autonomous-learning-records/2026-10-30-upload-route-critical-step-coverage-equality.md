# Supplemental OPS learning — Upload Route critical step coverage set equality (2026-10-30)

Append-only supplemental learning/history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under mandatory `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective incomplete fingerprint inventory

- **Symptom:** Future changes to the reviewed Upload Route step list or fingerprint dictionary could accidentally omit an executable step body, duplicate a reviewed step or add an unreviewed body while existing individual hash checks still pass for the remaining entries.
- **Observed evidence:** Publisher has 14 reviewed ordered steps (3 action steps, 11 executable); PR has 13 (3 action steps, 10 executable). Individual SHA-256 checks were in place for all reviewed executable steps, but there was no independent equality assertion between the actual YAML step-name set and the fingerprint dictionary minus action steps. This is a prospective coverage gap, not observed production behavior.
- **Verified root cause:** Individual fingerprint checks establish identity of covered steps, not completeness of the covered set.
- **Failed approach:** Inferring complete step coverage solely from successful per-step hash comparisons.
- **Correction / executable recurrence guard:** [`b641dc73`](https://github.com/m-shogo/memories-project/commit/b641dc7398b6f072f923c8662ea216caf4c41789) adds an exact set-equality and duplicate-rejection guard: actual workflow step names minus three reviewed action steps must equal the critical-body fingerprint names. Two positive controls and twelve negative mutations cover missing/extra/duplicate fingerprints, missing action names and duplicate/extra steps. Only the CI-reachable read-only negative validator changed (+41 lines).
- **Retry condition:** A legitimate step or action change requires explicit review of step execution semantics, updated action and executable fingerprint inventories, complete set equality, exact-source CI and protected-authority verification. Do not claim transitive dependency or trigger closure from step completeness alone.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40948792019](https://github.com/m-shogo/memories-project/actions/runs/40948792019) **SUCCESS** on exact source `b641dc7398b6f072f923c8662ea216caf4c41789`. Logs confirm append-only and contract PASS, 201 printed canonical negatives, 74 fanout synthetic cases, entry-document PASS, 1,186 helper-ancestor negative mutations and read-only completion. The twelve nested completeness negatives are additional to the printed 201.
- **Why safe:** Only the read-only validator changed. No actual Upload Route workflow, production service, credentials, traffic, readiness, generation/objective, drill, recovery evidence, typed eight-domain coverage, independent review or human promotion changed.
- **Reusable mechanism:** Pair exact ordered step identity and per-body fingerprints with a separate set-equality completeness proof, including duplicate and action-set checks.
- **Protected-authority check:** Compare shows one modified read-only validator. Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` unchanged. `productionDecision=NO_GO`; registered/eligible generations 0/0 and separate objective, executable reviewed-request, request-bound evidence, eight-domain, independent-review and human-promotion gates remain unsatisfied.

## Next safe target

Continue read-only Go/Python transitive dependency and trigger coverage analysis. The 109 reviewed static inputs and at least 81 uncovered trigger inputs per workflow are lower bounds; do not narrow or modify workflow triggers without complete closure and required permissions.
