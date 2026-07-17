# Memory OS Preview Spool Seal Checkpoint

最終更新: 2026-07-17

## Verdict

```txt
manifest contract:
HARDENED

Linux attempt filesystem:
PARTIAL IMPLEMENTATION

bounded accepted/rejected writer:
PARTIAL IMPLEMENTATION

stream fsync + no-replace manifest publication:
PARTIAL IMPLEMENTATION CREATED

independent reader / decode / count / re-hash:
NOT IMPLEMENTED

production PostgreSQL commit:
BLOCKED

production:
NO-GO
```

This checkpoint proves one durable publication boundary. It does not make the spool trustworthy for database commit; only a later independent verifier may do that.

## Implemented files

```txt
services/import-api/internal/previewspool/seal.go
services/import-api/internal/previewspool/seal_linux.go
services/import-api/internal/previewspool/seal_unsupported.go
services/import-api/internal/previewspool/seal_linux_test.go
services/import-api/internal/previewspool/seal_interruption_linux_test.go
```

## Successful transition

```txt
bounded writer remains open
→ validate exact job / owner / epoch / source / adapter / options / TTL bindings
→ fsync accepted.spool
→ cancellation checkpoint
→ fsync rejected.spool
→ cancellation checkpoint
→ close both stream handles
→ create manifest.tmp with O_CREAT | O_EXCL | O_NOFOLLOW and exact 0600
→ write deterministic compact JSON
→ fsync manifest.tmp
→ close manifest.tmp
→ cancellation checkpoint
→ publish manifest.json with linkat no-replace semantics
→ unlink manifest.tmp
→ fsync attempt directory
→ return seal evidence
```

An ordinary rename is not used because it can replace an existing final name. Publication uses `linkat` without replacement; an existing `manifest.json` is a terminal conflict and is never overwritten.

## Manifest binding

The generated manifest contains only schema-approved fields and binds:

- server-generated `spoolId`;
- job ID, owner account ID and account epoch;
- exact quarantine object key, version, content length and SHA-256;
- adapter ID/version/reviewed artifact SHA-256;
- normalized options SHA-256;
- exact accepted/rejected record formats, counts, byte lengths and hashes;
- aggregate source-row count and spool byte length;
- UTC created/expiry timestamps with maximum 24-hour TTL;
- fixed security constants forbidding parse-time DB transactions, raw rejected values, path fields, symlink following, cross-attempt reuse and backup eligibility.

The runtime intentionally narrows source object keys to the generated P0 form:

```txt
quarantine/{jobId}/{uploadAuthorizationId}
```

## Failure semantics

- input mismatch is terminal;
- stream fsync failure is terminal;
- manifest write/fsync/close failure removes `manifest.tmp` and publishes no final name;
- existing final or temp name is rejected without replacement;
- a temp-name symlink is not followed;
- cancellation between stream syncs or before publication is terminal;
- directory fsync failure removes the final name and syncs the rollback;
- if rollback durability cannot be established, the result is `ErrSealDurabilityUncertain` and the attempt must be quarantined for reconciliation;
- the same `Sealer` plus the same input is idempotent after success;
- conflicting reseal input is rejected.

A process crash may leave `manifest.tmp`, or both names temporarily linked to one inode. Such an attempt is not trusted. Startup reconciliation must remove or terminally quarantine it; normal `Attempt.Cleanup` remains fail-closed on unexpected crash residue rather than recursively deleting unknown entries.

## Targeted tests

Tests cover:

- successful publication and manifest JSON fields;
- final exact `0600` mode and single link;
- absence of temp after success;
- same-input idempotency and changed-input conflict;
- invalid job/object binding;
- accepted-stream fsync failure;
- cancellation after the first stream fsync;
- short manifest write;
- manifest fsync failure;
- existing final manifest preservation;
- `manifest.tmp` symlink attack;
- directory fsync rollback;
- durability-uncertain rollback failure;
- no final/temp artifact after handled failures.

## Validation language

```txt
independently reconstructed Linux package:
gofmt + go test -race + go vet PASS

exact repository-integrated Go suite:
UNCONFIRMED

remote GitHub Actions:
UNCONFIRMED
```

Targeted reconstruction is not production evidence and is not permission to begin PostgreSQL persistence.

## Residual risks

- no independent manifest parser or schema-equivalent runtime decoder;
- no length-prefixed stream decoder;
- no independent count/byte/hash verification;
- no malformed-length, truncation, append or stream-substitution proof;
- no startup reconciliation for temp/both-name/crash residue;
- no TTL cleanup worker;
- no production mount evidence for ephemeral `noexec,nosuid,nodev` storage;
- no repository-wide or remote CI evidence for the exact current HEAD;
- no production PostgreSQL commit integration.

## Immediate next task

```txt
Implement independent sealed-spool verifier only:
open attempt and all fixed entries descriptor-relative with O_NOFOLLOW
→ require final manifest regular 0600 single-link
→ require manifest.tmp absent
→ strictly decode manifest
→ reopen and decode both length-prefixed streams
→ enforce record and byte bounds while reading
→ independently count and SHA-256 exact bytes
→ compare every manifest binding
→ reject mismatch before any database transaction
```

Do not add PostgreSQL, object storage, parser-container or client wiring in that checkpoint.
