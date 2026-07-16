# Memory OS Round 9 Security Foundation Progress

最終更新: 2026-07-16

## Verdict

```txt
security architecture:
defined

machine-readable contracts:
created through authentication, authorization, RLS, signed upload and parser boundary

re-runnable validators:
created

PostgreSQL migration and integration test SQL:
created

remote GitHub Actions result:
not confirmed by the available connector

Go / iOS / Portal / object-storage implementation:
not created

production:
NO-GO
```

設計・schema・validator・SQL testを作ったことは、本番安全性の証明ではない。

---

# 1. Current security chain

```txt
Sign in with Apple token
→ verified issuer / audience / signature / nonce / code
→ canonical account binding by issuer + subject
→ authenticated account ID + account epoch
→ transaction-local PostgreSQL context
→ FORCE RLS tenant isolation
→ exact-bound signed quarantine upload
→ private quarantine object verification
→ networkless parser sandbox
→ bounded archive / JSON / CSV processing
→ immutable Preview
→ iOS-only final Apply authority in P0
→ idempotent Apply
→ deletion epoch fence
```

各層は前段のclient申告値をそのまま信用しない。

---

# 2. Machine-readable inventory

## Registered schemas

```txt
22 schemas
```

主要schema:

- Import Job
- Pairing Session
- Upload Authorization
- Quarantine Object
- Import Preview
- Apply Confirmation
- Adapter Manifest
- Deletion Fence
- Safe Audit Event
- Object Authorization Matrix / Cases
- PostgreSQL RLS Contract / Cases
- Sign in with Apple Validation Profile / Cases
- Parser Sandbox Profile
- Archive Safety Profile
- Profile Mutation Cases
- Archive Safety Cases

Registry:

```txt
docs/schemas/memory-os-security/schema-registry.v1.json
```

Fixture index:

```txt
docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json
```

---

# 3. Executable contract evidence

## Generic security contracts

```txt
mutation negative cases: 24
schema rejection: 22
semantic rejection: 2
```

Semantic checks:

- reviewed adapter artifact digest equals executed artifact digest;
- deletion fence contains every mandatory cleanup scope.

## Object authorization

```txt
cases: 8
allow: 2
deny: 6
```

Rejects:

- cross-user Import Job read;
- cross-user Preview read;
- stale account epoch Apply;
- browser pairing token final Apply;
- child-resource access without object lookup;
- owner-unscoped list query.

## PostgreSQL tenant RLS

```txt
tables: 9
policy profiles: 9
logic cases: 14
allow: 4
deny: 10
```

Tables:

- `import_job`
- `pairing_session`
- `upload_authorization`
- `quarantine_object`
- `import_preview`
- `apply_confirmation`
- `import_report`
- `export_job`
- `deletion_fence`

Contract decisions:

- `ENABLE ROW LEVEL SECURITY`;
- `FORCE ROW LEVEL SECURITY`;
- privilege roles are `NOLOGIN NOINHERIT NOBYPASSRLS`;
- runtime roles do not own user tables;
- account ID and epoch are supplied only through transaction-local server context;
- context missing means deny;
- only deletion runtime may DELETE user-owned security rows;
- Preview, Apply confirmation and Import Report are immutable after insert.

Executable SQL:

```txt
infra/postgresql/security/001_memory_os_import_rls.sql
infra/postgresql/security/test_memory_os_import_rls.sql
```

The live PostgreSQL CI job is defined, but its remote execution result has not been confirmed.

## Sign in with Apple

```txt
cases: 16
allow: 1
deny: 15
```

Validates or rejects:

- exact Apple issuer;
- exact audience allowlist;
- RS256 only;
- unknown `kid` refresh once, then fail closed;
- signature;
- expiration and issued-at window;
- required single-use nonce;
- subject presence;
- authorization-code replay;
- exact client binding;
- redirect URI match when one existed in the original request;
- email-only account linking;
- Apple subject account-binding conflict.

Canonical identity:

```txt
issuer + subject
```

Email and Apple private-relay email are contact metadata, not account identity.

## Signed quarantine upload OpenAPI

```txt
operations: 3
```

- issue authorization;
- complete and verify upload;
- revoke authorization.

