# Supplemental OPS learning — Upload Route toolchain resolver environment guard (2026-10-30)

Append-only supplemental history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under `contracts/operations/autonomous-learning-system.json`. This cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure / workflow-level static proof gap

- **Symptom:** Upload Route Python/Go dependency resolution can be changed through workflow-level `PYTHONPATH`, `GOWORK`, `GOFLAGS`, `GOPATH`, `GOMODCACHE`, `GOENV` and related environment overrides without changing source import/path inventories.
- **Observed evidence:** Both reviewed Upload Route Publisher/PR workflows currently have no matching toolchain override identifiers. Previous static guard pinned Go/Python source imports and workflow event paths but did not scan the workflow environment/step text for these resolver inputs. This was a prospective drift escape, not observed production behavior.
- **Verified root cause:** Source-level import fingerprints do not bind toolchain environment and resolver configuration.
- **Failed approach:** Treating a stable 109-path static source inventory as sufficient evidence of unchanged workflow-level dependency resolution.
- **Correction / executable recurrence guard:** [`8bbfcb1e`](https://github.com/m-shogo/memories-project/commit/8bbfcb1edabdc515c39a9ae7a7d3339efd2f3848) adds a read-only conservative workflow-source check rejecting 13 unreviewed Python/Go resolver environment identifiers, including `GITHUB_ENV`. It executes on both actual Upload Route workflows and 13 synthetic negatives; a normal database URL environment remains a positive control. This lexical guard is not a complete toolchain/runtime closure and does not claim third-party action behavior.
- **Retry condition:** Review any legitimate new resolver environment or workflow step with real Go/Python dependency impact, updated deterministic baseline, exact-source CI and protected-authority check. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical large-learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40940201972](https://github.com/m-shogo/memories-project/actions/runs/40940201972) **SUCCESS** on exact source `8bbfcb1edabdc515c39a9ae7a7d3339efd2f3848`. Logs confirm contract PASS, 201 printed fail-closed negatives, 74 fanout synthetic, 1186 helper-ancestor negatives, append-only, entry-document and read-only PASS. The 13 new nested negatives are not separately included in the printed 201.
- **Why safe:** Only the CI-reachable read-only negative validator changed (+34 lines); neither Upload Route workflow nor production code, credentials, traffic, generation/objective, reviewed requests, recovery evidence, typed eight-domain records, independent review or promotion was modified.
- **Reusable mechanism:** Validate workflow-level toolchain resolver inputs independently from source-level import and path identity, with negative controls and exact-source CI.
- **Protected-authority check:** Post-code-commit canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and protected registries unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations, human-approved current objectives, executable reviewed requests, generation evidence, complete typed eight-domain records, final candidates and human promotion remain zero. Preflight requires distinct unsuperseded semantically eligible environments and explicit human-approved current objective; reviewed requests remain planning-only, new evidence request-bound, independent review and promotion separate.

## Next safe target

Review mutable third-party action refs in Upload Route workflows and preserve fail-closed checks for any new action identities; do not change workflow YAML or narrow triggers until existing external blockers and complete dependency proof are addressed.
