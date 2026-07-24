# Memory OS Deletion Visibility Checkpoint

最終更新: 2026-07-24

## Verdict

```txt
Deletion backlog alerting, with identifiers withheld from the alerting surface:
CREATED AND LIVE-PROVEN

Apple code exchange / clients:
NOT IMPLEMENTED

production:
NO-GO
```

## The gap this closes

The previous checkpoint counted deletion attempts so a poisoned account would
be *visible* to an operator. Nobody was looking. An account whose erasure
failed every time would retry forever in silence: the user had asked to be
deleted, was not being deleted, and no signal existed anywhere.

A counter nobody reads is not observability.

## Two surfaces, deliberately unequal

```txt
deletion_backlog()   counts and ages only, no identifiers
                     -> memory_deletion_runtime, memory_readonly_observer
stuck_deletions()    account identifiers, worst first
                     -> memory_deletion_runtime only
```

The split is the point. Alerting needs a *number*; a dashboard that listed
accounts would turn watching deletion health into a way to enumerate people.
Identifiers go only to the runtime that must act on them, and the observer
role — which until now held no privilege anywhere in the schema — gets the
aggregate as its first and only capability.

Migration 009 grants that role `USAGE` on `memory_os`, without which it could
not name a function at all. Usage alone conveys nothing: every table in the
schema still revokes all privileges from it, and the test asserts that a direct
`SELECT` on `account_control` is still refused.

Neither function returns anything derived from user content. The tables they
read hold none, and that is a property to preserve rather than an accident —
which is also why migration 008 stores an attempt *count* and no failure
reason: a reason string would be free text derived from runtime state.

## Threshold

`StuckAttemptsThreshold = 3`. This is a judgement call, not a measurement: it
is where an account stops looking like a normal retry and starts looking like
one that will never succeed. The SQL functions take it as a parameter and floor
it at 1, so a caller cannot pass 0 to widen the listing to accounts that have
never been attempted.

The API runtime can call neither function. Deletion health is an operator
surface, not a tenant one.

## Verification actually run

- 10 migrations applied in sequence on a freshly created database, followed by
  all 10 SQL suites reporting PASS. The new suite proves: the observer reads
  correct counts (pending excludes the completed account; oldest-pending age
  ignores it too), the observer is refused both the identifier listing and
  direct table access, the runtime gets identifiers worst-first, the API role
  is refused both, and a zero threshold floors at one attempt.
- Every test database and the login role dropped first, reproducing CI's clean
  cluster rather than inheriting local state.
- Full Go module, `-count=1`, plain and `-race`: all packages ok.
- The live HTTP proof now continues past erasure: after one failed attempt the
  backlog sees the account but reports **healthy** — one failure must not page
  anyone — and after crossing the threshold it reports **stuck**. Once the
  resumed worker completes the deletion the backlog is healthy again, because
  an alert that never clears is an alert nobody reads.

## Observed in the real binary

The alert was watched end to end, not only unit-proven. `cmd/import-api-server`
was pointed at the dev PostgreSQL with a deliberately unreachable object-store
endpoint and an account seeded in `deleting`:

```txt
deletion runtime sweep failed; account remains fenced and claimable
ALERT deletion backlog: 1 pending, 1 stuck at >=3 attempts (worst 6 attempts, oldest pending 5h0m40s)
deletion runtime sweep failed; account remains fenced and claimable
ALERT deletion backlog: 1 pending, 1 stuck at >=3 attempts (worst 7 attempts, oldest pending 5h1m10s)
```

Three things this confirmed that the unit tests could not: the failure line
carries no reason string, the alert carries counts and ages but no account
identifier, and the attempt count actually climbs across cycles rather than
resetting. The seeded rows were removed from the dev database afterwards.

An earlier attempt at this demo seeded an account with a high attempt count but
nothing to erase — the runtime simply deleted it and no alert fired. That was
correct: the account was not stuck, only labelled as such. The alert follows
whether erasure fails, not what the counter says.

## Not done

- The alert is a line on stdout from the runtime loop. Wiring it to a real
  alerting system is deployment work, and there is no deployment yet.
- Nothing acts on a stuck account automatically. That is deliberate — an
  account failing erasure repeatedly needs a human to look at why — but it
  means the loop can only report, not resolve.
- Apple code exchange, clients, rich Memory domain model: unchanged.
