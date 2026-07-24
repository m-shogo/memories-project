# Memory OS — update_safe_fields Closure Checkpoint

最終更新: 2026-07-24

## Verdict

```txt
Destructive update_safe_fields apply path: CLOSED FAIL-CLOSED, LIVE-PROVEN
Append-only supersession (the replacement): NOT IMPLEMENTED, future work
skip_existing / keep_both: UNCHANGED
Apple code exchange: STILL THE SOLE nextRequired
production: NO-GO
```

## Why this checkpoint exists

The prior architecture checkpoint recorded F1 / GAP-MEM-005 honestly and left it
unfixed, because fixing it *properly* — corrections stored as append-only
supersession — changes Apply semantics and needs the unbuilt Memory domain.

But recording a live, reachable destructive path is not the same as being safe
from it. `update_safe_fields` was still a validated `DuplicatePolicy`, and its
implementation overwrote `memory_item.canonical_record` in place and repointed
`source_preview_id`, destroying both the earlier content and the record of where
it came from. Before Apple code exchange opens the API to real users, that path
is closed — not by building supersession, but by refusing the destructive policy
fail-closed until the safe replacement exists.

Closing a path is a smaller, safer change than building its replacement, and it
is the right thing to do first.

## What changed

Three layers, each refusing before it can do harm.

**Service** (`internal/apply/service.go`). `validateRequest` returns the new
`ErrDuplicatePolicyUnsupported` for `update_safe_fields`, before any transaction
is opened. No idempotency claim is written and no candidate is read. The policy
is never silently mapped onto `skip_existing` or `keep_both`: a client that
asked to update must not be told its update succeeded.

**Repository** (`internal/pgrepo/apply.go`). `ApplyMaterializedPreview` refuses
the same policy at its very top, before touching the transaction — defence in
depth if the service check is ever bypassed. The destructive `UPDATE
memory_os.memory_item` is deleted outright, as is the fingerprint-match count
query that existed only to feed it.

**Handler** (`internal/httpapi/apply_handler.go`). `ErrDuplicatePolicyUnsupported`
maps to `400 SEC_APPLY_DUPLICATE_POLICY_UNSUPPORTED`, kept distinct from
`SEC_APPLY_REQUEST_INVALID`. The value is well-formed and used to be accepted,
so the client is told the policy is unsupported, not that its request was
malformed.

The `DuplicateUpdateSafe` constant is kept rather than deleted, so the refusal
is explicit wherever the value can still arrive: an older client, a stored claim
row, or the migration 005 CHECK constraint that still lists it. Migration 005 is
**not** rewritten — the constraint keeps any historical claim rows valid, and
the closure is enforced at the application layer where it belongs.

## What did not change

`skip_existing` and `keep_both`: identical inserts, identical idempotency,
identical counts. Proven by a table-driven test asserting each still applies,
completes, and records its own policy on the claim.

## Verification actually run

- **Unit** (`internal/apply/service_test.go`): the refused request reaches
  neither the preview read, the idempotency claim, the materialization nor
  completion (every repository counter asserted zero); the error is
  distinguishable from `ErrInvalidRequest`; no fallback policy is substituted on
  the claim; and both supported policies keep their behaviour and counts.
- **Repository** (`internal/pgrepo/apply_policy_test.go`): the guard fires with a
  nil transaction, proving it runs before the transaction is used at all, while
  supported policies get past the guard (and fail only on the nil transaction).
- **Live HTTP** (`internal/httpserver/server_live_test.go`): applies a preview,
  snapshots every `memory_item` row (id, canonical_record, source_preview_id,
  updated_at), sends `update_safe_fields`, and asserts `400
  SEC_APPLY_DUPLICATE_POLICY_UNSUPPORTED` with every row byte-for-byte
  unchanged, no idempotency claim row consumed, and `keep_both` still working
  afterwards.
- gofmt clean, `go vet` clean, full `go test ./...` and `go test -race ./...`
  green, all SQL suites green on a fresh database. The full suite was run
  repeatedly to confirm a harness race fix (below) is stable.

### Harness race fixed in passing

`appLoginPool` took its role-password lock on advisory id 730002, distinct from
the migration lock 730001 — but migration 007 also ALTERs that role, so under
parallel packages the password change and the migration could mutate one role
concurrently and fail with `tuple concurrently updated`. The lock now runs on
the shared postgres maintenance database under the same 730001 id the migrations
hold. Pre-existing flakiness, surfaced by running the full suite; fixed rather
than retried.

## F1 / GAP-MEM-005 status

- The destructive path is **closed**. INV-MEM-003 in the invariant fixture now
  records `closedBy` instead of `currentlyViolatedBy`. Threat model T-032 and
  T-035 are updated from "weakened / violated" to closed.
- The *positive* rule — corrections stored non-destructively as append-only
  supersession — is still future work, gated behind the Memory domain, and
  GAP-MEM-005 now records exactly that narrowed gap.

## Not done, and not claimed

- No supersession table, no origin/assertion column, no Memory domain, no iOS,
  no Portal, no Town.
- Migration 005 is unchanged; the DB-level CHECK still lists the value by design.
- `nextRequired` is untouched and remains `["implement_apple_code_exchange"]`.
  This closure is recorded as its own completed checkpoint, not as a new next
  requirement.
- production remains NO-GO.
