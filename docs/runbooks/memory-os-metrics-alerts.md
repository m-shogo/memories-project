# Memory OS Metrics Alert Runbook

Status: **DEFINED / ROUTING NOT CONFIGURED**

Production decision remains: **NO_GO**.

These procedures define operator actions for the provider-neutral alert rules in `contracts/operations/metrics-alerting-contract.v1.json`. They do not prove that Prometheus, Alertmanager, paging, on-call ownership or delivery acknowledgements are configured.

## Non-negotiable rules

- Never paste bearer tokens, database URLs, object credentials, raw IP addresses, account IDs, job IDs, filenames or user content into an incident record.
- A dashboard or alert returning to green does not prove data integrity or authorize closing an incident.
- Do not disable authentication, `FORCE RLS`, deletion fencing, exact-version object checks or integrity verification to restore availability.
- Do not silence an alert without an owner, expiry, reason and follow-up issue.
- Security, cross-tenant visibility, deletion resurrection, integrity bypass and accepted-data loss are not error-budget events. Escalate them as incidents immediately.
- Production routing remains unconfigured. Manual observation is not a substitute for paging evidence.

## Common first response

1. Record the exact source commit and alert ID.
2. Confirm metrics freshness and scrape availability before interpreting absence of samples.
3. Check the service overview dashboard specification for concurrent 5xx, latency and saturation movement.
4. Preserve privacy-safe logs and metrics snapshots. Do not preserve request bodies or credentials.
5. Classify whether the issue is application, PostgreSQL, object store, Apple, rate-limit store or deletion worker.
6. Apply only reversible containment described below.
7. Re-run the relevant integrity verification after recovery.

## alert-http-5xx-burst

**Signal:** elevated 5xx ratio over a short window.

Immediate checks:

- Confirm denominator traffic is non-zero and metrics are fresh.
- Break down by bounded `route_class` and `route_template` only.
- Check recovered panic, database failure, object-store failure and rate-limit-store metrics.
- Compare the first failing timestamp with the exact deployed commit and migration sequence.

Containment:

- Pause the newest deployment if rollback remains schema-compatible.
- Use route fail-closed or strict local emergency rate limiting when dependency overload is suspected.
- Do not bypass authorization or integrity checks.

Recovery verification:

- 5xx ratio returns below the provisional threshold for at least the alert hold duration.
- No increase in integrity failures, deletion terminal failures or cross-tenant test failures.
- A representative authenticated Preview read and idempotent Apply check succeeds.

## alert-panic-detected

**Signal:** any recovered HTTP panic.

Immediate checks:

- Treat the panic as a code invariant failure even when the client received a bounded 500.
- Locate the privacy-safe request event by request ID; do not log the recovered value or stack into shared channels.
- Identify route template, commit and deployment instance.

Containment:

- Stop or roll back the implicated release when repeatable.
- Disable only the affected feature path through a reviewed fail-closed mechanism.

Recovery verification:

- Reproduction test is added and fails before the fix.
- Full Go tests and race tests pass on the exact fix commit.
- Panic counter remains flat through the observation window.

## alert-apple-exchange-failure-spike

**Signal:** Apple exchange failure ratio exceeds the provisional threshold.

Immediate checks:

- Separate external Apple failures from invalid requests and replay rejection.
- Verify JWKS freshness, issuer/audience configuration and clock health without exposing credentials.
- Confirm the session issuance ratio did not diverge from successful exchanges.

Containment:

- Preserve fail-closed authentication.
- Do not accept email as identity authority and do not bypass nonce or replay checks.
- Communicate degraded sign-in rather than weakening verification.

Recovery verification:

- Fake-Apple contract tests and current credential/key-rotation checks pass.
- Successful exchange and session issuance accounting agree.
- Replay rejection remains effective.

## alert-rate-limit-store-failing

**Signal:** any shared rate-limit store failure.

Immediate checks:

- Determine which route policy and failure mode are active.
- Verify public routes are fail-closed or using the approved strict local emergency mode.
- Check active-key saturation and proxy trust configuration.

Containment:

- Follow `docs/runbooks/memory-os-rate-limit-operations.md` when present.
- Never switch public routes to unlimited allow.
- Disable trusted-proxy interpretation when deployment ownership is uncertain.

Recovery verification:

- Shared store atomicity and latency checks pass.
- Rejected requests created no account, session, replay, upload, Apply or Memory mutation.
- Emergency mode is removed gradually with recorded approval.

## alert-db-failing

**Signal:** database failures occur above the provisional rule condition.

Immediate checks:

- Break down by bounded operation and failure class.
- Check connection availability, lock pressure, migration activity and runtime-role health.
- Confirm whether failures are read-only, transaction rollback or committed partial effects.

Containment:

- Stop migrations and destructive workers before increasing retry pressure.
- Preserve transaction boundaries and `FORCE RLS`.
- Use forward-fix or application rollback only under the migration recovery policy.

Recovery verification:

- Deployment-role RLS integration checks pass.
- Preview/Apply idempotency and deletion fencing remain correct.
- Database failure metric remains flat through the observation window.

## alert-deletion-backlog-stuck

**Signal:** a positive deletion backlog does not change for the rule window.

Immediate checks:

- Confirm metric freshness and worker liveness.
- Check leased-job ownership, retry count, object-store erasure and database lock pressure.
- Determine the age of the oldest deletion task through privacy-safe operational evidence.

Containment:

- Resume the existing leased worker; do not create a second uncontrolled deletion writer.
- Pause new destructive maintenance that competes for the same resources.
- Never mark deletion complete merely to clear the alert.

Recovery verification:

- Backlog decreases and oldest-task age improves.
- Stored-object erasure and account fencing checks pass.
- No deleted account or expired session becomes visible.

## alert-deletion-terminal-failure

**Signal:** any deletion terminal failure.

Immediate checks:

- Escalate immediately; right-to-erasure work may be incomplete.
- Preserve the append-only deletion evidence and exact failing phase.
- Check whether database rows, object versions, sessions and replay state agree.

Containment:

- Fence the affected account and prevent new writes.
- Do not clear terminal state or retry counters without reviewed remediation.
- Use isolated recovery procedures when state is ambiguous.

Recovery verification:

- Every required deletion phase is independently verified.
- Object erasure and canonical database deletion agree.
- Backup/restore non-resurrection checks are not bypassed.

## Alert closure requirements

An alert may be closed only when:

- the triggering signal and metrics freshness are understood;
- containment and recovery actions are recorded without secrets;
- integrity, authorization and deletion invariants have been rechecked where relevant;
- the alert remains clear for the defined observation window;
- a follow-up owner and deadline exist for any temporary mitigation;
- routing or threshold defects are tracked separately from the underlying incident.

## Current limitations

- No production Prometheus/Alertmanager or equivalent is configured.
- No paging destination, on-call owner, acknowledgement target or escalation timer is configured.
- Ratio thresholds are provisional and not calibrated by production-shaped load.
- The Prometheus rule file has not been validated with a production-pinned `promtool` artifact.
- No alert delivery or response drill has been completed.
