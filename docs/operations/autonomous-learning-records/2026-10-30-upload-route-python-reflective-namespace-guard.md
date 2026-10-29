# Supplemental OPS learning — Python reflective namespace guard (2026-10-30)

Append-only supplemental history only; canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure / identified static escape

- **Symptom:** The four reviewed Upload Route Python validators could introduce unreviewed runtime dependencies via `globals()`, `locals()`, `vars()`, `getattr()`, `setattr()`, `delattr()`, `__builtins__` or `__loader__` while preserving direct import/path fingerprints.
- **Observed evidence:** Existing AST scanner covered direct imports, selected `os`/ `sys.modules` reflection and process calls, but not these generic namespace primitives. Read-only inspection found no such primitives in the four real validators. Eight synthetic source shapes parse successfully and previously escaped the reviewed dynamic-dependency predicate; no production execution was observed.
- **Verified root cause:** Direct import and selected module-specific AST predicates do not exhaust reflective namespace and loader resolution.
- **Failed approach:** Treating stable import/path SHA and `os`-specific reflection guards as proof that arbitrary runtime namespace access was absent.
- **Correction / executable recurrence guard:** [`3b3cdef5`](https://github.com/m-shogo/memories-project/commit/3b3cdef5fea3433471a5c42653c3731f3e7a0bc7) conservatively rejects the six generic reflective call names and direct `__builtins__`/`__loader__` references, with eight CI-bound negative fixtures. Existing positive controls retain ordinary `os.path.basename`, `sys.stderr` and reviewed path usage. This remains bounded AST checking, not a complete dataflow/runtime closure.
- **Retry condition:** Re-review any legitimate reflective access with explicit runtime/dependency evidence, exact-source CI, deterministic baseline and protected-authority comparison. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical large-learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40939224003](https://github.com/m-shogo/memories-project/actions/runs/40939224003) completed **SUCCESS** on exact source `3b3cdef5fea3433471a5c42653c3731f3e7a0bc7`. Logs confirm contract PASS, 201 printed fail-closed negatives, 74 fanout synthetic, 1186 helper-ancestor negatives, append-only, entry-document and read-only PASS. The eight new nested negatives are not separately included in the printed 201.
- **Why safe:** Only read-only `scripts/validate-autonomous-learning-system-negative.py` changed (+16 lines). No production service, workflow trigger, credentials, traffic, generation/objective, reviewed requests, recovery evidence, typed non-resurrection, independent review or human promotion changed.
- **Reusable mechanism:** Reject unreviewed reflective execution mechanisms by AST shape, with exact-diagnostic negative fixtures and positive controls; preserve static-closure limits explicitly.
- **Protected-authority check:** After code commit, canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and all protected generation/objective/drill/evidence/non-resurrection/promotion registries were unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations, human-approved current objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records, final candidates and human promotion remain zero. Preflight requires distinct unsuperseded semantically eligible environments and explicitly human-approved current objective; reviewed requests remain planning-only, new evidence request-bound, independent review and promotion separate.

## Next safe target

Add AST capture-pattern binding identity checks for Python `match` cases, then continue Go/Python dependency closure audit without narrowing Upload Route triggers.
