# Memory OS Background Deletion Runtime Checkpoint

最終更新: 2026-07-24

## Verdict

```txt
Asynchronous, resumable account erasure with a claim lease:
CREATED AND LIVE-PROVEN INCLUDING INTERRUPTION AND RESUMPTION

Apple code exchange / clients:
NOT IMPLEMENTED

production:
NO-GO
```

## The gap this closes

Erasure ran inside the HTTP request that asked for it. That tied the whole
sweep — every table plus the object store — to one connection. A timeout, a
deploy or a crash mid-sweep left the account fenced in `deleting` with
**nothing that would ever look for it again**. The user had been told deletion
started, and it had; nothing would finish it.

The previous checkpoint recorded this honestly as an open gap rather than
claiming it was fine. This closes it.

## What changed in the request path

`DELETE /v1/account` now does exactly one thing: bump the epoch. It returns
**202 Accepted** with `status: "deleting"` and no counts.

That is the honest response. The counts it used to return described work the
request performed; now it performs none, and reporting counts would claim an
erasure that had not happened. What the request *does* guarantee is the part
that must be synchronous — from the moment it returns, the account is
unreachable from every surface, which is the promise actually owed at request
time.

## Migration 008

- `account_control` gains `deletion_lease_until` and `deletion_attempts`.
  Attempt count only: a failure reason would be free text derived from runtime
  state, and this table must never accumulate anything that could carry a
  fragment of the user's own content.
- `claim_deletion_work(lease_seconds)` leases the oldest unleased account in
  state `deleting`, using `FOR UPDATE SKIP LOCKED` so concurrent workers take
  disjoint accounts instead of blocking. The worker cannot name the account —
  the database picks it — so a worker can never be aimed at a live tenant.
- `release_deletion_lease()` hands a claim back after a failure so a retry
  starts immediately instead of waiting the lease out. It deliberately cannot
  mark anything deleted; only `complete_account_deletion()` does that, and only
  after the sweep.
- `complete_account_deletion()` now also clears the lease, or the tombstone
  would violate its own state constraint.
- The claim needs to scan before it knows which account it will get, so it
  cannot run under the account-scoped policy. A narrow policy lets the table
  owner reach rows already in state `deleting` and nothing else — and only the
  SECURITY DEFINER bodies ever run as that role, since no login role is a
  member of `memory_migration_owner`.

Note the same trap as migration 006: inside a `SECURITY DEFINER` body
`current_user` is the function owner, so a `current_user = 'memory_deletion_runtime'`
test would reject the very caller the EXECUTE grant admits. The role half is
enforced by the grant; only the state half is re-checked in the body.

## Ordering, and why it survives interruption

The worker erases objects **before** the rows that name them, exactly as the
synchronous version did, and for a reason that matters more now: the rows are
the only ledger of what the bucket holds. A partially erased account still
lists everything that remains, so a resumed attempt is *correct*, not merely
retried. Version deletes are idempotent, so re-erasing what is already gone
converges.

A failed attempt returns the error rather than swallowing it to keep the loop
going. An erasure that did not happen must be visible, and the account stays
fenced and claimable either way.

## Verification actually run

- 9 migrations applied in sequence on a freshly created database, followed by
  all 9 SQL suites reporting PASS, including the new claim/lease contract:
  oldest-first claim, no double-claim of a leased account, an active account
  never claimed, release makes it claimable again with a rising attempt count,
  release cannot mark anything deleted, completion clears the lease, and a
  completed account is no longer claimable.
- **Every test database and the login role were dropped first**, so the run
  reproduced CI's clean-cluster conditions rather than inheriting local state.
  This matters: the previous checkpoint passed locally and failed in CI
  precisely because a migration was missing from one list and a stale local
  database hid it.
- Full Go module, `-count=1`, plain and `-race`: all packages ok.
- `TestAccountDeletionFencesAndErasesOverHTTP` proves the whole async path:
  the request returns 202 and erases nothing; a worker whose object store
  always fails leaves the account in `deleting` with its rows and attempt count
  intact; the next worker resumes and finishes, reporting
  `memory_item=2, preview_ready=1, import_job=1, account_session=2` plus the
  erased object versions; every surface then returns 401; all nine tables hold
  zero rows for that owner; the tombstone remains at the deletion epoch.

## Not done

- The runtime polls every 30s inside the API process. It claims through the
  database lease, so moving it to its own deployment changes nothing about
  correctness — but that move has not been made.
- Nothing alerts on an account whose `deletion_attempts` keeps climbing. The
  count exists so an operator *can* see a poisoned account; no one is watching
  it yet.
- Apple code exchange, clients, rich Memory domain model: unchanged.
