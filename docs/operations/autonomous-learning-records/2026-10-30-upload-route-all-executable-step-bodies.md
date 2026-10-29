# Supplemental OPS learning — Upload Route all reviewed executable step bodies (2026-10-30)

Append-only supplemental history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. Learning cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure — prospective remaining shell-body drift

- **Symptom:** The Upload Route Publisher's source-SHA capture step and both workflows' dependency-installation and focused Go regression steps could acquire extra shell commands or change test/dependency arguments while preserving their step names, action identities, and the previously pinned critical shell bodies.
- **Observed evidence:** Read-only inspection found three remaining unpinned executable step bodies: Publisher `Capture validation source`, shared `Install validation dependencies`, and shared `Run focused route and live upload regressions`. The Publisher has 14 reviewed steps (3 action steps, 11 executable), and PR has 13 (3 action steps, 10 executable). This is a prospective drift gap, not observed production execution.
- **Verified root cause:** Partial shell-body fingerprint coverage does not prove the complete executable step set, even when the ordered step list is pinned.
- **Failed approach:** Assuming prior critical-step coverage implicitly included source capture, dependency installation and Go regression execution.
- **Correction / executable recurrence guard:** [`2432132d`](https://github.com/m-shogo/memories-project/commit/2432132dbad4d95e0e30475ba22cb7d0d6f411f5) adds SHA-256 fingerprints for the two shared executable steps and the Publisher-only source capture, plus five new nested mutation negatives (two shared cases per workflow and one Publisher-only case). The CI-reachable read-only validator now fingerprints all 11 Publisher and 10 PR executable step bodies; workflow YAML remains unchanged. Only the validator changed (+7 lines).
- **Retry condition:** Any legitimate executable step-body change requires explicit review of shell execution, source-SHA binding, dependency resolution, Go test selection and timeout, updated deterministic digests, exact-source CI and protected-authority verification. Do not claim complete transitive Go/Python dependency or trigger closure from shell-body coverage.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40948475656](https://github.com/m-shogo/memories-project/actions/runs/40948475656) **SUCCESS** on exact source `2432132dbad4d95e0e30475ba22cb7d0d6f411f5`. Logs confirm append-only and contract PASS, 201 printed canonical negatives, 74 fanout synthetic, entry-document PASS, 1,186 helper-ancestor negative mutations and read-only completion. The five new nested shell-body negatives are additional to the printed 201.
- **Why safe:** Only a read-only CI-reachable negative validator changed; no workflow YAML, production source, credentials, traffic, readiness, generation/objective, reviewed request, recovery evidence, typed eight-domain coverage, independent review or human promotion changed.
- **Reusable mechanism:** Bind every reviewed executable named step body with SHA-256 while separately binding action identity, step order, job execution, event source, environment and permissions.
- **Protected-authority check:** Compare shows exactly one modified read-only validator. Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` unchanged. `productionDecision=NO_GO`, registered/eligible generations 0/0, no approved objective, executable reviewed request, request-bound evidence, final candidate or human promotion.

## Next safe target

Add a deterministic set-equality meta-guard proving that the reviewed executable step-name set exactly equals the set of critical-body fingerprints for Publisher and PR, with negative tests for omitted/extra coverage. Do not narrow incomplete Go/Python trigger coverage.
