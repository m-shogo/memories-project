# Memory Town Affection-centered Visual Design Contract — Round 6

最終更新: 2026-07-14

## 目的

Memory Townのデザインを、単に可愛い・高品質な背景ではなく、保存した記憶へ長期的な愛着を持てる視覚体験として定義する。

```txt
Memory is the product.
Town is the visible side effect.
Affection is the long-term result.
```

町のデザインは、記憶を水増しさせる報酬装置ではない。

```txt
残した記憶が自分の棚になる
→ 同じ場所へ少しずつ痕跡が増える
→ 数か月・数年後に「自分の町だ」と分かる
```

実装はまだ開始しない。

---

# 1. 愛着を作る6原則

## 1.1 Continuity — 同じ場所が続いている

愛着は、毎回別の綺麗な画像を見ることではなく、同じ場所へ変化が積み重なることで生まれる。

必須:

- camera angleと主要landmarkを維持する
- layout migration後も町の骨格を保つ
- 建物stageが変わっても入口・位置・意味を維持する
- 季節変更で町全体を別世界へ交換しない
- asset更新でユーザーが知っているsilhouetteを突然失わせない
- 古い町のPostcardから現在の町へ連続性を感じられる

禁止:

- 毎回AI生成し直す町
- 季節ごとに別mapへ見える全面交換
- trendに合わせた頻繁なart style変更
- version updateで建物位置や色を理由なく変更

## 1.2 Recognition — 一目で自分の町だと分かる

個性は大量の家具ではなく、少数の反復される印で作る。

初期候補:

- Memory Treeの形と成長段階
- 選択したStyle Pack
- 各districtのPersonal Display Slot
- 港・海岸・中央広場の配置関係
- 建物ごとの灯り
- user-selected accent色
- private Postcardの時間・季節履歴

Rules:

- 1 districtにつき主役となるpersonal cueは1つを基本とする
- private titleや人物名を町へ自動掲示しない
- AIが「あなたらしさ」を推測して装飾を決めない
- personalization OFFでも完成された町に見える

## 1.3 Memory Causality — 記憶とのつながりが分かる

町の変化は、Memory OS上の何と結びついているか説明できる。

例:

```txt
映画棚 → 映画館
漫画・アニメ進行 → 物語館
食の記録 → 市場
旅行箱 → 港
Month Capsule → 中央広場
保存量の粗い積み重ね → 四季樹
```

ただし、次stageまでの件数や成長meterは表示しない。

正しい見せ方:

- 保存後に棚への反映を先に表示
- optionalな小さい光が対応buildingへ入る
- 建物cardから対応棚へ戻れる
- 成長理由は「記録が積み重なりました」程度の粗い説明

誤った見せ方:

- あと3件で成長
- XP獲得
- 記録価値の点数化
- 感情や重要度に応じた建物格差

## 1.4 Craft Quality — 丁寧に作られた一つの世界

愛着はasset量より、全assetが同じ世界に属して見えることで生まれる。

固定するvisual grammar:

- fixed-view 2.5D
- high-resolution dot styleを第一候補
- 同一の光源方向
- 同一のcontact shadow logic
- 建物classごとのscale range
- 彩度上限と明度階層
- 木、紙、石、砂、水のmaterial language
- 輪郭線の太さとsoftness
- animation amplitudeの上限
- texture noise量

禁止:

- assetごとにpixel密度が異なる
- AI生成assetを無修正で混在させる
- 建物ごとに光源方向が違う
- 季節overlayで元の識別色を失う
- generic asset packの寄せ集め
- 過度なblur、bloom、ネオン

## 1.5 Quiet Life — 静かな生活感

町は常に動いている必要はない。

P0:

- 雲
- 波
- 四季樹の小さな揺れ
- 建物灯り
- 海面反射

P1:

- 海鳥
- 蝶
- 魚影
- 小さなカニ
- 遠景の船

Rules:

- 同時に目立つ動きは最大2〜3箇所を候補とする
- ambient motionは操作を奪わない
- motion offでも同じ町の魅力が残る
- 小動物は世話・好感度・名前を持たない
- inactivityへ反応しない

## 1.6 Imperfect Warmth — 少しだけ人の手を感じる

完全な幾何学的均一さは、管理画面には適するが愛着を弱める。

候補:

- 木材や紙の小さな色揺らぎ
- 看板のわずかな傾き
- 草花の非対称配置
- 波や雲のゆっくりした位相差
- 建物ごとの小さな生活痕跡

ただし、壊れ・汚れ・放置・荒廃へ見せない。

---

# 2. Visual hierarchy

町を開いた最初の3秒で、次の順に読めることを目標にする。

```txt
1. 今の時間と季節
2. Memory Treeと中央広場
3. 主要building 5〜6個
4. 海岸・港など町の地形
5. 個人化された小さな印
6. ambient detail
```

小物、particle、badgeが主要buildingより先に目へ入る状態は失敗。

## Hero landmarks

初期のhero landmark候補:

1. Memory Tree
2. 中央広場
3. 港とビーチ

同時にすべてを強調しない。viewport、時間、選択状態に応じて主役を一つに絞る。

---

# 3. Growth design

成長は単なる大型化ではなく、同じ建物へ意味のある層が増えること。

```txt
Stage 0
小さいが機能と将来性が分かる

Stage 1
町へ根付いた形

Stage 2
そのdistrictのlandmark
```

良い成長差分:

