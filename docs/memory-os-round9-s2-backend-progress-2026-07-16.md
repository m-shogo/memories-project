# Memory OS Round 9 — S2 Backend Progress

最終更新: 2026-07-16

## Verdict

```txt
Go backend module:                  created
verified Principal boundary:        created
HTTP bearer middleware:             created
RLS-scoped transaction runner:      created
signed upload domain service:       created
strict signed-upload HTTP handler:  created
PostgreSQL upload repository:       created
upload DB migration / tests:        created
Go CI workflow:                     created
remote CI result:                   not confirmed
real Apple JWT verifier:             not implemented
real PostgreSQL driver wiring:       not implemented
real object-storage signer:          not implemented
parser supervisor:                   not implemented
production:                          NO-GO
```

## Implemented files

```txt
backend/go.mod
backend/cmd/api/main.go
backend/internal/security/principal.go
backend/internal/security/principal_test.go
backend/internal/httpauth/middleware.go
backend/internal/httpauth/middleware_test.go
backend/internal/dbscope/scope.go
backend/internal/dbscope/scope_test.go
backend/internal/upload/service.go
backend/internal/upload/service_test.go
backend/internal/httpapi/upload_handler.go
backend/internal/httpapi/upload_handler_test.go
backend/internal/postgres/upload_repository.go
infra/postgresql/security/002_memory_os_upload_authorization.sql
infra/postgresql/security/test_memory_os_upload_authorization.sql
.github/workflows/backend-go.yml
```

## Security properties now represented in code

### Identity

- only `security.Principal` may enter tenant-scoped services;
- zero / unverified principals are rejected before DB access;
- HTTP middleware resolves account from verified provider issuer + subject;
- client-provided account ID headers or JSON fields are not authority;
- missing or invalid bearer tokens return a generic unauthorized response.

### PostgreSQL scope

- every scoped transaction receives a verified Principal;
- account ID and epoch are installed with transaction-local `set_config`;
- runtime role is selected from compile-time constants only;
- handler failure rolls back;
- unknown role and unverified principal are rejected before transaction start.

### Signed upload

- request cannot choose owner, epoch, object key or bucket;
- Import Job lookup receives the verified Principal;
- authorization is bound to owner / epoch / job / generated key / size / SHA-256 / content type / expiry;
- raw display filename is never used as storage key authority;
- a pending authorization row is created before signing;
- signing or activation failure transitions the pending record to a safe failed state;
- cross-owner or unavailable jobs return a generic unavailable result;
- maximum P0 upload size is 256 MiB.

### HTTP boundary

- signed-upload endpoint body is limited to 16 KiB;
- unknown JSON fields are rejected;
- additional trailing JSON values are rejected;
- job ID comes from the route, not the request body;
- unavailable and cross-owner jobs share the same 404 response;
- responses containing signed URLs use `Cache-Control: no-store`;
- the API process currently exposes only `/healthz`; Import routes remain unregistered until dependencies are wired.

### Database persistence

- upload authorization references Import Job with a composite tenant FK:
  `(job_id, owner_account_id, account_epoch)`;
- object keys are unique;
- size, checksum, key format and state are DB constrained;
- worker role cannot issue upload authorizations;
- API / worker cannot delete authorization records;
- cleanup remains a deletion-runtime responsibility.

## Tests created

```txt
verified Principal:
- valid construction
- invalid account / epoch / subject
- zero-value rejection

DB scope:
- set_config before business query
- fixed SET LOCAL ROLE
- commit on success
- rollback on handler failure
- no DB access for unverified principal or unknown role

HTTP authentication:
- verified issuer + subject account resolution
- client account header ignored
- missing bearer rejected
- verifier failure rejected

Signed upload service:
- verified principal propagation to repositories
- server-generated key
- raw filename not used in key
- pending -> issued state
- signing failure -> failed state
- cross-owner job rejection
- 256 MiB limit

HTTP signed upload:
- authenticated successful response
- no-store response
- unknown identity field rejection
- generic 404 for unavailable job
- unauthenticated rejection

PostgreSQL:
- same-tenant authorization insert
- cross-tenant job FK rejection
- oversized length rejection
- invalid checksum rejection
- duplicate key rejection
- worker issuance rejection
```

## Important limitation

The execution environment could not resolve `github.com`, so a local repository clone and `go test ./...` could not be executed here. GitHub workflows were created, but the available connector did not return a remote workflow result. Do not claim Go tests or live PostgreSQL tests passed remotely until run evidence is obtained.

## Next implementation sequence

1. confirm Backend Go and Security Contracts workflows;
2. add a real PostgreSQL driver and process bootstrap without embedding credentials;
3. implement Sign in with Apple JWT/JWKS verifier and code replay store;
4. implement account binding repository for issuer + subject;
5. implement private S3-compatible signer and object HEAD verifier;
6. implement upload completion / atomic consume / scan queue transition;
7. implement parser supervisor runtime;
8. add Generic CSV adapter and immutable Preview;
9. implement idempotent Apply and deletion epoch cancellation.
