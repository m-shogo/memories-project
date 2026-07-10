# Adopted Patterns Implementation Plan

## 目的

この文書は、`docs/adopted-product-patterns-registry.md` で正式採用した他アプリ由来の優れたproduct patternを、Memory OSの実装順へ落とす。

参考資料のまま放置しない。

各patternを以下へ接続する。

```txt
Pattern
→ Screen
→ Domain Model
→ Parser / Adapter
→ Visible Reward
→ Weekly / Monthly Hook
→ Acceptance Test
```

## Phase A: 最初に価値が見えるVertical Slice

### PAT-A-001 Universal Quick Capture

Adopted patterns:

- Quick Capture
- Inbox First
- Gentle Return

User flow:

```txt
タイトル / URL / 短いメモを追加
→ Detector
→ Import Preview
→ 未整理Inboxまたは棚preview
```

Screens:

- 日常: Quick Add
- Import Preview
- Home: 未整理Inbox card

Domain:

- import_job
- import_preview
- import_preview_candidate

Visible reward:

- 最初の棚候補が出る
- 保存後に棚が1件増える

Acceptance:

- タイトルだけでもPreviewできる
- URLだけでもPreviewできる
- category/tagを保存前に必須にしない
- AI分析はoff
- no raw logs

### PAT-A-002 Manga / Anime Progress Rail

Adopted patterns:

- Domain-specific Collection
- Progress Tracking
- Visible Collection Growth

User flow:

```txt
作品名 12巻まで
→ Preview
→ 漫画/アニメ棚
→ 1タップ進行更新
```

Screens:

- ホーム: 漫画/アニメ棚
- 日常: 進行更新
- 棚詳細: Progress Rail

Visible reward:

- progress track created
- status chip
- shelf count

Weekly hook:

```txt
1作品だけ進行を更新できます
```

Acceptance:

- volume / episode / chapterを区別できる
- exact dateを勝手に作らない
- daily overall progress rateを出さない

### PAT-A-003 Food Map

Adopted patterns:

- Domain-specific Collection
- Favorites / Curated Lists
- Visible Collection Growth

User flow:

```txt
食べログURL / 店名
→ Preview
→ 行きたい / 行った
→ 地域別list/map
```

Screens:

- ホーム: 食の地図
- 日常: 店を1つ追加
- 棚詳細: 地域別list/map

Visible reward:

- map region added
- restaurant count

Weekly hook:

```txt
行きたい店を1つ追加できます
```

Acceptance:

- precise location/date/companionはowner_sensitive
- companion/relationship inferenceをしない
- login scrapingをしない

### PAT-A-004 Movie / Streaming Shelf

Adopted patterns:

- Domain-specific Collection
- Diary/List/Favorites
- Month Wrap-up

User flow:

```txt
Netflix CSV / Filmarks paste / manual
→ Preview
→ 視聴棚
→ watched timeline
```

Screens:

- ホーム: 映画/視聴棚
- 振り返り: 月の視聴timeline
- 棚詳細: 見た / 見たい

Visible reward:

- timeline unlocked
- duplicate candidate
- source stamps

Acceptance:

- shared profile warning
- owner_sensitive default
- rating/review optional
- no taste/personality diagnosis

## Phase B: 戻る理由を作る

### PAT-B-001 Weekly Box

Adopted patterns:

- visible reward
- gentle ritual
- organize later

Content candidates:

- 今週増えた棚
- 1件だけ進行更新
- 1件だけ重複確認
- 未整理Inbox 1件
- new exact cross-source link

Screens:

- Home top card

Rules:

- 1〜3件だけ
- sensitive sourceはdefault除外
- same card type cooldown
- no streak/guilt

Acceptance:

- cardがなくても空振りcopyを出さない
- raw sensitive dataを表示しない
- notificationなしでもHomeで見える

### PAT-B-002 Month Capsule

Adopted patterns:

- Year/Month Wrap-up
- photo/journal resurfacing
- collection growth

Content:

- 棚ごとの件数
- 新しくできた棚
- exact cross-source links
- user-corrected records
- selected low-risk records

Screens:

- 振り返り

Visible reward:

- month capsule unlocked
- monthly room snapshot

Acceptance:

- fact/count based
- no best/worst month
- no mood/personality inference
- restricted sources default除外

### PAT-B-003 Gentle Return

Adopted patterns:

- re-entry after lapse

Flow:

```txt
久しぶりに起動
→ 未利用日数を出さない
→ 最近追加可能な棚 / Quick Add / last unfinished progress
```

