# Concrete MVP Ticket Backlog

## 目的

`docs/concrete-mvp-product-scope.md` を、実装可能なticketへ分解する。

各ticketは、見える変化・依存関係・完了条件を持つ。

## Ticket Rule

すべてのticketに必須:

```txt
Adopted pattern ID
Visible screen change
Target persona
Collection drive
Safety exclusions
Acceptance tests
```

---

# Phase 0: Foundation

## MVP-0001 App shell and navigation

Visible:

- ホーム
- 発見
- 振り返り
- 日常

Acceptance:

- 4tab navigation works.
- each screen has empty state.
- back navigation works.
- no business logic yet.

## MVP-0002 Core domain schema v0

Tables/models:

- shelf
- collection_item
- source_item
- progress_state
- restaurant_record
- user_note
- user_tag
- record_relation

Acceptance:

- source_item and collection_item are separate.
- deleted/hidden/sealed flags exist where required.
- ownership is explicit.
- migrations are reversible in development.

## MVP-0003 Import job schema v0

Tables/models:

- import_job
- import_source
- import_preview
- import_preview_candidate

Acceptance:

- preview state is separate from committed records.
- failed/cancelled/expired states exist.
- candidates can be individually selected.

---

# Phase 1: First visible shelf

## MVP-0101 Home Shelf Grid

Visible:

- 漫画・アニメ棚
- 映画・視聴棚
- 食の地図
- あとで見る棚
- 未整理Inbox

Acceptance:

- item counts render.
- empty-state copy renders.
- cards navigate to details.
- no life score/streak.

## MVP-0102 Quick Add input

Visible:

- one input field on 日常.
- paste/file/preview actions.

Acceptance:

- title, URL, progress text accepted.
- blank input blocked.
- no direct commit.
- preview required.

## MVP-0103 Detector v0

Supported detection:

- URL
- manga/anime progress text
- watched/manual movie text
- restaurant name/URL
- unknown

Acceptance:

- outputs medium candidate + confidence.
- low confidence routes to Inbox candidate.
- detection reason is inspectable.

## MVP-0104 Import Preview UI v0

Visible:

- detected format.
- candidate rows.
- destination shelf.
- warnings.
- select/unselect.

Acceptance:

- candidate can be edited.
- save disabled until valid.
- no hidden automatic commit.
- source remains visible.

## MVP-0105 Safe Commit v0

Acceptance:

- only selected candidates commit.
- transaction prevents partial corrupt save.
- result counts returned.
- audit event contains metadata only.

## MVP-0106 Save result reward

Visible:

```txt
漫画・アニメ棚に3件追加しました
```

Actions:

- 棚を見る
- 続けて追加
- 戻る

Acceptance:

- destination shelf count updates immediately.
- reward is domain-specific.
- no achievement score.

---

# Phase 2: Manga / Anime vertical slice

## MVP-0201 Progress text parser

Examples:

```txt
SPY×FAMILY 12巻まで
葬送のフリーレン 8話まで
```

Acceptance:

- title extracted.
- volume/episode/chapter distinguished.
- ambiguous value flagged.
- exact date not invented.

## MVP-0202 Manga / Anime Shelf detail

Visible tabs:

- 進行中
- 見たい
- 完了
- 保留

Acceptance:

- item rows render.
- status changes persist.
- source stamp visible.
- search entry opens correct item.

## MVP-0203 Progress Quick Update

Actions:

- +1巻
- +1話
- direct number
- 完了
- 保留

Acceptance:

- cannot go below zero.
- total is optional.
- change history stores metadata.
- no daily total progress rate.

## MVP-0204 Manga weekly card rule

Card:

```txt
漫画棚で1作品だけ進行を更新できます
```

Acceptance:

- only low-risk shelf metadata used.
- max one card.
- no guilt copy.
- cooldown applies.

---

# Phase 3: Food vertical slice

## MVP-0301 Restaurant input parser

Supported:

- restaurant URL
- restaurant name
- area + restaurant name

Acceptance:

- URL host captured.
- source URL preserved.
- unknown area allowed.
- no scraping behind login.

## MVP-0302 Food list detail

Visible:

- area groups.
- 行きたい / 行った.
- favorite.
- source URL.

Acceptance:

- works without map SDK.
- area can be corrected.
- exact location optional.
- companion not inferred.

## MVP-0303 Food Quick Add

Acceptance:

- add from URL/name.
- choose 行きたい / 行った.
- favorite optional.
- note optional.

## MVP-0304 Food Home summary

Visible example:

```txt
食の地図
横浜 8件 / 川崎 5件
```

Acceptance:

- top areas derived from confirmed user data.
- no inferred home/work location.

---

# Phase 4: Movie / Streaming vertical slice

## MVP-0401 Manual watched text parser

Examples:

