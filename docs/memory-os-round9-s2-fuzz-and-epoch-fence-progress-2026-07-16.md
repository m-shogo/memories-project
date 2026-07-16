# Memory OS Round 9 — S2 Fuzz and Account-Epoch Fence Progress

最終更新: 2026-07-16

## Authority

This addendum supersedes older exact Go file/test counts and older statements that account-epoch fencing or parser fuzz targets had not been started. It does not override the Round 9 security architecture, threat model, hard stops or production `NO-GO` decision.

## Current executable inventory

```txt
Go files:     33
unit tests:   64
fuzz targets:  2
```

Local Go 1.23 validation:

```txt
go test ./...       PASS
go vet ./...        PASS
go test -race ./... PASS
```

Short local fuzz evidence:

```txt
Generic CSV parser:
46,723 executions / PASS

Apple compact JWT parser:
55,156 executions / PASS
```

The fuzz corpus is not a substitute for long-running release fuzzing or independent review.

---

# 1. Fuzz targets

## 1.1 Generic CSV

Target:

```txt
FuzzParserNeverPanicsOrExpandsLimits
```

Properties checked:

- arbitrary bytes do not panic;
- input above the fuzz cap is skipped rather than allocated;
- emitted rows never exceed the configured row limit;
- accepted candidates always contain a valid 64-character fingerprint;
- malformed quoting, invalid UTF-8, duplicate headers and formula-like content are exercised.

## 1.2 Apple compact JWT

Target:

```txt
FuzzParseCompactTokenNeverPanics
```

Properties checked:

- arbitrary compact-token strings do not panic;
- over-limit credentials are skipped before parser pressure;
- malformed segment counts, base64, JSON and signatures remain bounded parser failures.

## 1.3 CI smoke

`.github/workflows/import-api-security-slice.yml` now runs both fuzz targets for five seconds with `GOMAXPROCS=4` and a 30-second command timeout after format, vet and race tests.

Remote workflow result is not observable through the available connector and is not claimed as PASS.

---

# 2. Canonical account-epoch guard

Package:

```txt
services/import-api/internal/epochguard
```

The guard reads the canonical server-side account-control state using the account ID from the verified Principal. It never accepts an account ID from an HTTP request body.

Decisions:

```txt
same account + same epoch + active: allow
newer canonical epoch:              reject stale work
deleting:                           reject
deleted:                            reject
suspended:                          reject
mismatched account snapshot:        reject
unknown state / source failure:      reject
```

The checkpoint is a fast-fail second layer. PostgreSQL RLS, owner/epoch predicates and atomic write conditions remain authoritative against races after a checkpoint.

---

# 3. Required fenced production composition

Package:

```txt
services/import-api/internal/fenced
```

Production composition must use these wrappers rather than wiring raw upload, Preview or Apply services directly.

## Upload checkpoints

```txt
request start
→ before authorization insert
→ after object-storage HEAD
→ before authorization consume
→ before scan enqueue
```

If deletion changes the account epoch while the object is being inspected, the authorization is not consumed and no scan ticket is created.

## Preview checkpoints

```txt
materialization start
→ candidate staging inside transaction
→ immediately before immutable Finalize
```

A stale worker cannot finalize a Preview. Candidate staging remains part of the transaction and must roll back when Finalize is fenced.

## Apply checkpoints

```txt
Apply start
→ before idempotency claim
→ immediately before Memory write
→ before Apply completion
```

A deletion race cannot continue from a valid Preview into a new Memory write after the account epoch changes.

Tests prove:

- epoch change after object HEAD blocks consume and scan;
- epoch change before Preview Finalize blocks finalization;
- epoch change after idempotency claim but before Memory write blocks Apply;
- missing fence configuration fails closed.

---

# 4. What remains incomplete

```txt
canonical account-control PostgreSQL table and repository
atomic epoch increment at deletion start
worker lease cancellation and queue invalidation
signed URL revocation / object cleanup
concrete PostgreSQL write predicates
backup restoration tombstone replay
real object-storage integration
real parser supervisor runtime
long-running fuzz corpus
remote CI confirmation
```

Production remains `NO-GO`.

---

# 5. Next correct sequence

```txt
1. add canonical account-control and domain tables to PostgreSQL migration
2. implement concrete PostgreSQL repositories
3. integrate epoch guard source with a narrowly scoped account-control query
4. test Go transactions against PostgreSQL 16 FORCE RLS
5. implement private versioned S3-compatible signer and HEAD adapter
6. test overwrite, expiry, checksum and deletion cancellation
7. implement parser supervisor and adapter-digest verification
8. add deletion race and backup-restore integration tests
9. run longer fuzz campaigns and preserve minimized corpus
10. only then begin iOS Share Extension vertical slice
```
