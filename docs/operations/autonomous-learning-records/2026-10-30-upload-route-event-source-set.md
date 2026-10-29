# Supplemental OPS learning — Upload Route workflow event source set (2026-10-30)

Append-only supplemental history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy: `contracts/operations/autonomous-learning-system.json`. This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review or promotion evidence.

## Material failure — prospective hidden event expansion

- **Symptom:** A Publisher or PR workflow could acquire additional trigger events such as `schedule`, `workflow_call`, `pull_request_target`, or an unreviewed `workflow_dispatch` while retaining the expected push/PR path list and unchanged Go/Python command/import identities.
- **Observed evidence:** Read-only inspection of the actual Publisher source found exactly `push` and `workflow_dispatch` events; the PR source found only `pull_request`. The previous `upload_route_event_paths` guard parsed a selected event's `paths` but did not enforce the complete event set. This is prospective drift, not observed production execution.
- **Verified root cause:** A per-event path-filter validator cannot establish that no other workflow event keys exist.
- **Failed approach:** Inferring complete trigger authority from the selected push/PR path sequence alone.
- **Correction / executable recurrence guard:** [`a693483c`](https://github.com/m-shogo/memories-project/commit/a693483cd953c1fc9bac569c7db75d94aadd91c6) adds a CI-reachable read-only exact event-set check for both real workflows, with two positive and ten negative controls rejecting added, missing, quoted, duplicate, scalar and inline event forms. Only the negative validator changed (+45 lines); workflow YAML and production authorities were untouched.
- **Retry condition:** A legitimate new event requires review of workflow authorization, job permissions, external trigger scope, concurrency, path coverage, updated negative fixtures and exact-source CI. Do not retry unchanged MinIO, workflow permission, canonical large-learning transport or human approval blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40946430833](https://github.com/m-shogo/memories-project/actions/runs/40946430833) **SUCCESS** on exact source `a693483cd953c1fc9bac569c7db75d94aadd91c6`. Logs confirm append-only and contract PASS, 201 printed canonical negatives, 74 fanout synthetic cases, entry-document PASS and 1,186 helper-ancestor negative mutations. The ten nested event-set negatives are additional to the printed 201.
- **Why safe:** Only CI-reachable read-only validation changed; no real workflow, credential, production traffic, recovery evidence, readiness, registry or promotion change occurred.
- **Reusable mechanism:** Validate the entire workflow event-key set independently of per-event path-filter semantics; reject additional trigger sources before any workflow authority change.
- **Protected-authority check:** Compare shows exactly one changed read-only validator. Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` unchanged. `productionDecision=NO_GO`; registered/eligible generations remain 0/0 and all separate human/recovery/eight-domain gates remain unsatisfied and non-automatic.

## Next safe target

Pin the exact Upload Route step order and Publisher source-output `id` binding so command/action identities cannot be rearranged without review. Do not narrow the incomplete Go/Python trigger closure.
