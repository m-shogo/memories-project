# Supplemental OPS learning — live-test Go peer diagnostics and global closure distinction (2026-10-31)

Append-only operational learning only; not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence. Canonical learning and its mandatory contract remain unchanged.

## Material diagnostic gap and corrected scope

- **symptom:** Selected HTTP live-test Go dependencies `pgrepo`, `objectstore` and `previewcommit` lacked dedicated, source-specific missing/extra peer and comment-spoofed import negatives in the scoped MinIO-first classification.
- **evidence:** The live test imports all three packages. Their eight current non-test Go files contain 14 local import edges: `pgrepo/accountcontrol.go` (accountdelete/dbscope/epochguard/pgscope/security), `pgrepo/apply.go` (apply/dbscope/pgscope), `pgrepo/upload.go` (dbscope/pgscope/upload), `objectstore/client.go` (upload), and `previewcommit/commitkey.go` plus `committer.go` (previewspool); `objectstore/erase.go` and `sigv4.go` have no local imports.
- **rootCauseOrUnknown:** The scoped negative diagnostic coverage was incomplete. Importantly, deeper inspection found that existing `prove_upload_route_go_direct_inputs` already walks the Go import graph and pins **109 inputs** and **722 per-file import entries**, with **81 focused-workflow-uncovered inputs**. Therefore the new checks are not the first proof of global static source closure; the unresolved gap is independent Push/PR pre-MinIO test execution.
- **failedApproach:** Initially treating selected new peer checks as closing an otherwise unguarded full Go dependency graph, before inspecting the pre-existing dynamic transitive closure and its exact digests. The correction is to state the narrower diagnostic benefit and prioritize CI reachability rather than duplicate global source-inventory assertions.
- **correction:** [Code commit 1b7a6f37](https://github.com/m-shogo/memories-project/commit/1b7a6f37deaa215675a507b898ae1a202a0fe027) adds explicit parsed live-test edges, exact source-peer inventories, package identity checks and local-import-set assertions for these three packages.
- **recurrenceGuard:** Three comment-spoofed live-test import negatives, six missing/extra package inventory negatives, and eight extra local-import negatives run in-process within the existing CI-bound validator. No additional subprocess was added. Existing global 109-input/722-import digest and 81-uncovered-input checks remain authoritative for broad static closure.
- **retryCondition:** Reconcile an actual changed import graph or source inventory with both global digest and scoped negatives, then run exact-source direct and nested CI. Do not claim independent pre-MinIO CI until authorized workflow triggers and execution order cover the complete Go/Python dependency set. Do not retry unchanged MinIO HTTP 401, workflow-write permission or canonical full-text transport blockers.

## Material success and safe publication

- **outcome:** Eight Go source identities and 14 local edges now have explicit deterministic peer-level diagnostics, complementing—not replacing—the pre-existing global closure digest.
- **evidence:** Exact-source [Autonomous Learning Guard #41138071888](https://github.com/m-shogo/memories-project/actions/runs/41138071888) for `1b7a6f37deaa215675a507b898ae1a202a0fe027` completed **SUCCESS** on 2026-10-31 JST: append-only PASS, learning contract PASS, **601** direct and **601** independently nested negatives, 195 fanout synthetic, 1,186 helper ancestor negatives, 52-workflow/63-command/204-fixture source-negative reachability, entry-document PASS and clean/read-only completion. In-process cases do not increase the displayed 601 count.
- **whySafe:** The code commit modifies only `scripts/validate-autonomous-learning-system-negative.py` (+93 lines); no Go source, workflow YAML, MinIO, credential, traffic, recovery evidence, generation/objective, review or promotion was changed.
- **reusableMechanism:** Combine broad graph-hash closure with narrow, explainable per-package negative diagnostics. Search the complete existing validator before treating a scoped assertion as new global coverage. Wait for active branch writers before publishing append-only learning.
- **protectedAuthorityCheck:** The code diff contains only the read-only validator; all ten protected authority blobs remain unchanged, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six protected registries. `productionDecision=NO_GO`; OPS-P0-007 remains blocked. Canonical learning blob identity is known, but full text could not be retrieved.

## Active-writer recurrence guard observed

Before this learning write, [Reconcile Metrics Authority #41138367758](https://github.com/m-shogo/memories-project/actions/runs/41138367758) was observed **in progress** on the same source HEAD. Publication was deferred, not retried against an unchanged active-writer precondition. The writer subsequently completed SUCCESS without advancing `so`; only then was HEAD, target absence and mandatory contract re-read. This avoided the known stale-writer CAS collision. No claim of writer-side production evidence is made.

## Next safe target

Prioritize executable Push/PR trigger closure and pre-MinIO focused Go regression independence. A read-only survey of workflow sources may identify other Go test paths, but no narrow test path should be promoted to complete coverage without matching all 109 known inputs and their Python dependencies. The supplemental learning trigger gap remains scoped to workflow permissions.
