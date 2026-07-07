# Visible Excitement and Ritual Design

## 目的

この文書は、Memory OS の「良い利便性」と「良い依存性」を、ユーザーにも開発者にも見える形へ落とすための設計である。

今の課題は、慰めではない。

根本的な問題は、良い依存性が未来価値すぎて、開発中に手応えが見えにくいこと。

悪い依存性は見えやすい。

- AIキャラが優しい
- 否定しない
- 恋人関係が進む
- 結婚も受ける
- 毎日話したくなる
- 滞在時間が伸びる

これは作成者にも効いている感がすぐ見える。

一方、Memory OSの良い依存性は、放っておくとこうなる。

- 5年後に効く
- AIを乗り換えた時に効く
- 記録が積み上がった時に効く
- 失った時に価値が分かる

これでは開発のモチベーションが続きにくい。

だから、未来型の良い依存性を、今日見える体験に変換する。

## Core Shift

```txt
便利なImportアプリ
→ 自分の世界が見える・育つアプリ
```

```txt
AIに会いに戻る
→ 自分の棚・地図・年表を見に戻る
```

```txt
いつか役に立つMemory OS
→ Importした瞬間に自分っぽさが見えるMemory OS
```

## Product Emotion Target

ユーザーに持ってほしい感情:

- 入れたら見えた
- もっと入れたい
- これ俺っぽい
- 棚が育ってる
- 地図が埋まってきた
- 週1で見たくなる
- 時々ふと戻りたくなる
- 消したくない
- 他のAIにも持っていきたい

開発者が持てる手応え:

- fixtureを入れると棚が増える
- parserを作ると部屋が埋まる
- adapterを作ると別ジャンルの世界が開く
- Importが成功するとUIが変わる
- 件数ではなく「自分の世界」が増える

## Good Dependency Loop

```txt
Importする
→ 棚/地図/箱ができる
→ 自分っぽさが見える
→ もう少し埋めたくなる
→ 週1で見返す
→ 次のImportがしたくなる
```

このループは、AIキャラへの依存ではなく、自分の蓄積への愛着である。

## Weekly Hook

週1でも戻りたくなる中心体験。

### Weekly Memory Room

毎週1回、ユーザーが開くと以下が見える。

```txt
今週増えた棚
今週見返された記録
まだ空いている棚
去年の今ごろの棚
次にImportすると広がる場所
```

### Weekly One Action

週1で1つだけやればよい軽い行動。

- 1つImportする
- 1件だけ直す
- 1つ棚を見る
- 1つ行きたい店を追加する
- 1つ見たい作品を追加する
- 1つ古い記録を開く
- 1つExport readinessを確認する

Copy:

```txt
今週は1つだけ棚を増やせます。
```

```txt
1件だけ追加して、今週の箱を閉じられます。
```

Avoid:

```txt
今週も来ないと記憶が薄れます。
```

```txt
連続記録が途切れます。
```

## Daily Optional Hook

毎日でも可能だが、毎日を強制しない。

Daily micro-actions:

- 今日見たものを1つ入れる
- 今日聴いたものを1つ入れる
- 今日行きたい店を1つ入れる
- 最近の棚を眺める
- 1件だけタイトルを直す
- 1つだけ重複を確認する
- 1つだけ「あとで見る」に入れる

Principle:

```txt
毎日来ると少し育つ。
来なくても何も壊れない。
```

## Import Motivation Pattern

### Empty State

Bad:

```txt
まだ記録がありません。
```

Better:

```txt
映画棚はまだ空です。
NetflixやFilmarksを入れると、見た作品の棚ができます。
```

```txt
食の地図はまだ空です。
食べログのURLを貼ると、行きたい店の地図ができます。
```

```txt
漫画棚はまだ空です。
「12巻まで」のように貼るだけで進行表ができます。
```

### Before / After Preview

Before Import:

```txt
このImportで作れるもの
- 映画棚
- 2026年の視聴年表
- 重複候補
- 見たい/見たの整理
```

After Import:

```txt
映画棚ができました
126件 / 4年分 / 3件の重複候補 / 12件の見たい作品
```

### Next Import Suggestion

Allowed:

```txt
映画棚にFilmarksを足すと、評価や見たい作品も並べられます。
```

```txt
食の地図に食べログURLを足すと、行きたい店を地域別に見られます。
```

Avoid:

```txt
もっと入れないとあなたの記憶は不完全です。
```

## Visible Reward Types

```ts
type VisibleRewardType =
  | 'new_shelf_created'
  | 'shelf_filled'
  | 'timeline_unlocked'
  | 'map_region_added'
  | 'cross_source_link_found'
  | 'progress_track_created'
  | 'weekly_box_closed'
  | 'old_period_revealed'
  | 'export_readiness_improved'
  | 'duplicate_cleaned';
```

Examples:

- Netflix CSV → new_shelf_created: 視聴棚
- 食べログ URL → map_region_added: 食の地図
- 漫画進行 → progress_track_created: 進行棚
- Spotify + Last.fm → cross_source_link_found: 同じ曲の記録がつながる
- LINE snippet → weekly_box_closed: 安全な会話メモ箱

## Good Dependency Metrics

Measure:

- weekly_shelf_visits
- imports_started_from_empty_state
- imports_completed_after_preview
- shelves_created
- shelf_return_rate
- weekly_one_action_completion
- user_corrections
- cross_source_links_confirmed
- export_readiness_views
- user-initiated reflections

Do not optimize:

- compulsive chat length
- romantic escalation
- loneliness notification conversion
- late-night retention
- daily streak pressure
- user distress on absence

## Product North Star

```txt
ユーザーがAIに会いに来るのではなく、自分の世界を見に来る。
```

## MVP Implication

MVPは「Importできる」だけでは足りない。

最低限、Import後に以下が見える必要がある。

- 棚ができた
- 件数が入った
- 時期が見えた
- 次に何を入れると広がるか見えた
- 週1で見る理由ができた

## 結論

Memory OSの開発モチベーション問題は、思想不足ではなく、良い依存性の可視化不足である。

悪い依存性は即時に見える。

良い依存性も、棚・地図・箱・年表・進行表として即時に見える形へ落とす。

これにより、ユーザーだけでなく作成者本人も「先が見える」状態になる。
