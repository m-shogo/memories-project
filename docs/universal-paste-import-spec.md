# Universal Paste Import Spec

## 目的

Universal Paste Import は、APIや公式Exportがないサービスでも、履歴画面・一覧画面・URL一覧・手入力メモをMemory OSに取り込めるようにするためのS0機能である。

これはfallbackではなく、first-class Importである。

## なぜ必要か

Sランクサービスには、APIが弱いものが多い。

- Amazon Prime Video
- Disney+
- U-NEXT
- Filmarks
- 食べログ
- GERA
- 漫画アプリ
- ラジオアプリ
- Apple Musicの一部リスト

これらは「APIがないから後回し」にするとユーザーのやる気が落ちる。

Universal Paste Importにより、ユーザーは今使っている画面からそのままMemory OSへ文脈を移せる。

## 基本コンセプト

```txt
画面で一覧を見る
→ コピーする
→ Memory OSに貼る
→ sourceを選ぶ
→ parserが候補を作る
→ ユーザーが直す
→ Previewで確認する
→ 保存する
```

## 対応入力

```ts
type PasteInputKind =
  | 'plain_text'
  | 'url_list'
  | 'table_like_text'
  | 'line_based_list'
  | 'chat_snippet'
  | 'receipt_text'
  | 'mixed_text';
```

## 対応Source

初期S0対応:

- Generic title list
- URL list
- Netflix copied history
- Prime Video copied list
- Disney+ copied list
- U-NEXT copied list
- LINE copied snippet
- Filmarks copied list
- 食べログ copied list
- GERA copied list
- Podcast episode list
- Manga progress list
- Anime progress list
- Apple Music copied playlist
- Spotify copied playlist
- Radio program list

## User Flow

### Step 1: Paste Box

UI:

```txt
貼り付けてImport

履歴画面、一覧画面、URLリスト、メモを貼り付けできます。
APIがないサービスでもここから記録できます。
```

Fields:

- source selector
- pasted text area
- optional default date
- optional domain
- optional privacy default

### Step 2: Source Selector

The user can choose:

- 自動判定
- Apple Music
- Spotify
- X / Twitter
- Netflix
- Prime Video
- Disney+
- U-NEXT
- LINE
- 食べログ
- GERA
- Podcast
- Filmarks
- Manga
- Anime
- Movie
- Radio
- Generic list

User selection has priority over detector when confidence is low.

### Step 3: Detection

Detector extracts:

- URLs
- titles
- dates
- episode/season/chapter/volume
- status words
- rating-like values
- restaurant-like lines
- chat timestamp-like lines

```ts
interface PasteDetectionResult {
  detectedKind: PasteInputKind;
  sourceCandidates: {
    sourceId: string;
    confidence: number;
    reasons: string[];
  }[];
  warnings: string[];
}
```

### Step 4: Parse Candidates

Output:

```ts
interface PasteImportCandidate {
  candidateId: string;
  sourceId: string;
  domain: string;
  title?: string;
  url?: string;
  dateText?: string;
  occurredAt?: string;
  status?: string;
  progressText?: string;
  ratingText?: string;
  memoText?: string;
  lineNumbers: number[];
  confidence: 'high' | 'medium' | 'low';
  needsUserReview: boolean;
}
```

### Step 5: Correction UI

The user can edit:

- title
- date
- status
- progress
- source
- privacy
- memo
- skip/include

Bulk actions:

- all as watched
- all as want_to_watch
- all as reading
- all as listened
- all as owner_sensitive
- skip selected
- merge duplicates

### Step 6: Import Preview

Preview is mandatory.

Show:

- parsed count
- skipped count
- low confidence count
- private/sensitive candidate count
- duplicate count
- sourceRef
- rawStored default
- AI analysis default
- Export default

### Step 7: Save

Only confirmed candidates become records.

## Parser Strategies

### Line-based title parser

Input:

```txt
作品A
作品B
作品C
```

Output:

- each non-empty line becomes candidate title.
- source = user selected source.
- date = optional default date.
- status = user selected bulk status.

### URL list parser

Input:

```txt
https://example.com/item/1
https://example.com/item/2
```

Output:

- URL candidates.
- service detector by domain.
- title initially unknown.
- optional metadata enrichment after preview.

