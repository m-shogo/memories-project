# Memory OS reviewed client baseline registry

This directory documents the operator boundary for registering immutable iOS or Portal client artifacts into `contracts/operations/client-baseline-registry.v1.json`.

An approved client baseline is **not** a production release, a client/server support window, or production evidence. It only says that exact client bytes and their reviewed metadata are eligible to participate in a later skew-pair compatibility review.

## Current state

- approved client baselines: **0**
- approved iOS baseline: **none**
- approved Portal baseline: **none**
- admissible client/server skew pairs: **0**
- Production decision: **NO_GO**

Do not register source code, a branch head, a marketing version, a CI build result, or a digest string without the exact external artifact bytes.

## Required external inputs

Both inputs must live outside the repository working tree:

1. the immutable client artifact bytes (`.ipa`, reviewed exported iOS archive artifact, or reviewed Portal bundle), and
2. one JSON registration record matching `memory-os-client-baseline-record.v1`.

The writer recomputes SHA-256 and byte length from the supplied artifact. A mismatch fails closed before registry mutation.

## Registration record shape

The record must contain at least the fields required by `contracts/operations/client-baseline-registry-contract.v1.json`.

Illustrative shape only — values below are deliberately non-registrable placeholders:

```json
{
  "schemaVersion": "memory-os-client-baseline-record.v1",
  "clientBaselineId": "clb_YYYYMMDD_example",
  "clientClass": "IOS_APP",
  "marketingVersion": "0.0.0",
  "buildNumber": "placeholder",
  "sourceCommitSha": "0000000000000000000000000000000000000000",
  "artifactKind": "IOS_IPA",
  "artifactSha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "artifactByteLength": 1,
  "approvedAt": "1970-01-01T00:00:00Z",
  "approvalClass": "REVIEWED_CLIENT_BASELINE",
  "approvers": [
    {"role": "CLIENT_OWNER", "approverRef": "apr_placeholder01"},
    {"role": "SECURITY_REVIEWER", "approverRef": "apr_placeholder02"},
    {"role": "COMPATIBILITY_REVIEWER", "approverRef": "apr_placeholder03"}
  ],
  "apiMajor": "v1",
  "apiContractSha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "signedUploadContract": "memory-os-signed-upload.v1",
  "clientBehaviorContractSha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "buildProvenanceEvidenceRefs": ["path/to/reviewed/evidence.json"],
  "securityEvidenceRefs": ["path/to/reviewed/evidence.json"],
  "compatibilityEvidenceRefs": ["path/to/reviewed/evidence.json"],
  "artifactRetentionEvidenceRefs": ["path/to/reviewed/evidence.json"],
  "evidenceComplete": true,
  "approvedForPairing": true,
  "productionEvidence": false,
  "productionReady": false
}
```

The placeholder record above is documentation, not authority, and must never be registered.

## Required approval roles

Exactly three distinct operational pseudonyms are required:

- `CLIENT_OWNER`
- `SECURITY_REVIEWER`
- `COMPATIBILITY_REVIEWER`

Self-approval and duplicate identities are rejected.

## Registration

From a clean checkout at the reviewed repository state:

```bash
python scripts/register-memory-os-client-baseline.py \
  --record /absolute/path/outside/repo/client-record.json \
  --artifact /absolute/path/outside/repo/client-artifact.ipa \
  --confirm 'REGISTER REVIEWED CLIENT BASELINE'
```

Then run:

```bash
python scripts/validate-memory-os-client-baseline-registry.py
python scripts/validate-memory-os-client-server-support-window.py
python scripts/validate-memory-os-operability.py
```

The registry change still requires Git review. The writer never creates approvals, evidence, support-window authority or production readiness.

## What registration does not prove

A client baseline does **not** prove:

- old-client/new-server compatibility,
- new-client/old-server compatibility,
- offline retry/resume skew,
- minimum supported client version enforcement,
- rollback-safe previous backend support,
- App Store distribution state,
- production traffic safety,
- Production readiness.

Those claims belong to the client/server skew authority and remain fail-closed until exact approved client/backend pairs are executed and independently reviewed.
