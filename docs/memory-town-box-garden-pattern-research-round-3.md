# Memory Town Box-Garden Pattern Research — Round 3

最終更新: 2026-07-14

## 目的

Memory Townに不足している体験を、既存の箱庭・ジオラマ・生活シミュレーション・配置ゲームから抽出する。

固有UI、固有キャラクター、固有アート、経済設計をコピーしない。
採用するのは、長期利用、愛着、配置の気持ちよさ、眺める価値、戻りやすさを生む設計原理だけとする。

実装はまだ開始しない。

---

# 1. 調査対象

## Animal Crossing: New Horizons

参照:
- The Verge, 2025-12-16, "I've been waiting years for Animal Crossing's best new features"
- The Verge, 2026-01-19, "Animal Crossing: New Horizons added just enough to suck me back in"

観察:
- 本番の島を壊さず試せるSlumber Island
- 時間帯・天候を変えてデザイン確認
- 区画単位のReset Service
- 置き直し、terraform、素材管理の摩擦が長期的な離脱要因になる

抽出する原理:

```txt
canonical townを直接壊さず、draft空間で試す
大きな編集は区画単位でReset / Preview可能
見た目の自由度より編集摩擦の低さを優先
```

コピーしない:
- 日課
- 住宅ローン・通貨
- 素材集め
- 住人好感度
- 期間限定FOMO

## Townscaper

参照:
- Townscaper gameplay description and Oskar Stålberg's rule-based construction approach

観察:
- ユーザーは単純な配置しかしていないのに、ルールが塔、階段、庭、アーチなどを自動生成する
- 失敗しにくく、少ない操作で完成度が出る
- 目的や点数がなくても、操作自体が気持ちよい

抽出する原理:

```txt
配置データ
→ deterministic adjacency rules
→ 小さな美観detailを自動生成
```

Memory Town候補:
- 建物と道の間に小さな植栽
- 水路を道が横切るとbridge visual
- 隣接した街灯が同じ方向を向く
- 建物同士の隙間に花壇や物干しではなく、Memory Town向けの旗・ベンチ・低木
- 港とビーチの境界に木道

重要:
自動detailはderived render stateとし、user placement objectの正本にしない。

## Tiny Glade

参照:
- Tiny Glade gameplay and development descriptions
- procedural doors, windows, benches, pots, stairs and bridge behavior

観察:
- 建築の細部をユーザーへ全部操作させず、形状に応じて自然なdetailが付く
- 道、水、壁の関係をシステムが美しく解釈する
- 削除しても壊れた状態ではなく、別の自然な形へ戻る

抽出する原理:

```txt
ユーザーは大きな意図を決める
システムは小さな完成処理を行う
```

Memory Town候補:
- decoration slotを埋めなくても最低限整って見える
- stage変更時に窓・看板・植栽を自動調整
- user objectを消さず、derived detailだけを再計算

## Summerhouse

参照:
- The Guardian, 2024-03-13
- Summerhouse feature descriptions

観察:
- 小さなジオラマを眺める価値
- 時間・天候の切替で同じ場所を何度も見直せる
- 特定の組合せにより、キャラクターやanimationがひっそり現れる
- 点数や明示タスクではなく、偶然の発見として進行する
- 町が過去の記憶を連想させる媒体になる

抽出する原理:

```txt
quiet surprise
= 見つけなくても困らない、小さな変化
```

Memory Town候補:
- 春の朝だけ海辺に鳥
- 秋の夜だけ映画館前に落ち葉の渦
- 市場と広場が隣接すると小さな旗
- 旅行箱がある時だけ港に遠景の船

禁止:
- 見逃し損失
- 限定報酬
- 発見数コンプリート率

## Dorfromantik

参照:
- creative mode
- tile adjacency
- biomes and visual tile unlocks

観察:
- 隣接する地形の連続性が景観を作る
- 小さなtileの追加が、全体の景色を少しずつ変える
- creative modeでは点数・有限資源から切り離せる
- 新しいbiomeやvisual tileが長期変化になる

抽出する原理:

```txt
単体objectではなく、隣接関係で地区の空気を作る
```

Memory Town候補:
- 映画館周辺は夜の灯りが少し強い文化地区
- 市場周辺は布・花・食の色が集まる
- 港周辺は木道・ロープ・海風
- 物語館周辺は本・紙・小さな庭

コピーしない:
- tile score
- exact matching bonus
- 閉じた地形の得点

## ISLANDERS / ISLANDERS: New Shores

参照:
- minimalist island building
- compact island composition
- New Shores photo mode

