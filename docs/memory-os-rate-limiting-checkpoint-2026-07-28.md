# Memory OS — Rate Limiting Checkpoint (OPS-P0-005)

最終更新: 2026-07-28

## Verdict

```txt
OPS-P0-005 rate limiting: PARTIAL (advanced from NOT_IMPLEMENTED), NOT READY
production decision: NO_GO
```

This builds fail-closed, privacy-preserving rate limiting for the public HTTP
boundary, with the pre-authentication Apple exchange as the primary target. It
does not make OPS-P0-005 READY: the shipped store protects a single instance,
the limits are conservative assumptions rather than load-calibrated numbers,
and there is no trusted-proxy configuration or disable/rollback runbook. An
in-memory limiter is not distributed production enforcement.

## Attack surface and route classification

| Route | Class |
|---|---|
| `POST /v1/auth/apple` | PUBLIC_UNAUTHENTICATED (pre-auth, primary target) |
| `DELETE /v1/account` | PUBLIC_AUTHENTICATED |
| `POST /v1/import-jobs/{jobId}/upload-authorizations` | PUBLIC_AUTHENTICATED |
| `POST /v1/upload-authorizations/{id}/complete` | PUBLIC_AUTHENTICATED |
| `GET /v1/import-jobs/{jobId}/preview` | PUBLIC_AUTHENTICATED |
| `POST /v1/previews/{previewId}/apply` | PUBLIC_AUTHENTICATED |
| unmatched (`other`) | PUBLIC_UNAUTHENTICATED (global-guarded) |
| `GET /healthz` | HEALTH (exempt) |
| `-dev-issue-session` | DEVELOPMENT_ONLY (CLI flag, no HTTP route) |

## Algorithm

Token bucket, chosen over fixed/sliding window and leaky bucket because it
expresses a sustained rate (refill) and a short burst (capacity) directly with
bounded per-key memory, deterministic behaviour and a cheap concurrency-safe
update. A fixed window allows a 2x boundary burst; a sliding approximation costs
more state; a leaky bucket does not model burst as naturally. Elapsed time is
clamped to ≥ 0 (no token minting on a backward clock jump), refill is capped at
capacity, and Retry-After is clamped to [1s, 1h].

## Key derivation and proxy trust

A rate-limit key is never a raw address, token, code or account id. The network
key is an HMAC digest of the normalized client network — IPv4 /32, IPv6 masked
to a /64 so privacy-address rotation within an allocation cannot evade the limit
— keyed by a rotating secret, so the digest is short-lived and not a durable
identifier. The trusted-proxy boundary is explicit: no proxy is trusted by
default and X-Forwarded-For is ignored; only a configured trusted-proxy CIDR set
causes the right-most untrusted forwarded hop to be taken, so an arbitrary
client header cannot spoof a client address. This is not a single-IP limiter: a
whole-route global guard bounds the route even when many sources each stay under
the per-network threshold.

## Store and failure modes

The limiter is behind a `Store` interface. The shipped in-memory store is
single-instance only. Failure modes are per route class, proven with fake
failing stores:

- PUBLIC_UNAUTHENTICATED (Apple): fail closed, with a strict local emergency
  fallback — a distributed-store outage degrades to strict local limiting, never
  an open door;
- PUBLIC_AUTHENTICATED: fail closed;
- HEALTH: exempt, never consults the store, so readiness survives a store outage.

## HTTP rejection

`429` with a stable `SEC_RATE_LIMITED` code, a bounded integer `Retry-After`, a
request ID, and a generic body. The response reveals no policy id, key, network,
address, remaining tokens or which guard tripped. The middleware sits inside
observability and outside routing, so the decision precedes body decode and the
Apple exchange: a live-DB test proves a rate-limited Apple request creates no
account, session, Apple identity or replay row, and a unit test proves the Apple
exchange is never called on a 429.

## Observability and metrics boundary

Rate-limit events (allowed / rejected / store-unavailable / emergency-fallback /
policy-invalid / key-capacity) carry only route template, policy id, outcome,
retryability and request id — never a raw key, address, token or error string.
The future metric cardinality is bounded to policy_id, route_template,
route_class, outcome and failure_class; request id, correlation id, IP, account
id and Apple subject are forbidden labels. No metrics runtime is added here;
OPS-P0-004 stays NOT_IMPLEMENTED.

## Verification actually run

- `scripts/validate-memory-os-rate-limit.py`: PASS (8 policies, 9 negative cases
  rejected). Proven to fail by injecting a failure-mode drift and a clean
  negative case, both reverted.
- Observability, operability and entry-docs validators: PASS.
- `internal/ratelimit` unit and race tests: burst/refill/boundary, cap, backward
  clock, invalid policy, cardinality cap, cleanup, concurrent atomic consume;
  key derivation (trusted proxy, spoofed forwarded, IPv4/IPv6 normalization,
  malformed address, no-raw-address, secret rotation); enforcer failure modes;
  store contract (atomic consume, timeout-not-allow, deterministic consume
  count, expiry).
- `internal/httpserver` tests: 429 with bounded Retry-After and stable code,
  no-internal-detail body, request-id propagation, store-failure fail-closed,
  health never limited, privacy canaries (bearer/code/email/subject/IPv4/IPv6/
  forwarded, raw/URL-encoded/JSON-escaped/base64), and the live-DB no-state-on-429
  proof.
- Full Go module, `-count=1`, plain and `-race`: all packages ok.

## Not done, and why OPS-P0-005 stays PARTIAL

- No production-equivalent distributed (shared atomic) store — the in-memory
  store protects one instance only. The distributed contract is defined and
  fake-tested, not implemented.
- No per-deployment trusted-proxy configuration ownership.
- Limits are conservative assumptions, not load-calibrated from observed
  traffic.
- No operational disable/rollback runbook.

## Status changes

- `contracts/operations/production-operability-status.json`: OPS-P0-005
  `NOT_IMPLEMENTED` → `PARTIAL`, with evidenceRefs and a narrowed
  missingEvidence list. production decision unchanged: `NO_GO`.
- OPS-P0-003 (observability) remains PARTIAL; OPS-P0-004 (metrics) remains
  NOT_IMPLEMENTED. Apple live proof remains an external-credential blocker,
  untouched.

## Transport hardening (audited, already present)

`ReadHeaderTimeout` 5s, `ReadTimeout`/`WriteTimeout` 30s, `IdleTimeout` 60s,
`MaxHeaderBytes` 64KB, per-handler JSON body limits with strict decoding. Rate
limiting complements these; it does not replace them, and DoS defence is not
claimed complete.
