# Memory OS Security Verification Gate — Round 9

最終更新: 2026-07-16

## Verdict language

使用してよい表現:

```txt
security architecture defined
control implemented
specific verification passed
known residual risks documented
```

使用禁止:

```txt
perfectly secure
unhackable
zero risk
fully private by design
E2EE
```

E2EEはkey lifecycle、recovery、multi-device、search、AI processing、export、deletionを含むprotocolとexternal reviewが成立するまでclaimしない。

---

# 1. Gate overview

```txt
S0 threat model
→ S1 machine contracts
→ S2 backend security vertical slice
→ S3 iOS / App Group security slice
→ S4 Portal / pairing security slice
→ S5 import parser isolation and fuzzing
→ S6 deletion / recovery / backup evidence
→ S7 supply-chain / operations evidence
→ S8 independent review
→ production authorization judgment
```

Town implementationはCapture / Import S0〜S6のP0 unresolvedが0になるまでpriorityを上げない。

---

# 2. S0 — Threat model gate

Required:

- [x] assets identified
- [x] attacker classes identified
- [x] trust boundaries identified
- [x] P0 threat scenarios identified
- [x] residual risks documented
- [ ] data-flow diagram reviewed against implementation topology
- [ ] owner assigned per security control
- [ ] threat model review after first working vertical slice

Evidence:

- `memory-os-capture-import-security-architecture-round-9.md`
- `memory-os-capture-import-threat-model-round-9.md`

Pass condition:

```txt
No unknown internet-facing or cross-process component remains outside the data-flow and threat inventory.
```

---

# 3. S1 — Machine contract gate

Required schemas / contracts:

- ImportJob state schema
- PairingSession schema
- UploadAuthorization schema
- QuarantineObject schema
- ImportPreview schema
- ApplyConfirmation schema
- AdapterManifest schema
- DeletionFence schema
- SecurityIssueCode registry
- AuditEvent safe-field schema

Required invariant fixtures:

- resource ownership required
- account epoch required for pending work
- signed upload exact object binding
- Preview hash required
- idempotency key + request hash binding
- cancelled / expired job cannot Apply
- deleted account cannot create new output
- browser token cannot final Apply
- raw archive TTL required
- sensitive audit fields forbidden

Pass condition:

- schema validation PASS
- duplicate IDs zero
- missing reference zero
- positive fixtures PASS
- negative fixtures reject as expected
- no remote schema resolution

---

# 4. S2 — Backend security vertical slice

## 4.1 Authentication tests

- invalid issuer rejected
- invalid audience rejected
- expired token rejected
- bad signature rejected
- reused authorization code rejected
- deleted account session rejected
- unlinked device session rejected where applicable

## 4.2 Object-level authorization matrix

For each endpoint and resource:

```txt
owner read
owner mutate
other user read
other user mutate
unauthenticated read
unauthenticated mutate
expired account epoch
wrong resource state
```

Resources:

- import job
- pairing session
- upload authorization
- quarantine object metadata
- preview
- preview page
- rejected-row report
- confirmation
- export

Pass condition:

```txt
Every cross-user and unauthenticated case is denied without revealing resource existence or private metadata beyond approved error semantics.
```

## 4.3 API abuse tests

- body size enforced before JSON decode
- page size cap
- per-user job rate limit
- per-device pairing rate limit
- per-IP unauthenticated rate limit
- concurrent parser job cap
- upload byte quota
- Preview candidate quota
- timeout and cancellation behavior
- unknown fields policy
- mass assignment corpus

## 4.4 SSRF tests

Block:

- localhost IPv4 / IPv6
- private IPv4 ranges
- link-local
- cloud metadata
- decimal / octal / hex IP representations where resolver accepts them
- DNS name resolving to private IP
- redirect to blocked destination
- DNS rebinding attempt
- oversized response
- endless redirect
- slow response

Pass condition:

- isolated fetcher only
- blocked targets produce safe error
- no internal response body enters logs or Preview

---

# 5. S3 — iOS / App Group security gate

## 5.1 Share Extension

- activation rules only approved UTTypes / counts
- no release `TRUEPREDICATE`
- app-extension-safe API build check
- malformed NSItemProvider representation
- provider returns different type than declared
- provider stalls / fails / cancels
- oversized image / text
- extension terminated after file write before DB commit
- extension terminated after DB commit before completion
- extension invoked while DB migration required