### Table-like parser

Input:

```txt
2026/07/01 作品A
2026/07/02 作品B
```

Output:

- date + title candidates.

### Progress parser

Input:

```txt
ワンピース 108巻まで
呪術廻戦 完了
アニメA 7話まで
```

Output:

- title
- progress
- status

### Chat snippet parser

Input:

```txt
2026/07/01 21:05 A: ありがとう
2026/07/01 21:06 B: また行こう
```

Output:

- message snippet candidates
- raw default off
- summary-only recommended
- third-party sensitive default

### Restaurant list parser

Input:

```txt
店名A 横浜 焼肉
店名B 渋谷 イタリアン
```

Output:

- restaurant records
- source = 食べログ or manual restaurant list
- visit date unknown unless present

## Source-specific Paste Rules

### Netflix

Expected lines:

- title + date
- date + title

Default:

- domain = movie/tv
- status = watched
- privacy = owner_sensitive
- AI analysis = off

### Prime Video / Disney+ / U-NEXT

Expected lines:

- title
- title + episode
- title + watch state

Default:

- status = watched or watching depending user selection
- privacy = owner_sensitive

### LINE

Expected lines:

- timestamp + speaker + text
- copied plain chat text

Default:

- rawStored=false
- privacy=restricted for relationship/family contexts
- AI analysis=off
- summary-only recommended

### Filmarks

Expected lines:

- title
- title + rating
- title + date
- title + review fragment

Default:

- domain=movie
- status=watched or want_to_watch
- TMDb enrichment optional

### 食べログ

Expected lines:

- restaurant name
- restaurant name + area
- restaurant URL

Default:

- domain=restaurant
- companion/location details sensitive
- no relationship inference

### GERA / Radio / Podcast

Expected lines:

- show title
- episode title
- URL
- date

Default:

- domain=radio/podcast
- status=listened or want_to_listen

### Manga / Anime

Expected lines:

- title + volume/chapter/episode
- title + status

Default:

- status=reading/watching if progress exists
- manual correction expected

## Privacy Defaults

```ts
type PastePrivacyDefaultRule = {
  sourceId: string;
  defaultPrivacy: 'owner_only' | 'owner_sensitive' | 'restricted';
  aiAnalysisDefault: 'off' | 'allowed_after_user_request';
  exportDefault: 'included' | 'excluded';
};
```

Examples:

- LINE: restricted, AI off, export excluded
- X likes/bookmarks: owner_sensitive, AI off, export excluded
- Netflix/streaming watch history: owner_sensitive, AI off
- 食べログ visited list: owner_sensitive, AI off if location/companions included
- Manga/anime progress: owner_only unless sensitive folder/source
- Spotify playlist: owner_only unless private playlist/private folder

## Security

- no HTML rendering.
- pasted text is treated as plain text.
- URLs are validated.
- unsafe URL schemes are rejected.
- max paste size enforced.
- very large paste becomes file import suggestion.
- logs contain counts, not content.

## Error Handling

### Low confidence

Show:

```txt
形式を完全には判定できませんでした。
サービスを選ぶか、タイトルだけの一覧として取り込めます。
```

### Too many records

Show:

```txt
件数が多いため、まずPreviewを作成します。
保存前に範囲を選べます。
```

### Sensitive candidate

Show:

```txt
一部の記録はプライベート性が高い可能性があります。
既定ではAI分析・Tip・Exportから除外されます。
```

## MVP Acceptance Criteria

- User can paste a title list and create records.
- User can choose source manually.
- URL list is detected.
- Netflix-like date/title lines parse.
- Filmarks-like title/rating lines parse.
- Manga/anime progress lines parse.
- Restaurant list lines parse.
- Podcast/GERA URL/title lines parse.
- LINE snippet uses restricted defaults and raw off.
- Import Preview is mandatory.
- Low confidence requires user correction.
- No pasted content appears in logs.

## 結論

Universal Paste Import は、SランクImportの土台である。

APIがないサービスでも、履歴画面・一覧画面・URL・手入力からMemory OSに入れられる。

これを先に作ることで、Apple Music、Prime Video、Disney+、U-NEXT、Filmarks、食べログ、GERA、漫画、アニメ、ラジオなどを、個別API完成前から使えるようにできる。
