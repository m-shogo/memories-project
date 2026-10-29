# Supplemental OPS learning — Upload Route action identity and mutable-ref boundary (2026-10-30)

Append-only supplemental history only; canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy is `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure / scoped supply-chain proof gap

- **Symptom:** The two Upload Route workflows could add, replace, duplicate, remove or reorder third-party action steps without changing the Go/Python source import fingerprints or event path patterns.
- **Observed evidence:** Read-only inspection found the same three actions in both workflows: `actions/checkout@v4`, `actions/setup-go@v5`, `actions/setup-python@v5`. The existing negative validator had no independent `uses:` step identity check. These references are **mutable tags**, not immutable commit SHAs; no evidence of upstream compromise or drift was observed.
- **Verified root cause:** Static source/dependency and trigger-path checks do not bind the workflow action identity/execution layer.
- **Failed approach:** Treating unchanged Go/Python source and trigger paths as sufficient proof that the workflow's third-party execution dependencies cannot change.
- **Correction / executable recurrence guard:** [`52e286da`](https://github.com/m-shogo/memories-project/commit/52e286da826f6db622fb880be7a91727b7ba01b0) checks the exact ordered three-action sequence in both actual workflows. Six synthetic negatives reject new/changed/missing/duplicate/reordered action steps. This guard pins **the reviewed references**, not the remote bytes behind mutable tags; it does not close the pre-existing mutable-ref supply-chain risk.
- **Retry condition:** Rebaseline only after independent review of action identity, pinned immutable SHA and workflow source impact, with exact-source CI, known MinIO/permission blockers handled and protected-authority comparison. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permission, canonical large-learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40940542380](https://github.com/m-shogo/memories-project/actions/runs/40940542380) **SUCCESS** on exact source `52e286da826f6db622fb880be7a91727b7ba01b0`. Logs show contract PASS, 201 printed fail-closed negatives, 74 fanout synthetic, 1186 helper-ancestor negatives, append-only, entry-document and read-only PASS. Six new nested negatives are not separately counted in the printed 201.
- **Why safe:** Only the CI-reachable read-only negative validator changed (+36 lines); no workflow YAML, external action, production code, credentials, traffic, generation/objective, reviewed request, recovery evidence, typed eight-domain records, independent review or promotion was changed.
- **Reusable mechanism:** Fingerprint workflow action identity/order independently of trigger and source dependency identity; explicitly separate checked reference identity from immutable third-party code provenance.
- **Protected-authority check:** Post-code-commit canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and protected registries unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations, approved current objectives, executable reviewed requests, generation evidence, complete typed eight-domain records, final candidates and human promotion remain zero. Preflight requires distinct unsuperseded semantically eligible environments and explicit human-approved current objective; reviewed requests remain planning-only, new evidence request-bound, independent review and promotion separate.

## Next safe target

Audit GitHub Actions workflow shell/step runtime dependency surfaces and the remaining Go/Python/toolchain closure; do not mutate Upload Route YAML or narrow triggers while MinIO/permission and full-closure blockers remain.
