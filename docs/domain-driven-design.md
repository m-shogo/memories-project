# Domain-driven Design for Memory OS

## 目的

このドキュメントは、Domain-driven Design（DDD）を Memory OS にどう適用するかを説明する。

DDD は「コードをきれいにする技術」ではなく、**複雑な業務・思想・ルールを、言葉と境界で整理して、実装が迷子にならないようにする設計法**である。

Memory OS は、AIチャットアプリではなく、人生文脈を扱うOSである。

だから、最初に「何を何と呼ぶか」「どこまでを同じ責務にするか」「何を混ぜてはいけないか」を決める必要がある。

## DDDを一言で言うと

```txt
開発者の都合ではなく、サービスの本質に合わせてコードを分ける考え方。
```

例えば、Memory OSでは以下を混ぜてはいけない。

- RawRecord: 元データ
- NormalizedRecord: 検索しやすく整形したデータ
- Memory: ユーザーの記憶単位
- Interpretation: 後からの意味づけ
- Evidence: 根拠
- SourceRef: 出典

これらを全部 `Memo` や `Message` で実装すると、あとで必ず壊れる。

## Ubiquitous Language

DDDでは、チーム全体で同じ言葉を使う。

Memory OS の共通語彙:

| Term | Meaning | 混ぜてはいけないもの |
|---|---|---|
| SourceRef | どこから来たか | Memory本文 |
| RawRecord | 元データ | AI要約 |
| NormalizedRecord | 検索用整形 | 解釈 |
| Memory | ユーザーの記憶単位 | 人格診断 |
| Interpretation | 後からの意味づけ | 事実そのもの |
| Evidence | 根拠 | 推測 |
| PolicyDecision | 使ってよいかの判定 | 人生価値評価 |
| Tombstone | 削除済みマーカー | raw本文 |
| ExportJob | 持ち出し処理 | Backupそのもの |

## Bounded Contexts

Bounded Context は「ここではこの言葉はこの意味」という境界である。

Memory OS では、最低でも以下に分ける。

```txt
Capture Context
Import Context
Memory Context
Policy Context
Search Context
Export Context
Deletion Context
Storage Context
AI Context
UX Context
```

### Capture Context

ユーザーが小さな記録を残す領域。

責務:

- manual text
- share text
- occurredAt/importedAt
- source label
- raw preference

禁止:

- importance score required
- personality analysis
- AI summary forced

### Import Context

外部データを受け取る領域。

責務:

- detect
- inspect
- estimate cost
- user scope
- extract
- normalize

禁止:

- unknown full analysis
- LLM before inspect
- raw default storage for risky sources

### Memory Context

記憶として扱う中心領域。

責務:

- Memory creation
- Evidence link
- SourceRef link
- visibility
- lifecycle

禁止:

- AIが人生価値を決める
- 他人の秘密を記憶本文化する

### Policy Context

使ってよいかを判定する領域。

責務:

- allow / deny / summary_only / masked_only
- action-based decision
- risk class handling

禁止:

- 重要度判定
- 人格診断

### Search Context

探す領域。

責務:

- relevance ranking
- safe snippet
- result explanation

禁止:

- life ranking
- person ranking
- surveillance search

### Export Context

持ち出す領域。

責務:

- manifest
- redaction
- safe JSONL / Markdown
- short-lived package

禁止:

- raw leak package
- company dump
- third-party raw bundle

### Deletion Context

消す・隠す・封印する領域。

責務:

- hide
- seal
- delete
- raw-only delete
- tombstone
- backup restore replay

禁止:

- deleted resurrection
- guilt deletion UX

## Aggregates

Aggregate は「一緒に整合性を守る単位」である。

### ImportJob Aggregate

Root: `ImportJob`

Contains/links:

- AdapterMetadata
- ImportInspection
- ImportScope
- CostEstimate
- SourceRefs
- RawRecords

Invariant:

- extract before inspect is forbidden
- source unknown cannot full extract
- every extracted record has SourceRefDraft

### Memory Aggregate

Root: `Memory`

Contains/links:

- Evidence
- SourceRef references
- lifecycle
- surfaceVisibility
- privacy

Invariant:

- Memory without SourceRef is invalid
- deleted Memory cannot be searched/exported/LLM-sent
- Interpretation is not fact

### ExportJob Aggregate

Root: `ExportJob`

Contains/links:

- manifest
- redactions
- package status
- audit events

Invariant:

- export must run policy per entity
- export package expires
- raw default off

### Deletion Aggregate

Root: `DeletionTombstone` or deletion command

Invariant:

- pending_deletion blocks access immediately
- tombstone contains no raw
- re-import checks tombstone

## Domain Services

Domain Service は、1つのentityだけでは判断できないビジネスルールを置く場所。

Memory OS examples:

```ts
PolicyEvaluator
CostEstimator
SearchRanker
ExportRedactor
TombstoneMatcher
AdapterRegistry
SecretScanner
VisibilityResolver
```

重要:

- PolicyEvaluator は DB や LLM に依存しない。
- SearchRanker は importanceScore を持たない。
- ExportRedactor は raw secret をログに出さない。

## Domain Events

Domain Event は「重要な出来事が起きた」記録。

Examples:

```ts
MemoryCreated
MemoryHidden
MemorySealed
MemoryDeleted
RawDeleted
ImportInspected
ImportExtracted
PolicyDenied
ExportCreated
ExportExpired
TombstoneCreated
EmbeddingDisabled
```

Eventは便利だが、raw本文を入れない。

## Anti-corruption Layer

外部サービスの形式を、そのままMemory OSの中心に入れないための層。

Examples:

- ChatGPT export JSON
- LINE txt
- Google Calendar API
- GitHub commits
- Photos metadata

Adapter は Anti-corruption Layer である。

外部データをそのまま Memory として扱わない。

## DDDで防げる事故

| Accident | DDD Boundary |
|---|---|
| AIチャットログを事実扱い | Source/Evidence separation |
| LINE相手発言を自分の記憶に混ぜる | Import/Privacy Context |
| 検索順位が人生重要度になる | Search Context language |
| 削除しても復活 | Deletion Context |
| Exportがraw dumpになる | Export Context |
| 会社情報が個人記憶化 | Policy/Privacy Context |

## Implementation Folder Suggestion

```txt
src/
  domain/
    memory/
    import/
    policy/
    deletion/
    export/
    search/
    cost/
  application/
    useCases/
  infrastructure/
    db/
    objectStorage/
    adapters/
    searchIndex/
  presentation/
    api/
    ui/
```

## MVP Rule

MVPではDDDをやりすぎない。

やること:

- 言葉を分ける
- 型を分ける
- Policyを中心に置く
- Raw/Memory/Interpretationを混ぜない

やりすぎ注意:

- 抽象クラスだらけ
- repository patternの過剰導入
- 小さな機能に巨大な階層

## Acceptance Criteria

DDD適用として最低限OKな状態:

- RawRecord / Memory / Interpretation / Evidence が型として分離されている。
- Import / Policy / Search / Export / Deletion の責務が分かれている。
- PolicyEvaluator がUI/DB/LLMに直接依存しない。
- Adapter が外部形式を中心domainへ直接漏らさない。
- SearchにimportanceScore系フィールドがない。
- Tombstoneがraw本文を持たない。

## 結論

DDDは、Memory OSを「なんでも入るAIメモ」から守るための設計言語である。

言葉と境界を先に決めることで、あとから実装者が便利そうな機能を足しても、思想が崩れにくくなる。
