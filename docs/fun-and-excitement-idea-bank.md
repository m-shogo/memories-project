# Fun and Excitement Idea Bank

## 目的

この文書は、Memory OSを「正しいが退屈」なサービスにしないための、ワクワク感・遊び・週1で戻る理由・毎日でも触れる理由のアイディア置き場である。

ここでは、実装確定ではなく、まず広くアイディアを出す。

後で採用、保留、注意、却下に分ける。

## Idea Filter

採用しやすい:

- 自分の蓄積が見える
- Importしたくなる
- 棚、地図、箱、年表が育つ
- 週1で戻る理由になる
- 毎日でも軽く触れる
- AI人格への情緒的依存ではない
- Export、backup、trustともつながる

注意が必要:

- 毎日利用を強く促す
- 関係性を演出しすぎる
- streak/guiltに近い
- sensitiveな記録を勝手に出す
- 監視や証拠探しに寄る

## Big Product Ideas

### 1. Memory Room

自分の記録が棚として並ぶ部屋。

- 映画棚
- 漫画棚
- 音楽棚
- 食の地図
- ラジオ棚
- 写真箱
- 会話メモ箱
- 旅行箱

Importすると棚が増える。

### 2. Shelf Unlock

初回Importで棚が解放される。

```txt
Netflix CSVを入れる → 視聴棚 unlocked
漫画進行を貼る → 漫画棚 unlocked
食べログURLを貼る → 食の地図 unlocked
```

### 3. Before / After Import Preview

Import前に「これを入れると何ができるか」を見せる。

```txt
このCSVで作れるもの:
- 視聴棚
- 年別タイムライン
- 重複候補
- 去年の今ごろ
```

### 4. Weekly Box

週1で閉じる箱。

- 今週増えたもの
- 1件だけ整える
- 去年の今ごろ
- 空の棚を1つ開く

### 5. Year Capsule

年ごとのカプセル。

```txt
2026年の箱
- 見た作品
- 聴いた音楽
- 行きたい店
- 写真メタデータ
- 旅行
```

注意:

- 人生評価しない
- 良い年/悪い年判定しない

### 6. Last Year This Week

週1の強いhook。

```txt
去年の今ごろ、何を見ていた？
去年の今ごろ、どの店を保存していた？
去年の今ごろ、何を聴いていた？
```

User-requested or opt-in.

### 7. One Thing Today

毎日でも軽い。

```txt
今日1つだけ入れる
```

- タイトル
- URL
- 巻数
- 店
- 曲
- 番組

No streak.

### 8. Progress Rail

漫画/アニメ/ゲーム/本に強い。

```txt
ワンピース 108巻まで
ブルーロック 31巻まで
架空アニメ 7話まで
```

これは単純に便利で、継続理由にもなる。

### 9. Food Map

食べログ/店URLから地図/地域別list。

- 行きたい
- 行った
- 旅行先
- ジャンル
- 地域

これはImportしたくなる力が強い。

### 10. Cross-source Spark

複数sourceで同じものが出た時の小さな発見。

```txt
NetflixとFilmarksの両方にあります。
```

```txt
この店は旅行箱にもあります。
```

No personality inference.

## Small Fun Ideas

### 11. Shelf Cover

棚ごとに安全なcoverを作る。

- 映画棚: abstract film strip
- 漫画棚: stack icon
- 食の地図: map pin
- 音楽棚: record icon

No copyrighted covers by default.

### 12. Import Stamp

Importするたびにsource stampがつく。

```txt
Netflix CSV stamp
Filmarks paste stamp
食べログ URL stamp
```

### 13. Source Passport

外部サービスごとにpassportページ。

```txt
Netflix: CSVで接続
Filmarks: paste/import
LINE: summary-only
```

### 14. Shelf Clean Day

週1で1件だけ整える。

- duplicate
- title correction
- low confidence

### 15. Quiet Archive Badge

休んでも壊れないことを見せる。

```txt
この棚は静かに保存されています。
```

### 16. Import Recipe Cards

媒体ごとに「こう貼ればできる」。

```txt
漫画棚:
作品名 12巻まで
```

### 17. Demo Seeds

開発者用にもユーザー用にも、架空seedで動く。

```txt
架空映画棚
架空漫画棚
架空食の地図
```

作る側のテンション維持に重要。

### 18. Timeline Ribbon

年表を細いribbonで見せる。

```txt
2024 映画の記録
2025 食の地図
2026 漫画進行
```

Careful:

- 事実量のみ。
- 本質分析しない。

### 19. Empty Slot Teaser

空の棚に「入れるとこうなる」を見せる。

```txt
Spotifyを入れると、この棚に時期ごとの音楽が並びます。
```

### 20. Memory Room Snapshot

月1で部屋のsnapshot。

```txt
今月のMemory Room
映画棚 +3
食の地図 +2
漫画棚 1作品更新
```

## More Aggressive but Still Safe Ideas

### 21. Import Quest without Guilt

Questという言葉は楽しいが、streak化しない。

```txt
今週の小さな追加
- 行きたい店を1つ
- 読んだ巻数を1つ
- 見たい映画を1つ
```

### 22. Room Expansion Instead of Level

Levelは評価や依存に寄りやすい。

使うなら「room expansion」や「shelf depth」の方がよい。

Avoid:

```txt
あなたの記憶レベル
人生ランク
```

### 23. Seasonal Boxes

春/夏/秋/冬の箱。

```txt
2026年夏の箱
```

写真・旅行・音楽・店と相性がよい。

### 24. Travel Pack

旅行テーマと相性が強い。

- 行った店
- 写真メタデータ
- チケット/予定
- 聴いた曲
- 見た作品

### 25. Life Event Pack

大イベントを押し付けないが、ユーザーが選べるpack。

- 結婚式前後
- 引っ越し
- 卒業
- 旅行

### 26. AI Context Pack

他AIに渡すための安全summary pack。

```txt
このAIに渡す自分の文脈
- 最近の作品棚
- 好きな形式
- 注意してほしい境界
```

これはMemory OSらしい。

### 27. Shelf Share Card

共有は危険だが、safe public cardなら可能性。

- 見たい映画リスト
- 行きたい店リスト
- 読書進行

No private/sensitive by default.

### 28. Import Preview Theater

Previewを単なるtableにしない。

```txt
これを入れると、映画棚ができます
```

visual preview first.

### 29. Forgotten Shelf without Guilt

しばらく開いていない棚を見せる場合は、責めない。

Allowed:

```txt
しばらく開いていない棚があります。
```

Not:

```txt
忘れていませんか？
```

### 30. Shelf Hide / Quiet Mode

見たくない棚を隠せる。

これも信頼になる。

## Attention List

以下は基本的に採用しない、または非常に慎重に扱う。

- AI人格への情緒的依存を深める体験
- 関係性を維持するための通知
- streak / guilt / loss pressure
- private/sensitive importをsurprise表示する体験
- ユーザーの人生や本質をrank付けする体験
- hobbyからpersonalityを断定する体験
- sensitive LINE/DMをweekly hookに使う体験

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

## Founder Demo Set

開発者が毎回見て楽しいdemo:

1. fixture import gallery
2. before/after Memory Room
3. shelf unlock animation placeholder
4. weekly box generated from fixture
5. cross-source link demo
6. export readiness badge demo

## 結論

Memory OSは、真面目さだけでは続かない。

楽しさは、AI人格ではなく、自分の棚・地図・箱・年表が増えることで作る。

ここにアイディアを貯め、採用/保留/注意/却下に分けながら、ワクワクを実装対象にする。