Copy:

```txt
また必要なところから始められます
```

Acceptance:

- streak recoveryなし
- missed daysなし
- unresolved Inboxを全部押し付けない

## Phase C: 蓄積がつながる体験

### PAT-C-001 Exact Cross-source Links

Adopted patterns:

- backlinks
- connected records

Initial relations:

- same external id
- same normalized title + creator/year
- same restaurant + area
- same event/travel box
- same source-native item

Screens:

- 発見
- 各棚のrelated records

Visible reward:

```txt
NetflixとFilmarksが同じ映画棚につながりました
```

Acceptance:

- relation reason visible
- low confidenceはcandidate
- no hidden-intent inference

### PAT-C-002 Memory Constellation

Adopted patterns:

- graph discovery
- linked notes

Role:

- Homeではない
- 発見画面
- data量が十分な時だけ表示

Visual encoding:

- line thickness = relation strength
- line color = relation type
- solid = confirmed
- dotted = candidate
- glow = recently added

Acceptance:

- graphなしでも全機能を使える
- accessibility list alternative
- color-only encoding禁止
- user can inspect relation reason

### PAT-C-003 On This Day / Last Year

Adopted patterns:

- journal/photo resurfacing

Initial scope:

- movie
- manga/anime
- music/audio
- food/travel
- low-risk manual notes

Excluded default:

- LINE/DM
- restricted photos
- minors
- deceased-related sensitive data
- sealed/hidden

Acceptance:

- app card first
- notification opt-in
- person/date/source exclusion controls

## Phase D: Trust as Utility

### PAT-D-001 Basic Search

Filters:

- source
- date/period
- shelf/medium
- status
- area
- title
- user tag

Acceptance:

- no embedding required
- hidden/sealed/deleted excluded
- relation/source visible

### PAT-D-002 Export Readiness

Adopted patterns:

- portability
- backup trust

Screens:

- Settings
- 振り返り/backup card

Show:

- standard export eligible count
- excluded sensitive count
- manifest version
- last export date

Acceptance:

- free user can standard export eligible data
- no fear copy
- raw archive remains gated

### PAT-D-003 AI Context Pack

Adopted patterns:

- portable profile/context

User selects:

- shelves
- period
- source
- detail level
- exclusions

Output:

- facts
- user-provided preferences
- safe summaries
- provenance
- uncertainty

Acceptance:

- no persona clone
- no third-party raw
- user review before export

## Screen Ownership Matrix

| Pattern | Home | 発見 | 振り返り | 日常 |
|---|---:|---:|---:|---:|
| Quick Capture |  |  |  | Primary |
| Inbox | Summary |  |  | Primary |
| Shelf Grid | Primary |  |  |  |
| Progress Rail | Summary |  |  | Primary |
| Food Map | Summary |  |  | Primary |
| Movie Timeline | Summary |  | Primary |  |
| Weekly Box | Primary |  |  |  |
| Month Capsule |  |  | Primary |  |
| Cross-source Links | Summary | Primary |  |  |
| Memory Constellation |  | Primary |  |  |
| Search | Global | Global | Global | Global |
| Export Readiness | Summary |  | Primary |  |

## MVP Slice Recommendation

最初に実装するvisible product slice:

```txt
1. Home Shelf Grid
2. 日常 Quick Add
3. Universal Paste Preview
4. Manga/Anime Progress Rail
5. Food Map list
6. Weekly Box placeholder
7. Month Capsule placeholder
```

Netflix/Filmarks/APIより先に、manual/paste fixtureだけで画面価値を証明する。

## Ticket Definition Extension

すべての機能ticketに追加する。

```txt
Adopted pattern ID:
Visible screen change:
Collection drive:
Target persona:
Weekly/monthly return value:
Pattern-specific anti-copy note:
Safety exclusions:
```

## No-Go

- 他アプリのUIをそのまま複製する
- 各アプリの機能を全部混ぜる
- Homeを巨大dashboardにする
- social feedを先に作る
- graphをHomeの主画面にする
- streakを導入する
- AI要約を自動ONにする
- private memoryをsurprise表示する

## 結論

優れたpatternは正式採用する。

ただし、実装順は以下で統一する。

```txt
軽く入れる
→ 媒体に合う棚で見える
→ 週/月で戻れる
→ 複数sourceがつながる
→ 探せる
→ 持ち出せる
```

これがMemory OSとして一貫した体験になる。
