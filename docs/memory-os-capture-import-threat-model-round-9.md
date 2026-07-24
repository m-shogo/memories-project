# Memory OS Capture / Import Threat Model — Round 9

最終更新: 2026-07-16

## Status

```txt
threat model:
defined

controls implemented:
no

security evidence:
no

production:
NO-GO
```

本書は、Capture / Import全経路に対するattack surfaceとabuse caseを固定する。

---

# 1. Attacker classes

## A1 External unauthenticated attacker

目的:

- API abuse
- pairing session推測
- storage exhaustion
- parser exploit
- service disruption

## A2 Authenticated malicious user

目的:

- 他userのjob / preview / file取得
- quota回避
- malicious archive投入
- infrastructure resource消費
- illegal / harmful file hosting

## A3 Compromised browser session

原因候補:

- shared PC
- browser extension
- XSS
- token in history / logs
- shoulder surfing

目的:

- pairing token窃取
- filename / preview leak
- unauthorized upload / mapping change

## A4 Malicious or compromised host app / File Provider

目的:

- forged UTType / MIME
- huge payload
- unstable file reference
- path / filename tricks
- unexpected data representation

## A5 Compromised parser dependency or adapter

目的:

- arbitrary code execution
- cross-job data access
- network exfiltration
- candidate manipulation

## A6 Insider / overprivileged operator

目的・事故:

- raw archive閲覧
- production DB query
- excessive audit retention
- export misuse

## A7 Supply-chain attacker

対象:

- Swift package
- Go module
- npm package
- container base image
- CI secret
- release artifact

## A8 Lost / stolen iPhone

目的:

- local DB / staged file閲覧
- active session利用
- app switcher / notification漏洩

## A9 Race / crash / retry adversary

意図的または偶発的に:

- duplicate Apply
- stale Preview confirmation
- deletion後write
- orphan file残留
- revision rollback

---

# 2. Security properties

```txt
CONFIDENTIALITY
他user・browser・operator・analyticsへMemory contentを漏らさない

INTEGRITY
Previewした候補だけを、同じversion / hashでApplyする

AVAILABILITY
悪意あるfileでAPI、worker、storage、他user jobを停止させない

AUTHENTICITY
account、device、pairing session、upload、job、previewの主体を検証する

DELETION
削除後にqueue、backup、cache、workerから復活させない

PORTABILITY
Exportは安全で再取込可能だが、無制限なdata exposureにしない

TRANSPARENCY
何を受け取り、何を拒否し、何を保存したかをuserが確認できる
```

---

# 3. P0 threat scenarios

以下はProduction authorization前にnegative evidenceが必要。

## T-001 Cross-user Import Job read

Attack:

```txt
user Aがuser BのimportJobIdをAPIへ送る
→ status / filename / count / previewを取得
```

Impact: Critical confidentiality breach

Required controls:

- principal-derived user ID
- object-level authorization
- composite tenant query
- RLS defense in depth
- random ID is not sufficient

Required test:

- authenticated A cannot read / cancel / confirm B job

## T-002 Cross-user Preview page read

Attack:

Previewのpaged endpointやrejected-row reportだけownership checkが抜ける。

Impact: Critical; raw personal data exposure

Controls:

- every child resource inherits tenant fence
- preview page query includes user / account epoch
- no object-storage direct public URL

## T-003 Pairing token brute force / guessing

Controls:

- >=128-bit entropy
- short TTL
- rate limit
- attempt budget
- no sequential code alone as authority
- QR session revocation

## T-004 Pairing token leakage through URL / logs

Attack sources:

- access logs
- Referer
- browser history
- analytics
- support screenshot

Controls:

- bootstrap token exchange
- no third-party scripts
- no-referrer
- log redaction
- memory-only browser token
- short expiry

## T-005 Pairing browser confirms final Apply

Impact: compromised shared PC writes thousands of records

Control:

- P0 browser token cannot Apply
- final confirmation requires authenticated iOS session
- optional step-up authentication for high-risk imports

## T-006 Signed upload URL writes arbitrary object

Controls:

- server-generated exact key
- quarantine prefix
- method / content-length / checksum / expiry restriction
- object metadata bound to job and account epoch
- completion verification

## T-007 Signed URL reused after cancellation / deletion

Controls:

- job state checked at completion
- deletion epoch checked
- cancelled object cleanup
- consumed upload authorization marker

## T-008 ZIP Slip / path traversal

Payload examples:

```txt
../../database
/absolute/path
C:\\target
%2e%2e/path
Unicode slash variant
```

