# RFC-0007: Privacy Architecture

## Status

`accepted_with_limits`

## Summary

Privacy Architecture は、Memory OS がユーザー本人の人生文脈を守りながら、第三者・家族・未成年・故人・会社情報の境界を壊さないための仕様である。

このRFCは `docs/privacy-architecture.md` を採用仕様として扱う。

Memory OS は本人の記憶を作るサービスであり、本人を分析するサービスではない。

また、本人の人生には必ず他人が登場する。だからこそ、**他人の秘密をユーザーの記憶価値にしない**ことを実装で保証する。

## Motivation

Memory OS が扱う記録には以下が混ざる。

- LINE/DMの相手発言
- 家族・恋人・友人の事情
- 子どもや未成年の情報
- 故人・死別に関する記録
- 会社・顧客・同僚情報
- 写真の顔・位置情報
- AIチャット内の他人情報

本人の文脈として扱えるものと、他人をデータ化してしまうものを分ける必要がある。

## Non-goals

- 第三者の性格診断
- 家族/恋人/子どもの人格プロファイル
- 故人再現
- 会社情報検索
- 監視/証拠探し
- 完全な法務自動判定
- 公開SNSの人物分析

## Constitution Check

| Question | Answer |
|---|---|
| ChatGPT代替にならないか | Yes. privacy境界は会話機能ではない。 |
| Character.AI化しないか | Yes. roleplay/persona profileを抑止。 |
| 本人・家族・故人を演じないか | Yes. deceased/family simulation deny。 |
| 人格診断にならないか | Yes. third-party/person profiling禁止。 |
| 人生ランキングにならないか | Yes. privacy分類は価値評価ではない。 |
| 保存時に分析しすぎないか | Yes. rawよりsafe summary/metadataを優先。 |
| 小さな記録を捨てないか | Yes. shared event summaryは残せる。 |
| 大きなイベントを押し付けないか | Yes. family/griefを勝手に中心化しない。 |
| 出典・日付・検索性を守るか | Yes. privacy状態とSourceRefを併存。 |
| 削除・非表示・Exportを尊重するか | Yes. privacy levelでExport/Tip/LLM制御。 |

## User Value

- 自分の人生文脈を残せる。
- 他人の秘密を巻き込まない。
- 原文なしでも関係性・出来事を残せる。
- 家族/子ども/故人の記録を慎重に扱える。
- 会社情報の事故を防げる。

## Data Model Impact

Use `PrivacyContext` from `schema-v1-1-proposal.md`.

```ts
type PrivacyLevel =
  | 'public'
  | 'owner_only'
  | 'owner_sensitive'
  | 'third_party_limited'
  | 'restricted'
  | 'sealed';
```

```ts
type ConsentState =
  | 'not_required'
  | 'user_provided'
  | 'third_party_unknown'
  | 'third_party_opt_in'
  | 'guardian_required'
  | 'not_allowed';
```

Add to:

- RawRecord
- NormalizedRecord
- Memory
- Evidence
- SourceRef when derivable

## Policy Impact

| Action | Default decision | Reason |
|---|---|---|
| import_inspect | allow_with_warning for risky sources | user awareness. |
| extract_raw | restricted for third-party/corporate/minor | minimization. |
| store_raw | no/default for risky data | privacy. |
| create_memory | summary_only for third-party private | relationship context. |
| create_embedding | deny risky raw | search exposure. |
| send_to_llm | masked/summary only for risky | vendor exposure. |
| show_in_search | policy by privacyLevel | safe retrieval. |
| show_raw_quote | deny risky raw | privacy. |
| generate_tip | deny risky default | proactive exposure. |
| share_memory | opt-in or deny | other people. |
| export_memory | summary/exclude | portability vs privacy. |
| delete_memory | allow | user control. |
| admin_access | metadata_only | privacy. |

## Privacy Impact

This RFC defines privacy impact.

Default handling:

| Category | Raw | LLM | Embedding | Export | Tip |
|---|---|---|---|---|---|
| self_low_risk | optional | allow | allow | allow | maybe |
| self_sensitive | no/default | summary | restricted | warning | no/default |
| third_party_private | no/default | masked/summary | summary only | summary/exclude | no |
| minor_data | no/default | minimized | deny/default | exclude/default | no |
| deceased_or_legacy | restricted | summary | restricted | warning | no/default |
| corporate_data | deny/default | deny | deny | deny | no |
| secret_or_credential | deny | deny | deny | deny | no |

