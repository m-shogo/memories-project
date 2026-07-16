# Memory OS Round 9 Security S1 / S1.5 Validation Report

最終更新: 2026-07-16

## Scope

### Registered schemas

1. `core.v1.schema.json`
2. `security-issue-code-registry.v1.schema.json`
3. `import-job.v1.schema.json`
4. `pairing-session.v1.schema.json`
5. `upload-authorization.v1.schema.json`
6. `quarantine-object.v1.schema.json`
7. `import-preview.v1.schema.json`
8. `apply-confirmation.v1.schema.json`
9. `adapter-manifest.v1.schema.json`
10. `deletion-fence.v1.schema.json`
11. `safe-audit-event.v1.schema.json`
12. `security-negative-case-set.v1.schema.json`
13. `authorization-matrix.v1.schema.json`
14. `authorization-case-set.v1.schema.json`

### Fixtures and executable cases

- 12 positive contract fixtures
- 24 mutation-based negative cases
- 8 object-authorization cases

## Validation method

```txt
JSON Schema Draft 2020-12
exact repository-path schema registry
offline resolution only
format checking enabled
semantic rule execution
authorization decision execution
deny by default
```

Commands:

```bash
python -m pip install -r requirements-security-validation.txt
python scripts/validate-memory-os-security.py
python scripts/validate-memory-os-authorization.py
```

GitHub Actions workflow:

```txt
.github/workflows/security-contracts.yml
```

The workflow has been created with `contents: read` only. Its remote run result has not yet been confirmed through the connector.

## Result

```txt
registered schemas:
14

positive contract fixtures:
12 / 12 PASS in local generated-repository validation

mutation negative cases:
24

schema negative rejections:
22 / 22

semantic negative rejections:
2 / 2

authorization resources:
9

authorization cases:
8 / 8 matched expected decisions

allow cases:
2

deny cases:
6

network schema resolution:
disabled
```

## Machine-enforced controls

### Ownership and authorization

- client-provided user ID is not authority;
- same resource owner is required;
- same account epoch is required;
- child-resource operations requiring lookup fail when lookup is skipped;
- list operations fail when owner scope is absent;
- browser pairing authority cannot final Apply;
- deny-by-default applies when no matching resource-operation rule exists.

Authorization cases include:

- same-owner Import Job read: allow;
- cross-user Import Job read: deny;
- cross-user Preview read through browser token: deny;
- stale-epoch Apply: deny;
- browser-token Apply: deny;
- missing object lookup: deny;
- unscoped list query: deny;
- same-owner browser Preview summary read: allow.

### Upload and quarantine

- exact server-generated object key required;
- arbitrary key permission forbidden;
- public read forbidden;
- owner, account epoch, job, byte size, checksum and expiry represented;
- raw filename cannot become storage-key authority;
- quarantine TTL required;
- parser network and host filesystem access forbidden by contract.

### Preview and Apply

- Preview hash required;
- Preview immutable;
- source, adapter artifact, options and candidate set hashed;
- Apply confirmation originates from iOS in P0;
- browser token use forbidden for Apply;
- silent Apply-time reparse forbidden;
- idempotency key and request hash represented;
- same key with a different request is forbidden.

### Adapter and deletion

- adapter runtime cannot enable network, scripts, dynamic code or root execution;
- executing adapter digest must equal reviewed digest;
- deletion fence must contain every mandatory cleanup scope;
- old account-epoch writes forbidden;
- restore requires deletion tombstone replay.

### Audit privacy

Audit events cannot contain:

- Memory body or private content;
- raw filename;
- raw URL;
- token;
- email;
- user note.

Resource references use a hash rather than a raw resource identifier.

## Semantic checks now implemented

### Adapter review digest equality

```txt
adapter.artifactDigest
==
adapter.review.reviewedArtifactDigest
```

Mismatch produces:

```txt
SEC_ADAPTER_ARTIFACT_REVIEW_MISMATCH
```

### Deletion scope completeness

Every mandatory scope must be present, including:

```txt
backup_restore_tombstones
```

Missing scope produces:

```txt
SEC_DELETION_FENCE_SCOPE_INCOMPLETE
```

## What this proves

- current security contract documents are structurally valid under the dedicated offline registry;
- tested unsafe mutations are rejected;
- two cross-document semantic invariants are executable;
- current authorization cases produce the intended allow/deny decisions;
- cross-user ID substitution is represented as an explicit deny case;
- the checks can be rerun by repository scripts and have a CI workflow definition.

## What this does not prove

- the GitHub Actions run has succeeded remotely;
- PostgreSQL RLS policies are correctly implemented;
- every future HTTP handler invokes the authorization decision correctly;
- Sign in with Apple tokens are validated correctly;
- signed upload conditions are enforced by real object storage;
- parser runtime isolation exists;
- archive extraction limits exist in code;
- iOS App Group, Keychain and Data Protection behavior is correct;
- Portal CSP, CSRF and XSS protections exist;
- deletion races and backup restores are safe;
- production security.

## Verdict

```txt
Round 9 S1 machine-contract creation:
COMPLETE

Round 9 S1 targeted validation:
PASS

Round 9 S1.5 object-authorization contract:
CREATED AND LOCAL CASE EXECUTION PASS

GitHub Actions workflow:
CREATED, REMOTE RESULT UNCONFIRMED

PostgreSQL / backend enforcement:
NOT IMPLEMENTED

Production:
NO-GO
```

## Next sequence

1. PostgreSQL tenant and RLS machine contract;
2. RLS positive and cross-user negative fixtures;
3. Sign in with Apple server-validation contract;
4. signed-upload OpenAPI boundary;
5. worker sandbox runtime contract;
6. archive limit profile and negative fixtures;
7. backend security vertical slice.
