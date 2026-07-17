# Memory OS Preview Spool Stream Writer Checkpoint

最終更新: 2026-07-17

## Verdict

```txt
Preview spool manifest contract:
HARDENED

Linux attempt filesystem lifecycle:
PARTIAL IMPLEMENTATION CREATED

bounded accepted/rejected stream writer:
PARTIAL IMPLEMENTATION CREATED

fsync / seal / manifest publication:
NOT IMPLEMENTED

independent reader / decode / count / re-hash:
NOT IMPLEMENTED

production PostgreSQL commit:
BLOCKED

production:
NO-GO
```

This checkpoint is deliberately limited to exact stream bytes, bounds and terminal write behavior. It does not authorize database persistence.

## Implemented files

```txt
services/import-api/internal/previewspool/writer.go
services/import-api/internal/previewspool/writer_linux.go
services/import-api/internal/previewspool/writer_unsupported.go
services/import-api/internal/previewspool/writer_linux_test.go
services/import-api/internal/previewspool/writer_interruption_linux_test.go
```

## Binding writer behavior

- accepted and rejected streams are separate;
- each record is `8-byte unsigned big-endian length + canonical bytes`;
- accepted format is `memory-os-preview-candidate-v1-length-prefixed`;
- rejected format is `memory-os-preview-rejection-v1-length-prefixed`;
- aggregate record count is capped at `100,000`;
- aggregate spool bytes are capped at `512 MiB`;
- one canonical record is capped at `2 MiB`;
- limits are checked before starting the next record;
- exact-byte SHA-256 includes the length prefix;
- empty rejected stream uses SHA-256 of empty bytes;
- at least one accepted record is required before successful close;
- no goroutine or channel is created;
- concurrent calls are serialized by the writer mutex;
- first cancellation, invalid record, limit, short write, disk error or lifecycle failure is sticky;
- terminal failure closes both writable stream handles;
- a failed writer cannot be resumed or used to produce evidence;
- successful close is idempotent but is not a seal.

## Manifest publication correction

The earlier filesystem checkpoint created an empty `manifest.json` placeholder together with the data files. `NewStreamWriter` now:

1. verifies both stream handles are untouched, regular, owner-matching, single-link `0600` files;
2. verifies the original attempt directory device/inode through descriptor-relative access;
3. closes and unlinks the empty manifest placeholder without following links;
4. claims the attempt exactly once.

Therefore `manifest.json` is absent during stream writing. The final manifest must only appear in the later seal/publish phase.

## Negative and interruption evidence

Tests cover:

- exact length-prefixed bytes and exact-file hashes;
- zero-rejection evidence;
- idempotent stream close;
- write-after-close rejection;
- pre-cancelled context;
- cancellation after only the 8-byte prefix was written;
- aggregate record limit;
- aggregate byte limit;
- per-record byte limit;
- short write;
- simulated `ENOSPC`;
- no accepted records;
- second writer claim;
- prewritten stream rejection;
- sticky terminal errors and closed writable handles.

## Validation language

```txt
independently reconstructed Linux package:
gofmt + go test -race PASS

exact repository-integrated Go suite:
UNCONFIRMED

remote GitHub Actions:
UNCONFIRMED
```

Targeted reconstruction is useful implementation evidence but is not a full repository or production result.

## Residual risks

- raw stream file accessors still exist inside the internal filesystem package; production composition must expose only `StreamWriter`, and later independent re-hash remains mandatory;
- stream close does not call `fsync`;
- no directory sync or atomic manifest rename exists;
- no canonical decoder/verifier exists;
- no malformed-length or append/truncation verification exists;
- no startup reconciliation or TTL cleanup exists;
- no production mount evidence exists for `noexec,nosuid,nodev` or ephemeral-volume behavior;
- no PostgreSQL transaction may consume this checkpoint directly.

## Immediate next task

```txt
Implement seal and manifest publication only:
stream fsync
→ close confirmation
→ manifest.tmp exclusive 0600 write
→ manifest fsync
→ atomic rename to manifest.json
→ attempt directory fsync
→ sealed state
```

Do not add PostgreSQL, S3, parser-container or client wiring in the same checkpoint.