Controls:

- canonical normalization
- root containment check
- encoded / Unicode variants
- reject absolute / drive / UNC paths

## T-009 Symlink / hardlink archive escape

Controls:

- links and special entries rejected
- no link following
- job-specific extraction root

## T-010 ZIP bomb / decompression DoS

Controls:

- compressed / expanded limits
- ratio / nesting / entry limits
- streaming accounting
- CPU / memory / wall-time quotas
- per-user concurrent job quota

## T-011 Parser remote code execution

Controls:

- isolated worker
- non-root
- read-only root FS
- no network
- no host mounts
- resource limits
- patched parser libraries
- fuzzing
- scanner interface

## T-012 Parser exfiltration through outbound network

Control:

- outbound deny by default
- storage access scoped to one job object
- no cloud metadata access
- adapter cannot dynamically download code

## T-013 Parser reads another job temporary directory

Controls:

- per-job container or strong process isolation
- unique temp root
- filesystem permission separation
- cleanup
- scoped credentials

## T-014 Preview / Apply TOCTOU

Attack:

- source object replaced
- adapter updated
- mapping changed
- candidate set regenerated

Controls:

- source hash
- adapter / parser version
- options hash
- candidate-set hash
- immutable materialized Preview
- exact preview hash on Apply

## T-015 Duplicate Apply via retry

Controls:

- idempotency key
- request hash binding
- DB unique constraint
- logical apply journal
- same key + different body rejected

## T-016 Partial bulk Apply presented as success

Controls:

- logical atomicity
- staging tables or transaction / resumable commit protocol
- final status only after all chunks verified
- rollback / compensation evidence

## T-017 Account deletion while parser is running

Controls:

- account deletion epoch
- worker checks before parse output and before Apply
- lease invalidation
- object / Preview cleanup
- stale worker write rejected

## T-018 Backup restores deleted account data

Controls:

- deletion tombstone / erase ledger
- restore runbook reapplies deletion
- backup retention contract
- no silent resurrection

## T-019 URL enrichment SSRF

Targets:

- localhost
- RFC1918 / private IPv6
- link-local
- cloud metadata
- internal admin endpoint
- redirect to blocked host
- DNS rebinding

Controls:

- isolated fetcher
- IP classification before connect and after redirect
- redirect cap
- DNS rebinding defense
- response limits
- no credential forwarding

## T-020 Preview XSS

Payload locations:

- filename
- CSV cell
- JSON string
- warning
- adapter label
- source title

Controls:

- text-only rendering
- framework escaping
- no `dangerouslySetInnerHTML`
- strict CSP
- no raw Markdown / HTML P0

## T-021 CSV formula injection in downloaded report

Controls:

- neutralize `=`, `+`, `-`, `@` and control-prefix cases
- clear warning
- never execute spreadsheet formula server-side

## T-022 Local App Group token leakage

Controls:

- no token in UserDefaults
- Keychain access group
- minimal entitlements
- staged row contains opaque reference only

## T-023 App / extension SQLite corruption

Controls:

- synchronized access
- writer responsibility split
- main-app-only migration
- extension schema compatibility check
- transaction / WAL tests
- kill / crash recovery fixture

## T-024 Sensitive content in logs / crash reports

Controls:

- structured safe fields only
- centralized scrubber
- query / fragment removal
- error wrapper avoids raw parser line
- crash SDK network inspection

## T-025 Sensitive content in notifications / app switcher

Controls:

- generic notification copy
- privacy screen / scenePhase handling
- no title / filename / person name
- user-configurable preview policy

## T-026 Malicious image decode

Controls:

- pixel and dimension limit
- bounded decode
- re-encode thumbnail
- metadata stripping / precise-location gate
- image library updates and fuzz corpus

## T-027 Object storage bucket enumeration / public access

Controls:

- block public access
- opaque generated keys
- no list permission to clients
- short signed reads only when needed
- tenant authorization before read issuance

## T-028 Import Portal third-party script exfiltration

Controls:

- zero third-party analytics P0
- dependency review
- CSP / SRI if external resource unavoidable
- self-host core assets

## T-029 Malicious adapter version change

Controls:

- versioned adapter artifact
- reviewed release
- fixture hashes
- Preview invalidation after version change
- rollback plan

## T-030 Supply-chain dependency compromise

Controls:

- lockfiles
- provenance / SBOM
- vulnerability scanning
- minimal dependencies
- package review
- release artifact signing / traceability

