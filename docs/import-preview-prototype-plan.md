# Import Preview Prototype Plan

## 目的

この文書は、Memory OS の最初のImport実装を、保存なしの Preview-only prototype として進めるための計画である。

最初から保存・検索・Embedding・Exportまで作らない。

まず、安全に取り込む前の確認体験を作る。

## Prototype Goal

ユーザーが以下をできる状態にする。

```txt
履歴/一覧/URL/手入力メモを貼る
→ sourceを選ぶ
→ parser/detectorが候補を作る
→ Previewで確認する
→ 保存はまだしない
```

このprototypeは、Memory OSのImport UXと安全設計を実証するためのもの。

## Why Preview-only First

理由:

- rawを保存しないで安全にparserを検証できる。
- Import Preview UIの使い勝手を先に確認できる。
- Dedup / Tombstone / Policy の動作を保存前に検証できる。
- 失敗しても本データが増えない。
- Sランクサービスの「使える感」を早く出せる。

## Prototype Scope

### Include

- Universal Paste textarea
- Source selector
- Paste detector
- Basic parsers
- Import Preview summary
- Candidate list
- Candidate edit state in UI memory
- Privacy defaults
- Warnings
- Cancel
- No save

### Exclude

- final DB commit
- memory_record creation
- search_document creation
- embedding
- export
- OAuth API connectors
- raw retention beyond request/session

## First Supported Inputs

### Generic title list

```txt
作品A
作品B
作品C
```

### URL list

```txt
https://example.com/a
https://example.com/b
```

### Netflix-like date/title list

```txt
2026/07/01 作品A
2026/07/02 作品B
```

### Manga/anime progress list

```txt
ワンピース 108巻まで
アニメA 7話まで
```

### Restaurant list

```txt
店名A 横浜 焼肉
店名B 渋谷 イタリアン
```

### GERA/Podcast episode list

```txt
番組A #123 タイトル
番組B 2026/07/01 エピソード名
```

### LINE selected snippet

```txt
2026/07/01 21:05 A: ありがとう
2026/07/01 21:06 B: また行こう
```

## UI Flow

### Screen 1: Paste Import

Fields:

- source selector
- textarea
- default status
- default date optional
- privacy quick option

Copy:

```txt
履歴画面、一覧画面、URLリスト、メモを貼り付けできます。
保存前に内容を確認できます。
```

### Screen 2: Detection Result

Show:

- detected source candidates
- confidence
- parser used
- warnings

If confidence low:

```txt
形式の判定に迷っています。
サービスを選ぶと、より正確に取り込めます。
```

### Screen 3: Preview

Show:

- candidate count
- sensitive count
- low confidence count
- unsupported count
- duplicate-looking count
- AI analysis default
- Export default

Candidate item mobile card:

```txt
[checkbox]
Title
Date / Status / Source
Privacy badge
Confidence badge
Warnings
Edit
```

### Screen 4: Prototype End

Because prototype is preview-only:

```txt
ここではまだ保存しません。
保存処理はPolicy/Dedupe/Tombstoneの実装後に有効化します。
```

## Data Flow

```txt
PasteText
→ SecurityGate
→ SourceDetector
→ Parser
→ CanonicalImportCandidate[]
→ PrivacyDefaultClassifier
→ PreviewSummary
→ UI Candidate Editing
→ End without commit
```

## Security Gate

Before parsing:

- max text length
- no HTML rendering
- URL scheme validation
- strip/neutralize control characters for display
- logs contain counts only

## Candidate DTO

```ts
interface PreviewPrototypeCandidate {
  id: string;
  sourceId: string;
  domain: string;
  title?: string;
  url?: string;
  occurredAtText?: string;
  occurredAtPrecision?: 'exact_timestamp' | 'date' | 'month' | 'year' | 'period' | 'unknown';
  status?: string;
  progressText?: string;
  confidence: 'high' | 'medium' | 'low' | 'needs_user_selection';
  privacyLevel: 'owner_only' | 'owner_sensitive' | 'restricted';
  aiAnalysisDefault: 'off' | 'allowed_after_user_request';
  exportDefault: 'included' | 'excluded';
  warnings: string[];
  selected: boolean;
}
```

## Parser Heuristics v0

### Date detection

Support synthetic formats:

- YYYY/MM/DD
- YYYY-MM-DD
- YYYY年M月D日

Do not overfit.

Unknown date allowed.

### Progress detection

Recognize:

- N巻まで
- N話まで
- episode N
- ep N
- 完了
- 視聴中
- 読書中

### URL detection

Recognize URLs line by line.

Reject unsafe schemes:

- javascript:
- data:
- file:
- blob:
- chrome:
- extension:

### Source hints

Domain map:

- netflix.com → netflix
- spotify.com → spotify
- filmarks.com → filmarks
- tabelog.com → tabelog
- gera.fan or known GERA URL patterns → gera
- youtube.com / youtu.be → youtube

This is hint only.

## Privacy Defaults v0

```txt
LINE → restricted, AI off, export excluded
Netflix/streaming → owner_sensitive, AI off
食べログ with date/location/companions → owner_sensitive
X likes/bookmarks → owner_sensitive
private bookmarks → owner_sensitive
Manga/anime progress → owner_only
Generic list → owner_only
```

## Prototype Tests

P0:

1. title list produces candidates.
2. URL list rejects unsafe schemes.
3. Netflix-like date/title lines set date precision=date.
4. Manga progress line sets progress.
5. LINE snippet defaults restricted/raw off.
6. Restaurant list does not infer companion.
7. Low confidence does not auto-commit.
8. No raw pasted text in logs.
9. Candidate edit does not write DB final records.
10. Sensitive warning uses no shame copy.

## Success Criteria

Prototype is successful if:

- user can see pasted data structured in Preview.
- user can correct source/title/date/status.
- privacy defaults are visible.
- nothing is saved as MemoryRecord.
- developer can add new parser without touching all code.

## What Comes After Prototype

Next slice:

1. persist import_job/import_preview/import_preview_candidate.
2. add dedupe_key/tombstone checks.
3. add Safe Commit for low-risk manual/paste only.
4. add Browser Bookmark parser.
5. add Netflix CSV parser.
6. add LINE parser with summary-only default.

## 結論

最初のImport実装は、保存しないPreview-only prototypeにする。

これにより、SランクImportの体験を早く確認しつつ、DB・Policy・Dedupe・Tombstoneが未完成な状態で危険な保存を始めない。
