# Supplemental OPS learning — Upload Route Python imported-binding shadow guard (2026-10-30)

Append-only supplemental history only. Canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under mandatory `contracts/operations/autonomous-learning-system.json`. This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure / discovered semantic proof gap

- **Symptom:** Four reviewed Python validator import fingerprints could remain unchanged while imported runtime bindings (`Path`, `json`) are shadowed by assignments, deletions, declarations or parameters.
- **Observed evidence:** The prior import checker pinned 6/6/5/9 top-level imports and rejected nested imports but did not scan AST stores, deletions or declarations. Synthetic `Path = lambda value: value` leaves the import SHA unchanged. No actual production drift was observed.
- **Verified root cause:** Import declaration identity does not imply unchanged runtime name binding.
- **Failed approach:** Treating stable import-name/alias SHA-256 as sufficient evidence of stable imported-object resolution.
- **Correction / executable recurrence guard:** [`045184fa`](https://github.com/m-shogo/memories-project/commit/045184fa046fed6321209842c2b94911727b236d) rejects AST `Store`/`Del`, function/async-function/class declarations, parameter names and exception aliases that shadow imported bindings. Nine synthetic negatives run in the CI-reachable existing suite. This does not prove reflective namespace mutations or full runtime dependency closure.
- **Retry condition:** Legitimate imported-name rebinding requires explicit execution/dependency review, updated baseline, exact-source CI and protected-authority check. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical large-learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40938648233](https://github.com/m-shogo/memories-project/actions/runs/40938648233) completed **SUCCESS** on exact source `045184fa046fed6321209842c2b94911727b236d`. Logs show contract PASS, 201 printed fail-closed cases, 74 fanout synthetic cases, 1186 helper-ancestor negatives, append-only, entry-document and clean-source/read-only PASS. The nine new nested negatives are not separately included in the printed 201.
- **Why safe:** Only read-only `scripts/validate-autonomous-learning-system-negative.py` changed (+32 lines). No workflows, production services, credentials, traffic, recovery authorities, evidence or promotion were changed.
- **Reusable mechanism:** Independently verify import declaration identity and binding identity with synthetic digest-preserving semantic mutations.
- **Protected-authority check:** Post-code-commit tree verified unchanged canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and all six protected registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations, human-approved current objectives, executable reviewed requests, request-bound evidence, typed eight-domain records, final candidates and human promotion remain zero. Preflight requires distinct unsuperseded semantically eligible environments plus human-approved current objective; reviewed requests remain planning-only, new evidence is request-bound, independent review and human promotion are separate.

## Next safe target

Reject Python adjacent/escaped literal runtime paths that evade raw-source path fingerprints. Retain the 109-input/81-uncovered lower-bound distinction and do not narrow Upload Route triggers without complete dependency closure.