Pass condition:

- no crash
- no corrupt row
- no orphan without recovery state
- no final Memory write
- safe user-visible failure

## 5.2 Shared SQLite / GRDB

- concurrent app / extension writes
- WAL behavior verified
- main-app-only migration
- unsupported schema safe failure
- file / DB atomic recovery journal
- orphan staged file reconciliation
- orphan DB row reconciliation
- low-storage failure
- file protection while device locked

## 5.3 Local storage inspection

Test device backup / filesystem / logs for:

- raw Share text
- filename
- URL query
- Preview rows
- token
- signed URL
- Keychain secret
- staged image metadata

Required:

- raw / temporary intake excluded from backup
- secrets only in Keychain
- logs scrubbed
- privacy-sensitive cache purged on logout / deletion

## 5.4 UI privacy

- app switcher snapshot
- notification previews
- clipboard usage
- keyboard cache on sensitive fields
- screen reader labels without private overexposure
- background / inactive transition

Do not claim screenshot prevention. Verify only controls actually supported.

---

# 6. S4 — Desktop Portal and pairing gate

## 6.1 Token lifecycle

- entropy test
- expiry
- one-use / bounded-use
- revoke from iOS
- account deletion invalidation
- device unlink invalidation
- successful completion invalidation
- replay after terminal state
- wrong account use
- wrong import job use

## 6.2 Browser privacy

Verify:

- no token in persistent localStorage
- no raw file in IndexedDB
- no service-worker cache for private response
- no-store headers
- no private Preview in CDN cache
- no third-party analytics request
- no filename / token in Referer
- history behavior acceptable
- state cleared on expiry / logout / close

## 6.3 Web security

- CSP automated test
- frame-ancestors none
- CSRF tests
- CORS allowlist tests
- XSS corpus in filename / CSV / JSON / warning / adapter label
- DOM clobbering tests
- content-type / nosniff
- dependency audit

Pass condition:

Browser compromise through pairing token alone cannot read unrestricted Memory or final Apply.

---

# 7. S5 — Upload, archive and parser gate

## 7.1 Signed upload

- arbitrary key substitution rejected
- size overflow rejected
- checksum mismatch rejected
- wrong content type rejected
- expired URL rejected
- cancelled job completion rejected
- deleted account completion rejected
- object already consumed rejected
- cross-user metadata mismatch rejected
- public bucket access denied

## 7.2 Archive corpus

Must include:

- normal ZIP
- empty ZIP
- zero-byte entry
- nested ZIP at limit and over limit
- high compression ratio
- too many entries
- oversized single entry
- oversized expanded total
- `../` traversal
- absolute path
- Windows path
- Unicode separator
- symlink
- hardlink
- device / FIFO / socket metadata
- sparse-file candidate
- duplicate normalized path
- case-fold collision
- extreme filename length
- invalid central directory
- truncated archive
- encrypted archive policy case

## 7.3 JSON corpus

- depth at / over limit
- huge string
- huge object key
- huge array
- duplicate keys
- invalid UTF-8
- BOM
- huge number / exponent
- NaN / Infinity syntax
- many tiny objects
- schema recursive references if accepted format includes schemas

## 7.4 CSV corpus

- row / column / cell at and over limits
- multiline field
- malformed quoting
- mixed delimiters
- encoding ambiguity
- formula prefixes
- control characters
- huge first row
- many empty columns

## 7.5 Parser sandbox evidence

Automated runtime checks:

- non-root
- read-only root FS
- no outbound internet
- no metadata endpoint
- no host mount
- no container socket
- temp quota
- CPU quota
- memory quota
- process / FD quota
- wall-time kill
- job-specific storage access only
- another job object read denied

## 7.6 Fuzzing

Targets:

- archive inspector
- path normalization
- JSON streaming parser wrapper
- CSV parser wrapper
- source detector
- generic mapper
- adapter manifest parser
- canonical hash serialization

Required evidence:

- corpus checked into test fixtures where safe
- crash reproducer retained
- fixed crashes become regression cases
- fuzz timeout and resource budget documented

---

