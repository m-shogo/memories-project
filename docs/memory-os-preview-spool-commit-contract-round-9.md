# Memory OS Preview Spool and Atomic Commit Contract — Round 9

最終更新: 2026-07-17

## Verdict

```txt
parse untrusted source while a PostgreSQL transaction is open:
FORBIDDEN FOR PRODUCTION

required production flow:
version-bound source
→ parse outside DB transaction
→ create one private bounded spool attempt
→ seal and independently re-hash both streams
→ revalidate account epoch and all bindings
→ client-side bulk copy in one short transaction
→ insert candidates + safe rejections + immutable ready Preview
→ COMMIT or full ROLLBACK
```

The in-process `preview.AtomicMaterializer` is a security vertical-slice reference only. It proves hashing and row-decision invariants, but it consumes its source inside the transaction callback and must not be connected to a production PostgreSQL repository.

---

# 1. Required properties

The production implementation must provide all properties together:

1. no partial Preview is visible;
2. accepted candidates and safe rejected-row reports become visible together;
3. source parsing never holds a production database transaction open;
4. source object version, size and checksum are exact-bound;
5. adapter ID, version, reviewed artifact digest and normalized options digest are exact-bound;
6. accepted and rejected streams have fixed canonical formats, byte lengths, counts and hashes;
7. account deletion or epoch change invalidates work immediately before commit;
8. a crash leaves either no Preview or one complete immutable ready Preview;
9. spool data is private, bounded, short-lived and excluded from backup/crash upload;
10. rejected records never contain raw user values;
11. retry cannot duplicate candidates, rejections or Preview rows;
12. one parse attempt cannot reuse or substitute another attempt's spool.

---

# 2. Phase A — parse and create a verified spool

Phase A runs outside PostgreSQL transactions inside the isolated parser/supervisor boundary.

```txt
version-bound quarantine object
→ parser sandbox
→ synchronous row iterator
→ canonical candidate / safe rejection events
→ fixed-format accepted and rejected spool files
→ sealed manifest
```

## 2.1 Logical streams

Use separate streams:

```txt
accepted candidates
safe rejected-row report
```

Accepted records may contain normalized user content required for import.

Rejected records may contain only:

```txt
source row number
stable IMPORT_[A-Z0-9_]+ issue codes
```

Rejected records must not contain raw cells, titles, note fragments, URLs, filenames, email addresses, tokens, stack traces or arbitrary adapter messages.

## 2.2 Canonical record formats

The P0 record formats are fixed:

```txt
accepted:
memory-os-preview-candidate-v1-length-prefixed

rejected:
memory-os-preview-rejection-v1-length-prefixed
```

Each record is encoded as:

```txt
8-byte unsigned big-endian record length
+ exact canonical record bytes
```

The stream SHA-256 is computed over the exact file bytes, including every length prefix. Implementations must not hash decoded objects, reserialized JSON or adapter-provided digests as a substitute.

Ordering is source-row order. Duplicate, descending or non-contiguous stream ordinals are terminal errors. A later format requires a new reviewed format identifier and migration contract.

## 2.3 Manifest binding

The manifest must bind:

```txt
manifest schema version
server-generated spool attempt ID
job ID
owner account ID
account epoch
quarantine object key
object version ID
source content length
source SHA-256
adapter ID / version / reviewed artifact SHA-256
normalized options SHA-256
source row count
aggregate spool byte length
accepted record format / count / byte length / SHA-256
rejected record format / count / byte length / SHA-256
created-at / expires-at
```

Semantic invariants:

```txt
object key begins with quarantine/{jobId}/
accepted count >= 1
accepted count + rejected count = source row count <= 100,000
accepted bytes + rejected bytes = spool byte length <= 512 MiB
expiresAt > createdAt
expiresAt - createdAt <= 24 hours
```

An empty rejected stream is represented by:

```txt
recordCount = 0
byteLength = 0
sha256 = SHA-256(empty bytes)
```

The manifest does not contain filesystem paths. The supervisor selects fixed internal filenames; no filename or path from a request, adapter output or manifest may be passed to filesystem APIs.

The final Preview hash must include both stream hashes and both counts. The production commit key additionally binds the spool attempt's immutable manifest identity.

## 2.4 Filesystem controls

Each parse attempt receives one supervisor-created directory:

```txt
parent: supervisor-owned private root
attempt directory: 0700 or stricter
accepted file: 0600 or stricter
rejected file: 0600 or stricter
manifest file: 0600 or stricter
```

Storage must be bounded tmpfs or equivalently encrypted ephemeral storage, mounted `noexec,nosuid,nodev`, outside backup and crash-upload collection.

Runtime requirements:

- create with exclusive semantics; never open an existing attempt directory as a new attempt;
- use descriptor-relative operations such as `openat` where available;
- use `O_NOFOLLOW` or platform-equivalent no-symlink semantics;
- verify `lstat`/descriptor metadata, ownership, file type, mode and link count;
- never follow symlinks or hardlink substitutions;
- never expose one job or attempt to another;
- never give parser code cloud, database or signing credentials;
- delete the entire attempt after success, terminal failure, cancellation or expiry.

Manifest booleans such as `symlinkFollowingAllowed: false` are contract assertions, not runtime evidence. The implementation and tests must prove the filesystem behavior independently.

## 2.5 Seal and tamper resistance

After parser completion:

