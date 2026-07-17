# Next Chat Addendum — Memory OS Round 9 Preview Spool Runtime

最終更新: 2026-07-17

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

Commit and push small, independently verifiable checkpoints.

---

# Read first

1. `docs/memory-os-current-authority-order-round-9-security.md`
2. `docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md`
3. `docs/memory-os-preview-spool-commit-contract-round-9.md`
4. `services/import-api/README.md`
5. `SECURITY.md`
6. `docs/schemas/memory-os-security/preview-spool-manifest.v1.schema.json`
7. `scripts/validate-memory-os-preview-spool.py`

Historical Round 9 progress and older next-chat documents do not override these files.

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

Preview spool manifest contract:
hardened

Preview spool structural negatives:
9 targeted rejections

Preview spool semantic validator:
created with 6 targeted rejections

production Preview spool filesystem/writer/reader:
not created

production PostgreSQL Preview schema / pgx repository:
not created

current HEAD full local Go and remote Actions result:
unconfirmed

production:
NO-GO
```

---

# Locked contract

The production path is:

```txt
version-bound quarantine object
→ isolated synchronous parse outside DB transaction
→ one supervisor-owned spool attempt
→ fixed-format accepted/rejected streams
→ sealed manifest
→ independent stream re-hash and semantic verification
→ canonical account epoch recheck
→ one short client-side pgx.CopyFrom transaction
→ candidates + safe rejections + immutable ready Preview
→ COMMIT or full ROLLBACK
```

The manifest binds:

- server-generated `spoolId`;
- job / owner / account epoch;
- source key / version / content length / checksum;
- adapter ID / version / reviewed artifact digest;
- normalized options digest;
- aggregate source-row and spool-byte totals;
- exact accepted/rejected record formats, counts, byte lengths and SHA-256;
- creation and expiry with a maximum 24-hour TTL;
- no path fields, symlink following, cross-attempt reuse or backup eligibility.

P0 stream formats:

```txt
memory-os-preview-candidate-v1-length-prefixed
memory-os-preview-rejection-v1-length-prefixed
```

Each record is an 8-byte unsigned big-endian length followed by exact canonical bytes. Hash exact file bytes, including prefixes.

---

# Immediate implementation checkpoint

Implement only the filesystem attempt lifecycle.

Required behavior:

```txt
supervisor private root
→ create server-generated attempt directory exclusively
→ mode 0700 or stricter
→ create fixed accepted/rejected/manifest filenames exclusively
→ mode 0600 or stricter
→ descriptor-relative no-follow access
→ verify type / owner / mode / link count
→ idempotent terminal cleanup
```

Tests in the same checkpoint:

- existing attempt directory fails closed;
- existing stream/manifest file fails closed;
- symlink and hardlink substitution fail;
- cross-job and cross-attempt path reuse fail;
- cancellation between every creation step cleans partial state;
- repeated cleanup is safe;
- cleanup does not escape the supervisor root;
- unsafe permissions or non-regular files fail closed.

Do not implement stream serialization, PostgreSQL persistence, S3 networking or parser containers inside this first checkpoint.

---

# Following checkpoints

```txt
1. filesystem attempt lifecycle
2. canonical bounded stream writers
3. manifest writer, seal and independent reader/rehash
4. truncation / append / malformed record / disk-full / crash tests
5. production Preview candidate/rejection/ready PostgreSQL schema
6. pgx.CopyFrom atomic repository and account-epoch recheck
7. rollback and post-COMMIT acknowledgement-loss retry proof
8. concrete private versioned object storage
9. isolated parser supervisor and adapter artifact verification
```

---

# Hard stops

- parse while a production DB transaction is open;
- caller/adapter-controlled filesystem paths;
- opening existing attempts as new work;
- symlink or hardlink following;
- raw rejected values in spool/report;
- unbounded rows or bytes;
- manifest-only trust without independent re-hash;
- partial candidate/rejection visibility;
- missing epoch recheck immediately before commit;
- spool surviving success, failure, cancellation or expiry;
- remote CI unknown at release judgment time;
- unresolved P0 greater than zero.

Memory Town remains after Capture / Import P0 blockers close.
