# Memory OS Runtime-Role Repository Checkpoint

最終更新: 2026-07-23

## Verdict

```txt
pgx-backed runtime-role scoped executor + concrete upload repository:
CREATED AND LIVE-TESTED UNDER FORCE RLS (non-superuser access path)

executable HTTP server / Apple session issuance / clients:
NOT IMPLEMENTED

production:
NO-GO
```

This is the first slice of the executable-API composition: real service code
now reads and writes PostgreSQL **through the runtime roles**, closing the
residual risk recorded at the importctl checkpoint ("the executable API must
read through the runtime roles instead").

## Implemented files

```txt
services/import-api/internal/pgscope/beginner.go   (pgx adapter for dbscope)
services/import-api/internal/pgrepo/upload.go      (concrete upload.Repository)
services/import-api/internal/pgrepo/upload_live_test.go
```

## Design

`dbscope.Executor` (existing, driver-agnostic) opens every transaction with
`SET LOCAL ROLE` to a fixed NOLOGIN/NOINHERIT/NOBYPASSRLS runtime role plus
transaction-local `app.current_account_id` / `app.current_account_epoch`.
`pgscope.Beginner` adapts a pgx pool to that contract; `pgscope.Tx` adds the
query surface repositories need. Repositories assert back with
`pgscope.From`; a foreign executor is a composition error
(`ErrForeignTransaction`), never silently degraded access.

`pgrepo.Upload` implements the full `upload.Repository` over the security
migrations: import-job lookup, authorization insert/read/consume/revoke
(display filename in `safe_metadata`; every security binding in constrained
columns) and scan enqueue into `memory_os.quarantine_object` as
`scan_pending` with the exact verified object version.

Row visibility is decided by FORCE RLS, not repository code: a row another
tenant owns is absent, never filtered in Go.

## Live evidence (4 top-level tests, own database, real MinIO)

- inside a scoped transaction `current_user` is `memory_api_runtime`, and an
  INSERT into `preview_ready` fails with `42501` — proving `SET LOCAL ROLE`
  actually drops the privileged login for RLS purposes;
- tenant isolation through the executor: owner A reads its job; owner B gets
  not-found for the same ID;
- `upload.Service` end to end through runtime roles: Issue → real presigned
  PUT to MinIO → Complete (HEAD-verified exact version) → authorization
  consumed → scan ticket enqueued with the object version; a second Complete
  is rejected as consumed; a foreign tenant's Complete is not-found;
- repositories reject transactions from any other executor.

## Validation language

```txt
local golang:1.23 + postgres:16 + minio (scripts/dev-up.sh),
exact code HEAD 41a6c1404ed3fb50aaeab7994213e8f3954ac43f:
gofmt clean + go vet + go test ./... + go test -race ./... (21 packages,
all live suites included) + non-race parsersup bounds + both 5s fuzz smokes PASS

remote workflows:
recorded after the push completes
```

## Residual risks

- the dev stack connects as the postgres superuser and relies on SET ROLE
  semantics; production must use a dedicated NOSUPERUSER login with explicit
  role memberships (deployment evidence still missing);
- scan tickets are enqueued but no scan worker consumes them yet;
- Apple code exchange, replay/session stores, HTTP server main and clients
  remain unimplemented.

## Immediate next task

```txt
continue the executable-API composition: HTTP server main over the existing
strict handlers (internal/httpapi) + session-token principal middleware with
a concrete PostgreSQL session store — Apple code exchange remains a later
boundary because it needs real Apple credentials.
```
