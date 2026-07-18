# Memory OS Preview Spool Reconciliation Checkpoint

最終更新: 2026-07-18

## Verdict

```txt
manifest contract:
HARDENED

Linux attempt filesystem / bounded writer / seal publication:
PARTIAL IMPLEMENTATION

independent reader / decode / count / re-hash:
PARTIAL IMPLEMENTATION

startup reconciliation + TTL cleanup:
PARTIAL IMPLEMENTATION CREATED

production PostgreSQL commit:
BLOCKED

production:
NO-GO
```

This checkpoint closes the crash-residue boundary: a supervisor root can now be brought to a state holding nothing but trusted unexpired sealed attempts, without recursive deletion and without ever deleting a sealed unexpired attempt.

## Implemented files

```txt
services/import-api/internal/previewspool/reconcile.go
services/import-api/internal/previewspool/reconcile_linux.go
services/import-api/internal/previewspool/reconcile_unsupported.go
services/import-api/internal/previewspool/reconcile_linux_test.go
services/import-api/internal/previewspool/reconcile_interruption_linux_test.go
```

## Classification and actions

Reconciliation runs once at startup, before any attempt is created, holds the manager lock for the whole pass and walks root entries in deterministic name order:

```txt
foreign name / symlink / non-directory / unsafe stat
→ QUARANTINED in place (never deleted)

unknown entry inside an attempt
→ QUARANTINED in place

manifest.tmp without manifest.json
→ unsealed crash residue → attempt removed

manifest.tmp + manifest.json sharing exactly one inode with exactly two links
→ completed publication → temp unlinked, attempt directory fsynced, manifest kept

manifest.tmp + manifest.json on different inodes (or wrong type/mode/owner/links)
→ QUARANTINED in place

no manifest.json or empty placeholder manifest
→ unsealed → attempt removed

manifest present but not strictly canonical, oversized, or naming a foreign spool ID
→ QUARANTINED in place

sealed and now >= expiresAt
→ expired → attempt removed

sealed and unexpired
→ KEPT, byte-untouched, still passes independent verification
```

Removal touches only the four fixed entry names plus the attempt directory itself; the root directory is fsynced after any mutation. Quarantined entries are reported (`ReconcileReport.Quarantined`) and require operator review.

## Failure semantics

- a cancelled or failed pass returns the partial report and is safe to re-run; every action is idempotent per entry;
- no code path recursively deletes unknown content;
- a sealed unexpired attempt is never deleted, and reconciliation leaves its bytes verifiable;
- expiry uses the same boundary as the verifier (`now >= expiresAt` removes);
- non-Linux fails closed.

## Targeted tests

8 top-level tests cover:

- sealed unexpired kept, idempotent re-run, post-reconcile verification pass;
- expired sealed removal;
- unsealed removal (placeholder and claimed-but-unsealed);
- crashed-publication completion (both names, one inode) with post-completion verification;
- temp-only residue removal;
- quarantine of foreign root names, root symlinks, unknown attempt entries, non-canonical manifests, conflicting temp inodes and foreign-spool manifests — all without deletion;
- cancellation mid-pass with resumed full coverage;
- input validation (nil manager/context, zero clock, closed manager).

## Validation language

```txt
repository-integrated Go suite (exact HEAD 3628123fc978f4fcc0a12daed13235599b8218af):
gofmt clean + go vet + go test -race + both 5s fuzz smokes PASS
(golang:1.23 Linux container, local Docker)

remote GitHub Actions on the pushed HEAD:
recorded after the push completes
```

## Residual risks

- reconciliation assumes exclusive startup execution; a deployment supervisor must guarantee no concurrent parser workers on the same root;
- quarantined entries accumulate until an operator acts; no alerting exists;
- no production mount evidence for ephemeral `noexec,nosuid,nodev` storage;
- no production PostgreSQL commit integration.

## Immediate next task

```txt
Create the production Preview PostgreSQL domain only:
candidate / rejection / ready Preview tables
→ deterministic commit keys and uniqueness
→ immutability and contiguous ordinal constraints
→ FORCE RLS profiles matching the Round 9 contract
→ no partial reader visibility
→ SQL tests before any Go repository code
```

Do not add object storage, parser-container or client wiring in that checkpoint.
