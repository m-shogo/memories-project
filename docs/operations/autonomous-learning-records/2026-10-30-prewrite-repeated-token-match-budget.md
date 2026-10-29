# Supplemental OPS learning — repeated-token prewrite match-pair budget (2026-10-30)

Append-only supplemental learning only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under mandatory `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure / prospective adversarial comparison complexity

- **Symptom:** The existing 4,096-line prewrite ceiling still permits thousands of identical lines in both baseline and candidate; `difflib.SequenceMatcher(autojunk=False)` can then have a large repeated-token match search space even when the byte/line limits are satisfied.
- **Observed evidence:** A disposable 805/806-line baseline/candidate with 800 identical comment lines each produces **640,005** potential equal-line pairs, despite remaining under the 4,096-line ceiling. The real checked-in 3,566-line negative validator produces approximately 68,806 self-match pairs and the 2,780-line entrypoint approximately 12,646. No actual CI timeout was observed; this is prospective resource exhaustion.
- **Verified root cause:** Line count bounds sequence length, not repeated-token match density; `autojunk=False` disables the standard frequent-token heuristic.
- **Failed approach:** Treating the 4,096-line ceiling alone as a complete bound on diff matching work.
- **Correction / executable recurrence guard:** [`85cf108e`](https://github.com/m-shogo/memories-project/commit/85cf108e1a021a6b4945c729e1d36ab6900c8071) adds a deterministic pre-comparison `Counter` check: sum of baseline and candidate frequencies multiplied per shared line must be at most **500,000**. A new dense-line negative proves the 640,005-pair fixture is rejected before `SequenceMatcher`; existing large-source CLI positives still pass. This is a conservative match-density bound, not a proof of worst-case wall-clock time for all admitted inputs.
- **Retry condition:** Revisit the threshold only after reviewing actual source token frequencies, adversarial runtime tests, exact-source CI and protected-authority checks. Do not retry unchanged MinIO 401, workflow-write permission, canonical learning large-file append or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40957301802](https://github.com/m-shogo/memories-project/actions/runs/40957301802) completed **SUCCESS** on exact source `85cf108e1a021a6b4945c729e1d36ab6900c8071`. The code commit modified only `scripts/validate-autonomous-learning-system.py` (+16/-1 lines), and all exact-source learning contract, negative, helper ancestor, append-only and clean read-only CI steps passed.
- **Why safe:** The new check is a read-only resource guard for disposable prewrite inputs. No workflow YAML, Go service, MinIO, credentials, traffic, production data, recovery evidence, generation, objective, drill, typed non-resurrection, independent review or promotion authority changed.
- **Reusable mechanism:** Bound the potential matching-token cross product before invoking a potentially superlinear diff engine, independently of input byte and line ceilings.
- **Protected-authority check:** Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, mandatory contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and reviewed generation/objective/evidence/promotion registry blob identities remain unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, zero registered/semantically eligible generations and no approved recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Audit remaining prewrite semantic-shadow and resource-boundary cases with independent executable negatives, while separately preserving the known source-only Go CI trigger gap. Do not narrow Upload Route workflow triggers without complete dependency closure and authorization.
