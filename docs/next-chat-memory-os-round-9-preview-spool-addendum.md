# Next Chat Addendum — Memory OS Round 9 Preview Spool

最終更新: 2026-07-17

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

毎回、小さくcommit / pushする。

---

# Read first

1. `docs/memory-os-current-authority-order-round-9-security.md`
2. `docs/memory-os-preview-spool-commit-contract-round-9.md`
3. `services/import-api/README.md`
4. `SECURITY.md`
5. `docs/next-chat-memory-os-round-9-security-addendum.md`

---

# Absolute status

```txt
security perfection:
never claim

Capture / Import priority:
unchanged

synchronous Generic CSV iterator:
created

canonical CSV options digest:
created

CSV → Preview RowEvent bridge:
created

candidate + safe rejection Preview v2 hash model:
created

reference AtomicMaterializer:
created for invariant tests only

production Preview spool:
not created

production PostgreSQL Preview repository:
not created

latest Go CI result:
not confirmed by available connector after the new changes

production:
NO-GO
```

The previous Go baseline passed test / vet / race before the latest iterator and Preview spool changes. Do not copy that PASS claim forward until current CI or an equivalent local run succeeds.

---

# Critical correction

Do not parse a 256 MiB / 100,000-row source while a PostgreSQL transaction is open.

The earlier reference materializer consumes the source inside its transaction callback. It proves hashing and decision invariants only and must not be wired to production PostgreSQL.

Required production flow:

```txt
version-bound quarantine object
→ isolated parser outside DB transaction
→ bounded private accepted/rejected spool
→ manifest and stream re-hash
→ canonical account epoch recheck
→ short client-side pgx.CopyFrom transaction
→ candidates + safe rejections + immutable ready Preview
→ COMMIT or full ROLLBACK
```

Atomic visibility is required. A long parse transaction is forbidden.

---

# Implemented code added in this correction

```txt
services/import-api/internal/adapters/genericcsv/iterator.go
services/import-api/internal/adapters/genericcsv/iterator_test.go
services/import-api/internal/adapters/genericcsv/options_digest.go
services/import-api/internal/adapters/genericcsv/options_digest_test.go
services/import-api/internal/preview/atomic_materializer.go
services/import-api/internal/preview/atomic_materializer_test.go
services/import-api/internal/pipeline/generic_csv_preview.go
services/import-api/internal/pipeline/generic_csv_preview_test.go
services/import-api/internal/pipeline/generic_csv_pipeline.go
services/import-api/internal/pipeline/generic_csv_pipeline_test.go
```

Binding behavior:

- no hidden goroutines or channels;
- one source row per synchronous call;
- cancellation and fatal parse errors are sticky;
- accepted / rejected source rows must be strictly increasing;
- accepted candidate may have zero warnings;
- rejected row requires stable `IMPORT_[A-Z0-9_]+` issue codes;
- rejection type has no field for raw user values;
- options digest is computed from the actual normalized parser options;
- caller-supplied options hash mismatch is rejected before DB work;
- P0 date locations are embedded `UTC` and `Asia/Tokyo` only;
- candidate stream and rejection stream have separate hashes;
- final Preview v2 hash includes both stream hashes and both counts.

---

# Required Preview spool manifest

The next machine-readable contract must bind:

```txt
manifest format version
job ID
owner account ID
account epoch
source object key
source object version ID
source checksum
adapter ID / version / artifact digest
normalized options digest
accepted count / accepted stream hash
rejected count / rejected stream hash
created-at / expires-at
```

Spool files must be private, bounded, job-specific, ephemeral, excluded from backup and deleted after success, failure, cancellation or expiry.

Rejected spool records may contain only source row and stable issue codes.

---

# Next correct implementation sequence

```txt
1. confirm current Go format / test / vet / race result
2. add PreviewSpoolManifest JSON Schema and positive / negative fixtures
3. implement supervisor-owned 0700 spool directory and 0600 files
4. implement accepted and rejected stream writers with byte / row limits
5. implement manifest writer and independent stream re-hash reader
6. add truncation / append / cross-job / symlink / expiry negative tests
7. create PostgreSQL Preview candidate / rejection / ready Preview tables
8. implement client-side pgx.CopyFrom repository
9. verify canonical account epoch immediately before commit
10. prove candidate / rejection / Preview rollback together
11. prove retry after post-COMMIT acknowledgement loss returns one Preview
12. delete spool on every terminal path
13. only then connect concrete quarantine reader and parser supervisor
```

Do not implement concrete production Preview persistence before steps 1-10 pass.

---

# Hard stops

- untrusted parse while DB transaction is open;
- partial candidate or rejection visibility;
- rejected report containing raw cell values;
- caller-controlled options hash;
- source object version not bound;
- adapter digest not bound;
- spool without permissions, size limits, TTL and cleanup;
- server-side `COPY FROM '/path'`;
- missing epoch recheck immediately before commit;
- remote CI unknown at release judgment time;
- unresolved P0 greater than zero.

Memory Town remains after Capture / Import P0 blockers close.
