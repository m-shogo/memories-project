# Next Chat Addendum — Memory OS Round 9 Preview Spool Streams

最終更新: 2026-07-17

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

Continue with small, independently verifiable commits.

## Read first

1. `docs/memory-os-current-authority-order-round-9-security.md`
2. `docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md`
3. `docs/memory-os-preview-spool-commit-contract-round-9.md`
4. `services/import-api/README.md`
5. `services/import-api/internal/previewspool/storage.go`
6. `services/import-api/internal/previewspool/storage_linux.go`
7. `services/import-api/internal/previewspool/storage_linux_test.go`
8. `docs/schemas/memory-os-security/preview-spool-manifest.v1.schema.json`

Historical handoffs do not override these files.

---

# Current status

```txt
synchronous CSV iterator / Preview RowEvent bridge:
created

Preview v2 accepted/rejected hash model:
created as reference

Preview spool manifest:
hardened

Linux attempt filesystem lifecycle:
created

filesystem targeted reconstructed mini-module:
gofmt + go test -race PASS

actual repository full Go / remote workflows:
unconfirmed

canonical spool stream writer:
not created

manifest writer / seal / independent verifier:
not created

production PostgreSQL Preview path:
not created

production:
NO-GO
```

Filesystem checkpoint behavior:

- exact `0700` supervisor root;
- descriptor-relative `mkdirat/openat`;
- one validated server-generated `spoolId` segment;
- fixed exclusive `0600` accepted/rejected/manifest files;
- `O_NOFOLLOW`, owner/type/mode/link checks;
- attempt inode substitution rejection;
- cancellation cleanup at every creation stage;
- unknown-entry fail closed;
- successful cleanup idempotent;
- non-Linux fail closed.

---

# Immediate checkpoint

Implement only canonical bounded stream writing.

P0 formats:

```txt
accepted:
memory-os-preview-candidate-v1-length-prefixed

rejected:
memory-os-preview-rejection-v1-length-prefixed
```

Each record:

```txt
8-byte unsigned big-endian length
+ exact canonical record bytes
```

Required writer behavior:

- accepted and rejected writer types are not interchangeable;
- source rows strictly increase across all events;
- candidate/rejection decision is exclusive;
- accepted count remains at least one before a manifest can be finalized;
- aggregate rows never exceed 100,000;
- aggregate spool bytes never exceed 512 MiB;
- per-record size is bounded before allocation/write;
- stream SHA-256 covers exact bytes including length prefixes;
- byte count and record count are derived by the writer;
- context cancellation and any write/short-write error become sticky terminal failure;
- after terminal failure, no further write is accepted;
- no goroutine, channel or hidden persistence;
- writer does not publish the manifest or open a database transaction.

Tests in the same checkpoint:

- accepted and rejected canonical byte vectors;
- ordering changes hash;
- content/length-prefix changes hash;
- row limit at and over boundary;
- aggregate byte limit at and over boundary;
- oversized record fails before partial publication;
- short writer and disk-like failure become sticky;
- cancellation before and between writes becomes sticky;
- rejected record cannot contain raw user values by type;
- accepted writer rejects rejection format and vice versa;
- retry requires a new attempt rather than resuming partial bytes.

Do not implement manifest publication, fsync/seal, reader/rehash, PostgreSQL, S3 or parser containers in this checkpoint.

---

# Following sequence

```txt
1. bounded canonical accepted/rejected stream writers
2. fsync/close and atomic manifest publication
3. independent reader/decode/count/re-hash verifier
4. startup reconciliation and 24-hour TTL cleanup
5. truncation/append/malformed length/disk-full/crash tests
6. production Preview candidate/rejection/ready PostgreSQL schema
7. short atomic pgx.CopyFrom repository
8. epoch recheck, rollback and post-COMMIT retry proof
9. real private versioned object storage
10. isolated parser supervisor
```

# Hard stops

- resuming a failed partial stream;
- hashing decoded/reserialized data instead of exact bytes;
- raw rejected values;
- unbounded record/row/byte allocations;
- hidden concurrency;
- manifest publication before both streams close successfully;
- parse inside production DB transaction;
- partial Preview visibility;
- release judgment while remote CI is unknown.

Memory Town remains after Capture / Import P0 closes.
