# Memory OS Preview Spool and Atomic Commit Contract — Round 9

最終更新: 2026-07-17

## Verdict

```txt
parse untrusted source while a PostgreSQL transaction is open:
FORBIDDEN FOR PRODUCTION

required production flow:
parse outside DB transaction
→ create bounded verified spool
→ revalidate account epoch and bindings
→ client-side bulk copy in one short transaction
→ insert immutable ready Preview and safe rejection report
→ commit or rollback everything
```

The existing in-process `preview.AtomicMaterializer` is a security vertical-slice reference only. It proves hashing and row-decision invariants, but it must not be connected to a production PostgreSQL repository because it currently consumes the source inside the transaction callback.

---

# 1. Required properties

The production implementation must provide all of the following at the same time:

1. no partial Preview is visible;
2. accepted candidates and safe rejected-row report become visible together;
3. source parsing does not hold a database transaction open;
4. the exact source object version, checksum, adapter artifact and options digest are bound;
5. the exact accepted and rejected row sets are hash-bound;
6. account deletion or epoch change invalidates work before commit;
7. a crash leaves either no Preview or one complete immutable ready Preview;
8. spool data is short-lived, private, bounded and excluded from backup;
9. raw rejected cell values are never written to the rejection report;
10. retry cannot duplicate candidates, reports or Preview rows.

---

# 2. Phase A — parse and create verified spool

Phase A runs outside PostgreSQL transactions inside the isolated parser/supervisor boundary.

```txt
version-bound quarantine object
→ parser sandbox
→ synchronous row iterator
→ canonical candidate / safe rejection events
→ bounded spool files
→ spool manifest
```

## 2.1 Spool contents

Use separate logical streams:

```txt
accepted candidates
safe rejected-row report
```

Accepted candidate records may contain normalized user content required for import.

Rejected-row records may contain only:

```txt
source row number
stable IMPORT_* issue codes
```

Rejected-row records must not contain:

- raw cell values;
- title or note fragments;
- raw URLs;
- filenames;
- email addresses;
- tokens;
- parser stack traces;
- arbitrary adapter messages.

## 2.2 Manifest binding

The spool manifest must bind:

```txt
job ID
owner account ID
account epoch
quarantine object key
object version ID
source SHA-256
adapter ID
adapter version
adapter artifact SHA-256
normalized options SHA-256
accepted count
rejected count
accepted stream SHA-256
rejected stream SHA-256
manifest format version
created-at and expires-at
```

The final Preview hash must include both stream hashes and both counts.

## 2.3 Filesystem controls

Spool storage must be:

- job-specific;
- supervisor-owned;
- mode `0700` directory and `0600` files or stricter;
- on bounded tmpfs or an equivalently encrypted ephemeral volume;
- `noexec`, `nosuid`, `nodev`;
- outside backup and crash-upload collection;
- unavailable to other jobs;
- deleted after successful commit, terminal failure, cancellation or TTL expiry.

The parser must not receive cloud, database or signing credentials.

## 2.4 Tamper resistance

After parser completion:

1. parser process exits;
2. supervisor closes parser write access;
3. spool directory becomes read-only to the commit reader;
4. supervisor re-hashes both streams while reading them;
5. hashes and counts must match the manifest;
6. any mismatch is terminal and no Preview transaction starts.

Do not trust hashes reported only by adapter code.

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
verify source object version / checksum binding
verify adapter reviewed digest binding
verify options digest binding
allocate Preview ID or claim deterministic commit key
client-side bulk copy accepted candidates
client-side bulk copy safe rejections
verify inserted counts and contiguous ordinals
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

## 3.1 Bulk loading rule

Use client-side `pgx.CopyFrom` or an equivalent parameterized protocol.

Forbidden:

- `COPY FROM '/server/path'`;
- database access to worker filesystem paths;
- SQL assembled from filenames, column names or user content;
- one transaction per row;
- parsing archive / CSV / JSON while the transaction remains open.

## 3.2 Visibility rule

The production schema must not expose a `building` Preview to iOS or Portal readers.

Preferred P0 behavior:

- no Preview row exists before commit;
- candidate and rejection rows are inserted in the same transaction as the final `ready` Preview;
- Apply accepts only `ready` Preview rows.

If future scale requires chunked persistent staging, it requires a new reviewed contract. Chunked staging is not authorized by this document.

---

# 4. Idempotency and crash recovery

The commit operation requires a stable commit key bound to:

```txt
owner account ID
account epoch
job ID
source object version ID
source checksum
adapter artifact digest
options digest
accepted stream hash
rejected stream hash
```

Retry rules:

- same key and same manifest: return the existing complete Preview;
- same key with different manifest: reject as conflict;
- transaction failure: no durable Preview state;
- crash after COMMIT before acknowledgement: retry discovers and returns the committed Preview;
- expired or deleted-account work: reject and delete spool.

---

# 5. Required tests before concrete PostgreSQL wiring

## Unit and property tests

- options digest changes for every material parser option;
- event source rows are strictly increasing;
- candidate / rejection decision is exclusive;
- accepted row with zero warnings is valid;
- rejected row without issue code is invalid;
- raw rejected values cannot fit the rejection type;
- spool stream hash changes on ordering, count or content changes;
- final Preview hash changes when either stream changes;
- cancellation is terminal and cannot resume a partial iterator.

## Integration tests

- 100,000-row spool is parsed before transaction start;
- transaction duration excludes source parsing time;
- candidate insert failure rolls back rejection rows and Preview;
- rejection insert failure rolls back candidate rows and Preview;
- finalize failure rolls back all rows;
- account epoch change between parse and commit rejects the commit;
- source object version change rejects the commit;
- adapter digest mismatch rejects the commit;
- duplicate commit retry returns one Preview;
- conflicting retry is rejected;
- crash-after-commit retry returns the committed Preview;
- spool is deleted after success, failure, cancellation and expiry.

## Adversarial tests

- spool file modified after manifest creation;
- truncated accepted stream;
- extra rejected record appended;
- duplicate or non-contiguous ordinal;
- invalid UTF-8 or malformed internal record;
- issue code containing control characters or private text;
- symlink replacement attempt in spool directory;
- cross-job spool path substitution;
- stale account epoch;
- deletion starts during parse and immediately before commit.

---

# 6. Current implementation status

```txt
synchronous Generic CSV iterator:
created

CSV → Preview RowEvent bridge:
created

candidate + safe rejection hash model:
created

reference AtomicMaterializer:
created, test-only / vertical-slice only

production spool writer / reader:
not created

concrete pgx bulk-copy repository:
not created

production PostgreSQL wiring:
BLOCKED until this contract is implemented and tested
```

This contract replaces the earlier assumption that parsing and Preview persistence should occur in one long database transaction. Atomic visibility is required; long-lived parse transactions are not.