観察:
- 小さな島と限られた視界は、巨大mapより愛着を作りやすい
- 建物同士の相性が配置判断を生む
- photo modeは完成物を眺め、残す理由になる

抽出する原理:

```txt
配置相性は点数ではなくvisual synergyへ変換する
```

Memory Town候補:
- 港とビーチで木道detail
- 市場と広場で屋台旗
- 映画館と夜で看板灯
- 四季樹とベンチで木陰detail

採用候補:
- private postcard mode
- 季節・時間・stageを含むTown snapshot
- social feedなし

## Gourdlets

参照:
- Polygon, 2024-08-15

観察:
- 通貨、資源、病気、火事、失敗状態を排除している
- 住人は配置に不満を持たず、眺める生活感を作る
- 短いtutorialで即座に作り始められる

抽出する原理:

```txt
personalizationにeconomyを持ち込まない
ambient lifeは評価者にしない
```

Memory Town候補:
- decorationは通貨購入ではない
- generic animalは町を評価しない
- 不適切配置でも悲しむ、去る、病気になる演出なし

## Cozy Grove

参照:
- real-time daily structure
- daily task loop

観察:
- 現実時間に沿う島は長期変化を感じやすい
- 一方、毎日のtaskや30〜40分前提のloopは義務化しやすい

採用する:
- 現実時間による環境変化
- 長期間で少しずつ変わる場所

採用しない:
- daily task quota
- 今日やらないと失う進行
- 連続訪問前提
- 未完了task backlog

## Unpacking

参照:
- wordless environmental storytelling through personal objects

観察:
- 人物説明を直接書かなくても、選ばれた物と置かれた場所が物語を生む
- 少数の具体物が空間へ個人性を与える

抽出する原理:

```txt
一つのuser-selected objectが、百個の自動装飾より個人性を持つ
```

Memory Town候補:
- 各主要建物にPersonal Display Slotを1つ
- ユーザーが色、象徴物、汎用アイコンを選ぶ
- private titleや人物名を自動表示しない
- AIが「最も重要な思い出」を選ばない

## MemoryDiorama research

参照:
- Ihara et al., 2026, "MemoryDiorama: Generating Dynamic 3D Diorama from Everyday Photos for Memory Recall"

観察:
- 日常写真を動的ジオラマ化した条件は、静止写真・静止ジオラマより、想起時の内的詳細や知覚的詳細を増やしたと報告されている

Memory Townへの意味:
- 動きのある小さなsceneは、単なる装飾でなく記憶想起cueになり得る

将来研究候補:
- ユーザーが明示的に選んだ写真だけを使う
- on-demandで一時的なMemory Windowを生成
- 保存時自動分析には使わない
- private local processing / explicit preview / deletionを必須にする

初期採用しない理由:
- 生成品質
- privacy
- asset cost
- 誤ったscene補完
- 本人・他人の人物表現リスク

## GardenDesigner research

参照:
- Li et al., 2026, "GardenDesigner: Encoding Aesthetic Principles into Jiangnan Garden Construction via a Chain of Agents"

観察:
- 水、道、asset配置を別工程として扱い、美的制約に沿って配置する
- layoutとfurnishingを分けると、非専門家でも整った空間を作りやすい

Memory Townへの意味:

```txt
layout skeleton
→ path / water
→ landmark
→ structures
→ furnishing
→ ambient detail
```

この順を守り、装飾を先に置いて町を詰まらせない。

---

# 2. 現在のMemory Townに不足しているもの

## GAP-01 町が自動で整うrule layer

現在はobject catalog、layout、Growth Envelopeはあるが、隣接関係から美観detailを導出する契約がない。

必要:
- derived micro-detail rules
- deterministic
- reversible
- privacy neutral
- user object非破壊

## GAP-02 本番を壊さず試すDraft Town

previewは時間・季節確認中心で、将来の配置変更を試す独立draftが弱い。

必要:
- canonical layoutからcopy-on-write draft
- Saveまで正本を変更しない
- season / time / stage / theme preview
- discard / compare / apply

## GAP-03 写真として残すTown history

町は育つが、過去の姿を安全に残す契約が弱い。

必要:
- private postcard
- manual capture default
- milestone capture suggestion opt-in
- raw memoryなし
- Town state versionsのみ
- export / delete可能

## GAP-04 空白を埋めるambient inhabitants

雲・波・木はあるが、町の大きさを変えず生活感を作る小動物が未定義。

必要候補:
- 鳥
- 蝶
- 魚影
- 猫または犬ではなく、identityを持たない小動物候補
- 港のカモメ
- ビーチの小さなカニ

