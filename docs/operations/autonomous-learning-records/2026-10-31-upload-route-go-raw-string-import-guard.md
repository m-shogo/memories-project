# Supplemental OPS learning — Go raw-string import spoof rejection (2026-10-31)

Append-only operational learning only. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective/request, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure mode

- **symptom:** A Go raw backtick string can contain a line beginning `import "package"`. The reviewed regex-based source graph previously counted that documentation text as a compiled import edge.
- **evidence:** A disposable local Go 1.23.2 fixture containing a raw-string fake `import "fmt"` and a block-comment fake `import "os"` compiled successfully with `GO111MODULE=off go test ./...`, confirming neither was a real import. The prior line-anchored regex would match the raw-string line. No production impact is asserted.
- **rootCauseOrUnknown:** Verified lexical mismatch: the Go import inventory parsed line shape without excluding multiline backtick literals. This is separate from the block-comment spoof already guarded in `f7a4118`.
- **failedApproach:** Inferring executable Go imports from regex matches without excluding import-shaped text inside raw strings.
- **correction:** [1d6214b](https://github.com/m-shogo/memories-project/commit/1d6214bfb1cfe82c33e47dea4c1ef771b97f8ada) rejects line-anchored `import` inside a backtick-delimited raw string before extracting package edges.
- **recurrenceGuard:** Two deterministic negative fixtures (raw single and grouped fake imports) and a normal raw-string positive are executed in the existing CI-bound parser suite. No new subprocess or timeout expansion.
- **retryCondition:** Replace this conservative lexical rejection only after source-specific Go syntax review, equivalent negative coverage, full direct/nested exact-source CI PASS within the unchanged 120s nested timeout, and protected authority parity. Unchanged MinIO 401 and workflow permission blockers are not retried.

## Material success

- **outcome:** Raw-string documentation cannot impersonate compiled Go import edges in the scoped read-only Upload Route source inventory.
- **evidence:** Exact-source [Autonomous Learning Guard #41098802559](https://github.com/m-shogo/memories-project/actions/runs/41098802559) for `1d6214bfb1cfe82c33e47dea4c1ef771b97f8ada` completed **SUCCESS**. Direct and nested negative suite both reported **601** canonical fail-closed cases; 195 fanout synthetic cases, 1,186 helper ancestor negatives, learning contract, append-only, entry-document and read-only checks PASS. The two parser-specific fixtures are included in the suite but not separately counted as canonical CLI cases.
- **whySafe:** Only the existing read-only Python negative validator changed; no Go source, workflow YAML, production credential/traffic, MinIO startup, recovery evidence, human approval or promotion was executed.
- **reusableMechanism:** Distinguish executable import declarations from comment/raw-string examples before treating a static path inventory as compilation-input evidence; retain explicit spoof negatives and do not equate source identity with Push/PR trigger closure.
- **protectedAuthorityCheck:** Code commit `1d6214b` changed only `scripts/validate-autonomous-learning-system-negative.py`. Canonical learning blob `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and all six protected generation/objective/request/evidence/non-resurrection/promotion registries remain unchanged.

## Remaining blockers and next safe target

Complete transitive Go/Python source closure and all Push/PR trigger reachability remain unproven. The scoped Import API Security Slice starts MinIO before Go tests; the unchanged external MinIO HTTP 401 and workflow-write permissions prevent independent focused Go CI proof. Canonical learning full text was not retrieved; its immutable blob identity is known and supplemental learning cannot substitute. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no current human-approved recovery objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain non-resurrection coverage, independent review or human promotion. Next: measure and design a bounded actual-source classifier that reuses workflow source snapshots without repeating the failed five-subprocess approach.