# 8. S6 — Preview, Apply, deletion and recovery gate

## 8.1 Preview integrity

Reject:

- source hash changed
- adapter version changed
- parser image changed when relevant
- options changed
- candidate hash changed
- Preview expired
- wrong user
- wrong account epoch
- cancelled / superseded job
- invalid preview hash

## 8.2 Idempotency

- same key + same request returns same result
- same key + different request rejected
- network timeout after commit does not duplicate
- app double tap does not duplicate
- worker retry does not duplicate
- two-device confirmation race produces one result

## 8.3 Crash matrix

Crash / kill at each boundary:

```txt
upload object written
upload completion recorded
scanner started
scanner completed
parser output partial
Preview materialized
Apply chunk N committed
attachment promoted
search index updated
sync outbox written
```

Each case must resolve to one of:

- safe retry
- safe rollback
- explicit repair state
- terminal rejection

Never silent partial confirmed state.

## 8.4 Deletion race

Run deletion concurrently with:

- upload
- scan
- parse
- Preview generation
- user confirmation
- Apply
- attachment promotion
- search indexing
- export generation
- push notification scheduling

Pass condition:

- old epoch work cannot create or resurrect user data
- pending objects / jobs are removed or terminally fenced

## 8.5 Backup restore

Evidence:

- deleted-account tombstone survives / is reapplied after restore
- raw archive retention remains bounded
- restored background jobs cannot write for deleted account
- operational restore runbook tested

---

# 9. S7 — Supply-chain and operations gate

Required CI / release checks:

- Swift dependency resolution locked
- Go module verification
- npm lockfile frozen in CI
- SAST
- secret scan
- dependency vulnerability scan
- container scan
- SBOM artifact
- license inventory
- test fixture private-data scan
- release provenance / artifact traceability
- migration review
- infrastructure policy scan

Required operational controls:

- production / staging separation
- least-privilege service accounts
- secret manager
- key rotation runbook
- incident response runbook
- security contact
- vulnerability intake process
- patch SLA by severity
- backup restore runbook
- deletion failure alert
- quota / cost anomaly alert
- parser crash / timeout anomaly alert

Logging verification:

- automated canary private values never appear in logs, traces, metrics or crash reports
- log retention finite
- production log access audited

---

# 10. S8 — Independent review gate

Before public production handling real archives:

- mobile security review against OWASP MASVS / relevant MASTG tests
- API authorization review against OWASP API Security risks
- file upload / parser review
- external penetration test or independent qualified reviewer
- privacy review
- account deletion and backup review
- threat model update from findings

Critical / High findings:

```txt
open = production blocked
accepted without fix = not allowed for private Memory body exposure or cross-user access
```

Medium findings require owner, deadline and explicit risk record.

---

# 11. Security issue severity

## Critical

- cross-user Memory / raw archive disclosure
- auth bypass
- parser escape to infrastructure
- production key disclosure
- deleted account data resurrection at scale
- final Apply without user authorization

## High

- pairing token grants unrestricted Memory access
- stored XSS on Preview
- SSRF to internal / metadata service
- arbitrary object storage write / read
- repeatable duplicate / corrupt bulk Apply
- private content in third-party analytics

## Medium

- bounded local temporary leak
- missing rate limit with limited impact
- short retention violation without disclosure evidence
- insufficient warning / state transparency

Severity does not depend only on exploit difficulty; data sensitivity and blast radius matter.

---

# 12. Production security definition of done

All required:

```txt
[ ] P0 threat negative tests PASS
[ ] cross-user matrix PASS for every object endpoint
[ ] parser sandbox verified at runtime
[ ] archive / JSON / CSV fuzz baseline PASS
[ ] Preview / Apply integrity tests PASS
[ ] duplicate-safe confirmation PASS
[ ] App Group crash recovery PASS
[ ] local storage / backup / log inspection PASS
[ ] deletion race and restore evidence PASS
[ ] supply-chain CI checks blocking
[ ] incident and key-rotation runbooks reviewed
[ ] independent review Critical / High zero
[ ] privacy disclosure matches actual data flow
[ ] unresolved P0 zero
```

Passing this gate still does not justify a claim of perfection. It justifies a narrowly stated production readiness judgment for the tested version and scope.
