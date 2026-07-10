# Similar App Evidence and Feature Map

## 目的

この文書は、類似アプリ調査からMemory OSの機能判断へ追跡できるようにするevidence mapである。

各アプリについて、以下を固定する。

- 長期利用を支える特徴
- 利用者が嫌う/離脱する特徴
- Memory OSで真似るもの
- Memory OSで真似ないもの

調査時点: 2026-07-10

## Evidence Table

| App / Category | Long-term value | Friction / criticism | Copy to Memory OS | Do not copy |
|---|---|---|---|---|
| Day One | quick capture, search, map, multimedia, privacy, export | AI interpretation concern, subscription/platform dependency | metadata capture, period/place search, export | automatic mood/meaning analysis |
| Daylio / DailyBean | two-tap input, icons, calendar, simple stats | shallow mood scale, daily obligation, streak pressure | one-action input, month view | life/mood scoring, daily completion |
| 1 Second Everyday | visible calendar accumulation, powerful year compilation | missed-day guilt, experience becomes recording task | Month/Year Capsule, visible compilation | mandatory daily slot filling |
| Google/Apple Photos Memories | automatic grouping, nostalgia, travel/time resurfacing | painful people/dates/events can reappear | opt-in safe resurfacing, period box | surprise sensitive resurfacing |
| Letterboxd | diary, lists, favorites, watchlist, yearly stats, domain identity | rating anxiety, gamification, social performance | domain shelf, favorites, year review | public rank, life-wide ratings |
| StoryGraph | progress, stats, reading wrap-up, flexible challenges | numerical goals can replace pleasure, social expectations differ | domain progress, open-ended challenges | raw quantity as success score |
| Goodreads | huge catalog/community | ads, clutter, review bombing, old UX | catalog depth concept | social toxicity, clutter |
| Raindrop.io | one-click save, visual views, tags, search, cross-device | saved items can become unvisited piles | share extension, visual Inbox, search | collect-only loop |
| Pocket | simple save/revisit, large long-term archive | service shutdown/portability risk | Import/Export, migration | closed archive dependency |
| Readwise Reader | many content types, annotation, search, resurfacing | price/complexity, information overload | safe resurfacing, full-text where allowed | all-content complexity in MVP |
| Finch | small actions unlock pet/items, emotional motivation | pet/streak obligation, dependency risk | visible shelf unlocks | emotional relationship reward |
| Habitica | game progression makes tasks tangible | external reward can replace purpose | optional visible progression metaphor | punishment/damage/compulsion |
| Streak apps | simple and behaviorally strong | loss aversion, anxiety, abandonment after break | none as default | daily streak |
| Pinterest-like collections | saving + visual revisit supports retention | endless recommendations and collecting without use | visual shelf, revisitation ranking | infinite feed, algorithmic compulsion |

## Strong Evidence Patterns

### Pattern A: Entry friction must be below organization friction

Users will save when:

- share action is one tap
- title/URL/progress is enough
- category can be decided later

If folder/tag/importance is required first, Lightweight Capturer leaves.

Memory OS decision:

```txt
Capture first, Preview and organize later.
```

### Pattern B: Accumulation needs a product artifact

Long-term value appears when small entries become:

- diary
- calendar
- shelf
- timeline
- map
- progress tracker
- yearly wrap-up

Memory OS decision:

```txt
Every import must promise a visible artifact.
```

### Pattern C: Revisit beats raw retention

Saving alone is insufficient.

Need:

- search
- unfinished items
- last year same period
- month capsule
- cross-source link

Memory OS decision:

```txt
Save → Shelf → Revisit
```

### Pattern D: Domain-specific views beat generic dashboards

Users understand:

- 映画棚
- 漫画進行
- 食の地図
- 音楽の時期

They understand generic “126 memories” less.

Memory OS decision:

```txt
Domain meaning before total count.
```

### Pattern E: Stats are attractive and dangerous

Stats make collections visible, but can replace enjoyment.

Memory OS decision:

Allowed:

- item counts
- date coverage
- shelf growth
- progress
- source coverage

Denied:

- life score
- good/bad month
- completion pressure
- public ranking

### Pattern F: Nostalgia needs hard controls

Automatic resurfacing is powerful and sometimes harmful.

Memory OS decision:

- default allowlist by shelf
- restricted sources off
- person/date/period exclusion
- hide now
- notification opt-in

### Pattern G: Long absence is normal

Personal tracking research shows people often return after long gaps when a goal or intent reappears.

Memory OS decision:

- no streak
- no missed-day count
- no forced backfill
- new use cycle can begin

### Pattern H: Trust is a recurring feature, not legal text

Long-term users care about:

- privacy
- export
- sync
- service survival
- acquisition/change

Memory OS decision:

Show:

- source status
- export readiness
- backup state
- AI analysis state
- support raw access policy

## Feature Priority Derived from Research

### P0 Experience

1. one-tap/manual/paste import
2. Import Preview
3. visible shelf creation
4. progress update
5. search and source/date filters
6. hide/seal/exclude
7. standard export
8. guilt-free return

### P1 Retention

1. Weekly Box
2. Month Capsule
3. Last Year This Week
4. cross-source link
5. one-item cleanup
6. safe share card

### P2 Expansion

1. relationship/constellation graph
2. advanced stats
3. custom shelf views
4. social collection sharing
5. AI Context Pack

## Features to Delay

- automatic AI reflection
- emotional analysis
- social feed
- complex graph as home
- OCR on all images
- full media archive
- gamification economy

## Research-backed Product Statement

```txt
Memory OSは、毎日入力させる日記でも、何でも保存する倉庫でもない。

軽く取り込み、自分の棚として見え、必要な時に再発見でき、空白があっても戻れる場所である。
```

## 結論

類似アプリの成功要因をそのまま混ぜるのではなく、役割ごとに抽出する。

- Day Oneから軽いcaptureとsearch
- 1SEから時間でまとまる報酬
- Letterboxd/StoryGraphからdomain collectionとwrap-up
- Raindrop/Pocketからshare/save/import
- Photos Memoriesからresurfacingの魅力と危険
- Finch/Habiticaからvisible rewardだけを抽出

関係依存、streak、score、surprise sensitive resurfacingは持ち込まない。
