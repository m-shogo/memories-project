# Memory OS approved release baselines

This directory documents the authority boundary for production release
baselines. The machine-readable registry is:

- `contracts/operations/release-baseline-registry.v1.json`
- contract: `contracts/operations/release-baseline-registry-contract.v1.json`

## Candidate is not release

A commit is **not** an approved release because it:

- exists on `so` or `main`;
- has a tag;
- compiles;
- passes CI;
- passes a historical candidate compatibility drill;
- was deployed to a local, preview or canary environment.

Candidate and rejected-candidate evidence remains in its own registries. It must
never be copied into the approved release registry with a changed label.

## Required approval

Every release record requires three distinct approvers:

1. `SECURITY_REVIEWER`
2. `OPERABILITY_REVIEWER`
3. `RELEASE_OWNER`

One person cannot fill more than one required role for the same record. An
approval identifier is an operational pseudonym, not an email address or user
account identifier.

## Required immutable bindings

The record binds the exact release commit and tag to SHA-256 fingerprints of:

- the public API contract;
- canonical migration sequence;
- reviewed parser artifact set;
- runtime configuration schema.

Changing one of these surfaces requires a new release record. Existing records
are never edited to point at new bytes.

## Required evidence

Registration requires repository-relative evidence for:

- authorization, RLS and deletion invariants;
- approved old/current mixed-version compatibility;
- isolated restore and non-resurrection;
- migration recovery point and operator execution;
- parser artifact retention and replay;
- load, capacity, metrics and alert operation;
- open risks, owners and deadlines.

Local MinIO, ephemeral PostgreSQL and historical-candidate results can support
foundations, but cannot be relabeled as production evidence.

## Rollback eligibility

`ELIGIBLE` means the exact release can start against the expanded target schema
and preserve security, deletion, idempotency, parser artifact and object-version
invariants. `CONDITIONALLY_ELIGIBLE` requires explicit conditions in the record.
Unknown or incomplete evidence means `NOT_ELIGIBLE`.

A release stops being a rollback target when a destructive contract migration
removes a required surface, an artifact is no longer retained, or a security
invariant can no longer be proven. The existing record is not rewritten;
a later evidence record supersedes operational eligibility.

## Append-only procedure

1. Confirm exact clean repository HEAD.
2. Confirm release ID, tag and commit SHA have never been registered.
3. Verify all evidence paths and SHA-256 bindings.
4. Verify three distinct required approvers.
5. Generate one record through the reviewed writer.
6. Run the registry validator.
7. Commit the registry change for independent review.
8. Do not route production traffic until all separate production gates pass.

## Current state authority

The append-only release registry is the sole authority for the current approved
release count, approved predecessor availability and rollback-eligible release
availability. Those values may progress only through a valid reviewed registry
append; this document never supplies or overrides them.

A nonzero approved-release inventory is still only release-baseline authority.
It does not complete the separate integrated independent review, authorize
application production readiness, change credentials, or route production
traffic. Production remains **NO_GO** until the separate production-promotion
authority is satisfied.
