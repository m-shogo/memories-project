# Supplemental OPS learning — Go block-comment import spoof rejection (2026-10-31)

Append-only operational learning only. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation/objective/request, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure mode and correction

- **symptom:** The line-anchored Go import inventory could count an `import`-shaped line inside a `/* ... */` comment as a compiled dependency. A removed executable import could be represented by a fake comment line, invalidating the source-edge proof.
- **evidence:** The prior parser matched `(?m)^[ \\t]*import` without lexical block-comment exclusion. Isolated positive and two negative fixtures now exercise ordinary comments, commented grouped imports and commented single imports. This is a static trust-boundary failure mode, not an observed production outage.
- **rootCauseOrUnknown:** Verified parser design gap: regex import extraction did not distinguish Go block comments from executable import declarations. No production impact is claimed.
- **failedApproach:** Treating the line-anchored regex import inventory as proof of compiled Go import identity without first rejecting comment-shaped import spoofing.
- **correction:** [f7a4118](https://github.com/m-shogo/memories-project/commit/f7a411884bb3431a8af5f03ea5131b88ed418c60) rejects any line-anchored `import` token within a Go block comment before computing the dependency set.
- **recurrenceGuard:** Two deterministic negative fixtures and one ordinary-comment positive run in the existing CI-bound `prove_upload_route_go_import_parser` suite; the existing source-path inventory remains fail-closed.
- **retryCondition:** Broaden lexical parsing only after reviewing real Go source forms, preserving fail-closed rejection, validating all fixture outcomes and exact-source direct plus nested CI within the unchanged 120-second deadline. Do not retry unchanged MinIO HTTP 401 or blocked workflow writes.

## Material success

- **outcome:** Commented import lines are no longer accepted as compiled import edges by the scoped read-only Upload Route Go parser.
- **evidence:** Exact-source [Autonomous Learning Guard #41098029762](https://github.com/m-shogo/memories-project/actions/runs/41098029762) for `f7a411884bb3431a8af5f03ea5131b88ed418c60` completed **SUCCESS**. Logs: append-only PASS, learning contract PASS, direct and nested **601** canonical fail-closed cases PASS, 195 fanout synthetic cases PASS, 1,186 helper ancestor negatives PASS, entry-document and read-only checks PASS. The two parser-specific new negatives are included in the suite but not separately added to the canonical CLI case count.
- **whySafe:** Only the read-only negative validator changed; no Go source, workflow YAML, external MinIO, credentials, traffic or production recovery authority was modified.
- **reusableMechanism:** Reject syntactically non-executable import-shaped text before treating regex-extracted source edges as a dependency graph; retain an executable spoof negative and avoid conflating static graph evidence with CI reachability.
- **protectedAuthorityCheck:** Commit `f7a4118` changed exactly `scripts/validate-autonomous-learning-system-negative.py`. Canonical learning blob `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six protected generation/objective/request/evidence/non-resurrection/promotion registry blobs are unchanged.

## Remaining boundaries and next safe target

The Go parser still needs a separately reviewed raw-string-literal spoof guard. Complete Go/Python transitive dependency closure, all Push/PR CI trigger reachability and independent pre-MinIO focused Go regression proof remain unproven. Canonical learning full-text transport is unavailable; supplemental history cannot substitute. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no human-approved current recovery objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain coverage, independent review or human promotion.
