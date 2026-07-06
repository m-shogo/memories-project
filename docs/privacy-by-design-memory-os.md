# Privacy by Design for Memory OS

## 目的

Privacy by Design は、プライバシーを後付けではなく、設計の最初から組み込む考え方である。

Memory OS は人生文脈・第三者情報・未成年情報・故人情報・会社情報・raw記録を扱うため、Privacy by Design の7原則を Memory OS 用に具体化する。

## Privacy by Design 7 Principles

```txt
1. Proactive not reactive; preventive not remedial
2. Privacy as the default setting
3. Privacy embedded into design
4. Full functionality — positive-sum, not zero-sum
5. End-to-end security — full lifecycle protection
6. Visibility and transparency — keep it open
7. Respect for user privacy — keep it user-centric
```

## Memory OS Mapping

## 1. Proactive not reactive

### 原則

事故が起きてから直すのではなく、先に防ぐ。

### Memory OS での意味

- import前にinspectする。
- raw保存前にsecret scanする。
- LLM送信前にPolicyを通す。
- Export前にredactionする。
- 削除済み復活をtombstoneで防ぐ。

### Required design

```txt
inspect -> policy -> cost -> user scope -> extract -> normalize
```

Forbidden:

```txt
upload -> LLM full analysis
```

### Test

- unknown source full analysis blocked
- secret detected before storage
- third-party raw export denied

## 2. Privacy as the default setting

### 原則

ユーザーが何もしなくても、プライバシーが守られる。

### Memory OS での意味

Default:

- raw off for risky sources
- third-party raw excluded
- minor data no-tip/export-exclude
- corporate data denied
- hidden/sealed excluded
- image face recognition off
- precise location off/rounded

### Good default

```txt
原文を保存せず、安全な要約だけ残す
```

### Bad default

```txt
全履歴を読み込んでAIが整理します
```

### Test

- LINE raw not stored default
- minor not tipped default
- Gmail/Slack full import blocked default

## 3. Privacy embedded into design

### 原則

Privacyを設定画面だけに置かず、データモデル・API・UX・テストに埋め込む。

### Memory OS での意味

Privacy must exist in:

- PrivacyContext
- SurfaceVisibility
- PolicyDecision
- ExportRedaction
- DeletionTombstone
- SearchSnippet
- AdapterInspection

### Required fields

```ts
type PrivacyContext = {
  privacyLevel: PrivacyLevel;
  dataCategories: PrivacyDataCategory[];
  containsRawThirdPartyText: boolean;
  containsMinor: boolean;
  containsCorporateData: boolean;
};
```

### Test

- every record has privacy context or derivable privacy
- export uses privacy level
- search uses privacy level

## 4. Full functionality — positive-sum, not zero-sum

### 原則

プライバシーを守るために機能を全部捨てるのではなく、両立を探す。

### Memory OS での意味

Rawを保存しなくても、文脈は残せる。

Example:

| Need | Unsafe way | Memory OS way |
|---|---|---|
| LINEの思い出を残す | 相手発言raw保存 | relationship summary |
| 写真を探す | 顔認識 | metadata/date/place rough |
| 仕事の転機を残す | Slack全文保存 | personal career context |
| 故人を振り返る | 故人再現 | source-based memory summary |

### Test

- raw delete preserves SourceRef
- relationship summary allowed while raw denied
- photo metadata works without face recognition

## 5. End-to-end security — full lifecycle protection

### 原則

取得から削除まで、ライフサイクル全体で守る。

### Memory OS での意味

Lifecycle:

```txt
capture/import
-> storage
-> search/index
-> AI/interpretation
-> export/backup
-> deletion/tombstone
```

Each stage requires privacy control.

### Required controls

- encryption for raw/export/backup
- no raw logs
- short-lived export URL
- delete propagation
- backup tombstone replay
- embedding disable on deletion

### Test

- export URL expires
- deleted vector disabled
- backup restore replays tombstones

## 6. Visibility and transparency

### 原則

何が起きているか、ユーザーに見える。

### Memory OS での意味

User should know:

- raw stored or not
- source/date
- AI summary or user fact
- why data is excluded
- export redactions
- policy denied reason
- delete state

### UI copy

Good:

```txt
安全のため、相手の原文は保存せず要約だけ残します。
```

Bad:

```txt
AIがいい感じに処理しました。
```

### Test

- memory detail shows source/ref/rawStored
- export preview shows excluded counts
- policy denial has safe explanation

## 7. Respect for user privacy — keep it user-centric

### 原則

ユーザーに分かりやすく、操作しやすく、尊重する。

### Memory OS での意味

User controls must be visible:

- hide
- seal
- delete
- raw delete
- exclude from AI
- exclude from tips
- exclude from export
- export safe archive

Do not use:

- guilt copy
- confirmshaming
- hidden delete
- forced full import

### Test

- deletion button visible
- deletion copy guilt-free
- capture does not require importance

## Privacy by Design Review Checklist

Before shipping a feature:

1. Is privacy default safe?
2. Is raw storage optional or denied?
3. Does it handle third-party data?
4. Does it handle minor/corporate/deceased data?
5. Is Policy checked before LLM/export/search?
6. Is user told what is stored/excluded?
7. Can user delete/raw-delete/seal?
8. Are logs raw-free?
9. Does export show redactions?
10. Does backup respect tombstones?

## Acceptance Criteria

- 7 principles mapped to product behavior.
- raw default off for risky sources.
- privacy is represented in schema/policy/export/search.
- user-visible transparency exists.
- delete/export/backup lifecycle covered.
- tests map to each principle.

## 結論

Privacy by Design は、Memory OS では単なる法務・設定画面ではない。

Memory OS の入口、保存、検索、AI、Export、Backup、削除のすべてに埋め込むべき基本設計である。
