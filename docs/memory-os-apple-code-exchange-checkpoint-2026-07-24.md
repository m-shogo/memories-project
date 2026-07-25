# Memory OS — Sign in with Apple Code Exchange Checkpoint

最終更新: 2026-07-24

## Verdict

```txt
Apple code exchange, provisioning, replay store, login endpoint:
IMPLEMENTED AND LIVE-PROVEN AGAINST A FAKE APPLE OVER HTTP + PostgreSQL

Live proof against real Apple:
BLOCKED ON DEVELOPER CREDENTIALS (the sole remaining Apple gate)

Rich Memory / iOS / Portal / Town:
NOT IMPLEMENTED
production:
NO-GO
```

This closes the implementation of the sole `nextRequired`. Everything that can
be built and proven without Apple developer credentials is done; only the final
live handshake with Apple's real servers remains, and that is left as an
explicit, un-fabricated blocker.

## What was already there

The `appleauth.Verifier` already existed and already orchestrated the whole
flow through four interfaces: `KeyProvider`, `CodeExchanger`, `ReplayGuard`,
`AccountBindingStore`. It enforced algorithm, kid, signature, issuer, audience,
subject, nonce, iat/exp, code binding and unknown-kid single refresh. This
checkpoint did not reimplement any of that; it supplied the four adapters, the
endpoint, and the session issuance, and proved the whole composition live.

No new parallel vocabulary was introduced.

## Migration 010

Two definer-only surfaces, reachable only by `memory_auth_runtime`:

- `apple_identity` — the canonical `(issuer, subject) -> account` binding.
  Account-owned PII, erased with the account; a reverse-unique index on
  `account_id` stops a second identity attaching to one account. Email is never
  a key and never auto-links.
- `apple_replay` — single-use nonce and code digests with a TTL. Not
  account-owned (consumed before an account is resolved), so cleaned by TTL, not
  the account sweep. `consume_apple_replay` claims both digests in one
  statement; either already present rolls back both.

`provision_apple_identity` resolves-or-creates atomically: concurrent first
logins race on the primary key, the loser reads the winner's row, so exactly one
account is created. A returning identity whose account is not `active` is
refused, never revived. `sweep_deleted_account` was extended (CREATE OR REPLACE,
not an edit to migration 006) to erase the identity binding.

## Go composition

- `client_secret.go` — ES256 client-secret JWT from an EC P-256 `.p8`. The key
  is held only as a parsed value; raw bytes are never logged and are zeroed in
  `main.go` after parsing. Signature is fixed-width R||S, not ASN.1.
- `token_client.go` — the `CodeExchanger`. Regenerates the secret per exchange,
  reads sub and aud from the token-endpoint id_token (trusted by TLS channel),
  cross-checks audience. The form body carrying the secret and code never
  appears in a wrapped error.
- `pgstores.go` — `PostgresReplayGuard` and `PostgresAccountBindingStore` call
  the definer functions under `memory_auth_runtime`. The nonce claim is hashed
  before storage; a non-active account surfaces as a binding conflict.
- `login.go` — verifies then issues a session, distinguishing a session
  failure (retryable) from an auth rejection.
- `httpapi/apple_handler.go` — `POST /v1/auth/apple`, mounted ahead of the
  session middleware because it mints the session. Client body carries no
  account id or email. Errors map to one code per category so the failing check
  cannot be probed, and any unclassified failure — including a replay — fails
  closed as a rejection, never a 500.
- `main.go` wires the service only when the four Apple env vars are present, so
  the binary runs unchanged in dev and CI without credentials.

## Secret handling

No raw authorization code, nonce, id_token, access token, refresh token, session
token or private key is ever logged, put in a fixture, or committed. The `.p8`
bytes are read, parsed, and zeroed inside one function. The nonce is stored only
as a sha256 digest.

## Verification actually run

- 11 migrations on a fresh database + 11 SQL suites PASS, including the new
  Apple identity binding suite (first login creates one active account at epoch
  0; returning login resolves the same; a different subject is a different
  account; replayed nonce or code rejected; a deleting account not revived; the
  sweep erases the binding).
- Full Go module, `-count=1`, plain and `-race`: all packages ok, run
  repeatedly.
- Unit tests: client-secret is a verifiable ES256 JWT; token client maps
  rejection, malformed response and audience mismatch; login service issues as a
  full user, propagates rejection, and reports session failure distinctly.
- **Live HTTP journey against a fake Apple + real PostgreSQL**: first login
  creates an account and returns a session that authenticates a real subsequent
  request; returning login resolves the same account; a second subject is a
  distinct account; replayed code rejected; nonce mismatch rejected; Apple
  rejection is a 401 not a 500; malformed token is a 400. A second test proves a
  deleting account is refused with 409, not revived.
- OpenAPI documents the endpoint and its four problem codes; the signed-upload
  validator allowlists exactly this session-minting endpoint and asserts it
  carries no bearer.

## Not proven, and why

`appleCodeExchangeLiveProven` is **false**. The one thing a fake Apple cannot
prove is the real handshake: real Apple key rotation, a real client secret
accepted by Apple's token endpoint, and a real authorization code. That needs
Apple developer credentials, which are not fabricated here.

To run the real proof, set these (locally or as GitHub Actions secrets) — the
names only; the values are the operator's:

```txt
MEMORY_OS_APPLE_TEAM_ID
MEMORY_OS_APPLE_KEY_ID
MEMORY_OS_APPLE_CLIENT_ID
MEMORY_OS_APPLE_PRIVATE_KEY_PATH   (path to the .p8; never commit the file)
```

With those set, `cmd/import-api-server` wires the real Apple login, and a sign-in
from a real device completes the live proof.

## Status changes

- `appleCodeExchangeImplemented`, `appleCodeExchangeSqlTestsPassed`,
  `appleCodeExchangeMockLiveTestsPassed` → true.
- `appleCodeExchangeLiveProven` → false (the blocker above).
- `nextRequired` → `prove_apple_code_exchange_against_real_apple`.
- Corrected a stale flag: `deletionFencingRemoteLiveJobPassed` was false, but
  the deletion-fencing SQL suite runs in Security Contracts and has been green
  remotely; set true.

## Post-open hardening

Because sign-in is now a public, unauthenticated endpoint, two fail-closed
properties were locked with regression tests before real users arrive:

- **Apple linkage is erased on the deployed deletion path.** The
  account-deletion HTTP test now seeds an apple_identity binding, asserts the
  sweep reports `apple_identity=1`, and proves zero bindings remain afterwards.
  The SQL unit test already covered the sweep function; this closes the gap that
  the real HTTP+worker path did not prove a deleted user's Apple identity is
  gone.
- **The unconfigured endpoint opens nothing.** Without credentials, POST
  /v1/auth/apple returns 503 and provisions no identity row — verified once by
  hand against the binary, now a regression test so the credential-free binary
  can never ship a half-built account-creation surface.

The focused audit that accompanied this — body limits, Cache-Control no-store on
the token-returning response, bearer handling, replay ordering, audience
authority — found no reachable destructive or trust-violating path to close on
the Apple surface, unlike the earlier update_safe_fields case.

## Not done

- Rich Memory domain, supersession, iOS, Portal, Town: untouched.
- The real-Apple live proof, gated on credentials.
- production remains NO-GO.
