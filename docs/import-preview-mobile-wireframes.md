# Import Preview Mobile Wireframes

## 目的

この文書は、Memory OS のImport Previewをモバイルで迷わず使えるようにするためのwireframe/specである。

Import Previewは、安全性だけでなく、ユーザーが「保存前に範囲を選べる」と感じる体験の中心である。

## UI Principles

### 1. Preview before save

保存ボタンはPreview確認後にだけ出す。

### 2. Summary first, details later

モバイルでは全件table表示しない。

上部にsummary、下にcard list。

### 3. Sensitive content collapsed by default

private/sensitive候補は開かないと詳細を見せない。

### 4. No shame copy

adult/private/sensitive系の可能性があっても、恥ずかしさを刺激する文言を使わない。

### 5. Clear cancel path

Importをやめてもよいことを常に表示する。

## Screen Flow

```txt
Paste / Upload / Select Source
→ Detection Review
→ Preview Summary
→ Candidate Cards
→ Bulk Controls
→ Confirm Scope
→ Save or Preview-only End
```

## Screen 1: Input

### Components

- Source selector
- Input mode tabs
  - Paste text
  - URL list
  - File upload
  - Manual entry
- Textarea / file picker
- Privacy note
- Continue button

### Copy

```txt
履歴画面、一覧画面、URL、メモを貼り付けできます。
保存前に内容を確認できます。
```

### Avoid

```txt
全部自動で吸い上げます。
あなたの趣味を分析します。
```

## Screen 2: Detection Review

### Card

```txt
検出結果

候補: Netflix 視聴履歴
信頼度: 高
件数: 128件
期間: 2022-01-03〜2026-07-07

[変更する]
[Previewへ]
```

### Low confidence state

```txt
形式の判定に迷っています。
サービスや媒体を選ぶと、より正確に確認できます。
```

Actions:

- choose medium
- choose service
- continue as generic list
- cancel

## Screen 3: Preview Summary

Sticky top summary:

```txt
128件の候補

保存候補: 116
確認が必要: 8
重複候補: 3
保存しない候補: 1

AI分析: オフ
Export: プライベート候補は既定で除外
```

Badges:

- Safe
- Private
- Restricted
- Low confidence
- Duplicate candidate
- Previously deleted
- Unsupported

## Candidate Card Layout

```txt
[checkbox] 作品タイトル / 店名 / URL / 番組名
日付: 2026-07-07 / 不明 / 月まで
状態: 視聴済み / 読書中 / 保存 / 行きたい
Source: Netflix CSV
Privacy: owner_sensitive
Confidence: medium
Warnings: shared profile possible

[編集] [詳細] [保存しない]
```

For sensitive candidates:

```txt
[checkbox] 詳細を隠しています
プライベート性が高い可能性があります。
既定ではAI分析・Exportから除外されます。

[1件だけ表示] [保存しない]
```

## Candidate Editing

Editable fields:

- title
- date
- date precision
- status
- progress
- privacy level
- selected / skipped
- source label

Not editable in Preview-only prototype:

- raw source hash
- policy decision
- dedupe key
- source account hash

## Bulk Controls

Collapsed by default.

Actions:

- select all visible
- skip all low confidence
- skip private/restricted
- mark selected owner_sensitive
- metadata only
- title redacted
- set status
- set date

Must show warning when bulk revealing private titles.

## Medium-specific UI Variants

### Streaming

Show:

- title
- watched date
- profile/shared warning
- status

Default badges:

- owner_sensitive
- AI off
- Export excluded

### Music

Show:

- track
- artist
- album/playlist
- played/saved/current

For recent/current:

- owner_sensitive badge

### Anime/Manga

Show:

- title
- media type
- episode/volume/chapter progress
- status

### Restaurant/Food

Show:

- restaurant name
- area
- visit/reservation date if present
- companion warning if present

Do not show relationship inference.

### Audio Episode

Show:

- show title
- episode title/number
- listened/saved/subscribed

### Message/Conversation

Show:

- date range
- message count
- source label
- raw hidden by default

Copy:

```txt
会話の原文は既定では保存しません。
必要な場合だけ、安全な要約として残せます。
```

### Image/Media

Show:

- media kind
- dimensions
- EXIF stripped badge
- OCR off badge
- export excluded badge

Do not show raw image in unsafe context.

### Persona-like

Show:

- data kind
- identity boundary
- simulationAllowed=false badge
- export excluded badge

Copy:

```txt
このデータは記録として扱います。
人格として起動しません。
```

### Export Archive Re-import

Show:

- package class
- contains raw/media/persona/sealed/minor flags
- tombstone check required

Copy:

```txt
Exportファイルでも、再Import時には安全確認を行います。
```

## Error States

### Unsupported

```txt
この形式はまだ自動解析できません。
タイトル一覧として貼り付けるか、手入力で記録できます。
```

### Security blocked

```txt
安全のため、このファイルの一部は読み込みませんでした。
読み込めた範囲だけ確認できます。
```

### Previously deleted

```txt
この候補は以前削除した記録と一致する可能性があります。
既定では保存しません。
```

### Sensitive detected

```txt
一部の候補はプライベート性が高い可能性があります。
既定ではAI分析・Exportから除外されます。
```

## Sticky Footer

Preview-only mode:

```txt
[保存せず閉じる] [確認だけ完了]
```

Commit-enabled mode:

```txt
[保存せず閉じる] [選択した候補を保存]
```

Danger:

- never auto-save on back navigation.
- never save all by default for sensitive imports.

## Accessibility

- large tap targets.
- screen reader labels for privacy badges.
- no color-only status.
- plain language warnings.
- card pagination or virtual list for large imports.

## Performance

For large imports:

- summary loads first.
- candidates paginated.
- bulk actions apply to visible or filtered set explicitly.
- do not render thousands of DOM nodes.
- no thumbnails unless safe and lazy-loaded.

## P0 UI Tests

1. Sensitive candidate collapsed by default.
2. Save button absent in Preview-only prototype.
3. Low confidence prompts source selection.
4. Previously deleted candidate selected=false.
5. LINE raw copy not visible by default.
6. Image OCR off badge visible.
7. Persona simulationAllowed=false visible.
8. Bulk reveal private titles requires confirmation.
9. Cancel path always available.
10. No shame copy appears.

## 結論

Import Preview mobile UIは、tableではなくsummary + card listで作る。

ユーザーが保存前に範囲を選べること、sensitive候補が静かに保護されること、AI分析/Exportが既定で安全側にあることを最初に伝える。
