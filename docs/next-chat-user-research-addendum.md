# Next Chat User Research Addendum

## 目的

この文書は、類似アプリの長期利用者調査、SNS/公開コミュニティ上の意見、レビュー、関連研究から得たMemory OSの利用者像と機能判断を、次チャットへ引き継ぐ。

調査時点: 2026-07-10

## 追加済みdocs

- `docs/long-term-user-research-synthesis.md`
- `docs/persona-feature-fit-matrix.md`
- `docs/retention-resurfacing-and-notification-policy.md`
- `docs/similar-app-evidence-and-feature-map.md`

## 調査対象

- Day One / Journey / Daylio / DailyBean
- 1 Second Everyday
- Google Photos / Apple Photos Memories
- Letterboxd
- StoryGraph / Goodreads / Bookly / Bookmory
- Raindrop.io / Pocket / Instapaper / Readwise Reader / Pinboard
- Finch / Habitica / Streaks系
- personal information management / self-tracking / long-term archiving研究

## 最重要発見

### 1. 年齢より利用動機でpersonaを分ける

```txt
Collector / Curator
Progress Tracker
Lightweight Capturer
Nostalgia Reflector
Family / Event Archivist
Practical Re-finder
AI Portability Power User
Lapsed / Returning User
Sensitive Control-first User
Social Taste Sharer
```

同じ人が時期によって複数personaを行き来する。

### 2. 長期利用は毎日連続ではない

ユーザーは数週間〜数カ月離れ、目的が再発した時に戻る。

Memory OSはsingle continuous habitではなく、multiple livesを前提にする。

```txt
旅行前
新しい趣味
結婚式/イベント
年末
AI乗り換え
昔の記録を探す時
```

### 3. 軽い入力だけでは足りない

長く使われるには、入力後に以下が返る必要がある。

```txt
Search
Shelf
Timeline
Map
Progress
Month/Year Capsule
Safe Resurfacing
```

### 4. 件数よりdomain meaning

```txt
126 memories
```

より、

```txt
映画126本、去年の今ごろ4本
漫画42作品、進行未更新3件
食の地図31店、横浜8店
```

の方が意味がある。

### 5. Nostalgiaは強いが危険

Google/Apple系の自動Memoriesは魅力がある一方、元恋人、故人、病気、喪失、見たくない期間を出す事故がある。

必要:

- shelf/source/person/date/period除外
- 今は見せない
- restricted/hidden/sealed default除外
- product notification opt-in

### 6. streakは採用しない

Streakは行動を強く変えるが、本来の目的を数字維持へ置き換える。

不採用:

- daily streak
- missed-day count
- daily completion percentage
- record goal

### 7. 週1より月1が特別報酬に向く

Weekly:

- 今週増えた棚
- 先週保存した続き
- 進行更新
- duplicate1件

Monthly:

- Month Capsule
- shelf growth
- timeline/map
- Last Year This Week
- Export readiness

### 8. 「1週間前なにしてた」は中心機能にしない

理由:

- 近すぎる
- 驚きが弱い
- 記録がない週に弱い
- private recap事故

代わりに:

```txt
先週保存した続きを見る
今週棚で変わったものを見る
1件だけ整える
```

## Persona別の中心機能

| Persona | Core features | Avoid |
|---|---|---|
| Collector | shelves, favorites, capsules, cross-source | public ranking |
| Progress | progress rail, quick update | daily total score |
| Lightweight | share extension, Inbox | required folders/tags |
| Nostalgia | capsule, last year, timeline | surprise sensitive memories |
| Family/Event | event box, map, safe photo metadata | relationship analysis |
| Re-finder | search, filters, source/date | graph-first home |
| AI Power | context pack, versioned export | all-history AI upload |
| Returning | guilt-free restart | missed-day/streak |
| Sensitive | exclusions, seal, analysis off | automatic reflection |
| Social Taste | safe list/share card | DM/infinite feed |

## Notification Policy

### Operational

採用:

- Import Preview ready
- Export expiry
- backup result
- OAuth reconnect
- security/account
- user-set reminder

### Product Value

opt-in:

- Month Capsule ready
- safe Last Year This Week
- cross-source connection

### Engagement-only

不採用:

- 最近開いていません
- 今週まだ記録していません
- streakが切れます
- 1週間前を振り返りませんか、だけの通知

## MVPへの反映

P0:

1. One-tap/manual/paste Import
2. Import Preview
3. visible shelf creation
4. Manga/Anime Progress Rail
5. Food Map
6. Movie/Streaming Timeline
7. search/source/date filters
8. hide/seal/exclude
9. standard Export
10. guilt-free return

P1:

1. Weekly Box
2. Month Capsule
3. Last Year This Week
4. cross-source link
5. one-item cleanup
6. safe share card

P2:

1. constellation graph
2. advanced stats
3. custom shelves
4. social collection sharing
5. AI Context Pack

## Product Statement

```txt
Memory OSは、毎日入力させる日記でも、何でも保存する倉庫でもない。

軽く取り込み、自分の棚として見え、必要な時に再発見でき、空白があっても戻れる場所である。
```

## Research Limitations

- 公開SNS/コミュニティ意見は全利用者を代表しない。
- 強い肯定/不満が投稿されやすい。
- Reddit全文を安定取得できなかったため、検索で公開された議論、SNS利用者への取材記事、review aggregation、academic researchを組み合わせた。
- 実装後はMemory OS独自のuser interview / diary study / cohort dataが必要。

## Next Recommended Research

1. 5〜8人へのconcept interview
2. 2週間のdiary study
3. Empty Shelf → First Import prototype test
4. Month Capsule vs Weekly Box比較
5. Notification opt-in率と嫌悪理由
6. 3カ月離脱後のreturn flow test

## Last Commits

- `030d1c98e36dbd1480fc542d88542aa921b8e63b` docs: add long term similar app user research synthesis
- `b1408c2d4d0ae2e0dc1a13301c004b2ae22d6eec` docs: add persona feature fit matrix
- `a1ed2d1a993f65fd31f27be148157cf461780532` docs: add retention resurfacing and notification policy
- `9bac2069c37f9582208bf6cba4d2687a379da4f5` docs: add similar app evidence and feature map
