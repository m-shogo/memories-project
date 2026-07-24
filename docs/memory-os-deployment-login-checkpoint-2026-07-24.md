# Memory OS Deployment Login Principal Checkpoint

最終更新: 2026-07-24

## Verdict

```txt
Non-superuser deployment login + FORCE RLS proof on the path a deployment
actually uses: CREATED AND LIVE-PROVEN

Apple code exchange / clients / background deletion runtime:
NOT IMPLEMENTED

production:
NO-GO
```

## The gap this closes

Every runtime role is NOLOGIN by design, so something else has to open the
connection. Until now that something was the migration superuser — in the dev
stack, in CI, and in every live test in the repository.

That made a whole class of proof vacuous. A superuser **bypasses row-level
security outright**: `rolbypassrls` is implied, and `FORCE ROW LEVEL SECURITY`
does not apply. Every "FORCE RLS holds" result the project had recorded was
true for the NOLOGIN runtime roles, but said nothing about the principal a
deployment would really connect as. A deployment that connected with an
over-privileged login would have had every tenant policy silently disabled,
and no test in the suite would have noticed.

`productionNosuperuserLoginProven` had been sitting false in the authority
index for exactly this reason. It is now true, and it was earned by moving the
tests onto that path rather than by asserting it.

## Migration 007

`memory_app_login` is deliberately powerless on its own:

- `LOGIN NOINHERIT NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION`
- **no** table privileges, **no** `USAGE` on `memory_os`
- member of `memory_api_runtime`, `memory_worker_runtime`,
  `memory_deletion_runtime`, `memory_auth_runtime` — and explicitly **not** of
  `memory_migration_owner`, which owns the tables and the policies
- attributes are re-asserted on every apply, so an operator who loosened the
  role by hand gets it tightened again rather than keeping a quiet escalation

`NOINHERIT` is the load-bearing attribute. With `INHERIT`, the connection would
hold every runtime role's privileges before any `SET ROLE`, and the scoped
executor's role discipline would be decorative. With `NOINHERIT`, membership
grants nothing until the connection issues an explicit `SET ROLE`.

No password is set in the migration. Credentials belong to deployment
configuration, never to version control.

## What is actually proven, and where

The SQL suite can only check attributes and grants — psql is already connected
as the superuser, so it cannot demonstrate the connection itself. The other
half is carried by the Go live suites:

- `TestDeploymentLoginIsBoundByForceRLS` opens a real connection as
  `memory_app_login` and proves: reads are denied before any `SET ROLE`;
  `SET ROLE memory_migration_owner` fails; after `SET LOCAL ROLE
  memory_api_runtime` it sees exactly its own account's row and zero foreign
  rows; a cross-tenant INSERT fails; and `DISABLE ROW LEVEL SECURITY`,
  `DROP POLICY` and `ALTER ROLE ... BYPASSRLS` all fail.
- The entire HTTP live suite — upload → preview → apply → account deletion —
  now runs through `memory_app_login` instead of the superuser. The preview
  committer does too.
- Both helpers assert `current_user = memory_app_login` with `rolsuper` and
  `rolbypassrls` false before running anything. Without that assertion,
  repointing the database URL at a superuser would silently turn every RLS
  proof in those packages back into a no-op.

The test password is the one already present in the test database URL. That
introduces no new secret, and — unlike a per-run random value — lets the
several test binaries sharing one cluster set the same thing. The `ALTER ROLE`
runs under advisory lock 730002, because role changes are cluster-wide and two
packages running in parallel otherwise collide with `tuple concurrently
updated` (this actually happened, and is why the lock is there).

## Verification actually run

- 8 migrations applied in sequence on a **freshly created** database, followed
  by all 8 SQL suites reporting PASS.
- Full Go module, `-count=1`, plain and `-race`: all packages ok.
- `TestDeploymentLoginIsBoundByForceRLS` confirmed running (not skipped) and
  passing.

## Not done

- The dev stack and CI still *apply migrations* as the superuser, which is
  correct — migrations need ownership. Only the application path moved.
- `cmd/import-api-server` takes whatever database URL it is given; pointing it
  at the unprivileged login is deployment configuration, and there is no
  deployment yet.
- Background deletion runtime, Apple code exchange, clients: unchanged.
