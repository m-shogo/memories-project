# Memory OS rollback rehearsal admission

## Purpose

This runbook defines admission to an isolated rollback rehearsal. Admission is a planning record only. It does not execute rollback, change traffic, approve a release or create production evidence.

## Candidate is not a release

A historical candidate, branch head, tag or CI compatibility PASS is not an approved source or rollback target. Both sides of the rehearsal must already exist in `release-baseline-registry.v1.json` as distinct approved production release baselines.

## Required release pair

The source release is the version being rehearsed as the active version. The rollback target is the previously approved version to which the application would return. The target must have `rollbackEligibility.status` equal to `ELIGIBLE` or `CONDITIONALLY_ELIGIBLE` and `verified` equal to `true`.

A conditional target carries every unresolved condition into the rehearsal stop conditions. Admission is rejected when a condition is omitted or weakened.

## Required environment boundary

The request must state:

- `environmentClass`: `ISOLATED_NON_PRODUCTION_REHEARSAL`
- production traffic forbidden
- production credentials forbidden
- synthetic or approved sanitized data only
- automatic promotion forbidden
- destructive down migration forbidden

No request may route user traffic, alter a production database or automatically approve recovery.

## Required evidence

Entry criteria must reference repository evidence for:

- approved source and rollback-target release records
- mixed-version and persisted-state compatibility
- database recovery point and restore verification
- retained parser artifacts and exact object versions
- migration operation and forward-fix decision procedure
- monitoring, stop conditions and evidence preservation

The request must retain the exact release IDs, tags and commit SHAs from the approved registry. All entry-criteria, recovery-point, forward-fix, artifact and approval evidence files are bound to exact committed `HEAD` bytes and stored in the request's append-time SHA-256 evidence map. Later byte drift invalidates the historical request authority.

## Required approvals

Two distinct operational pseudonyms are required:

- `RELEASE_OWNER`
- `DATABASE_RECOVERY_OWNER`

Each `approvers` entry contains exactly `role`, `approverRef` and `approvalEvidenceRef`. `approvalEvidenceRef` must point to a tracked JSON file under `docs/evidence/rollback-rehearsal/approvals/` using schema `memory-os-rollback-rehearsal-approval.v1`.

Each approval document must bind exactly to the request's `rehearsalId`, `sourceReleaseId`, `rollbackTargetReleaseId`, review role and reviewer pseudonym. Its decision must be `APPROVED`, its approval timestamp must not predate the request, and `productionTraffic`, `productionCredentials` and `automaticPromotion` must all remain `false`.

These approvals authorize an isolated rehearsal request only. They do not authorize production traffic, release promotion, rollback execution or incident closure. The system never creates these human approval documents automatically.

## Stop conditions

The request must stop before mutation or traffic movement when any of the following is true:

- source or target identity differs from the approved registry
- rollback eligibility is absent, expired or conditional terms are incomplete
- required binary, parser artifact or exact object version is missing
- database recovery point is unavailable or incoherent
- destructive schema contraction would be required
- tenant isolation, deletion fencing, idempotency or session authority is ambiguous
- monitoring, evidence capture or human command authority is incomplete

## Current state authority

The approved release registry and append-only rollback rehearsal registry are the
sole authorities for the current approved-release count, rollback-eligible
release count, admissible release-pair count and reviewed rehearsal-request
count. Those values may progress only through their reviewed writers and this
runbook never supplies or overrides them.

A reviewed rehearsal request is planning authority only. Even when an admissible
release pair and reviewed request exist, `rehearsalExecuted`, independent review,
production evidence, production readiness, production credentials and production
traffic remain separate authorities and are never inferred from admission.

Production remains **NO_GO**.
