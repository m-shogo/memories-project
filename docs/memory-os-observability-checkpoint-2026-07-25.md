# Memory OS — Observability Foundation Checkpoint (OPS-P0-003)

最終更新: 2026-07-25

## Verdict

```txt
OPS-P0-003 observability: PARTIAL (advanced from MINIMAL), NOT READY
production decision: NO_GO
```

This checkpoint builds the observability *foundation* Round 10 requires. It does
not make OPS-P0-003 READY, and it does not claim to: Round 10 requires a
structured event contract, correlation identifiers, privacy checks, retention
and real alert routing together, and the last two are deployment configuration
that does not exist yet. Structured emission is not alert delivery, and a logger
is not a retention policy.

## What was built

### Structural redaction, not a runtime filter

The privacy guarantee is enforced by the type system, not by scrubbing. In
`services/import-api/internal/obslog`, `Event` is the only shape the logger
emits, and it has no free-form message field, no field that accepts an error
value, and no `map[string]any` escape hatch. There is physically nowhere to put
a bearer token, an Apple credential, raw user content, a SQL parameter or an
unbounded error string. Severity, outcome, component, event code and failure
class are closed enumerations; every string field is length-bounded; an event
with an invalid enum fails closed to a fixed internal-invariant marker rather
than leaking the bad value.

### Request and correlation identifiers

`services/import-api/internal/reqid` never trusts an inbound request ID: a
client value is echoed only when it matches a strict URL-safe charset and
length, otherwise it is replaced with a fresh server-minted opaque ID returned
in `X-Request-Id`. Background work (the deletion sweep) opens its own
correlation boundary per cycle. An account ID or Apple subject is never reused
as a correlation ID — the generators produce opaque random IDs precisely so
nothing identifying is reused.

### HTTP middleware and worker events

The outermost middleware assigns the request ID, recovers panics into a bounded
event plus a fixed 500 (no recovered value, no stack, no request content reaches
the client or the log), and emits one request event per request with method, a
low-cardinality route template, status, duration and a coarse failure class.
Route templates collapse account, job, preview and upload IDs to placeholders
and unknown paths to `other`, so a path cannot inflate cardinality or smuggle
content. The server binary's ad-hoc `fmt.Printf` lifecycle and deletion-runtime
lines are replaced with structured events; the backlog stuck signal stays a
count with no identifier.

### Machine-readable contract and validator

`contracts/operations/observability-event-contract.v1.json` is the single
source of truth, and `scripts/validate-memory-os-observability.py` fails on:
missing required event definitions, forbidden or secret-shaped field names (an
exact-name list plus a substring list, so `refreshTokenDigest` or `userEmail`
is caught unnamed), unbounded fields, duplicate or unknown event codes, invalid
enums, wrong schema version, code drift between the contract and the Go source,
a valid fixture event that would be rejected, a negative case that would pass,
and OPS-P0-003 marked READY without retention and alert routing.

## Error and event taxonomy

Internal event codes (`OBS_*`) are deliberately distinct from the public HTTP
problem codes (`SEC_*`): a client never sees an event code and an operator never
triages on a public code. The failure taxonomy separates authentication,
authorization, invalid request, replay, external Apple, database, object store,
parser, integrity, rate-limited, deletion retry, deletion terminal, internal
invariant and panic.

## Verification actually run

- `scripts/validate-memory-os-observability.py`: PASS (16 event codes, 6 valid
  fixture events, 13 negative cases rejected). Proven to fail by removing a code
  from the contract (drift) and by appending a clean event to the negative set.
- `scripts/validate-memory-os-operability.py` and
  `scripts/validate-memory-os-entry-docs.py`: PASS.
- obslog and reqid unit tests: PASS, including canary redaction, bounded fields,
  concurrent whole-line emission, invalid-enum fail-closed, and hostile
  inbound-ID rejection.
- HTTP capture tests: a request with a secret bearer token and a hostile inbound
  request ID leaks neither into the log and echoes a fresh server ID; a handler
  that panics with a secret-shaped value yields a fixed 500 with the value in
  neither the body nor the log.
- Full Go module, `-count=1`, plain and `-race`: all packages ok. Behaviour is
  otherwise unchanged; a nil logger is a no-op, so every prior test still passes.

## Not done, and why OPS-P0-003 stays PARTIAL

- **Log retention and access policy** is not configured. It is deployment
  configuration, recorded as `retention.policyDefined: false` in the contract.
- **Real alert routing** is not wired. The deletion backlog is emitted as a
  structured event, but nothing carries it to a paging or dashboard system;
  recorded as `alertRouting.routingConfigured: false`.
- Metrics (OPS-P0-004), tracing (OPS-P1-001) and the remaining operability gates
  are out of scope here and untouched.

The one deliberate exception to structured logging is the `-dev-issue-session`
flag in the server binary, which prints a session token to stdout for local
testing. It is flag-gated, never runs the server, and is documented as a dev
affordance; it is not part of the observability path.

## Status changes

- `contracts/operations/production-operability-status.json`: OPS-P0-003
  `MINIMAL` → `PARTIAL`, with `evidenceRefs` naming the contract, fixtures,
  validator and implementation, and `missingEvidence` narrowed to retention and
  alert routing. production decision unchanged: `NO_GO`.
- Repository-wide next work remains Round 10 production-operability P0
  implementation. Apple live proof remains an external-credential blocker,
  untouched by this checkpoint.
