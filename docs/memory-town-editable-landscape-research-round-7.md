# Memory Town Editable Landscape Research — Round 7

最終更新: 2026-07-14

## 目的

Memory Townを一枚の完成背景へ固定せず、将来ユーザーが次を変更・増築できる構造を調査する。

- 海岸線
- 砂浜
- 川・水路・池
- 道・広場・橋
- 草地・土・石
- 森・木・花
- 家・主要建物
- 新しい地区・岬・島

本調査は、自由度だけを最大化するものではない。

```txt
景観を壊しにくい
+ 編集が面倒にならない
+ 将来のasset変更に耐える
+ mobileで操作できる
+ Memory-firstを維持する
```

を同時に満たす方式を選ぶ。

実装はまだ開始しない。

---

# 1. 調査した方式

## 1.1 一枚絵・巨大背景

長所:

- 構図を完全に制御できる
- 最初から高品質な景観を作りやすい
- 描画負荷を読みやすい

短所:

- 海岸、川、道、家が背景へ焼き込まれる
- 建物移動で周囲を描き直す必要がある
- 新地区追加で継ぎ目が出る
- 四季、時間、成長、編集の組み合わせがasset爆発する

Verdict:

```txt
concept artには使う
production source of truthにはしない
```

## 1.2 完全なcell単位terraforming

参考:

- Animal Crossing: New Horizonsの崖・水・道編集
- 一般的なTileMap editor

長所:

- 高い自由度
- terrainの形を細かく変えられる
- cell validationが比較的明確

短所:

- mobileで1cellずつ編集すると疲れる
- 川岸、崖、角を何度も直す作業になる
- 全景を壊して再設計する心理的負荷が高い
- 見た目を良くするために大量の手作業が必要

Animal Crossingの長期利用事例では、崖・川・植物を一つずつ編集する摩擦が大きく、2026年の更新でも位置合わせや指定範囲の片付けが改善対象になった。

Verdict:

```txt
内部gridには使う
user interactionを1cell作業中心にはしない
```

## 1.3 Terrain / Rule Tile

参考:

- Tiled Terrain Sets
- Godot Terrain Sets
- Unity Rule Tile

共通原理:

```txt
ユーザーはgrass / sand / roadなど意味を塗る
→ systemが周囲との接続を判定
→ corner / edge / junction spriteを自動選択
→ 変更箇所の周辺も整える
```

TiledはCorner / Edge / Mixed terrain setを持ち、道路、柵、platform、地面遷移に応じて隣接tileを自動調整する。Godotは周辺へ接続するConnectと、同じstroke内を接続するPathを分け、特定tileによるoverrideも可能にしている。Unity Rule Tileも周辺条件、回転、mirror、random、animationを規則で選べる。

長所:

- 海岸・砂浜・道・草地の継ぎ目を自動化できる
- asset差し替えがrule catalog更新で可能
- 同じterrain dataから季節variantを描ける

短所:

- tileだけでは人工的な反復が見えやすい
- Mixed setは必要asset数が増える
- 大きな景観構図までは自動で良くならない

Verdict:

```txt
base terrain transitionの中核に採用
```

## 1.4 Rule-based procedural completion

参考:

- Townscaper
- Tiny Glade

共通原理:

```txt
ユーザーは大きな形だけ決める
→ systemが窓、角、屋根、階段、植栽などを補完
```

Townscaperは歪んだgridと接続ruleにより、配置されたblock群を塔、balcony、arch、garden、stairsへ変換する。Tiny Gladeも壁、道、建物の関係から完成感のあるdetailを生成する。

長所:

- 少ない操作で完成感が出る
- landscapeを手作業で埋めなくてよい
- user layoutとdecorative detailを分離できる

短所:

- ruleが弱いと単調になる
- ruleが強すぎるとユーザーの意図を上書きする
- derived detailを正本化するとmigrationが難しい

Verdict:

```txt
Derived Micro-detailsとして採用済み
canonical layoutへ保存しない
```

## 1.5 Water-first hierarchical generation

参考:

- GardenDesigner

GardenDesignerは、水中心のterrain distribution、探索性を持つpath生成、asset選択、asset layout最適化を段階分離している。

Memory Townへの示唆:

```txt
water / coast
→ roads / bridges
→ parcels / buildings
→ vegetation / detail
```

の順で構成する方が、建物を先に置いて残りへ川を押し込むより景観を保ちやすい。

Verdict:

```txt
scene generationと編集validationの順序に採用
```