禁止:
- 名前
- 好感度
- 空腹
- 病気
- 去る演出
- user本人や故人の代理

## GAP-05 地区ごとのvisual identity

建物は識別できるが、建物周辺の地区としての空気が弱い。

必要:
- culture lane
- story garden
- market square
- harbor edge
- archive lane
- reflection grove

地区は独立mapではなく、小さなground cue、props、灯り、音で表現する。

## GAP-06 Personal Anchor

町全体が自動生成だけだと、整っていても「自分の町」になりにくい。

必要:
- 主要featureごとに1個のPersonal Display Slot
- 色・旗・象徴物・汎用アイコン
- private text default禁止
- AI自動選定禁止

## GAP-07 選択肢過多を防ぐcurated style pack

将来editorでcatalogを増やしすぎると、選ぶ作業が主役になる。

必要:
- 8〜12点程度の小さなcoordinated pack
- preview一括適用
- 個別微調整
- free placementより先にslot personalization

## GAP-08 negative space / sightline contract

配置可能だから置く、を続けると小画面で過密になる。

必要:
- landmark sightline
- coast visibility
- building silhouette separation
- open ground budget
- front prop density limit
- no-animationでも読めるcomposition

具体数値はprototypeで決める。

## GAP-09 Quiet Surprise

現在は季節・時間の変化はあるが、偶然見つける小さな驚きの契約がない。

必要:
- nonessential
- replayable in preview
- no FOMO
- no reward
- no completion rate
- deterministic conditions

## GAP-10 復帰時のTown change summary

長期間離れた後、町の変化を理解する方法が弱い。

必要:

```txt
前回から変わったこと 最大3件
- 季節が秋になりました
- 映画館がStage 2になりました
- 港に新しい灯りが増えました
```

禁止:
- 未処理件数の責め
- 離れていた日数
- task backlog

---

# 3. 重要な反面教師

## Daily obligation

Cozy GroveやAnimal Crossingの現実時間は愛着を作る一方、日課、待ち時間、反復作業は義務化する。

Memory Townでは:
- 時間は環境だけに使う
- daily questを作らない
- 今日限定報酬を作らない

## Decoration friction

Animal Crossingで長期不満になった手作業の置き直し、素材待ち、区画清掃は避ける。

Memory Townでは:
- instant preview
- area reset
- draft
- undo / redo
- curated packs
- no crafting

## Score-driven composition

Dorfromantik / ISLANDERSの隣接得点はゲームとして強いが、Memory OSへ入れると記録量・配置効率競争になる。

Memory Townでは:
- scoreをvisual synergyへ変換
- best layout判定なし
- rankなし

## Empty sandbox without meaning

Townscaper / Tiny Glade型の道具だけでは、長期的に「何のための町か」が薄くなる可能性がある。

Memory Townでは:
- 建物は必ず棚・箱・振り返りへbinding
- personal display
- town history
- memory route

で意味を維持する。

---

# 4. Round 3 recommendation

```txt
Adopt now at contract/prototype level:
1. Derived Micro-details
2. Draft Town
3. Private Postcard / Town History
4. Ambient Nature
5. District Identity
6. Personal Display Slot
7. Curated Style Packs
8. Negative Space Contract
9. Quiet Surprise
10. Gentle Change Summary

Research only:
- On-demand Memory Window from selected photo
- procedural aesthetic assistant
- larger district generation

Reject:
- daily chores
- currency / crafting / inventory
- NPC affection
- decay
- limited-time rewards
- adjacency score
- public town ranking
```

---

# 5. Sources

- https://www.theverge.com/games/845242/animal-crossing-new-horizons-3-0-update-switch-2-edition-features
- https://www.theverge.com/games/863747/animal-crossing-new-horizons-update-3-0-switch-2-quality-of-life
- https://en.wikipedia.org/wiki/Townscaper
- https://en.wikipedia.org/wiki/Tiny_Glade
- https://www.theguardian.com/games/2024/mar/13/summerhouse-this-dreamy-pixel-renovation-game-is-the-ideal-escape
- https://en.wikipedia.org/wiki/Dorfromantik
- https://www.polygon.com/gaming/611666/islanders-new-shores-nintendo-switch-2-recommendation
- https://www.polygon.com/impressions/440606/gourdlets-laid-back-building-sim
- https://en.wikipedia.org/wiki/Cozy_Grove
- https://en.wikipedia.org/wiki/Unpacking_(video_game)
- https://arxiv.org/abs/2604.06773
- https://arxiv.org/abs/2604.01777
