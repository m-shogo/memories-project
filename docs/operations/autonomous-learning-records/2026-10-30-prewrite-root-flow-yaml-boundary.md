# Supplemental OPS learning — flow-style workflow root fanout (2026-10-30)

Append-only supplemental history only. Canonical learning authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. This record is NOT production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective direct-trigger undercount

- **Symptom:** The conservative prewrite workflow fanout matcher could report no direct push/PR trigger for a YAML document whose root mapping is flow-style, such as `{"on": ["push"]}`, because it searches only for block-style root `on:` and nested event keys. This is a prospective static-parser defect, not an observed production incident.
- **Observed evidence:** The pre-change `workflow_matches_path` source has no flow-style root detection; source review shows that a root JSON-compatible flow mapping lacks every block-style regex anchor. Five focused Python reproductions of the new first-document guard returned expected results (4 conservative matches and 1 nested-JSON nonmatch); these are not an exact-source full CI run.
- **Verified root cause:** Narrow block-YAML trigger recognition silently treats an otherwise valid flow-style YAML root mapping as a non-match.
- **Failed approach:** Inferring dispatch-only/no-trigger solely from the absence of a literal root `on:` block key.
- **Correction:** [`868c0722`](https://github.com/m-shogo/memories-project/commit/868c0722bb7e3b133642813a9d0763c1f42e6cb1) conservatively treats a flow-style first document mapping as a possible direct trigger, including after YAML directives, comments and a document marker.
- **Executable recurrence guard:** [`db548021`](https://github.com/m-shogo/memories-project/commit/db548021d970862c34280de439b5bdca09981070) adds five ordered, identity-pinned positive/negative fixtures to the actual prewrite CLI suite, paired with the audit script's five self-test cases. A nested JSON block inside a dispatch-only workflow must not be mistaken for a root mapping.
- **Retry condition:** Revisit only if an exact-source CI run or reviewed YAML semantics reveal a concrete counterexample; do not weaken to a regex-only non-match. Full transitive workflow/Go/Python reachability remains unproven.

## Material failure — exact-source CI visibility limitation

- **Symptom:** This run cannot independently attest that the current two-commit source passed the GitHub Actions guard.
- **Observed evidence:** The connector's combined commit statuses for `db548021d970862c34280de439b5bdca09981070` returned an empty status list; its commit-workflow-run endpoint returned no runs and is documented to filter to PR-triggered runs. The workflow's push/PR paths do include the edited negative validator.
- **Root cause or explicit unknown:** Exact push-run visibility is unavailable through the exposed read endpoints; whether the push workflow passed is **unknown**, not a verified CI failure.
- **Failed approach:** Treating an empty combined-status response or a PR-only run list as proof of push CI success.
- **Correction:** Keep exact-source CI marked **UNVERIFIED**; do not claim PASS, production readiness or admission.
- **Recurrence guard:** Require a real run ID, exact source SHA and completed conclusion before recording CI success; do not substitute static fixture review or supplemental learning.
- **Retry condition:** A verified GitHub Actions run/check result for this exact SHA becomes accessible, or a permission-authorized CI listing endpoint is available.

## Material success — bounded read-only source hardening

- **Observed outcome and evidence:** Commits `868c0722` and `db548021` updated the conservative audit and its negative CLI validator. The GitHub compare from `9b4a49b1` to `db548021` reports exactly two modified read-only Python files, no production/authority files. Five local focused guard reproductions matched expectations; full exact-source CI is not yet observed.
- **Why safe:** The new behavior only increases conservative direct-trigger matches for ambiguous root flow mappings; it cannot generate credentials, traffic, evidence, production-equivalent generations, objectives or promotion decisions.
- **Reusable mechanism:** First-document YAML grammar guard plus paired self-test/actual-CLI positive and negative controls, with exact ordered fixture identity.
- **Protected-authority check:** The only branch changes are `scripts/audit-memory-os-workflow-trigger-fanout.py` and `scripts/validate-autonomous-learning-system-negative.py`. Canonical learning SHA remains `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract SHA `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`; the previously reviewed production status, OPS-P0-007 snapshot and six registries are untouched by this two-file diff. `productionDecision=NO_GO` and OPS-P0-007 `PREREQUISITES_BLOCKED` remain the governing posture; no new real recovery or human promotion authority is asserted.

## Limits and next safe target

The canonical learning file's full text remains unavailable via this connector (only blob SHA is returned). The audit script itself is still omitted from the Autonomous Learning Guard path filters, although the paired negative validator triggers it. The independent next targets are exact-source CI verification and Go/Python transitive input closure with MinIO-independent Go-only CI reachability. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permission or human-approval blockers.
