# Memory OS Migration Operation Evidence

This directory is the append-only ledger for migration preflight, apply,
verification and recovery decisions.

## Scope

A record proves only what its exact source SHA, environment and result fields
state. A record does **not** prove that a recovery point is restorable, that
Production backup/PITR is configured, that mixed-version traffic is safe or
that OPS-P0-001 is READY.

The binding contracts are:

- `contracts/operations/migration-lifecycle-contract.v1.json`
- `contracts/operations/migration-operation-evidence-contract.v1.json`

## Creating a record

1. Start from
   `docs/fixtures/memory-os-operability/migration-operation-record.template.v1.json`.
2. Replace every synthetic value with an opaque, privacy-safe operational
   reference. Never paste a database URL, hostname, credential, SQL text,
   tenant/account identifier or user content.
3. Keep `migrationSequenceBefore` and `migrationSequenceAfter` as canonical
   prefixes of the migration lifecycle registry.
4. Use distinct opaque operator and reviewer IDs.
5. Use an opaque `rpt_...` recovery-point reference. The record does not assert
   that the recovery point is usable unless separate restore evidence exists.
6. Run:

```bash
python scripts/create-memory-os-migration-operation-evidence.py /path/to/record.json
python scripts/validate-memory-os-migration-operation-evidence.py
```

The writer uses exclusive file creation. A second write for the same
`migrationRunId` fails; records are never updated in place.

## Production records

A `PRODUCTION` record additionally requires the exact confirmation phrase from
the contract. This confirmation only authorizes writing the evidence record. It
is not migration approval and is not Production-readiness evidence.

## Corrections

Do not edit or delete an existing record to correct it. Create a new migration
operation or incident record that references the prior opaque run ID and
explains the corrected decision without including sensitive values.
