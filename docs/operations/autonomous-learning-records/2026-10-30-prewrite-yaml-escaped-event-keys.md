# Supplemental OPS learning — escaped YAML event keys and values (2026-10-30)

Append-only supplemental learning under the unchanged `contracts/operations/autonomous-learning-system.json`. The canonical learning authority remains separate. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion gates.

## Material semantic failure and correction

- **symptom:** The read-only prewrite workflow fanout parser could undercount a GitHub Actions push/PR event whose YAML double-quoted root key, event key or inline event value uses Unicode escapes.
- **evidence:** YAML double-quoted scalar escapes can turn `"o\\u006e": push` into an `on` mapping key and `on: "p\\u0075sh"` into a push event. The prior lexical parser required visible `^on:` or literal push/PR names and therefore did not recognize these spellings. This was a static source defect, not observed production execution.
- **rootCauseOrUnknown:** Verified mismatch between raw YAML lexical scanning and decoded double-quoted scalar semantics. No external cause is asserted.
- **failedApproach:** Treating the absence of literal `on` or push/PR text as proof that a workflow cannot be triggered.
- **correction:** [`7fe49f45`](https://github.com/m-shogo/memories-project/commit/7fe49f4564e4236d6cd6e59bc4c55aaf06ffd124) conservatively flags escaped double-quoted root keys, inline `on` values and nested event keys as potentially triggering. A plain quoted unrelated root key remains a negative control.
- **recurrenceGuard:** Five new synthetic and five actual CLI fixtures exercise escaped root, escaped inline, escaped inline-array, escaped nested key and unrelated quoted-root cases. The ordered fixture-identity pins now require 57 auditor and 40 CLI cases.
- **retryCondition:** Replace conservative matching only with an independently validated YAML parser and tests proving equivalent GitHub Actions semantics, including ambiguous escapes. Do not retry unchanged MinIO, canonical learning transport, workflow-write permission or human-promotion blockers.

## Material success and protected authority

- **outcome/evidence:** [Autonomous Learning Guard #40913322945](https://github.com/m-shogo/memories-project/actions/runs/40913322945) completed **SUCCESS** on exact source `7fe49f4564e4236d6cd6e59bc4c55aaf06ffd124`. Logs show **194** autonomous learning negatives, **67** prewrite fanout synthetic cases, **1,186** helper-ancestor negatives, append-only and contract PASS, and 9 shared-entrypoint direct matches classified `BLOCKED_KNOWN_WRITER_CAS`.
- **whySafe:** Only the read-only prewrite auditor and its existing CI-bound negative suite changed. No workflow triggers, production services, credentials, traffic, recovery evidence or human promotion authority changed.
- **reusableMechanism:** Ambiguous YAML escape spellings are treated as possible triggers rather than false non-matches, with real CLI fixtures and exact fixture-identity reconciliation.
- **protectedAuthorityCheck:** Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and all six protected registries remained unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records, final candidates and human promotion reviews.
- **limitation:** The canonical learning file's contents remain too large for the connector to return; only its blob identity was verified. A direct fanout match is not transitive workflow-call proof or permission to edit production/workflow authorities.
- **nextSafeTarget:** Perform an independent read-only audit of remaining workflow trigger grammar and Upload Route dependency closure; avoid broad workflow-trigger changes until coverage is demonstrated.
