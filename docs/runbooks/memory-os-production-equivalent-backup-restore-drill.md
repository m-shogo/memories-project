# Memory OS production-equivalent backup/restore drill planning runbook

## Purpose

This runbook governs **planning admission only** for a future production-equivalent, isolated backup/restore drill under `OPS-P0-007`.

It does not execute PostgreSQL backup, PITR, object restore, traffic changes, promotion, failover or any production mutation. A registered request is not execution authority and is not production evidence.

Canonical authority:

- `contracts/operations/backup-restore-drill-request-contract.v1.json`
- `contracts/operations/backup-restore-drill-request-registry.v1.json`
- `contracts/operations/production-equivalent-environment-generation-registry.v1.json`
- `contracts/operations/recovery-objectives-registry.v1.json`
- `contracts/operations/backup-restore-generation-evidence-contract.v1.json`
- `contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json`

## Current boundary

Until the repository contains at least two distinct, unsuperseded registered production-equivalent environment generations and a current approved recovery objective, drill request admission remains blocked.

Do not invent generations, RPO/RTO values, environment identifiers, recovery timestamps, object versions, reviewer approvals or drill evidence merely to make the gate green.

Local PostgreSQL logical restore, local MinIO exact-version restore, coherent local recovery-set and local Apple replay restore are foundation evidence only. They cannot be relabeled as production-equivalent drill authority or production evidence.

## Required roles

A request must bind three distinct repository evidence references representing:

1. **Recovery Owner** — owns recovery-point selection, restoration sequence, stop decision and later promotion recommendation.
2. **Security Review** — reviews tenant isolation, FORCE RLS/NOBYPASSRLS, deletion/non-resurrection, credentials, replay and privacy boundaries.
3. **Operability Review** — reviews backup freshness, monitoring, PITR/WAL continuity, object retention, RPO/RTO/skew measurement and rollback/abort observability.

The three approval references must be distinct. A single review artifact cannot satisfy multiple roles.

## Entry criteria

Before creating a request, verify all of the following from canonical append-only authorities:

- source production-equivalent generation exists and is not superseded;
- restore-target production-equivalent generation exists and is not superseded;
- source and restore-target generation IDs differ;
- source and restore-target environment IDs differ;
- both manifest SHA-256 values match their registered generation exactly;
- a current approved recovery objective exists;
- the request binds that exact current objective ID;
- the drill remains network-isolated from production routing;
- only synthetic or explicitly approved sanitized data is permitted;
- production traffic and production credentials are forbidden;
- destructive down migration is forbidden;
- PostgreSQL PITR and WAL continuity are required;
- restore targets a separate database/environment;
- independent object retention and exact-version restore are required;
- object access uses TLS and restore-only credential separation;
- deletion protection and immutability are required;
- all eight required evidence domains are planned;
- every mandatory stop condition is retained;
- no HIGH or CRITICAL open risk exists.

## Required evidence domains

The planning request must list all eight domains exactly. This is a plan for what a later drill must prove; listing a domain does not count as proof.

1. `postgresqlPitrSelectionAndWalContinuity`
2. `independentObjectRetentionAndExactVersionRestore`
3. `measuredRpoSeconds`
4. `measuredRtoSeconds`
5. `measuredObjectDatabaseSkewSeconds`
6. `databaseObjectRecoveryCoherence`
7. `typedNonResurrectionEightDomainCoverage`
8. `independentSecurityOperabilityAndRecoveryOwnerReview`

The typed non-resurrection domain ultimately requires the eight separate typed domains defined by `backup-restore-non-resurrection-admission-contract.v1.json`. A generic `nonResurrectionVerification: PASS` is never sufficient.

## Stop conditions

Abort planning/execution admission rather than weakening evidence if any required stop condition becomes true. At minimum this includes:

- generation or environment manifest drift;
- recovery objective replacement before execution;
- any need for production traffic or production credentials;
- inability to prove PITR/WAL continuity;
- ambiguity in exact object-version recovery authority;
- inability to bind database/object recovery points coherently;
- deleted-account/session, terminal-session, replay, deletion-lease or idempotency invariant failure;
- tenant isolation, FORCE RLS or NOBYPASSRLS invariant failure;
- measured RPO/RTO/object-database skew exceeding the approved objective;
- incomplete Recovery Owner, Security or Operability review.

Do not convert a stop condition into a warning to keep the drill moving.

## Request preparation

Create the request JSON **outside the repository working tree**. Do not store secrets, credentials, URLs, raw account/session identifiers, IP addresses or mutable aliases such as `latest` in the request.

The request must use schema `memory-os-backup-restore-drill-request.v1` and exactly the fields defined by the contract. Use immutable generation IDs and manifest digests from the canonical generation registry; use the exact current objective ID from the recovery-objectives registry.

Before registration:

```bash
python scripts/validate-memory-os-backup-restore-drill-request.py
```

The canonical validator must already pass in the current repository state.

To register a reviewed request after all prerequisites really exist:

```bash
python scripts/request-memory-os-backup-restore-drill.py --request /absolute/path/outside/repo/request.json
```

The writer requires a clean working tree, external input, an exclusive lock, exact canonical references and all fail-closed admission rules. It atomically appends the request authority and never executes a restore.

Then reconcile and validate:

```bash
python scripts/reconcile-memory-os-backup-restore-drill-request.py
python scripts/validate-memory-os-backup-restore-drill-request.py
python scripts/validate-memory-os-backup-restore-generation-evidence.py
python scripts/validate-memory-os-backup-restore-non-resurrection-admission.py
python scripts/validate-memory-os-operability.py
```

## Historical request versus current executability

The request registry is append-only. A request that was valid when admitted remains historical audit evidence even after its generation is superseded or its recovery objective is replaced.

However, historical validity is **not** execution authority. Immediately before any future execution, the request must be revalidated against current append-only authorities. If either referenced generation has been superseded or the objective is no longer current, `currentExecutableRequestCount` excludes it and a new reviewed request is required.

Never delete or rewrite a stale historical request to make the current count look cleaner.

## Execution boundary

This repository currently defines the planning admission layer only. A request does not authorize a production-equivalent restore runner.

A later execution layer must, at minimum:

- revalidate the request immediately before execution;
- bind exact backup artifact and manifest digests;
- bind exact PostgreSQL recovery-point and object-version recovery-point evidence;
- measure RPO, RTO and database/object skew against the approved objective;
- produce isolated restore evidence without production traffic or credentials;
- bind all typed non-resurrection evidence;
- require independent Recovery Owner, Security and Operability review;
- keep production promotion as a separate explicit human decision.

Until those evidence records exist and pass canonical admission, `OPS-P0-007` remains blocking and `productionDecision` remains `NO_GO`.

## Failure handling

GitHub Actions for this gate must fail closed. On validation failure it records only a bounded privacy-safe diagnostic and must not mutate the request registry, create a request, execute a restore or change production readiness.

Fix the underlying contract/validator/reconciliation defect; do not bypass a red gate by deleting a required check or relabeling local evidence.
