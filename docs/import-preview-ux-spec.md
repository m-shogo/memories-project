# Import Preview UX Spec

## 目的

Import Preview は、Memory OSのImportで、保存前にユーザーが範囲・出典・private/sensitive候補・raw保存・AI分析・Export既定値を確認するための必須画面である。

Memory OSでは、Importが直接保存に進んではいけない。

## 基本原則

### 1. No preview, no import

Import Previewを通らない保存は禁止。

### 2. User controls scope

Import範囲はユーザーが決める。

### 3. AI does not analyze on import

Import直後にAI分析しない。

### 4. Sensitive by default

private/sensitive候補は静かに保護する。

### 5. Source-first

すべてのImport候補にsourceRefを表示する。

## Preview Flow

```txt
Import input
→ parse candidates
→ classify privacy/safety
→ show preview
→ user edits scope
→ policy evaluation
→ save confirmed records
```

## Preview Sections

### 1. Source Summary

Show:

- source name
- input method
- file name or pasted text label
- detected service
- confidence
- record count
- date range
- parser used

Example:

```txt
Netflix 視聴履歴CSVとして検出しました。
238件の候補を見つけました。
期間: 2021-03-12〜2026-07-07
保存前に範囲を選べます。
```

### 2. Safety Summary

Show counts, not private titles.

- private/sensitive candidate count
- raw included count
- third-party content count
- low confidence count
- unsupported count
- duplicate count

Example:

```txt
12件はプライベート性が高い可能性があります。
既定ではAI分析・Tip・Exportから除外されます。
```

### 3. Scope Controls

User can choose:

- import all safe candidates
- import selected only
- skip private/sensitive candidates
- include private/sensitive as sealed
- include private/sensitive as owner_sensitive
- metadata only
- title redacted
- date range filter
- source folder filter
- domain filter

### 4. Candidate Table

Columns:

- checkbox
- title
- date
- source
- status/progress
- confidence
- privacy
- raw
- warnings

For private/sensitive candidates:

- title may be redacted by default.
- user can reveal one by one.
- bulk reveal requires warning.

### 5. Bulk Actions

- Select all visible
- Skip all low confidence
- Mark selected as owner_sensitive
- Seal selected
- Metadata only
- Redact titles
- Set status: watched/reading/listening/want_to_watch
- Set date
- Merge duplicates

### 6. Raw Handling

Default:

- rawStored=false.

If user enables raw:

- show warning.
- require source-specific privacy check.
- third-party raw remains restricted or denied by policy.

Copy:

```txt
rawを保存すると検索やExport時の取り扱いが重くなります。
必要な場合だけ選択してください。
```

### 7. AI Analysis Default

Default:

- off for all Import.
- allowed only after user request.

For sensitive/private:

- off and excluded.

Copy:

```txt
Import直後にAI分析は行いません。
必要な時だけ、選んだ記録に対して実行できます。
```

### 8. Export Default

Default:

- normal owner_only hobby records may be included in standard export.
- private/sensitive/third-party/raw/sealed excluded by default.

Copy:

```txt
プライベート性が高い候補は、既定ではExportに含まれません。
```

## Preview Modes

```ts
type ImportPreviewMode =
  | 'normal'
  | 'privacy_preserving'
  | 'metadata_only'
  | 'title_redacted'
  | 'sealed_candidate';
```

### normal

Use for low-risk records.

### privacy_preserving

Use for:

- LINE/DM
- X likes/bookmarks
- private bookmarks
- search/watch histories
- health/body/relationship/mental/work-related candidates

### metadata_only

Use when content is too sensitive or rights-sensitive.

### title_redacted

Use when revealing title in shared-screen situation is risky.

### sealed_candidate

Use when user marks records as sealed before save.

## Source-specific Defaults

### LINE

- preview mode: privacy_preserving
- raw: off
- AI: off
- export: excluded
- third-party raw: restricted/summary-only

### X / Twitter

- own posts: owner_only default
- likes/bookmarks: owner_sensitive default
- DMs: excluded unless explicitly selected and policy allows summary-only

### Netflix / Prime / Disney+ / U-NEXT

- watch history: owner_sensitive default
- AI: off
- export: excluded or user-selected
- profile/shared account warning

### 食べログ

- restaurant title: owner_only
- visit date/location/companion: owner_sensitive
- companion inference: disabled

### Filmarks

- watched title: owner_only
- review/rating: owner_only or owner_sensitive user choice
- AI taste diagnosis: disabled

### Apple Music / Spotify / Last.fm

- public playlists: owner_only
- private playlists/recent listening: owner_sensitive option
- no personality inference

### Manga / Anime

- progress: owner_only default
- private folders/sources: owner_sensitive

### Browser Bookmarks

- normal folders: owner_only
- private-like folders: owner_sensitive
- title redaction option
- no active content

## Empty / Error States

### Unsupported format

```txt
この形式はまだ自動解析できません。
タイトル一覧として貼り付けImportするか、手入力で記録できます。
```

### Low confidence

```txt
形式の判定に迷っています。
サービスを選ぶと、より正確に取り込めます。
```

### Security blocked

```txt
安全のため、このファイルの一部は読み込みませんでした。
保存前に読み込めた範囲を確認できます。
```

### Sensitive detected

```txt
一部の記録はプライベート性が高い可能性があります。
既定ではAI分析・Tip・Exportから除外されます。
```

## Do Not Use Copy

- 全部自動で吸い上げました。
- あなたの趣味傾向を分析しました。
- 恥ずかしい記録が見つかりました。
- この履歴からあなたの本質が分かります。
- ImportしたのでAIがすぐ要約します。

## Use Copy

- 保存前に確認できます。
- Import直後にAI分析は行いません。
- プライベート性が高い候補は既定で保護されます。
- 不要な候補は保存しないで閉じられます。
- 原文を残さず、日付とタイトルだけ保存できます。

## Accessibility / Mobile

Mobile-first requirements:

- preview count summary at top.
- sticky save/cancel buttons.
- bulk actions collapsed.
- sensitive candidates collapsed.
- one-tap skip source/folder.
- no horizontal-only table on mobile.

## Audit

Audit only records:

- import job id
- source id
- parser id
- count
- selected count
- skipped count
- sensitive count
- policy decision ids

Audit must not include raw titles for private records.

## MVP Acceptance Criteria

- User can preview before save.
- User can skip records.
- User can edit title/date/status.
- User can set privacy per record and bulk.
- User can see parser confidence.
- Private titles can be hidden.
- Raw is off by default.
- AI analysis is off by default.
- Export defaults are visible.
- Save cannot happen if policy denies.

## 結論

Import Previewは、Memory OSのImport安全性とユーザー信頼の中心である。

Importは「入れる」よりも「入れる前に選べる」ことが大事。

特にSランクImportでは、Netflix、X、LINE、食べログ、Filmarks、Apple Music、Podcast、漫画、アニメなど、privateな内容が自然に混ざる。

だからPreviewで静かに守り、ユーザーが範囲を決める。
