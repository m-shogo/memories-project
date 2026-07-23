# Memory OS Executable HTTP Server Checkpoint

最終更新: 2026-07-23

## Verdict

```txt
executable Import API server (session auth over the strict upload handlers):
CREATED, LIVE-TESTED, AND EXERCISED FOR REAL WITH curl

Apple code exchange / replay store:
NOT IMPLEMENTED (needs real Apple credentials — explicitly a later boundary)

Apply/Memory persistence / clients:
NOT IMPLEMENTED

production:
NO-GO
```

For the first time an HTTP request can reach this backend: bearer-session
authentication resolves a verified principal, and the existing strict upload
handlers execute through runtime-role PostgreSQL access and the real
presigned-storage binding.

## Implemented files

```txt
infra/postgresql/security/004_memory_os_account_session.sql
infra/postgresql/security/test_memory_os_account_session.sql
services/import-api/internal/authstore/store.go
services/import-api/internal/httpserver/server.go
services/import-api/internal/httpserver/server_live_test.go
services/import-api/cmd/import-api-server/main.go
.github/workflows/security-contracts.yml (004 + session test steps)
```

## Session store design

Sessions authenticate requests **before** a principal (and therefore the
owner/epoch RLS context) exists, so `memory_os.account_session` cannot use
the standard tenant policy. Instead:

- the table stores **only SHA-256 token digests** — raw tokens exist only in
  the client and the request being authenticated;
- **no role holds any table privilege**; access is exclusively through three
  SECURITY DEFINER functions (`issue` / `resolve` / `revoke`);
- the new `memory_auth_runtime` role (NOLOGIN/NOINHERIT/NOBYPASSRLS) holds
  EXECUTE on those functions and nothing else;
- constraints bind the `ses_` ID shape, 64-hex digest, interactive-authority
  allowlist (worker/deletion leases can never be session-backed), a 30-day
  TTL cap and an active/revoked state machine;
- SQL tests prove: resolution round-trip, direct table SELECT denied even to
  the auth role (42501), other roles cannot execute the functions, unknown /
  expired / revoked digests resolve to nothing, duplicate digests rejected.

`authstore.Store` wraps the functions in short `SET LOCAL ROLE
memory_auth_runtime` transactions. `Resolve` collapses every failure —
wrong shape, unknown, expired, revoked — into one error so responses cannot
distinguish token states.

## HTTP composition

`httpserver.New` mounts an unauthenticated `GET /healthz` plus the existing
strict `httpapi` handlers behind the session middleware; the raw token is
never logged and never placed on the context — only the resolved principal
is. `cmd/import-api-server` wires pgx, the runtime-role executor, the
concrete repository and the SigV4 store, with hardened server timeouts and
graceful shutdown. Session issuance is **not** exposed over HTTP: production
sessions come from the Apple exchange (later boundary); development uses the
clearly-labeled `-dev-issue-session` mode which prints one token and exits.

## The visible run (real server, real curl)

```txt
1. POST /v1/import-jobs/{job}/upload-authorizations  (Bearer session)
   → 201 with presigned URL + bound headers
2. PUT source bytes to the presigned URL             → HTTP 200
3. POST /v1/upload-authorizations/{id}/complete      → HTTP 202
4. PostgreSQL: quarantine_object state=scan_pending
   with the real object version (dfc32d8a-…)
5. the same POST without a session                   → HTTP 401
```

## Live evidence (3 top-level HTTP tests + 5-block SQL suite)

- health probe needs no session;
- missing, malformed, forged, expired and revoked sessions all yield 401;
- full lifecycle over HTTP: issue → real presigned PUT → complete (202) →
  double completion 409 → cross-tenant completion 404.

## Validation language

```txt
local golang:1.23 + postgres:16 + minio (scripts/dev-up.sh),
exact code HEAD c36e2bd0f30079b7eff939c2cb900b4a9a3d65ed:
gofmt clean + go vet + go build ./cmd/... + go test ./... + go test -race ./...
(22 packages, all live suites included) + both 5s fuzz smokes PASS

migration 004 + all four SQL test suites re-verified on a fresh database: PASS

real-server curl demo executed against the dev stack: SUCCESS (transcript above)

remote workflows (pushed HEAD 21ed7d7, code identical to c36e2bd):
Import API Security Slice run 30012223776 SUCCESS (httpserver live suite executed under race)
Security Contracts run 30012223686 SUCCESS (004 migration + session SQL suite executed)
```

## Residual risks

- session issuance is dev-bootstrap only; the Apple code exchange, nonce
  replay store and account provisioning remain unimplemented;
- no TLS termination, rate limiting or request logging policy yet;
- the dev stack still logs into PostgreSQL as a superuser (SET ROLE semantics
  proven; NOSUPERUSER production login remains deployment evidence);
- no session rotation/refresh; revocation exists but nothing calls it yet.

## Immediate next task

```txt
Apply / Memory persistence boundary: concrete Preview read + Apply
confirmation repositories over runtime roles, wired into the executable
server — Apple exchange stays deferred until real credentials exist.
```
