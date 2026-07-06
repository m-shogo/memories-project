# Human Data Interaction for Memory OS

## 目的

Human Data Interaction（HDI）は、人が自分に関するデータを理解し、操作し、必要に応じて交渉できるようにする考え方である。

Memory OS はユーザーの人生文脈を扱うため、データをただ保存するだけでは足りない。

ユーザーが「何が保存されているか」「どこから来たか」「AIが何を推測したか」「何を消せるか」「何をExportできるか」を理解できる必要がある。

## HDI を一言で言うと

```txt
自分のデータを、見える・分かる・動かせる・拒否できるようにする設計。
```

## Core HDI Concepts for Memory OS

```ts
type HDIConcept =
  | 'legibility'
  | 'agency'
  | 'negotiability'
  | 'provenance'
  | 'contestability'
  | 'portability'
  | 'reversibility';
```

## 1. Legibility

### 意味

データがユーザーにとって読める・理解できること。

### Memory OS での意味

User can understand:

- what is stored
- source
- date
- rawStored status
- AI summary vs user fact
- privacy level
- lifecycle state
- export eligibility

### UI requirements

Memory detail must show:

- 出典
- 記録日 / 出来事の日
- 原文保存状態
- AI要約かどうか
- 検索/AI/Export対象か

Bad:

```txt
AIが処理済み
```

Good:

```txt
この記録は、2026-07-06に手動入力されたメモに基づいています。原文は保存していません。
```

## 2. Agency

### 意味

ユーザーがデータに対して行動できること。

### Required actions

- edit/correct
- hide
- seal
- delete
- raw delete
- exclude from AI
- exclude from tips
- exclude from export
- export
- show evidence

### Rule

If user can see a memory, user should have control actions nearby.

## 3. Negotiability

### 意味

データの扱いを一度決めたら終わりではなく、後から変更できること。

### Memory OS examples

- raw保存を後でやめる
- AI対象から外す
- Tip対象から外す
- Export対象から外す
- hiddenから戻す
- sealedを解除する
- AI要約を訂正する

### Important

Negotiability does not mean Policy can be bypassed.

User may negotiate within safe boundaries.

Example:

- user can include own low-risk raw in export
- user cannot include third-party secret raw in export

## 4. Provenance

### 意味

データの由来が分かること。

### Memory OS requirements

Every Memory must trace:

```txt
Memory -> Evidence -> SourceRef -> ImportJob -> AdapterMetadata
```

### UI copy

Good:

```txt
出典: 手動メモ / 2026-07-06
```

Bad:

```txt
AIが覚えています
```

## 5. Contestability

### 意味

ユーザーがデータやAI推測に異議を唱えられること。

### Required features

- これは違う
- AI要約を削除
- 出典を確認
- 信頼度を下げる
- この推測を使わない

### Rule

AI interpretation must be removable without deleting original memory.

## 6. Portability

### 意味

データを持ち出せること。

### Memory OS implementation

- JSONL export
- Markdown export
- manifest
- SourceRef included
- redactions included
- schemaVersion included
- local archive later

### Important

Portability must not become raw leak.

## 7. Reversibility

### 意味

操作を戻せる、または取り返しがつかない操作を明確にすること。

### Memory OS examples

Reversible:

- hide/unhide
- archive/restore
- AI interpretation delete/regenerate if safe

Irreversible:

- raw-only delete
- account deletion after retention
- export downloaded outside service cannot be revoked

UX must explain this.

## Data Control Panel

Memory OS should eventually provide a Data Control Panel.

Sections:

- 保存されている出典
- 原文保存中の記録
- AI対象の記録
- Tip対象の記録
- Export除外中の記録
- 封印中の記録
- 削除済み/tombstone数
- 最近のPolicy deny

## HDI Tests

1. Memory detail shows SourceRef.
2. Memory detail shows rawStored status.
3. AI summary is labeled.
4. User can delete AI interpretation only.
5. User can exclude from AI.
6. User can exclude from Export.
7. Export manifest explains redactions.
8. Raw delete explains irreversible nature.
9. Hidden can be unhidden.
10. Policy deny explanation is visible and safe.

## HDI Review Checklist

Before shipping a feature:

1. Can user see what data exists?
2. Can user see where it came from?
3. Can user distinguish fact vs AI inference?
4. Can user correct/delete/exclude it?
5. Can user export it safely?
6. Are irreversible actions clear?
7. Does policy denial explain why?
8. Does UI hide important controls?

## Acceptance Criteria

- legibility requirements defined.
- user agency controls defined.
- negotiability boundaries defined.
- provenance required.
- contestability for AI output defined.
- portability and reversibility covered.
- HDI tests listed.

## 結論

Human Data Interaction は、Memory OS のユーザー主導性を支える設計である。

ユーザーは、AIに記憶を預けるのではない。

自分の人生文脈を、理解し、探し、直し、隠し、消し、持ち出せる必要がある。
