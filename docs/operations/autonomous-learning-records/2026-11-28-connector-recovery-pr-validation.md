# Supplemental OPS learning — bounded connector recovery (2026-11-28)

Operational learning only; never production evidence, readiness, backup/restore, RPO/RTO/skew, drill, credential, traffic or promotion authority. Canonical history remains unchanged.

## Material failure
- **Symptom / evidence:** Canonical history fetch_file returned empty content with blob b809c69dda5d788245abd2a79b34c6e8c1d6c628; fetch_blob returned 4,171,820 characters. Canonical tail records the earlier full-content h2 protocol failure and unchanged ref/blob.
- **Root cause or unknown:** Transport/payload cause unknown. The prior diagnostic run reported missing-ref HTTP 422 and a generic GraphQL error for a stale expected SHA; CAS is not established.
- **Failed approach:** Full-content Contents write; updating a nonexistent ref; assuming an isolated branch push matches so-only CI.
- **Correction / recurrence guard:** Resolve fresh commit/tree independently, use bounded new regular files in the existing supplemental scope, create branch explicitly, verify exact readback and compare changed paths. Existing all-parent history validator rejects modifications/deletions; existing CI checks canonical prefix and PR merge parents. Do not weaken these checks.
- **Retry condition:** Retry large transport only after capability changes; retry CI only with a qualifying PR or verified authorized dispatch. Generic errors are not proof of CAS.

## Material success
- **Outcome / evidence:** This run read so d282e84af521aa577097a4694e5981e0f26f694d, tree 3ea1fa0f783e59c222a4a43559bf11f874c85a6f, mandatory contract and canonical blob, and verified the existing workflow and supplemental validator source. Earlier diagnostic commit 9c2fac344d8bda1eb39aa93a88a99969c8f682ac was reported as isolated write/readback; runtime CI remains unverified.
- **Why safe / reusable mechanism:** Use a fresh branch based on current so and add only this record. Preserve all existing bytes and workflow definitions; use PR review rather than unproven CAS. No automatic merge.
- **Protected-authority check:** Proposed change is one new learning file only; verify actual diff and canonical blob after commit. NO_GO and OPS-P0-007 gates must not change.

## External evidence and experiment
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow (retrieved 2026-11-28): token-triggered PR runs may require approval; actual credential type unknown.
- https://github.com/github/docs/blob/main/content/actions/reference/workflows-and-actions/events-that-trigger-workflows.md (retrieved 2026-11-28): PR CI uses synthetic merge SHA, not necessarily head SHA; branch and path filters both apply. Verify run and merge parent identities, not just a head status.
- https://www.reddit.com/r/git/comments/1ecplap (2024-07-26): community discussion corroborates distinction, not authoritative.
- Experiment: open a bounded PR targeting so with this new record only, inspect run status and exact merge parents; do not claim PASS until observed. If approval is required, preserve the PR and request authorized review rather than bypassing it.