## T-031 False Memory Injection

Asset: the account holder's own record of their life.
Failure mode: a record that nobody lived is stored as firsthand, by a
compromised adapter, a malicious import file, or a bug that mislabels origin.
Trust boundary: adapter output → Preview → Apply.
Preventive: every item carries a source reference to an object version whose
checksum was verified before parsing (INV-MEM-002); origin is assigned by the
pipeline, never taken from parsed content.
Detective: the artifact chain is re-walkable — item → preview → object version
→ checksum — so an item with no reachable artifact is detectable.
Deletion: injected items are owned rows and are erased by the account sweep.
Testability: SQL-testable once origin is stored; today only the checksum half
is proven, by the existing spool verifier and upload binding tests.

## T-032 Provenance Stripping

Asset: the link between content and where it came from.
Failure mode: content survives an update or migration while its source
reference does not, after which nothing can say whether a person wrote it.
Trust boundary: any write path that touches a stored item.
Preventive: source reference is NOT NULL and no operation may drop it while
keeping content (INV-MEM-002).
Detective: an item whose source reference does not resolve is an integrity
failure, checkable in SQL.
Deletion: unaffected.
Testability: go-testable. The update_safe_fields policy that repointed
source_preview_id is now closed fail-closed at the service and repository
layers (services/import-api/internal/pgrepo/apply.go, GAP-MEM-005), so no
shipped path repoints the reference. Restoring the reference on a genuine
correction requires append-only supersession, which is future work.

## T-033 Interpretation Promotion

Asset: the distinction between what a person said and what a model guessed.
Failure mode: an AI summary or inference is stored under an assertion kind that
speaks for the account holder, and later reads as their own words.
Trust boundary: any future generation surface writing into memory storage.
Preventive: origins ai_summary, ai_inferred and derived have
canBecomeUserFact=false and cannot take a person-authored assertion kind
(INV-MEM-001, cases MEMCASE-002/003/011).
Detective: an item whose origin is AI and whose assertion is record is a
constraint violation, not a judgement call.
Deletion: AI outputs are derivatives and are erased with the account
(INV-MEM-010).
Testability: contract-only today — nothing stores AI output yet (finding F7),
which is why the boundary is cheap to place now.

## T-034 Identity Misbinding

Asset: whose life a record belongs to.
Failure mode: another person's record attaches to this account, or an inferred
identity hardens into a stored fact.
Trust boundary: tenant isolation, and any future relation or grouping table.
Preventive: relations may only link items of one owner (INV-MEM-012), enforced
by the same FORCE RLS predicates as every existing table; secondhand origin
cannot become the account holder's record (INV-MEM-001).
Detective: cross-tenant links are structurally unwritable rather than merely
audited.
Deletion: relations are owned rows, swept with the account.
Testability: SQL-testable by the same pattern as the existing RLS suite.

## T-035 Silent Rewrite

Asset: what the person believed at the time they believed it.
Failure mode: a later record replaces an earlier one in place, leaving no trace
that the earlier view existed.
Trust boundary: the Apply write path.
Preventive: corrections and reinterpretations are new items linked to what they
supersede; records are not supersedable (INV-MEM-003, MEMCASE-007/008).
Detective: absent — an in-place overwrite leaves nothing to detect, which is
what makes this class serious.
Deletion: unaffected.
Testability: go-testable, and proven: the in-place overwrite is removed and
update_safe_fields is refused fail-closed (INV-MEM-003 closedBy), covered by a
unit test, a repository test and a live HTTP test that snapshots every row and
shows none change. The non-destructive correction path that replaces it —
append-only supersession — remains gated to the future migration plan.

## T-036 Context Collapse

Asset: the separateness of events that merely resemble each other.
Failure mode: display-level grouping becomes storage-level identity, and the
evidence for the grouping can no longer be re-examined.
Trust boundary: any future event-grouping or dedupe surface.
Preventive: grouping is a view over artifacts and never replaces them; each
retains its own artifact, canonical record, retrieval path, timestamps and
hashes (INV-MEM-006).
Detective: if the underlying artifacts survive, a wrong grouping is reversible;
if they do not, it is not.
Deletion: unaffected.
Testability: requires the unbuilt domain. Note the existing fingerprint already
merges on a hash of title, date, url and text — a deliberate narrow rule, but
one that will need re-examining before it drives grouping.

## T-037 Duplicate Amplification