1. parser process exits;
2. supervisor closes all parser write descriptors;
3. stream files and manifest become immutable to parser code;
4. commit reader opens only the supervisor-owned attempt directory;
5. reader independently parses, counts and re-hashes both streams;
6. exact formats, sizes, counts and hashes must match the manifest;
7. source/job/owner/epoch/adapter/options/TTL bindings are revalidated;
8. any mismatch is terminal and no Preview transaction starts.

Do not trust hashes or counts reported only by adapter code.

---

# 3. Phase B — short atomic database commit

Only after Phase A succeeds may the commit worker open a PostgreSQL transaction.

Required order:

```txt
BEGIN
SET LOCAL ROLE memory_worker_runtime
SET LOCAL app.current_account_id
SET LOCAL app.current_account_epoch
verify canonical account epoch is still active
verify Import Job owner / epoch / state
verify source object version / size / checksum
verify reviewed adapter artifact digest
verify normalized options digest
claim deterministic commit key
client-side bulk copy accepted candidates
client-side bulk copy safe rejections
verify counts and contiguous ordinals
insert immutable ready Preview with all hashes and counts
mark Import Job preview_ready
COMMIT
```

On any error:

```txt
ROLLBACK
no candidate rows
no rejection rows
no ready Preview
no success status
```

## 3.1 Bulk loading

Use client-side `pgx.CopyFrom` or an equivalent parameterized protocol.

Forbidden:

- server-side `COPY FROM '/path'`;
- database access to worker filesystem paths;
- SQL assembled from filenames, column names or user content;
- one transaction per row;
- archive/CSV/JSON parsing while the transaction is open.

## 3.2 Visibility

The production schema must not expose a `building` Preview to iOS or Portal readers.

P0 behavior:

- no Preview row exists before commit;
- candidate, rejection and final ready Preview rows are inserted in one transaction;
- Apply accepts only immutable `ready` Preview rows.

Chunked persistent staging is not authorized by this contract.

---

# 4. Idempotency and crash recovery

The stable commit key binds:

```txt
owner account ID
account epoch
job ID
source object version ID
source size and checksum
adapter artifact digest
options digest
accepted count / hash
rejected count / hash
```

Retry rules:

- same key and same manifest returns the existing complete Preview;
- same key with a different manifest is a conflict;
- transaction failure leaves no durable Preview state;
- crash after COMMIT but before acknowledgement is recovered by returning the committed Preview;
- expired, cancelled or deleted-account work is rejected and its spool removed;
- a new parse attempt receives a new spool ID and may not inherit partial files.

---

# 5. Required tests before concrete PostgreSQL wiring

## Unit and property tests

- options digest changes for every material parser option;
- source rows are strictly increasing;
- candidate/rejection decision is exclusive;
- accepted row with zero warnings is valid;
- rejected row without issue code is invalid;
- raw rejected values cannot fit the rejection type;
- stream hash changes on order, count, length or content changes;
- empty rejected stream uses exact empty-stream representation;
- aggregate row/byte totals match stream totals;
- cancellation is terminal and cannot resume a partial iterator.

## Filesystem and adversarial tests

- attempt directory and files have exact private modes;
- existing directory/file creation fails closed;
- symlink and hardlink replacement attempts fail;
- cross-job and cross-attempt substitution fail;
- accepted stream truncation fails;
- rejected stream append fails;
- malformed length prefix and oversized record fail;
- invalid UTF-8/internal record fails;
- TTL expiry before commit fails;
- cancellation, parser crash and supervisor crash leave no reusable partial attempt;
- cleanup succeeds after success, failure, cancellation and expiry.

## Database integration tests

- 100,000-row parse completes before transaction start;
- transaction duration excludes source parsing;
- candidate insert failure rolls back rejections and Preview;
- rejection insert failure rolls back candidates and Preview;
- finalize failure rolls back all rows;
- account epoch change before commit rejects;
- source version/checksum or adapter digest mismatch rejects;
- duplicate retry returns one Preview;
- conflicting retry rejects;
- post-COMMIT acknowledgement loss returns the committed Preview.

---

# 6. Current implementation status

```txt
synchronous Generic CSV iterator:
CREATED

CSV → Preview RowEvent bridge:
CREATED

candidate + safe rejection Preview v2 hash model:
CREATED

reference AtomicMaterializer:
CREATED — invariant/reference only

Preview spool manifest schema:
CREATED AND HARDENED

structural manifest negatives:
9 TARGETED REJECTIONS

semantic manifest validator:
CREATED — 6 TARGETED REJECTIONS

production spool directory/writer/reader/cleanup:
NOT CREATED

production Preview PostgreSQL domain schema / pgx repository:
NOT CREATED

remote workflow result for current HEAD:
UNCONFIRMED

production:
NO-GO
```

Machine-readable authority:

```txt
docs/schemas/memory-os-security/preview-spool-manifest.v1.schema.json
docs/schemas/memory-os-security/preview-spool-semantic-case-set.v1.schema.json
docs/fixtures/memory-os-security/preview-spool-manifest.round9.valid.v1.json
docs/fixtures/memory-os-security/preview-spool-manifest-negative-cases.round9.v1.json
docs/fixtures/memory-os-security/preview-spool-manifest-semantic-cases.round9.v1.json
scripts/validate-memory-os-preview-spool.py
```

Atomic visibility is required; long-lived parse transactions are not.
