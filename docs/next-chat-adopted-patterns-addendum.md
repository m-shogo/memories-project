# Next Chat Adopted Patterns Addendum

## 目的

この文書は、類似アプリ調査で見つけた優れたproduct patternを、Memory OSへ正式採用した判断を次チャットへ引き継ぐ。

関連docs:

- `docs/long-term-user-research-synthesis.md`
- `docs/persona-feature-fit-matrix.md`
- `docs/retention-resurfacing-and-notification-policy.md`
- `docs/similar-app-evidence-and-feature-map.md`
- `docs/adopted-product-patterns-registry.md`
- `docs/adopted-patterns-implementation-plan.md`

## Core Decision

```txt
他アプリの良いところは採用する。
ただしUIや固有表現をコピーせず、長く使われる理由をMemory OSへ再設計する。
```

## 正式採用済みpattern

```txt
ADOPT-001 Quick Capture / Share Extension
ADOPT-002 Inbox First, Organize Later
ADOPT-003 Domain-specific Collections
ADOPT-004 Progress Tracking
ADOPT-005 Favorites / Curated Lists
ADOPT-006 Year / Month Wrap-up
ADOPT-007 On This Day with Controls
ADOPT-008 Search and Re-find First
ADOPT-009 Backlinks / Cross-source Links
ADOPT-010 Visible Collection Growth
ADOPT-011 Gentle Return after Absence
ADOPT-012 Export / Portability as Product Feature
ADOPT-013 User-controlled Resurfacing
ADOPT-014 Optional Social Sharing
```

## MVP採用順

### P0

1. Quick Capture / Share Extension
2. Inbox First
3. Domain-specific Collections
4. Manga/Anime Progress Rail
5. Food Map
6. Movie/Streaming Shelf
7. Visible Collection Growth
8. Gentle Return
9. Basic Search
10. Import PreviewからShelf Preview

### P1

1. Weekly Box
2. Month Capsule
3. Favorites / Custom Lists
4. exact Cross-source Links
5. On This Day controls
6. Export Readiness

### P2

1. Year / Seasonal Capsule
2. Memory Constellation graph
3. AI Context Pack
4. Share-safe Cards
5. Semantic Search

## Screen Structure

```txt
ホーム: Memory Room / 棚
発見: Cross-source links / Memory Constellation
振り返り: Timeline / Month-Year Capsule / On This Day
日常: Quick Add / Inbox / Progress Rail / Food Map
```

## First Visible Slice

```txt
1. Home Shelf Grid
2. 日常 Quick Add
3. Universal Paste Preview
4. Manga/Anime Progress Rail
5. Food Map list
6. Weekly Box placeholder
7. Month Capsule placeholder
```

API連携や高度なAIより先に、manual/paste fixtureでこの画面価値を証明する。

## Feature Ticket Rule

今後のticketには以下を必須化する。

```txt
Adopted pattern ID:
Visible screen change:
Collection drive:
Target persona:
Weekly/monthly return value:
Pattern-specific anti-copy note:
Safety exclusions:
```

## Adopt but Transform

### Journal/photo appsから

採用:

- date/place/sourceで見返す
- month/year/on-this-day
- private-first

変更:

- sensitive resurfacing controls必須
- AI自動感情分析なし

### Movie/book tracking appsから

採用:

- diary
- progress
- want-to-watch/read
- custom lists
- wrap-up

変更:

- public rankingなし
- quantity goalを中心にしない

### Bookmark/read-it-later appsから

採用:

- share extension
- Inbox
- full/basic search
- organize later

変更:

- 保存前のfolder/tag必須なし
- 貯めるだけで終わらず棚へ変換

### Habit/game appsから

採用:

- 小さな操作で画面が変わる
- collectionが育つ
- unlockが見える

変更:

- streakなし
- missed-day penaltyなし
- AIキャラの情緒的依存なし

### Linked note toolsから

採用:

- backlinks
- relation reason
- graph discovery

変更:

- graphはHomeにしない
- explanationできるrelationのみ
- hidden intent/personality推論なし

## No-Go

```txt
他アプリのUI/名称/animationをそのまま複製する
全部の良い機能を無秩序に混ぜる
Homeを巨大dashboardにする
graph-first home
social feed first
streak
自動AI要約ON
private memory surprise
public life ranking
```

## Product Sequence

```txt
軽く入れる
→ 媒体に合う棚で見える
→ 週/月で戻れる
→ 複数sourceがつながる
→ 探せる
→ 持ち出せる
```

## Commits

- `208f97d44095a2ba1966f841810708e667ca9f4c` docs: add adopted product patterns registry
- `0c9d796c4acfe9623f66009cd5e52fc7d446c9e2` docs: add adopted patterns implementation plan