## 1.6 Wave Function Collapse / model synthesis

長所:

- 少ないruleから多様な接続結果を生成できる
- districtやterrain variationを増やしやすい

短所:

- constraint conflictとbacktrackingが発生する
- userが既に作った場所を勝手に再生成しやすい
- 生成結果を正本にすると変更理由を説明しにくい

Verdict:

```txt
初期layoutやderived variationの候補
user layoutの正本・save時の必須処理にはしない
```

---

# 2. 比較結果

| 方式 | 景観 | 編集性 | mobile負担 | 拡張性 | 採否 |
|---|---:|---:|---:|---:|---|
| 一枚絵 | 高 | 低 | 低 | 低 | concept only |
| 完全cell terraform | 中 | 高 | 高 | 中 | internal only |
| terrain rule tiles | 中〜高 | 高 | 中 | 高 | 採用 |
| spline / graph | 高 | 高 | 低〜中 | 高 | 採用 |
| procedural completion | 高 | 中 | 低 | 高 | 採用 |
| district plates only | 高 | 低〜中 | 低 | 中 | template用途 |
| hierarchical hybrid | 高 | 高 | 低〜中 | 高 | 正式推奨 |

---

# 3. 推奨方式 — Hierarchical Editable Diorama

```txt
Level 0: World Frame
Level 1: District / Expansion Topology
Level 2: Terrain Regions
Level 3: Linear Networks
Level 4: Parcels / Landmarks
Level 5: Objects / Vegetation
Level 6: Derived Visual Details
```

## Level 0 — World Frame

- sky
- horizon
- distant sea
- distant islands
- global light

ユーザー地形とは分離する。

## Level 1 — District / Expansion Topology

- central district
- river district
- harbor district
- forest district
- future district

地区は外側へsocket接続できる。

## Level 2 — Terrain Regions

- grass
- soil
- sand
- stone
- forest floor
- shallow water
- plaza surface

ユーザーは意味をbrushで塗り、描画tileはsystemが選ぶ。

## Level 3 — Linear Networks

- road
- footpath
- river
- canal
- fence
- coast boundary

cell列を直接一つずつ置くより、stroke / spline / graphを正本候補にする。

## Level 4 — Parcels / Landmarks

- building parcel
- bridge anchor
- plaza anchor
- Memory Tree grove
- harbor pier anchor
- scenic-view corridor

## Level 5 — Objects / Vegetation

- houses
- major feature buildings
- trees
- flowers
- benches
- lamps
- boats

## Level 6 — Derived Visual Details

- terrain corner / edge
- shoreline foam
- riverbank
- road intersection
- bridge approach
- fence join
- forest undergrowth
- building contact shadow
- small planting

source of truthへ保存しない。

---

# 4. Memory Townへ採用する重要原則

1. semantic dataを保存し、最終spriteを保存しない
2. terrain / water / path / buildingを別stateにする
3. user editはbrush strokeまたはobject command単位
4. 一つのstrokeを一つのundo単位にする
5. 周辺transitionは自動更新する
6. 自動更新はuser objectを削除・移動しない
7. 地区追加で既存座標原点を変更しない
8. outer seaとskyはworld frame、near coastはeditable landscape
9. free elevation sculptは初期採用しない
10. すべてDraft Townでpreviewしてからatomic applyする

---

# 5. 研究からの最終判断

Memory Townは次ではない。

```txt
巨大な一枚絵
完全自由なterrain sculpt tool
1cellずつ作業するterraforming game
```

正式方向:

```txt
大きな地区を増築できる
+ 地面を意味で塗れる
+ 道と川を線で引ける
+ 家と森を移動・変更できる
+ 継ぎ目をsystemが静かに整える
```

この構造を確定した後に、同じlandscape dataから複数の景観画像を作り、編集前後と地区増築を比較する。

---

# 6. Sources

- Tiled Documentation, Using Terrains / Automapping
- Godot Engine Documentation, TileMaps and terrain connections
- Unity 2D Tilemap Extras, Rule Tile
- Oskar Stålberg, Organic Towns from Square Tiles / Townscaper
- Pounce Light, Tiny Glade procedural building direction
- GardenDesigner: Encoding Aesthetic Principles into Jiangnan Garden Construction via a Chain of Agents, arXiv:2604.01777
- Extend Wave Function Collapse to Large-Scale Content Generation, arXiv:2308.07307
- Animal Crossing: New Horizons island editing and 2026 quality-of-life observations
