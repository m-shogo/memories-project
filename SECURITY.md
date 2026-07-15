# Security

最終更新: 2026-07-16

Memory OSは、ユーザーの人生の文脈、画像、URL、視聴・読書・食事・旅行・人間関係などの高感度になり得る情報を扱う。

## Current status

```txt
security architecture:
defined at contract level

threat model:
defined

verification gate:
defined

implementation and security evidence:
not created

production readiness:
NO-GO
```

このrepositoryは現在、設計段階である。「完璧に安全」「hack不可能」「完全なprivacy」をclaimしない。

## Read first

1. [Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)
2. [Capture / Import Security Architecture](docs/memory-os-capture-import-security-architecture-round-9.md)
3. [Capture / Import Threat Model](docs/memory-os-capture-import-threat-model-round-9.md)
4. [Security Verification Gate](docs/memory-os-security-verification-gate-round-9.md)
5. [Capture / Import Implementation Architecture](docs/memory-os-capture-import-implementation-architecture-round-8.md)
6. [Privacy and Ethics](docs/privacy-and-ethics.md)
7. [Persistence, RLS and Recovery](docs/memory-town-persistence-rls-and-recovery-contract.md)

## Security priorities

```txt
1. prevent cross-user disclosure
2. prevent unauthorized / silent Memory writes
3. isolate untrusted imports and parsers
4. bind Preview to exact Apply content
5. keep raw files short-lived
6. prevent retry / deletion resurrection
7. keep private content out of logs, analytics and notifications
8. preserve export and deletion rights
```

## Binding implementation boundaries

- iOS Share Extension receives only minimal quick-capture input.
- iOS Files and the limited Desktop Import Portal upload to the same canonical Go import pipeline.
- Raw archives are stored only in private quarantine storage.
- Parser workers run outside the public API process with restricted filesystem, network and resources.
- Browser pairing tokens cannot final-apply confirmed Memory records in P0.
- Every import job, Preview, upload object, report and confirmation requires object-level authorization.
- Preview and Apply are bound by source, adapter, options and candidate hashes.
- App Group data is minimized; secrets remain in Keychain.
- Account deletion fences jobs, workers, objects, caches, exports and restored backups.

## Production blockers

Production is blocked until all required evidence in the Security Verification Gate passes, including:

- cross-user authorization matrix
- signed upload binding tests
- archive / JSON / CSV negative and fuzz tests
- parser sandbox runtime evidence
- Preview / Apply integrity and idempotency
- App Group crash recovery and local storage inspection
- pairing Portal XSS / CSRF / privacy tests
- deletion race and backup restore tests
- supply-chain CI gates
- independent review with zero unresolved Critical / High findings
- zero unresolved P0 security findings

## Vulnerability reporting

A private vulnerability-reporting channel has not yet been published because the product is not in public production.

Before public beta, this repository must define and publish:

- private security contact
- supported versions
- acknowledgement target
- severity / remediation targets
- disclosure coordination policy

Do not place private user data, credentials, tokens or live exploit payloads in a public GitHub issue.
