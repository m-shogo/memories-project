# Supplemental OPS learning — Python match capture binding guard (2026-10-30)

Append-only supplemental history only; canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy is `contracts/operations/autonomous-learning-system.json`. This cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure / semantic guard gap

- **Symptom:** Python `match` capture patterns can shadow imported `Path` or `json` bindings without an AST `Name(Store)` node, leaving the reviewed import fingerprint unchanged.
- **Observed evidence:** Isolated Python AST parsing showed `case Path:` and `case [1] as Path:` bind through `MatchAs.name`, `case [*json]:` through `MatchStar.name`, and `case {**Path}:` through `MatchMapping.rest`. The earlier binding guard checked Store/Del, declarations, parameters and exception aliases but not these fields. None of the four real validators has a live match statement; this is a prospective escape, not observed production drift.
- **Verified root cause:** Python pattern capture bindings are stored as string fields in AST pattern nodes rather than conventional Store contexts.
- **Failed approach:** Assuming AST Store/Del and declaration nodes exhaust imported-name rebinding.
- **Correction / executable recurrence guard:** [`b3e444d5`](https://github.com/m-shogo/memories-project/commit/b3e444d5bb0a50bd762dd1409a48c79e75930f02) rejects imported-name captures in `MatchAs`, `MatchStar` and `MatchMapping`. Four negative controls and one benign nonimported capture positive control run in the existing CI-bound validator.
- **Retry condition:** Permit legitimate capture of an imported name only after reviewed source/runtime input audit, deterministic baseline update, exact-source CI and protected-authority verification. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical large-learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40939521714](https://github.com/m-shogo/memories-project/actions/runs/40939521714) **SUCCESS** on exact source `b3e444d5bb0a50bd762dd1409a48c79e75930f02`. Logs confirm contract PASS, 201 printed fail-closed negatives, 74 fanout synthetic, 1186 helper-ancestor negatives, append-only, entry-document and read-only PASS. Four new nested negatives are not separately included in the printed 201.
- **Why safe:** Only the read-only negative validator changed (+11 lines); no workflow trigger, production code, credentials, traffic, generation/objective, reviewed requests, recovery evidence, typed eight-domain records, independent review or promotion changed.
- **Reusable mechanism:** Check AST capture-specific binding fields in addition to conventional Store/Del when protecting imported-name identity.
- **Protected-authority check:** Post-code-commit canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and all protected registries unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations, human-approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records, final candidates and human promotion remain zero. Preflight still requires distinct unsuperseded semantically eligible environments and explicit human-approved current objective; reviewed requests remain planning-only, evidence request-bound, independent review and human promotion separate.

## Next safe target

Reject unreviewed Python `sys.path` and import-hook mutations that could change module resolution without changing import declarations. Preserve the 109-input/81-uncovered lower bound and do not narrow Upload Route triggers without complete closure.