```txt
PERFECT DAYS 見た
ミッドサマー 見たい
```

Acceptance:

- title and status parsed.
- watched date optional.
- rating optional.
- no taste analysis.

## MVP-0402 Netflix CSV fixture parser

Acceptance:

- fixture-only first.
- detects shared-profile risk.
- rows preview before commit.
- original row source retained.

## MVP-0403 Movie / Streaming Shelf detail

Tabs:

- 見た
- 見たい
- お気に入り

Acceptance:

- source visible.
- duplicate candidate shown.
- review field optional.
- no public feed.

## MVP-0404 Movie monthly count

Visible in 振り返り:

```txt
映画 2件追加
```

Acceptance:

- only known dates counted.
- unknown date shown separately.

---

# Phase 5: Inbox and Search

## MVP-0501 Unsorted Inbox

Actions:

- shelfへ移す
- title修正
- source確認
- 保留
- 削除

Acceptance:

- unresolved count shown on Home.
- no forced cleanup.
- bulk action not required for MVP.

## MVP-0502 Basic Search

Search:

- title
- restaurant name
- user note
- source label

Filters:

- shelf
- source
- status
- period
- area

Acceptance:

- hidden/sealed/deleted excluded.
- no embedding dependency.
- result explains shelf/source.

---

# Phase 6: Weekly and Monthly return value

## MVP-0601 Weekly Box rule engine v0

Candidate rules:

1. one progress update.
2. one Inbox item.
3. one new shelf change.
4. one exact duplicate/cross-source candidate.

Acceptance:

- displays 0 or 1 card.
- same type cooldown.
- sensitive sources excluded.
- no push notification in MVP.

## MVP-0602 Month Capsule v0

Visible:

- month selector.
- shelf counts.
- updates/additions.
- unknown-date count.

Acceptance:

- facts only.
- no ranking.
- no emotional inference.
- empty month does not generate fake summary.

## MVP-0603 Gentle Return state

Trigger:

- return after configurable inactivity threshold.

Visible:

```txt
また必要なところから始められます
```

Actions:

- Quick Add
- last unfinished progress
- recent shelf

Acceptance:

- no missed-day count.
- no streak recovery.
- no unresolved backlog dump.

---

# Phase 7: Discovery and relations

## MVP-0701 Exact relation matcher v0

Supported:

- same external id.
- same normalized title + year/creator.
- same restaurant name + area.

Acceptance:

- reason stored.
- confidence stored.
- low confidence not auto-confirmed.

## MVP-0702 Discovery list screen

Visible:

- recent additions.
- confirmed connections.
- empty state.

Acceptance:

- no graph required.
- relation reason visible.
- candidate and confirmed visually distinct.

---

# Phase 8: Export

## MVP-0801 Standard JSON export

Acceptance:

- choose shelf/period/status.
- manifest included.
- hidden/sealed/deleted excluded.
- export downloadable.

## MVP-0802 CSV export for progress and food

Acceptance:

- manga/anime progress CSV.
- restaurant CSV.
- stable column names.
- UTF-8.

## MVP-0803 Export readiness summary

Visible:

- eligible count.
- excluded count.
- last export date.
- schema version.

Acceptance:

- no fear copy.
- user can inspect exclusion reasons.

---

# Deferred Tickets

P1:

- Last Year This Month.
- map SDK pins.
- favorites/custom lists.
- Filmarks paste adapter.
- browser share extension.
- safe Month Capsule notification.

P2:

- Memory Constellation.
- music/radio shelf.
- photo metadata box.
- AI Context Pack.
- semantic search.
- safe share card.

No-Go:

- AI companion.
- social feed.
- streak.
- automatic mood/personality analysis.
- LINE bulk raw import.
- face recognition.

---

# Recommended Build Order

```txt
MVP-0001〜0003
→ MVP-0101〜0106
→ MVP-0201〜0204
→ MVP-0301〜0304
→ MVP-0501〜0502
→ MVP-0601〜0603
→ MVP-0401〜0404
→ MVP-0701〜0702
→ MVP-0801〜0803
```

Reason:

漫画/アニメ進行と食は、manual/pasteだけでvisible valueを証明しやすい。

Netflix CSVはparser complexityとshared-profile riskがあるため、その後。

---

# MVP Definition of Done

MVP complete when:

1. title/URL/progress can be pasted.
2. Import Preview always appears before save.
3. manga/anime shelf works end-to-end.
4. food list works end-to-end.
5. movie/manual + Netflix fixture works.
6. Inbox handles unknown data.
7. search finds saved data.
8. Weekly Box can show one safe action.
9. Month Capsule shows factual monthly change.
10. standard Export works.
11. no streak, life score, personality inference, or direct import-to-save.
12. synthetic fixture demo shows before/after in under 2 minutes.
