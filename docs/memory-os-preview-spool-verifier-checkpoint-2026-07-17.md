# Memory OS Preview Spool Verifier Checkpoint

最終更新: 2026-07-18

## Verdict

```txt
manifest contract:
HARDENED

Linux attempt filesystem:
PARTIAL IMPLEMENTATION

bounded accepted/rejected writer:
PARTIAL IMPLEMENTATION

stream fsync + no-replace manifest publication:
PARTIAL IMPLEMENTATION

independent reader / decode / count / re-hash:
PARTIAL IMPLEMENTATION CREATED

startup reconciliation / TTL cleanup:
NOT IMPLEMENTED

production PostgreSQL commit:
BLOCKED

production:
NO-GO
```

This checkpoint proves the independent read-side boundary: a sealed spool can now be rejected or accepted from exact on-disk bytes without trusting any writer- or sealer-process state. It does not create the PostgreSQL commit path.

## Implemented files

```txt
services/import-api/internal/previewspool/verifier.go
services/import-api/internal/previewspool/verifier_linux.go
services/import-api/internal/previewspool/verifier_unsupported.go
services/import-api/internal/previewspool/verifier_linux_test.go
services/import-api/internal/previewspool/verifier_corruption_linux_test.go
```

## Successful transition

```txt
verify root descriptor identity
→ open attempt directory descriptor-relative with O_NOFOLLOW
→ require directory type / exact 0700 / effective-user owner
→ list entries and fail closed on anything beyond the three fixed names
→ require manifest.tmp absent
→ open manifest.json with O_NOFOLLOW
→ require regular / exact 0600 / single link / bounded size
→ read exact manifest bytes
→ strictly decode exactly one JSON value with unknown fields forbidden
→ re-serialize decoded fields through the seal builder
→ require byte-for-byte canonical equality
→ require manifest spool ID equals the requested attempt
→ require the manifest unexpired against the caller clock
→ require exact job / owner / epoch / source / adapter / options expectation match
→ reopen accepted.spool and rejected.spool with O_NOFOLLOW
→ require regular / exact 0600 / single link
→ decode 8-byte big-endian length prefixes with record and byte bounds enforced while reading
→ independently count records and bytes and SHA-256 the exact stream bytes
→ require recomputed evidence equal to every manifest stream binding
→ return recomputed (never copied) evidence
```

Canonical re-serialization makes the strict decoder exactly as narrow as the sealer: duplicate keys, unknown fields, whitespace, re-ordered fields, non-UTC timestamps, altered security constants and every seal-time validation failure all produce one malformed-manifest rejection.

## Failure semantics

- verification is read-only, stateless and retryable; cancellation is not sticky;
- a missing attempt, missing manifest, empty placeholder manifest, missing stream, `manifest.tmp` residue and unknown entries are all distinct rejections and never trigger deletion;
- symlinked entries are not followed; hard-linked, wrong-mode or wrong-owner entries are unsafe;
- torn length prefixes, zero or oversized record lengths, record/byte-bound violations and truncated bodies reject as malformed framing before hashing completes;
- appended records, appended bytes and same-length content substitution reject as stream mismatch;
- a manifest naming a different spool ID and every expectation-field mismatch reject as binding mismatch;
- expiry is enforced at the boundary (`now >= expiresAt` rejects);
- no code path in the verifier can start, prepare or authorize a database transaction.

## Targeted tests

15 top-level tests cover:

- acceptance with recomputed evidence equal to sealed evidence, and repeatability;
- input validation (nil manager/context, zero clock, invalid/unknown spool ID, closed manager);
- unsealed attempts (placeholder manifest and claimed-but-unsealed);
- `manifest.tmp` residue;
- unexpected directory entries;
- 11 expectation-field mismatches plus a spoofed manifest spool ID;
- expiry boundary, post-expiry and pre-expiry acceptance;
- non-canonical manifests (trailing whitespace, unknown field, inflated row count, disabled security constant);
- hard-linked manifest, symlinked stream, world-readable stream;
- cancelled-then-retried verification;
- truncation, appended record, torn append, zero/oversized length prefixes and accepted/rejected content substitution.

## Validation language

```txt
repository-integrated Go suite (exact HEAD e75b7324e0388b264d90f67ee3094d788fadf5f4):
gofmt clean + go vet + go test -race + both 5s fuzz smokes PASS
(golang:1.23 Linux container, local Docker)

Preview spool contract validator (scripts/validate-memory-os-preview-spool.py):
PASS

remote GitHub Actions on this HEAD:
UNCONFIRMED at commit time
```

This checkpoint also repaired the previously failing repository-integrated suite: five sources were unformatted and `internal/upload/service_test.go` called a pointer method on an unaddressable value, which failed the remote Format/Vet steps on every earlier push.

## Residual risks

- no startup reconciliation for temp/both-name/crash residue;
- no TTL cleanup worker;
- verification passes reflect a moment in time; the commit path must hold the verified evidence and re-check epoch/job state inside its own transaction;
- no production mount evidence for ephemeral `noexec,nosuid,nodev` storage;
- no production PostgreSQL commit integration.

## Immediate next task

```txt
Implement Preview spool startup reconciliation and TTL cleanup only:
enumerate the supervisor root descriptor-relative
→ classify attempts (sealed / unsealed / temp residue / both-name residue / unknown)
→ terminally quarantine or remove crash residue without recursive deletes of unknown entries
→ remove expired sealed attempts after the 24-hour TTL
→ never delete a sealed unexpired attempt
→ prove interruption safety with targeted tests
```

Do not add PostgreSQL, object storage, parser-container or client wiring in that checkpoint.
