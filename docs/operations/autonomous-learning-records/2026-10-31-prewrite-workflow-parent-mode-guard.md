# Supplemental OPS learning — prewrite workflow parent write authority (2026-10-31)

Append-only operational learning only. The canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or eligible environment-generation, approved recovery-objective, executable reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure risk and correction

- **symptom:** A checkout root, `.github` parent, or `.github/workflows` directory with group/world write permission could allow an unreviewed local principal to replace workflow source names even when individual YAML files are uniquely linked and read-only.
- **evidence:** Source inspection at baseline `6cbe25b08b97994269e72415038fcd970deec1d5` showed directory inode/ctime and symlink-swap checks, but no fail-closed write-mode check for the three in-checkout ancestors. This is a prospective local source-authority gap, not an observed production compromise.
- **rootCauseOrUnknown:** Verified missing `0o020`/`0o002` directory-mode predicates in the prewrite workflow matcher. Whether any deployed runner actually has an untrusted group member is unknown.
- **failedApproach:** Treating a stable inode/ctime snapshot and non-symlink leaf as sufficient to prove an immutable source pathname despite writable ancestor directory permissions.
- **correction:** [`972112ca`](https://github.com/m-shogo/memories-project/commit/972112ca606904c27a5045dd8ee369016192d208) checks all three ancestors for directory type and rejects world/group writable modes with distinct diagnostics before enumerating workflows. Outer runner ancestors such as `/tmp` are intentionally outside this repository authority policy.
- **recurrenceGuard:** Six real-CLI negatives cover 3 ancestors × 2 unsafe modes (`0o777`/`0o775`); each case checks clean positive, exact canonical error and restoration positive. Fixture bytes are asserted to contain a real LF, not an escaped backslash-n. The canonical negative count is updated to reflect executed cases.
- **retryCondition:** Relax only after independent review of the checkout principal/group/ACL trust model, an explicit policy change, new positive/negative controls and exact-source CI. Do not retry unchanged MinIO HTTP 401, workflow-write permission, large canonical-learning transport or human-promotion blockers.

## Material success and protected-authority check

- **outcome:** Read-only guard and six executable negatives landed on `so` at `972112ca606904c27a5045dd8ee369016192d208`.
- **evidence:** [Autonomous Learning Guard #41079237916](https://github.com/m-shogo/memories-project/actions/runs/41079237916) completed SUCCESS for that exact SHA. Job logs report append-only PASS, learning contract PASS, **566 canonical fail-closed negatives**, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document PASS and read-only PASS.
- **whySafe:** Only `scripts/audit-memory-os-workflow-trigger-fanout.py` and `scripts/validate-autonomous-learning-system-negative.py` changed. All permission mutations are confined to disposable temporary checkouts. No workflow YAML, production runtime, traffic, credentials or recovery authority changed.
- **reusableMechanism:** Combine descriptor/source-byte identity and directory inode checks with explicit in-checkout ancestor write-authority rejection and real CLI fail/recovery controls.
- **protectedAuthorityCheck:** GitHub compare `6cbe25b0...972112ca` lists exactly the two read-only Python scripts; all ten previously protected authority paths are untouched, including canonical learning blob `b809c69d` and contract blob `87712ea9`. Canonical learning content was not fully transported in this session; blob identity is not a claim of full text retrieval.
- **production boundary:** Keep `productionDecision=NO_GO` and OPS-P0-007 prerequisites blocked. This record cannot create or satisfy any generation, objective, reviewed request, recovery evidence, typed eight-domain, independent review, final candidate or human promotion gate.

## Next safe target

Reject group/world writable workflow **leaf** sources in the same bounded descriptor reader, with strict/non-strict descriptor negatives and actual CLI negatives; continue independent Go/Python transitive dependency and pre-MinIO CI reachability audit without changing workflow YAML.
