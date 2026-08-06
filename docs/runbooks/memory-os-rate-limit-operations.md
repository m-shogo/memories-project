# Memory OS Rate-Limit Emergency Operations Runbook

Status: **POLICY DEFINED / PRODUCTION CONTROL PLANE NOT IMPLEMENTED**

Production decision remains: **NO_GO**.

This runbook governs operational changes to the rate-limit boundary. It never authorizes unlimited public traffic, fail-open behavior, authentication bypass or arbitrary forwarded-header trust.

## Non-negotiable rules

- Public routes must remain bounded or fail closed.
- `UNLIMITED_OR_FAIL_OPEN` is forbidden in every environment that handles real traffic.
- Emergency local fallback is permitted only for a route whose machine-readable policy already declares `fail_closed_emergency_local`.
- An unavailable shared store is not evidence that traffic is safe to allow.
- Do not disable authentication, authorization, `FORCE RLS`, exact object checks, metrics or structured events to reduce load.
- Never record raw IP addresses, tokens, account IDs or request content in the operation record.
- Every emergency mode expires automatically after no more than 60 minutes.

## Before changing mode

1. Open or identify the incident record.
2. Record exact source commit, environment and current policy generation.
3. Name operator and independent reviewer.
4. List the exact affected policy IDs and route templates.
5. Verify whether each policy permits emergency local fallback or requires fail closed.
6. Record current shared-store failure, rejection, active-key and request metrics.
7. Set start time and expiry no more than 60 minutes later.
8. Decide whether user-facing degraded-service communication is required.

## NORMAL_CONFIGURED

Use only when the configured store and deployment-owned trusted-proxy boundary are verified.

Required evidence:

- atomic store increment and expiry behavior;
- expected policy generation and route inventory;
- bounded key cardinality;
- trusted proxy ownership or explicit direct-peer mode;
- no unexplained store-failure signal.

## STRICT_LOCAL_EMERGENCY

Use only for an explicitly permitted route and only when a stricter bounded local token bucket is safer than total rejection.

Activation steps:

1. Confirm the route contract uses `fail_closed_emergency_local`.
2. Record local capacity and refill values; they must not exceed the normal policy.
3. Verify local key-memory and cardinality caps.
4. Activate only the named policies.
5. Confirm structured fallback events and metrics are emitted.
6. Observe rejection rate, memory growth and business-state mutation checks.
7. Escalate to `ROUTE_FAIL_CLOSED` if accounting becomes uncertain or expiry is reached.

This mode must not be expanded to routes whose contract requires strict fail closed.

## ROUTE_FAIL_CLOSED

Use when store, policy, proxy, key cardinality or identity state is uncertain.

Activation steps:

1. Identify the smallest affected route set.
2. Preserve health and separately authenticated internal operational access.
3. Reject affected public traffic with the existing bounded public error behavior.
4. Do not reveal store state, keys, network identity or internal reason.
5. Verify rejected requests cause no account, session, replay, upload, Apply or Memory mutation.
6. Record user-impact and recovery criteria.

## TRUSTED_PROXY_DISABLED

Use whenever the deployment-owned proxy boundary cannot be verified.

1. Stop interpreting forwarded client-address headers.
2. Derive the bounded network key from the direct peer only.
3. Record the proxy configuration discrepancy without raw addresses.
4. Keep the stricter behavior until infrastructure ownership is reviewed.
5. Never enable arbitrary `X-Forwarded-For` trust to restore apparent client separation.

## Shared-store recovery

Before returning to `NORMAL_CONFIGURED`:

1. Verify atomic increment, TTL and key isolation behavior.
2. Verify latency and error rate under a bounded canary.
3. Confirm the policy generation equals the exact source commit.
4. Confirm emergency local counters are not silently copied into shared-store keys.
5. Verify trusted-proxy mode separately.
6. Run mutation checks proving rejected requests created no canonical state.
7. Restore one policy or bounded traffic slice at a time.
8. Observe store failures, 429 ratio, 5xx ratio, active keys and memory.
9. Stop and return to the safer mode on any ambiguity.

## Rollback of an operational change

Rollback means returning to the previous **safe** mode, not returning to unlimited traffic.

- From `STRICT_LOCAL_EMERGENCY`, rollback may be `ROUTE_FAIL_CLOSED` when the shared store is still unhealthy.
- From `ROUTE_FAIL_CLOSED`, rollback to normal requires the complete recovery verification.
- From `TRUSTED_PROXY_DISABLED`, re-enable proxy trust only through reviewed deployment configuration.
- If configuration generation is uncertain, remain fail closed.

## Required mutation checks

For representative rejected requests, verify:

- no account row created;
- no bearer session issued;
- no Apple replay or identity binding inserted;
- no upload authorization created or consumed;
- no quarantine object enqueued;
- no Preview Apply confirmation or Memory item created;
- no deletion state marked complete merely to clear pressure.

## Evidence closure

The operation record must include:

- previous and new mode;
- proxy mode;
- affected policy IDs;
- start, expiry and restore times;
- exact source SHA;
- operator and reviewer;
- privacy-safe verification results;
- user-impact decision;
- remaining risk and follow-up owner.

An emergency operation cannot close while temporary mode remains active or its expiry is unverified.

## Current limitations

- No production shared atomic store is implemented.
- No deployment-owned trusted-proxy configuration is registered.
- No production emergency control plane or automatic expiry mechanism exists.
- No append-only operation ledger exists.
- Limits are not calibrated by production-shaped traffic.
- No emergency-mode or recovery drill has been completed.
