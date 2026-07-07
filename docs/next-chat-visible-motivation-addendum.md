# Next Chat Visible Motivation Addendum

## 目的

この文書は、`docs/next-chat-handoff.md` への追加引き継ぎである。

今回の中心は、安全設計、マネタイズ、慰めではない。

中心は、AIで楽に作れてしまう時代に、作成者本人が真面目に作る先を見失わないための、見えるワクワク設計である。

## 追加済みdocs

- `docs/founder-visible-motivation-loop.md`
- `docs/import-to-visible-reward-loop.md`
- `docs/fun-and-excitement-idea-bank.md`
- `docs/visible-excitement-and-ritual-design.md`
- `docs/memory-shelf-visualization-spec.md`
- `docs/weekly-ritual-and-daily-micro-action-spec.md`

## Core Correction

以前の「非搾取型マネタイズ」方向は、この悩みの中心ではない。

中心はこれ。

```txt
悪い依存性の方が作る側にも手応えが見えやすい。
良い依存性は未来価値すぎて、作成者に今日の報酬が見えにくい。
だから、良い依存性を今日見える棚・地図・箱・年表へ変換する。
```

## Main Product Direction

```txt
便利なImportアプリ
→ 自分の世界が見える・育つアプリ
```

```txt
AIに会いに戻る
→ 自分の棚・地図・箱・年表を見に戻る
```

```txt
いつか役に立つMemory OS
→ Importした瞬間に自分っぽさが見えるMemory OS
```

## Founder-visible Loop

```txt
fixtureを作る
→ parserが動く
→ previewが出る
→ shelfが生まれる
→ map/timeline/progressが埋まる
→ weekly actionが増える
→ 作った意味が画面で見える
```

## Implementation Rule

すべてのMVP ticketは、以下に答える。

```txt
1. このticketで、どの棚/箱/地図/年表が見えるようになるか？
2. fixtureを入れた時、画面のどこが変わるか？
3. ユーザーがImportしたくなる理由は何か？
4. 週1で戻る理由は増えるか？
5. 毎日でも触れるmicro actionは増えるか？
```

答えられないticketは、必要でもinvisible foundationとして短く切り、visible reward ticketとpairにする。

## Invisible Work Budget

```txt
2〜3個のinvisible foundation作業ごとに、1個visible reward作業を挟む。
```

Examples:

```txt
SecurityGate
ParserRegistry
Detector
→ title-list shelf preview
```

```txt
RLS tests
Migration slice
Policy tests
→ Netflix fixture to Movie/Streaming Shelf
```

## Memory Room Direction

Top-level Home should be a Memory Room, not a boring dashboard.

```txt
あなたの棚

映画棚          126件
漫画/アニメ棚    42件
音楽棚          230件
ラジオ棚         18件
食の地図         31件
写真箱           12件
会話メモ箱        4件
旅行箱            2件
```

Empty shelves should invite Import.

```txt
漫画棚はまだ空です。
「12巻まで」のように貼るだけで進行表ができます。
```

## MVP Fun Set

MVPに入れたい最小ワクワク:

1. Memory Room Home
2. Empty Shelf Cards
3. Import Preview says what shelf will be created
4. Post-import Shelf Created state
5. Manga/Anime Progress Rail
6. Food Map list by area
7. Movie/Streaming timeline
8. Weekly Box with one action
9. Last Year This Week placeholder
10. Cross-source link badge placeholder

## Weekly / Daily Core

```txt
週1で意味がある。
毎日でも少し育つ。
来なくても壊れない。
```

Weekly actions:

- 1つImportする
- 1件だけ進行を更新する
- 1件だけ重複を確認する
- 去年の今ごろを1つ見る
- 行きたい店を1つ足す

Daily micro actions:

- タイトルを1つ入れる
- URLを1つ入れる
- 漫画の巻数を1つ更新する
- 行きたい店を1つ入れる
- 重複候補を1つ確認する

No streak.

No guilt.

No AI loneliness.

## Import to Visible Reward Loop

Every medium should follow:

```txt
Empty Shelf
→ Import Prompt
→ Preview
→ Visible Reward
→ Weekly Hook
→ Next Import Suggestion
```

Examples:

```txt
Netflix CSV
→ 視聴棚
→ 年別タイムライン
→ 去年の今ごろ見ていた作品
```

```txt
漫画進行
→ 進行棚
→ 何巻/何話まで
→ 1作品だけ更新
```

```txt
食べログURL
→ 食の地図
→ 地域別list
→ 行きたい店を1つ追加
```

```txt
GERA/Podcast
→ ラジオ棚
→ 番組/エピソード
→ 今週聴きたい回を1つ入れる
```

## Developer Demo Requirement

Local demo should show before/after in under 2 minutes.

```txt
empty Memory Room
→ fixture import
→ Preview
→ shelf created
→ weekly action appears
```

This is not polish.

This is founder motivation infrastructure.

## Product North Star

```txt
ユーザーがAIに会いに来るのではなく、自分の世界を見に来る。
```

## Final Note

真面目さだけでは続かない。

安全設計だけでも続かない。

良い依存性を、作成者本人にも今日見える報酬へ変換する。

それが棚・地図・箱・年表・週の箱・daily micro actionである。