Asset: the difference between corroboration and repetition.
Failure mode: copies sharing one origin — a re-import, a repost, a quote, the
same photo on two devices — are counted as independent evidence.
Trust boundary: any confidence or ranking computation.
Preventive: evidence counts distinct origins, not artifacts (INV-MEM-005,
MEMCASE-015/016).
Detective: comparing artifact count against distinct-origin count exposes it.
Deletion: unaffected.
Testability: contract-only. **The current contract gets this wrong**:
TrustScore.evidenceCount and the "repeated appearance" trust rule both count
copies (GAP-MEM-002, GAP-MEM-003).

## T-038 Unauthorized Resurfacing

Asset: the right not to be shown something right now.
Failure mode: a memory deliberately set aside is pushed back into view by a
feature that only checked whether it existed.
Trust boundary: search, reflection, anniversary notification, Town display.
Preventive: storage is not consent to search, analyse, resurface or display;
these are separate permissions (INV-MEM-007), and a single boolean is refused
(MEMCASE-017).
Detective: each resurfacing surface must name which permission it checked.
Deletion: presentation preferences are owned rows, swept with the account.
Testability: requires the unbuilt domain. The permission set is deliberately
not fixed yet.

## T-039 Persona Reconstruction

Asset: the distinction between a person and a collection of records about them.
Failure mode: a high-fidelity imitation is offered, or received, as the person
— the account holder, a deceased person, a family member, a partner.
Trust boundary: any generation surface that speaks about a person.
Preventive: statements about a person are attributed to the record that carries
them and phrased as what the record says, never as what the person would say
(INV-MEM-009, MEMCASE-018); restates INV-P0-018.
Detective: output without a citable source record is a policy failure.
Deletion: unaffected.
Testability: requires the unbuilt domain.

## T-040 AI Output Laundering

Asset: the traceability of model output back to a model.
Failure mode: an AI summary loses its origin marking through an export, an
import round-trip, or a migration, and re-enters as user-authored text.
Trust boundary: export and re-import — the round trip is where origin is most
easily lost.
Preventive: origin is required and non-removable (INV-MEM-002); AI origins can
never take a person-authored assertion kind (INV-MEM-001).
Detective: an import whose content matches a prior AI output is a signal, not a
proof; the durable control is that export carries origin.
Deletion: unaffected.
Testability: blocked on an export contract, which does not exist yet
(finding F9). Recorded as an open gap rather than a solved threat.

---

# 4. Additional abuse cases

## Identity / authorization

### T-031 Device unlink does not revoke pairing

Expected: all device-issued pairing sessions invalidated.

### T-032 Apple account transfer / relay email change creates duplicate account

Expected: stable Apple subject binding and explicit recovery flow.

### T-033 Support role can read raw Memory

Expected: support role denied by default; break-glass audited and separately approved if ever introduced.

### T-034 Mass assignment changes `userId` / state / object key

Expected: request DTO allowlist; server-set fields ignored or rejected.

### T-035 Cancel endpoint cancels another user job

Expected: same object-level checks as read / confirm.

## Resource abuse

### T-036 Many small files evade total quota

Expected: total bytes, total entries and job count quotas.

### T-037 Many pairing sessions cause DB / notification abuse

Expected: per-account active-session cap and rate limit.

### T-038 Repeated failed parser retries cause cost attack

Expected: retry budget, backoff, terminal classification and user quota.

### T-039 Preview pagination scrapes excessive data

Expected: bounded page size, same-account only, request rate limit.

### T-040 Multipart upload never completed

Expected: abort lifecycle and orphan multipart cleanup.

## Input confusion

### T-041 Double extension

Example: `history.json.exe`.

Expected: allowlist after filename normalization plus content validation.

### T-042 Unicode filename spoofing

Expected: normalized display, bidi control handling, original retained only as untrusted metadata.

### T-043 Duplicate normalized archive paths

Expected: reject case-folding / Unicode normalization collisions.

### T-044 JSON duplicate keys alter semantics by parser

Expected: explicit duplicate-key policy and fixtures across adapter versions.

### T-045 NaN / Infinity / huge exponent numeric confusion

Expected: numeric grammar / precision limits.

### T-046 CSV encoding confusion changes duplicate keys

Expected: encoding detection confidence, user override and options hash.

### T-047 Billion-laughs-like XML inside supported package

Expected: XML disabled unless explicitly required; external entity and DTD disabled.

### T-048 Nested archive hidden with wrong extension

Expected: content sniffing and nesting policy based on bytes, not filename.

## Integrity / lifecycle

### T-049 Preview expires while confirmation is in flight

