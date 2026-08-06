# Rate-Limit Operation Evidence Ledger

This directory is the append-only repository evidence ledger for rate-limit emergency operations and drills.

## Rules

- One operation ID maps to one JSON file: `<operationId>.json`.
- Existing operation IDs are never overwritten.
- Use `scripts/create-memory-os-rate-limit-operation-evidence.py`; do not hand-edit committed records.
- Records contain operational identifiers and closed enums only. Raw IP addresses, network digests, tokens, account/session/request identifiers, URLs, credentials and request content are forbidden.
- `sourceCommitSha` is always a full 40-character commit SHA.
- Operator and reviewer are separate individual handles; email addresses are not evidence identifiers.
- Emergency duration may not exceed 60 minutes.
- `RESTORED` requires every required verification check to be `PASS` and an explicit `restoredAt`.
- `FAILED` requires at least one open risk.
- Repository evidence records actions; it does not activate a production mode, configure a shared store or change `productionDecision`.

The template under `docs/fixtures/memory-os-operability/` is not evidence and must never be copied into this directory with placeholders intact.