- silhouetteが明確に豊かになる
- 灯りや入口が増える
- 周囲にderived micro-detailが生まれる
- 対応する棚の性質が建物に表れる
- 旧stageの面影が残る

避ける:

- 単純な縦横拡大
- 金色・宝石・王冠による価値格付け
- Stage 0を空き地、失敗、未完成として描く
- Stage 2だけ極端に豪華
- 成長で海岸・道路・Memory Treeを隠す

---

# 4. Color and light

## Base palette

土台は次を中心とする。

- warm white / 生成り
- natural wood
- muted green
- clear blue
- sand
- soft gray / silver accent

建物識別色は持つが、町全体の彩度帯を揃える。

## Time modes

```txt
morning
暖かい低角度光。新鮮だが眩しすぎない。

day
最も読みやすいneutral light。

night
深い青＋暖かな窓灯り。

midnight
月光と星。夜より静かだが孤独・罰にしない。
```

## Contrast

- UI contrastはscene paletteへ依存しない
- dark sceneでもbuilding silhouetteを失わない
- lighting overlayでasset固有色を塗り潰さない
- color vision deficiencyでもfeature識別を色だけに頼らない

---

# 5. Seasonal identity

四季は同じ町が一年を過ごしていると感じさせる。

```txt
春
桜motif、淡い草、小さい花

夏
深い緑、明るい水面、木陰

秋
モミジmotif、暖色地面、少量の落ち葉

冬
枝、薄い雪、冬草、暖かな灯り
```

必須:

- particleなしでも季節が分かる
- buildingの基本silhouetteを維持する
- 冬を枯死・失敗・放置にしない
- seasonal propがtap targetを隠さない
- 同じpersonal cueを四季で維持する

---

# 6. Personalization without clutter

個性化は段階的に解放する。

```txt
Phase A
Style Pack / accent color

Phase B
Personal Display Slot

Phase C
safe decoration slots

Phase D
zone内の木・花・家具

Phase E
道・植栽・建物移動
```

Rules:

- 初期状態も完成されて見える
- 変更前Preview必須
- Undo / Draft Townを提供
- personal cueは町全体へ大量反復しない
- auto beautifyはuser objectを移動・削除しない
- blank optionを必ず用意する

---

# 7. Affection safety

愛着は依存誘導に変えない。

禁止:

- 町や小動物が寂しがる
- 不在で暗くなる、荒れる、枯れる
- 戻ってきた日数を強調する
- 限定装飾の取り逃し
- 町を守るための通知
- Town visit streak
- キャラクターからの情緒的圧力
- 「あなたが来ないと困る」表現

許可:

- 同じ場所が静かに残っている
- 季節が自然に変わる
- 過去の町を自分で見返す
- 記憶を保存した結果として小さく反応する
- userが選んだ装飾が長く残る

---

# 8. Prototype variants

デザイン方向は文章だけで承認しない。

## Art style

```txt
A. strict pixel art
B. high-resolution dot illustration
C. soft miniature illustration
```

現推奨はB。ただしA/B/Cを同じmap、同じbuilding、同じviewportで比較する。

## Affection test scenes

```txt
A0 初回・記録0件・春昼
A1 3か月後・Stage 1・夏夜
A2 2年後・Stage 2・秋夜
A3 冬夜中・motion off
A4 Personal Display ON / OFF
A5 Style Pack 3案
A6 Postcard: same town across four times
A7 Maximum density
A8 Town OFF / DOM list equivalent
```

---

# 9. Design acceptance gates

## AD-1 World consistency

- perspective、scale、shadow、light directionが統一
- asset単体ではなくscene全体で違和感がない
- missing asset fallbackも同じ世界に見える

## AD-2 Recognition

- 主要buildingを5秒以内に区別できる候補
- labels OFFでもsilhouette差がある
- labels ONで意味を確定できる
- 3つの町候補から自分のpersonal cueを識別できる

## AD-3 Continuity

- Stage 0→2で同じ建物と認識できる
- 春→冬で同じ町と認識できる
- versioned asset更新前後でlandmark continuityを維持

## AD-4 Emotional quality

- 記録0件でも完成された静かな場所
- 冬・夜中でも孤独や罰に見えない
- 町が記憶を入れる義務を要求して見えない
- AI生成の無個性な背景に見えない

## AD-5 Memory-first hierarchy

- 保存確認がTown animationより強い
- Town OFFでも主要utilityが同一
- 町の見た目だけを目的としたmandatory captureがない
- visual reactionはnon-blocking、skip可能

## AD-6 Responsive and accessible

- six mobile viewports
- 200% text zoom
- motion off / reduced motion
- colorだけに依存しない
- DOM list / layered fallbackでも世界観と機能を維持

---

# 10. Art production rule

生成AIをasset ideationに使う場合も、完成assetとして自動採用しない。

必須工程:

```txt
art brief
→ rough candidates
→ silhouette review
→ perspective / light correction
→ palette normalization
→ footprint / anchor verification
→ human cleanup
→ scene composite review
→ provenance / license record
→ approval
```

禁止:

- prompt出力を無検査でproductionへ入れる
- 他作品固有assetに似たcandidateを採用する
- assetごとに異なる生成styleを混ぜる
- provenance不明assetを使う

---

# Decision

```txt
愛着は、派手な報酬ではなく、
同じ場所が長く続き、
自分の記憶の痕跡が静かに増え、
数か月後も数年後も「自分の町だ」と分かることで作る。

そのため、デザイン品質は副次機能ではなく、
Memory-first体験を成立させる製品要件である。
```
