# Memory OS Observability Access and Retention Runbook

Status: **POLICY DEFINED / PRODUCTION CONFIGURATION NOT PRESENT**

Production decision remains: **NO_GO**.

This runbook governs structured events emitted under `contracts/operations/observability-event-contract.v1.json`. It does not authorize collecting request bodies, raw errors, account identities, Apple subjects, credentials, SQL parameters, object keys or user content.

## Non-negotiable rules

- Structured-event access is denied unless an individual identity is assigned a reviewed role.
- Shared accounts and unlogged administrative access are forbidden.
- Logs are not a backup, source of user memory content or alternate database.
- A production outage does not justify disabling event schema validation, access audit or automatic retention expiry.
- A missing log signal does not prove an operation did not happen; verify canonical state independently.
- Production backend, groups, break-glass and export automation are not currently configured.

## Standard access request

1. Record requester, requested role, environment, purpose and expiry.
2. Confirm the task cannot be completed with dashboards or aggregated metrics alone.
3. Verify the role grants only the required structured fields and time range.
4. Require independent approval for production access.
5. Assign the individual identity through infrastructure-as-code or the approved identity workflow.
6. Verify an access-audit event is emitted before use.
7. Remove access at expiry and record revocation evidence.

## Role boundaries

### on_call_observer

May read recent valid structured events and filter only on bounded contract fields. May not bulk export, change retention or use raw provider administration.

### incident_commander

May read hot and warm structured events and create a reviewed incident snapshot. Break-glass access still requires an independent approver and automatic expiry.

### security_reviewer

May review security, authorization, rate-limit, integrity and deletion events plus access/export audit records. May not approve their own break-glass request.

### observability_platform_admin

May configure sinks, retention and provider integration through reviewed infrastructure changes. Routine event-content access is forbidden.

## Break-glass procedure

1. Open or identify the incident record.
2. State the exact environment, event classes, fields and time range required.
3. Confirm no search for secrets, personal data, raw content or unrestricted identifiers is requested.
4. Obtain independent approval.
5. Grant the minimum role for no more than 60 minutes.
6. Verify every query is written to append-only access audit.
7. Export only through the reviewed export procedure when evidence must leave the backend.
8. Revoke access automatically at expiry.
9. Complete post-access review and record unexpected fields or access paths as an incident.

Break-glass must not be used to bypass normal access for convenience, dashboard development or routine debugging.

## Incident evidence export

1. Bind the export to an incident reference and exact source commit.
2. Select the smallest time range and field set that answers the incident question.
3. Confirm every selected field exists in the structured event contract.
4. Run privacy review before export.
5. Write to an encrypted destination with explicit owner and expiry.
6. Record checksum, creation time, source environment and deletion deadline.
7. Do not export raw provider indexes, unrestricted backend dumps or access credentials.
8. Verify deletion at expiry and preserve only the deletion evidence.

## Retention operation

Required policy tiers:

- all valid structured events: 14 days searchable;
- warn/error plus security, rate-limit, deletion and integrity outcomes: 90 days warm;
- explicitly reviewed incident snapshots: 365 days;
- access audit: 365 days append-only.

Retention changes require exact-source infrastructure changes, independent review and rollback plans. Silent extension and silent reduction are both forbidden.

## Retention expiry verification

1. Select a synthetic event or reviewed test marker with a known expiry.
2. Confirm it is searchable before expiry and absent after the policy window.
3. Confirm warm or incident copies obey their separate tier rather than silently extending hot data.
4. Verify access-audit records remain while the underlying event expires.
5. Record backend policy version, execution time and deletion result without copying event content.
6. Treat expiry failure as a high-severity operational defect.

## Sink health response

When ingestion freshness exceeds five minutes, event rejection increases or access audit stops:

1. Treat absence of telemetry as unknown state, not healthy state.
2. Preserve application safety boundaries; do not disable schema validation to recover ingestion.
3. Check sink credentials, quota, network and schema compatibility without exposing secret values.
4. Use metrics and canonical database/object verification for operational decisions while logs are degraded.
5. Access-audit failure is SEV0 because untracked production access must not continue.
6. Re-establish ingestion and verify ordered, bounded event output before declaring recovery.

## Access review

Every 90 days:

- enumerate individual production identities and assigned roles;
- revoke inactive access older than 30 days unless explicitly justified;
- verify no shared accounts exist;
- confirm break-glass grants expired automatically;
- review exports and deletion evidence;
- confirm provider administrators do not have routine event-content access;
- record reviewer and open remediation items.

## Closure requirements

A log-access, retention or sink-health issue may close only when:

- access and configuration changes are tied to exact source evidence;
- unexpected access is independently reviewed;
- temporary privileges and exports have explicit expiry;
- retention or sink behavior is verified rather than inferred from configuration;
- no secret or user-content field was introduced;
- Production remains `NO_GO` unless all independent P0 gates are deliberately reviewed.

## Current limitations

- No production log backend is configured.
- No production identity groups or access-audit sink are configured.
- Break-glass and export workflows have not been tested.
- Retention tiers and deletion verification are not enforced by a provider.
- No log-derived paging route is configured.
