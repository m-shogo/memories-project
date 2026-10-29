# Supplemental OPS learning — Python adjacent/escaped literal path guard (2026-10-30)

Append-only supplemental history only; canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under `contracts/operations/autonomous-learning-system.json`. This cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure / static proof gap

- **Symptom:** Python can combine adjacent string tokens or decode escaped characters into new repository-relative runtime input paths without adding a complete raw quoted `contracts/...` or `docs/...` string.
- **Observed evidence:** An isolated Python AST/regex reproduction accepted `Path("con" "tracts/operations/new.json")` and `Path("\\u0063ontracts/operations/new.json")` under the previous raw-literal digest despite different AST-resolved paths. This was a potential future escape, not observed production drift.
- **Verified root cause:** The existing raw-source literal regex did not account for Python's compile-time adjacent-string concatenation and escape decoding.
- **Failed approach:** Treating complete raw quoted path literals as the only relevant static string constants.
- **Correction / executable recurrence guard:** [`167cd9f1`](https://github.com/m-shogo/memories-project/commit/167cd9f17bedcd8f81f08e4dde467e0be964e332) independently checks that every AST constant starting with a reviewed repository root exists in the exact raw-literal set. Four negatives cover adjacent Path, adjacent division, Unicode and hex escapes. The exact 4/5/6/11 source-literal counts and SHA fingerprints remain in force.
- **Retry condition:** Rebaseline only after reviewing a legitimate new input and its runtime source/trigger closure, with exact-source CI and protected-authority comparison. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical large-learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40938966213](https://github.com/m-shogo/memories-project/actions/runs/40938966213) **SUCCESS** on exact source `167cd9f17bedcd8f81f08e4dde467e0be964e332`. Logs confirm contract PASS, 201 printed fail-closed negatives, 74 fanout synthetic, 1186 helper-ancestor negatives, append-only, entry-document and read-only PASS. The four new nested negatives are not included separately in the printed 201.
- **Why safe:** Only the existing read-only learning negative validator changed (+13 lines); no Upload Route workflow, production source, credentials, traffic, generation/objective, reviewed requests, recovery evidence, typed eight-domain record, independent review or promotion was modified.
- **Reusable mechanism:** Compare compiler-resolved AST string constants with raw-source fingerprints to detect static path construction that source-text-only scanners miss.
- **Protected-authority check:** After code commit, canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and protected generation/objective/drill/evidence/non-resurrection/promotion registries were unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations, human-approved current objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records, final candidates and human promotion remain zero. Preflight still requires distinct unsuperseded semantically eligible generations and human-approved current objective; reviewed requests remain planning-only, new evidence remains request-bound, independent review and promotion remain separate.

## Next safe target

Review reflective Python namespace and dynamic loader escape routes while preserving the 109 reviewed static inputs/81 uncovered-per-workflow lower bound. Do not narrow triggers without complete dependency closure.
