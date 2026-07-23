# Memory OS Deletion Fencing Checkpoint

最終更新: 2026-07-24

## Verdict

```txt
Account deletion fencing + authorized erasure sweep + fenced HTTP surfaces:
CREATED AND LIVE-TESTED OVER AUTHENTICATED HTTP

Apple code exchange / clients / object-storage erasure:
NOT IMPLEMENTED

production:
NO-GO
```

Deletion was the one security boundary that existed on paper but not in the
running system. The epoch-bump machinery had been written in migration 002
and never wired: the migration was not applied by CI or by any Go suite, its
test file had never run, the tables added afterwards (Preview domain, applied
memory) carried no epoch predicate at all, and the `epochguard`/`fenced`
packages — written, tested, correct — were not composed into the deployed
server. This checkpoint closes all of it.

## Findings this checkpoint corrected

- **The account_control migration was orphaned.** `002_memory_os_account_control.sql`
  was in no migration list and in no workflow step, so
  `account_epoch_is_authorized()` did not exist in any database the tests ran
  against. Its test suite had therefore never executed once.
- **A sweep could not have deleted anything.** The tenant policy requires
  `row.account_epoch = current epoch`, but the deletion bump moves the account
  to a *new* epoch while every existing row keeps the old one. The deletion
  runtime would have seen zero rows. The pre-existing assertion
  (`count = 0 after delete`) passed on invisibility, not erasure — a
  false-positive that would have shipped "deletion" that deleted nothing.
- **Post-002 tables were never fenced.** `preview_ready`, `preview_candidate`,
  `preview_rejection` and `memory_item` had owner/epoch policies without the
  authorization predicate, so a bumped account could still reach its committed
  Previews and applied memory.
- **Sessions were outside the sweep.** `account_session` is reachable only
  through SECURITY DEFINER functions, so it was silently absent from erasure.
- **The fence was never composed.** `cmd/import-api-server` wired the bare
  services, not the `fenced.*` wrappers, so the guard protected nothing in the
  deployed binary.

## Migration 006

- Reinforces the four post-002 tables with the full
  `owner = current AND epoch = current AND account_epoch_is_authorized()`
  predicate.
- `deletion_sweep_authorized()` — true only for `memory_deletion_runtime`, only
  while the account is in state `deleting`. Row epoch is deliberately *not*
  compared: erasing an account means erasing every epoch it ever wrote.
- Per-table PERMISSIVE SELECT/DELETE policies for the deletion runtime, each
  still scoped to `owner_account_id = current_account_id()`.
- `purge_account_sessions()` keeps the definer-only access path for
  `account_session` instead of breaking it with a table grant. It cannot reuse
  `deletion_sweep_authorized()` (inside a definer body `current_user` is the
  function owner), so the role half is enforced by the EXECUTE grant and the
  `deleting` state is re-checked in the body.
- `sweep_deleted_account()` erases all nine owned tables and returns per-table
  removal counts — the receipt, not an estimate.

## Go composition

```txt
services/import-api/internal/accountdelete/service.go   deletion boundary
services/import-api/internal/pgrepo/accountcontrol.go   epoch source + sweep
services/import-api/internal/httpapi/account_handler.go DELETE /v1/account
services/import-api/internal/fenced/services.go         + PreviewRead fence
services/import-api/internal/httpserver/server.go       account route
services/import-api/cmd/import-api-server/main.go       fenced composition
```

- The account erased is always the principal's own: the endpoint takes no body
  and no account identifier, and `begin_account_deletion()` reads the account
  from transaction-local verified context. No request field can redirect it.
- Only `ios_user_access_token` may delete. Device sessions, browser pairings,
  worker leases and the deletion worker itself are refused with 403.
- The service refuses to sweep if the returned epoch did not advance: the bump
  is what closes the fence on every other live session.
- A failed sweep is reported as a failure. The account stays fenced in
  `deleting`, so a retry is safe — but success is never claimed for an erasure
  that did not happen.
- `AccountControl.Current` reads through the pool rather than `dbscope`,
  because the executor needs a verified epoch and the whole point of the read
  is to learn the canonical epoch when the caller's may be stale. The
  `account_control` SELECT policy filters on account_id alone, so the read
  stays RLS-scoped either way.

## Verification actually run

- 7 SQL suites (`import_rls`, `account_control`, `upload_authorization`,
  `preview_domain`, `account_session`, `apply_memory`, `deletion_fencing`)
  applied in sequence on PostgreSQL 16 and all reporting PASS.
- Full Go module, `-count=1`, plain and `-race`: all packages ok.
- `TestAccountDeletionFencesAndErasesOverHTTP` confirmed running (not skipped)
  and passing: a real account with a committed Preview, two applied memory
  items and two live sessions is deleted over HTTP; the receipt reports
  `memory_item=2, preview_ready=1, import_job=1, account_session=2`; every
  surface then returns 401 for the same token; all nine tables hold zero rows
  for that owner; the tombstone remains at the deletion epoch.

## Not done

- Object-storage erasure. The sweep removes the `quarantine_object` rows but
  does not yet delete the underlying versioned objects from the bucket. This
  is a real remaining gap, not a completed step.
- Deletion is synchronous inside the request. A background deletion runtime
  with resumable sweeps is future work; today a failure leaves the account
  fenced and awaiting a retry.
- Apple code exchange, iOS client, Desktop Portal, Memory Town runtime remain
  unimplemented by design.
