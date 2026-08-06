# Memory OS parser artifact registry

## Purpose

This runbook defines how exact parser artifact bytes become reviewable, retained compatibility authority. A registry entry does not make Memory OS production-ready and does not approve a release by itself.

## Test harness is not an artifact

`services/import-api/internal/parsersup/worker.go` is a targeted isolation-test harness. A Go test binary re-executed with `MEMORY_OS_PARSER_WORKER_MODE` is not a production parser artifact, even when the parser security and restart tests pass.

Source code, a successful build, a copied digest, a branch head or a release tag is also insufficient. Registration requires the exact artifact bytes outside the repository plus independent evidence and approvals.

## Required artifact identity

Every record binds:

- immutable artifact ID
- adapter ID and adapter version
- SHA-256 computed from the exact artifact bytes
- artifact byte length
- artifact format
- target operating system and architecture
- parser frame-protocol version

The artifact ID, adapter-version tuple and digest must each be unique.

## Required review

Three distinct operational pseudonyms are required:

- `SECURITY_REVIEWER`
- `RUNTIME_REVIEWER`
- `RELEASE_OWNER`

The record must reference build provenance, security review, independent retention evidence and at least one replay result. The writer verifies evidence paths but does not manufacture the evidence or approvals.

## Release compatibility binding

Every `compatibleReleaseId` must already exist in the approved release baseline registry. Candidate commits, CI results and unapproved tags cannot be used as release IDs.

A release is not rollback eligible merely because an artifact record exists. The release record must separately bind the artifact-set digest and satisfy all rollback requirements.

## Retention states

- `RETAINED`: exact bytes are independently retained and may support rollback when all other release conditions pass.
- `RETENTION_PENDING`: review may exist, but rollback must remain blocked.
- `RETIRED_BLOCKED_FROM_ROLLBACK`: the artifact cannot support rollback or new compatibility claims.

Automatic artifact deletion is forbidden. Retirement requires proof that no approved rollback-capable release still depends on the artifact.

## Replay evidence

Replay evidence must use synthetic or approved sanitized inputs, verify the exact artifact digest before execution, bind the protocol version and prove deterministic accepted/rejected output accounting. Repository test-harness output cannot substitute for replay of the registered artifact bytes.

## Stop conditions

Stop registration when:

- artifact bytes do not match the declared digest or length
- target OS, architecture, format or protocol is ambiguous
- review roles are missing or duplicated
- provenance, security, retention or replay evidence is absent
- a compatible release ID is not approved
- evidence contains credentials, infrastructure URLs or user content
- the registry lock already exists or uniqueness cannot be proven

## Current state

No reviewed production parser artifact exists. No old artifact replay or rollback retention is proven. The test harness remains test-only.

Production remains **NO_GO**.