Expected: transactionally reject or bind accepted request before expiration; deterministic policy.

### T-050 Adapter output order changes candidate hash

Expected: canonical ordering and canonical serialization.

### T-051 Worker finishes after cancellation

Expected: state / epoch fence before output commit.

### T-052 Stale iOS cache confirms superseded Preview

Expected: server authority and superseded-state rejection.

### T-053 Import record exists but attachment promotion failed

Expected: transactional state machine / reconciliation; no broken confirmed reference.

### T-054 Attachment promoted but DB Apply rolled back

Expected: orphan confirmed-object cleanup or staged promotion protocol.

### T-055 Same external record imported through two adapters

Expected: source provenance and duplicate strategy; no silent merge.

## Privacy / operational

### T-056 Raw filename appears in metrics tag

Expected: static metric labels only; opaque IDs excluded or sampled safely.

### T-057 Rejected row report retained indefinitely

Expected: short TTL and independent deletion.

### T-058 Portal browser cache restores private Preview

Expected: no-store headers, clear state, no service worker cache for private responses.

### T-059 CDN caches authenticated Preview

Expected: private/no-store response policy and CDN bypass.

### T-060 Screenshot / screen recording exposes Preview

Expected: user-facing privacy guidance and app switcher protection; iOS cannot guarantee blocking all user-initiated capture, so do not overclaim.

### T-061 Analytics session replay captures Memory content

Expected: session replay prohibited on Capture / Preview / Search surfaces.

### T-062 Third-party AI receives raw archive

Expected: prohibited; explicit minimal post-confirmation processing only.

### T-063 Error response echoes raw input

Expected: safe error codes and bounded redacted details.

### T-064 Operator downloads quarantine object for debugging

Expected: no ordinary operator permission; break-glass if ever allowed, with approval, audit and expiry.

## Mobile / platform

### T-065 Share Extension activation rule too broad

Expected: supported UTTypes and count limits only; no `TRUEPREDICATE` release.

### T-066 Extension uses non-extension-safe framework

Expected: `Require Only App-Extension-Safe API` and build check.

### T-067 Background URLSession identifier collision

Expected: unique identifier per app / extension process.

### T-068 Raw staged file included in device backup

Expected: backup exclusion verification.

### T-069 Keychain item accessibility too broad

Expected: per-secret accessibility class and device / unlock behavior tests.

### T-070 Logout leaves local search / Preview cache

Expected: scoped cache purge and key / session invalidation.

---

# 5. Threat-to-component matrix

| Component | Primary threats |
|---|---|
| Share Extension | forged type, huge payload, App Group race, token / log leak |
| iOS app | stale Preview, local storage, screenshot / notification, duplicate confirmation |
| Desktop Portal | pairing theft, XSS, CSRF, browser cache, third-party script |
| Go API | BOLA, broken auth, mass assignment, resource abuse, SSRF |
| Object Storage | arbitrary key write, public access, orphan objects, cross-tenant read |
| Parser Worker | RCE, sandbox escape, exfiltration, DoS, cross-job read |
| PostgreSQL | tenant leakage, stale state, duplicate Apply, deletion resurrection |
| Adapter | nondeterminism, malicious update, parser confusion, wrong duplicate keys |
| Export | formula injection, overbroad content, unsafe archive, stale deleted records |
| Town Projection | raw content leakage, privacy-field mixing |

---

# 6. Residual risks that cannot be called solved by design

- unknown zero-day in parser / image decoder / OS
- compromised Apple device or browser with full user control
- malicious but valid source data designed to influence user decisions
- insider with infrastructure-level access
- cloud-provider compromise
- dependency compromise before advisory / detection
- user intentionally sharing sensitive file with wrong account
- screenshots or external camera capture
- legal / regulatory requirements varying by region and data category

These require operational controls, monitoring, incident response, external review and ongoing patching. No document eliminates them.

---

# 7. P0 security test priority

```txt
1. cross-user resource matrix
2. pairing token expiry / revoke / replay
3. signed upload key / size / checksum binding
4. archive traversal / links / bombs fuzz suite
5. parser network and filesystem isolation
6. Preview / Apply hash mismatch
7. duplicate Apply idempotency
8. deletion epoch race
9. XSS / CSV injection corpus
10. App Group crash / migration / orphan recovery
11. log / analytics sensitive-data scan
12. backup / local storage / Keychain verification
13. SSRF test corpus
14. supply-chain and secret scanning
15. restore-from-backup deletion test
```
