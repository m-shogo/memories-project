# Memory OS Operability Admission Authorities

This runbook explains the **admission layer** for P0 operability evidence. Admission authorities do not manufacture runtime proof, approvals, environments, production traffic, credentials, or `READY` status. They only decide whether externally produced evidence is strong enough to enter a canonical append-only registry.

## Core rule

`foundation implemented` is not `evidence admitted`, and `evidence admitted` is not `Production READY`.

Every admission writer must fail closed when its prerequisite authority is absent. Do not bypass an empty prerequisite registry by copying a digest, branch name, CI result, screenshot, environment label, or local fixture into an admission record.

## Canonical admission map

| P0 | Admission authority | Current evidence source | What it must never manufacture |
|---|---|---|---|
| OPS-P0-001 migration | `migration-production-shaped-admission-contract.v1.json` | canonical append-only migration rehearsal evidence | environment generation, approved release pair, generation-bound restore, mixed-version proof |
| OPS-P0-002 incident | `incident-human-tabletop-evidence-contract.v1.json` | human-led tabletop completion records | human attendance, production recovery, paging configuration |
| OPS-P0-002 incident contacts | `incident-contact-routing-admission-contract.v1.json` | configured contact ownership layered on an admitted observability stack | phone/email data, provider ownership, successful delivery |
| OPS-P0-003/004 observability | `observability-stack-deployment-contract.v1.json` | integrated logs + metrics + access audit + paging deployment | backend deployment, retention deletion, access review, paging delivery |
| OPS-P0-005 rate limiting | `rate-limit-distributed-runtime-admission-contract.v1.json` | distributed shared-store/trusted-proxy runtime evidence | shared state, runtime expiry, restart continuity |
| OPS-P0-006 deletion host failure | `deletion-worker-host-failure-contract.v1.json` | physical host/node failure evidence | host loss from process/container kill evidence |
| OPS-P0-007 backup/restore | `backup-restore-generation-binding-contract.v1.json` | generation-bound backup and restore evidence | production-equivalent generation, PITR, RPO/RTO |
| OPS-P0-008 client baseline | `client-baseline-registry-contract.v1.json` | exact reviewed client artifact bytes | client/server skew support or production release compatibility |
| OPS-P0-009 failure drills | `production-shaped-failure-drill-contract.v1.json` | generation-bound production-shaped failure drills | production proof from local outage/process/container/candidate results |

`operability-admission-inventory.v1.json` is the deterministic snapshot of which foundations exist and how many records have actually been admitted.

## Registration order

Use the dependency order rather than registering the most visible artifact first:

1. Establish immutable source artifacts and exact commit bindings.
2. Register a production-equivalent environment generation when the environment really exists and passes its own admission requirements.
3. Register reviewed release/client/parser baselines only when their own approval and artifact requirements pass.
4. Produce the runtime/rehearsal/drill evidence in that exact generation.
5. Obtain the independent reviews required by the target admission contract.
6. Run the target admission writer using an input record outside the repository working tree.
7. Run the target registry validator and canonical operability validators.
8. Commit only privacy-safe append-only evidence and authority changes.

A later step must not be used to infer an earlier one.

## Production-equivalent versus production

Production-equivalent records must bind to a registered immutable environment generation. They use synthetic data, no production traffic, and do not become production evidence.

Where an admission writer supports a production evidence class, it requires an explicit confirmation phrase and the record must explicitly classify itself as production evidence. Even then, that individual admission must keep application-level `productionReady=false`; only the canonical integrated production gate may decide overall readiness.

## Privacy boundary

Admission records must use repository-relative evidence references, digests, and operational pseudonyms. Do not commit:

- credentials or tokens;
- raw database/object-store/backend URLs;
- phone numbers or email addresses;
- user/account/session/job/object identifiers;
- imported user content;
- unreviewed infrastructure identities where the contract requires a digest.

Failure diagnostics are troubleshooting evidence only and must never be listed as canonical proof in a P0 `evidenceRefs` array.

## Anti-drift validators

The following cross-cutting checks exist specifically because authority drift has already caused real classification bugs:

- `validate-memory-os-operability-evidence-ownership.py` prevents high-impact evidence from being attached to the wrong P0 area.
- `validate-memory-os-operability-status-hygiene.py` rejects duplicate P0 authority entries, broken evidence references, and failure diagnostics used as proof.
- `validate-memory-os-admission-authority-linkage.py` rejects admission contracts whose source contracts, registries, writers, validators, workflows, runbooks, or ledger directories no longer exist.
- `validate-memory-os-operability-admission-inventory.py` checks the deterministic cross-P0 admission inventory against canonical status and registries.

## Current boundary

Production remains `NO_GO`. Empty admission registries are intentional: an implemented admission path is useful because it makes the missing evidence precise, but it is not a substitute for actually provisioning the environment, executing the drill, completing human exercises, configuring routing, or obtaining independent review.
