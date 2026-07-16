# Memory OS Current Authority Order — Round 9 S2 Backend

最終更新: 2026-07-16

## Current verdict

```txt
product priority:
Capture / Import first

security contract foundation:
created through authentication, RLS, signed upload and parser boundary

Go backend foundation:
partially implemented

implemented code path:
verified Principal
→ bearer middleware
→ strict signed-upload handler
→ upload service
→ RLS-scoped PostgreSQL repository

real provider / infrastructure wiring:
not implemented

remote CI evidence:
not confirmed by available connector

production:
NO-GO
```

## Authority order

矛盾時は上を優先する。

1. `memory-os-current-authority-order-round-9-s2-backend.md`
2. `memory-os-round9-s2-backend-progress-2026-07-16.md`
3. `memory-os-current-authority-order-round-9-security.md`
4. `memory-os-round9-security-foundation-progress-2026-07-16.md`
5. `memory-os-capture-import-security-architecture-round-9.md`
6. `memory-os-capture-import-threat-model-round-9.md`
7. `memory-os-security-verification-gate-round-9.md`
8. active security schemas, fixtures, validators, OpenAPI and PostgreSQL migrations
9. Round 8 Capture / Import and iOS architecture contracts
10. prior privacy, persistence, deletion and Memory Town contracts

## Binding stack

```txt
iOS canonical client:
Swift 6 + SwiftUI + Share Extension + GRDB

Backend:
Go API + PostgreSQL FORCE RLS

Bulk file storage:
private S3-compatible quarantine

Parser:
isolated supervisor / worker

Desktop support:
limited import-only Portal

Town later:
SpriteKit after Capture / Import P0 blockers close
```

## Implemented backend boundary

### Verified identity

- `security.Principal` is opaque and cannot be assembled from request fields;
- zero / unverified Principal is rejected before DB access;
- account binding input is verified provider `issuer + subject`;
- HTTP bearer middleware ignores client account ID fields.

### Tenant transaction

- transaction-local account ID and epoch;
- runtime role allowlist only;
- rollback on all failure paths;
- no handler execution before tenant context and role setup.

### Upload issuance

- client cannot choose owner, epoch, object key or bucket;
- owned Import Job lookup receives verified Principal;
- pending authorization is persisted before signer execution;
- activation and failure states are explicit;
- unavailable and cross-owner jobs are indistinguishable;
- signed response is no-store.

### PostgreSQL

- upload authorization has composite tenant FK to Import Job;
- object key is unique;
- content length, SHA-256, object-key format and states are constrained;
- RLS remains the second authorization boundary;
- only deletion runtime may delete security-domain rows.

## Not implemented

- real Apple JWT / JWKS signature verification;
- authorization-code exchange and replay persistence;
- actual account binding tables;
- PostgreSQL driver and application bootstrap;
- actual object-storage signer and HEAD verification;
- upload completion atomic consume;
- scan queue;
- parser supervisor runtime;
- Generic CSV parser;
- immutable Preview generation;
- idempotent Apply;
- deletion race implementation;
- iOS and Portal clients.

## Hard stops

Do not expose Import endpoints or authorize production if any is true:

- unverified identity can construct Principal;
- request owner / epoch can reach SQL scope;
- DB query executes before `SET LOCAL` context and role;
- runtime role is not allowlisted;
- cross-owner job receives a distinguishable error;
- client controls object key or bucket;
- signed URL can exist without a tracked pending authorization;
- upload completion trusts client metadata;
- DB lacks composite tenant FK or FORCE RLS;
- actual tests are failing or remote evidence is unavailable at release judgment;
- unresolved P0 > 0;
- independent Critical / High findings remain.

## Next sequence

1. obtain Go and PostgreSQL CI evidence;
2. add PostgreSQL driver bootstrap and environment validation;
3. implement Apple verifier and replay store;
4. implement issuer + subject account binding;
5. implement S3-compatible signer and HEAD verifier;
6. implement completion / consume / scan transition;
7. implement parser supervisor runtime;
8. add Generic CSV → immutable Preview;
9. implement idempotent Apply;
10. implement deletion epoch cancellation and restore tests.

Memory Town implementation remains behind Capture / Import P0 security evidence.
