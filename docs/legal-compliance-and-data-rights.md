# Legal Compliance and Data Rights

## 目的

この文書は、Memory OS が長期運用で扱う法務・利用規約・データ権利・地域差・未成年/第三者/故人データの境界を整理する。

これは法的助言ではない。

実装/公開前には、対象地域の弁護士・専門家レビューが必要である。

## なぜ必要か

Memory OS は、単なるメモアプリではない。

扱う可能性があるもの:

- 自分の記録
- 他人との会話
- 家族/恋人/友人/同僚の情報
- 未成年の写真や記録
- 故人に関する記録
- 健康/医療/金融/位置情報
- private bookmark
- 視聴/読書/音楽/嗜好履歴
- AIチャット/ロールプレイ/人格データ
- 外部サービスのExport/APIデータ

このため、Import/保存/分析/Export/削除のそれぞれで権利境界を分ける。

## Data Subject Classes

```ts
type DataSubjectClass =
  | 'self'
  | 'third_party_adult'
  | 'partner_or_family'
  | 'minor'
  | 'deceased_person'
  | 'public_figure'
  | 'employee_or_corporate'
  | 'unknown';
```

## Legal Risk Classes

```ts
type LegalRiskClass =
  | 'personal_data'
  | 'sensitive_personal_data'
  | 'third_party_private_data'
  | 'minor_data'
  | 'health_data'
  | 'financial_data'
  | 'location_data'
  | 'communication_content'
  | 'biometric_or_face_data'
  | 'copyrighted_content'
  | 'corporate_confidential'
  | 'credential_or_secret'
  | 'provider_terms_restricted_data';
```

## Import Rights vs Storage Rights vs Export Rights

These are separate.

```txt
Can user import it?
Can Memory OS store raw?
Can Memory OS summarize it?
Can Memory OS analyze it?
Can Memory OS export it?
Can Memory OS re-import it later?
```

Example:

- LINE snippet can be imported as summary-only.
- raw LINE may not be stored by default.
- relationship intent analysis is denied.
- raw export is denied/default excluded.

## Data Rights Map

### Access / Portability

User should be able to access/export their own eligible records.

But export excludes by default:

- third-party raw
- secrets
- sealed data
- minors
- persona-like high-risk data
- raw media with faces/location

### Deletion

User can delete records.

Deletion creates tombstone when needed to prevent re-import resurrection.

Account deletion needs separate decision:

```ts
type AccountDeletionMode =
  | 'delete_records_keep_nonreversible_tombstones'
  | 'full_erasure_with_no_reimport_guard'
  | 'legal_hold_restricted';
```

This must be product/legal reviewed before production.

### Correction

User can correct:

- title
- date
- source label
- status/progress
- privacy level
- merge decisions

AI interpretations never overwrite source facts.

### Restriction / Seal

User can hide/seal records.

Sealed means:

- excluded from search/tips/export by default.
- LLM denied unless explicit unlock flow exists.

## Regional Strategy

Memory OS should not assume one global legal model.

Need region strategy:

```ts
type DataRegionStrategy =
  | 'single_region_japan_first'
  | 'regional_storage_later'
  | 'global_with_standard_contracts_later';
```

Recommended MVP:

```txt
single_region_japan_first
```

Reason:

- simpler compliance.
- clear user base.
- avoid premature multi-region complexity.

But design must keep:

- user region field.
- storage region field.
- export region metadata.
- provider terms by region.

## Provider Terms Compliance

Every Source Adapter must document:

- official API/export path.
- whether scraping is forbidden.
- redistribution limits.
- AI/ML usage limits if any.
- caching limits.
- attribution requirements for catalog data.

No-Go:

- login scraping.
- bypassing access controls.
- storing copyrighted raw content when not allowed.
- presenting provider data as Memory OS-owned truth.

## Copyright / Licensed Content

Examples:

- manga pages
- full recipes
- song lyrics
- video thumbnails/cover art
- book scans

Default:

- metadata/reference/URL only.
- user memo allowed.
- raw content denied or metadata-only.

## Third-party Requests

Potential future issue:

- someone asks to remove their information from another user's memory.

Need future process:

- accept report.
- verify scope without exposing user's private data.
- restrict/share-deny raw third-party content where appropriate.
- no broad surveillance of user data.

## Legal Hold

Rare but must model.

```ts
type LegalHoldState = 'none' | 'restricted_hold' | 'released';
```

Rules:

- legal hold must not be a normal admin action.
- raw access still restricted.
- user-facing deletion/export behavior must be documented.
- legal review required.

## Children / Minors

Default:

- minor data restricted.
- proactive tips denied.
- export excluded by default.
- face/location/minor media high risk.

Need production decision:

- whether minors can create accounts.
- guardian consent handling.
- age gate.
- family sharing boundaries.

## Deceased / Legacy

Default:

- memory records allowed.
- deceased simulation denied.
- export as clone/persona denied.
- values reference summary allowed under policy.

Need production decision:

- legacy contact?
- account handoff?
- memorial mode?
- death verification?

Do not implement before legal/product review.

## Privacy Notice Requirements

Privacy notice must explain:

- what is imported.
- what is raw vs summary.
- what is sent to LLM.
- what is embedded.
- retention periods.
- export defaults.
- deletion/tombstone behavior.
- admin/support access limits.
- third-party/provider data handling.
- model/provider usage.

## P0 Tests

1. secret/credential import denied.
2. third-party raw export denied/default excluded.
3. minor photo export denied/default excluded.
4. copyrighted manga page raw denied.
5. account deletion mode must be selected before production.
6. provider adapter cannot ship without terms review placeholder.
7. scraping route marked No-Go.
8. sealed data excluded from standard export.
9. correction does not overwrite source fact.
10. regional storage metadata exists.

## 結論

Memory OS は、ユーザー本人の記憶だけでなく、第三者・未成年・故人・著作物・外部サービス規約をまたぐ。

そのため、Import/Storage/Analysis/Export/Re-import/Deleteを同じ許可で扱わない。

MVPでは日本/単一地域から始め、地域・法務・権利の拡張余地を持たせる。