Client cannot authoritatively submit:

- owner account ID;
- account epoch;
- object key;
- bucket;
- storage version;
- completion checksum / size / content type.

Authorization is bound to:

- verified owner;
- current account epoch;
- one Import Job;
- server-generated quarantine key;
- exact content length;
- SHA-256;
- declared content type;
- expiry;
- idempotency key.

Completion performs a server-side object-storage metadata lookup before queueing scanning.

```txt
contracts/openapi/memory-os-import-security.v1.openapi.json
```

## Parser sandbox

```txt
unsafe configuration mutations: 16
```

Contract requires:

- non-root;
- no privilege escalation;
- drop all capabilities;
- read-only root filesystem;
- no host path, Docker socket or device mounts;
- one empty tmpfs per attempt with `noexec,nosuid,nodev`;
- no cross-job path visibility;
- no network, DNS, proxy or metadata-service access;
- seccomp and platform mandatory-access-control profile;
- bounded CPU, memory, PID, time, file-descriptor, temp and output usage;
- supervisor-staged read-only input;
- supervisor-collected schema-validated output;
- no private stdout / stderr;
- digest-pinned, signed and provenance-verified artifact;
- no cloud, DB or signing secrets.

## Archive / JSON / CSV safety

```txt
cases: 25
allow: 1
deny: 24
```

P0 archive profile:

```txt
compressed:       256 MiB
expanded:           1 GiB
single entry:      128 MiB
entries:            10,000
compression ratio: 100x
nested depth:       1
```

Rejects:

- `../` traversal;
- backslash traversal;
- Unix absolute path;
- Windows drive path;
- NUL and overlong name;
- symlink / hardlink;
- device and other special files;
- compressed / expanded / per-entry / count / ratio limits;
- excessive nesting;
- Unicode-normalized duplicate paths;
- case-fold collision;
- encrypted and multi-volume archive;
- unknown compression method;
- malformed central directory;
- excessive JSON depth;
- duplicate JSON object keys;
- oversized CSV cells.

---

# 4. Re-run commands

```bash
python -m pip install -r requirements-security-validation.txt
python scripts/validate-memory-os-security.py
python scripts/validate-memory-os-authorization.py
python scripts/validate-memory-os-postgresql-rls.py
python scripts/validate-memory-os-apple-auth.py
python scripts/validate-memory-os-signed-upload-openapi.py
python scripts/validate-memory-os-parser-security.py
```

Live PostgreSQL evidence:

```bash
psql --set=ON_ERROR_STOP=1 \
  --file infra/postgresql/security/001_memory_os_import_rls.sql
psql --set=ON_ERROR_STOP=1 \
  --file infra/postgresql/security/test_memory_os_import_rls.sql
```

GitHub workflow:

```txt
.github/workflows/security-contracts.yml
```

---

# 5. Known limitations

The current repository does not yet prove:

- the remote GitHub Actions jobs pass;
- a real Go API verifies Apple tokens correctly;
- real deployment login roles cannot bypass privilege roles;
- actual S3-compatible signed URLs enforce every signed header;
- real object-storage bucket policy is private and non-listable;
- the parser sandbox runtime matches the contract;
- the selected archive library rejects all crafted corpus cases;
- cancellation and account deletion revoke in-flight signed URLs;
- deletion races and backup restoration cannot resurrect data;
- iOS App Group, Keychain and Data Protection behavior;
- Portal CSP, XSS and browser-token lifecycle;
- dependency and container supply-chain integrity;
- penetration testing or independent review.

---

# 6. Next implementation order

```txt
1. confirm remote security workflow result
2. create Go module and verified-auth context
3. implement transaction-scoped SET LOCAL account ID / epoch + SET ROLE
4. implement signed-upload storage adapter against a local S3-compatible emulator
5. test exact header / key / size / checksum enforcement
6. implement parser supervisor and sandbox runtime manifest
7. build malicious archive / JSON / CSV corpus
8. implement one Generic CSV adapter
9. materialize immutable Preview
10. implement idempotent Apply and deletion epoch fence
```

Do not start Memory Town production implementation before the Capture / Import P0 security blockers are closed.