## Security Impact

Privacy relies on security controls:

- no raw logs
- admin metadata-only
- redaction
- export expiration
- encryption
- secret scan
- precise location minimization

## Third-party Impact

Allowed:

- shared event summary
- user's feeling
- relationship_context from user's perspective

Forbidden:

- other person's secret
- other person's diagnosis
- other person's weakness
- hidden intent inference
- surveillance/blame evidence

## Minor / Family Impact

Minor data stricter than normal family data.

Rules:

- no child personality profile
- no child weakness analysis
- no precise location default
- no face recognition default
- no tip default
- export exclude default

Family records:

- safe relationship_context allowed
- family diagnosis prohibited
- family share post-MVP only

## Legacy / Deceased Impact

Allowed:

- memory about the person
- values reference with source
- grief-safe summary

Forbidden:

- speak as deceased
- generated letter from deceased
- persona profile
- simulation dataset

## Corporate Data Impact

Allowed:

- user's career transition
- personal work reflection
- public project milestone

Forbidden:

- customer data
- coworker analysis
- company secrets
- private code search
- Slack/Gmail knowledge base

## Cost Impact

Privacy restrictions reduce AI/embedding cost by blocking risky raw processing.

Costs added:

- classification
- redaction
- privacy audit logs

Hard stops:

- corporate raw LLM
- third-party raw export/share
- minor raw tip/share
- secret storage

## UX Impact

Risky source warnings are required.

Examples:

LINE/DM:

```txt
このデータには、あなた以外の人の発言が含まれます。相手の秘密や原文は既定では保存せず、あなたとの関係性や出来事の安全な要約を優先します。
```

Photos:

```txt
写真には顔や位置情報、未成年情報が含まれる場合があります。MVPではメタデータ中心で扱います。
```

## Explainability Impact

User should understand:

- why raw is not stored
- why summary-only
- why export excludes data
- why tip is disabled
- why share is denied

## Deletion / Export Impact

- privacyLevel affects Export redaction.
- minor/corporate/third-party raw exclude default.
- sealed privacy level excludes from normal export.
- raw delete should be easy for sensitive data.

## Failure Modes

- third-party raw stored as user memory.
- partner diagnosis generated.
- minor data tipped.
- company data embedded.
- deceased profile created.
- family share leaks private data.
- public SNS used for personality profiling.

## Abuse Cases

1. LINE相手の秘密を記憶化。
2. 妻の性格診断。
3. 子どもの性格固定。
4. 故人を再現。
5. Slackを会社検索。
6. 友人の弱点検索。
7. 写真位置情報で行動追跡。
8. Gmailから他人の病気情報を保存。
9. Family shareで第三者秘密混入。
10. 公開SNS返信から人物分析。

## Alternatives Considered

### User owns all imported data

却下。会話や写真には他人の人生が含まれる。

### Require explicit consent for all third-party mentions

MVPでは過剰。shared event summaryは扱えるがraw/secretsは抑制。

### Store raw and rely on UI hiding

却下。検索/Export/LLM/管理者リスクが残る。

## Acceptance Criteria

- Every record has or derives PrivacyContext.
- Third-party private raw summary/exclude default.
- Minor data no-tip/export-exclude default.
- Deceased simulation denied.
- Corporate data excluded default.
- Risky source warnings shown.
- Use actions go through Policy Engine.
- Privacy audit logs contain no raw.
- User controls include hide/seal/delete/AI-exclude/export-exclude.

## Rollout Plan

1. PrivacyContext type
2. source-based privacy defaults
3. third-party raw restrictions
4. minor/corporate/deceased hard rules
5. privacy warnings in UI
6. privacy audit logs
7. family share design post-MVP

## Open Questions

- consent model for future family share。
- guardian/child account support。
- public SNS archival boundary。

## Decision

`accepted_with_limits`

制限:

- third-party raw no/default.
- family share post-MVP.
- no persona/diagnosis/surveillance.
