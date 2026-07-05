# Threat Model

## 目的

Threat Model は、Memory OS に対して誰が、どこから、何を壊せるかを体系的に整理する。

Red Team Worst Cases は悪用シナリオ集であり、Threat Model は攻撃面・資産・攻撃者・対策を構造化するための設計である。

Memory OS は人生文脈・第三者情報・未成年情報・故人情報・会社情報・raw記録を扱うため、一般的なWebアプリより高い慎重さが必要である。

## Assets

守る対象:

```ts
type ThreatAsset =
  | 'raw_memory_text'
  | 'source_ref'
  | 'evidence'
  | 'normalized_record'
  | 'memory'
  | 'interpretation'
  | 'export_package'
  | 'backup_snapshot'
  | 'embedding_vector'
  | 'policy_decision'
  | 'deletion_tombstone'
  | 'auth_session'
  | 'admin_access'
  | 'audit_log';
```

## Trust Boundaries

```txt
User device
-> API boundary
-> Application use cases
-> Domain policy
-> Relational DB
-> Object storage
-> Search/vector index
-> LLM vendor
-> Export download
-> Backup/local archive
-> Admin console
```

危険な境界:

- upload/import boundary
- LLM boundary
- export boundary
- admin boundary
- vector search boundary
- backup restore boundary

## Threat Actors

```ts
type ThreatActor =
  | 'external_attacker'
  | 'malicious_user'
  | 'curious_admin'
  | 'compromised_admin'
  | 'compromised_user_session'
  | 'third_party_vendor'
  | 'cost_attacker'
  | 'well_meaning_user_misuse'
  | 'future_developer_mistake';
```

## STRIDE Overview

STRIDE categories:

| Category | Meaning | Memory OS example |
|---|---|---|
| Spoofing | なりすまし | ownerになりすます |
| Tampering | 改ざん | SourceRefやtombstoneを書き換える |
| Repudiation | 否認 | Exportしたのに記録がない |
| Information Disclosure | 情報漏洩 | raw DMがExportされる |
| Denial of Service | サービス妨害 | huge ZIPでコスト攻撃 |
| Elevation of Privilege | 権限昇格 | support_adminがrawを読む |

## Threats by Boundary

## 1. Import Boundary

Threats:

- huge archive upload
- path traversal zip
- secret/API key import
- company data import
- third-party private import
- prompt injection text import

Mitigations:

- archive safe extraction
- size/file count limits
- secret scan
- inspect before analyze
- unknown inspect-only
- policy before storage/LLM/embedding

P0 tests:

- path traversal rejected
- `.env` excluded
- unknown full analysis blocked
- secret not logged

## 2. LLM Boundary

Threats:

- policy-denied raw sent to LLM
- prompt injection overrides system rules
- third-party secret sent unmasked
- corporate data sent to vendor
- sealed/deleted memory sent

Mitigations:

- PolicyDecision send_to_llm required
- redaction before LLM
- imported content treated as untrusted
- cost gate
- no sealed/deleted/pending records

P0 tests:

- corporate raw LLM deny
- sealed LLM deny
- prompt injection fixture cannot override policy

## 3. Export Boundary

Threats:

- raw DM export
- secrets in export
- hidden/sealed/deleted export
- export URL long-lived
- redaction report missing

Mitigations:

- policy per entity
- redaction log
- raw default off
- short-lived URL
- export audit

P0 tests:

- third-party raw export deny
- secret export deny
- expired export cannot download

## 4. Search / Vector Boundary

Threats:

- deleted memory appears
- hidden/sealed memory appears
- secret searchable
- third-party raw snippet appears
- vector returns unsafe record

Mitigations:

- lifecycle filter before scoring
- policy show_in_search
- safe snippets only
- embedding lifecycle
- no secret embedding

P0 tests:

- deleted/hidden/sealed excluded
- secret not searchable
- vector disabled on delete/seal

## 5. Deletion / Backup Boundary

Threats:

- backup restore resurrects deleted memory
- re-import restores tombstoned content
- tombstone contains raw
- raw delete leaves object behind

Mitigations:

- pending_deletion immediate block
- tombstone by contentHash/externalId
- backup restore replay
- object delete async but access blocked

P0 tests:

- tombstone skip re-import
- backup replay before index rebuild
- tombstone no raw

## 6. Admin Boundary

Threats:

- support reads raw
- admin exports user data
- break-glass abuse
- logs expose content to admins

Mitigations:

- metadata-only admin default
- break-glass reason/scope/expiry/audit
- no raw logs
- user notification policy

P0 tests:

- support_admin raw deny
- break-glass required
- admin is not owner

## 7. Cost Boundary

Threats:

- free full-history analysis
- repeated re-import
- huge export generation
- embedding all data

Mitigations:

- cost estimate
- medium+ confirmation
- plan limits
- hard stops
- contentHash dedupe
- no full history default

P0 tests:

- huge archive partial
- repeated re-import guarded
- unknown full analysis blocked

## Threat Register

| ID | Threat | Severity | Mitigation |
|---|---|---|---|
| T-001 | Secret stored/searchable | Critical | secret scan, policy deny, tests |
| T-002 | Third-party raw export | Critical | export policy, redaction |
| T-003 | Deleted resurrection | Critical | tombstone, backup replay |
| T-004 | Corporate data LLM send | Critical | policy hard deny |
| T-005 | Admin raw browsing | Critical | metadata-only, break-glass |
| T-006 | Prompt injection import | High | untrusted content wrapper |
| T-007 | Hidden vector result | High | embedding lifecycle |
| T-008 | Cost attack | High | limits, estimate, dedupe |
| T-009 | Minor data proactive tip | Critical | policy deny |
| T-010 | Deceased simulation | High | policy deny |

## Abuse vs Attack

Memory OS must handle both:

- Attack: someone breaks system security.
- Abuse: allowed features are used for harmful purposes.

Example:

- SQL injection is attack.
- Partner surveillance export is abuse.

Both need design controls.

## Review Cadence

Threat Model must be reviewed when:

- adding new adapter
- adding LLM feature
- adding Export mode
- adding sharing/family features
- changing storage
- changing admin tools
- changing backup restore

## Acceptance Criteria

- assets listed
- trust boundaries listed
- STRIDE categories considered
- P0 threats mapped to mitigations/tests
- admin/export/LLM/import/search/deletion boundaries covered
- abuse cases included, not only attacks

## 結論

Threat Modeling は、Memory OS を壊す人だけでなく、便利な機能を危険に使う人も想定する設計である。

人生文脈を扱う以上、攻撃と悪用の両方を入口から出口まで見る必要がある。
