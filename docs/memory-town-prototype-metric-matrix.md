# Memory Town Prototype Metric Matrix

最終更新: 2026-07-13

## 目的

Memory Townのtile metric、map寸法、parcel、建物silhouette、hit area、camera、performanceを、好みだけで固定せず、比較結果から決める。

実装はまだ開始しない。

本書はprototypeを作る時の評価契約であり、現在の28x28 mapや各footprintをproduction確定値にはしない。

---

# 1. 比較する3つのTile Metric候補

数値はprototype用候補。asset制作前の永久固定値ではない。

| Profile | Tile width | Tile height | Elevation step | 狙い |
|---|---:|---:|---:|---|
| A compact | 48px | 24px | 12px | 町全体を小画面へ収めやすい |
| B balanced | 64px | 32px | 16px | 可読性と全体表示の中間 |
| C readable | 80px | 40px | 20px | 建物識別とタップ性を優先 |

Rules:

- logical gridは候補間で変えない
-比較時にlayout座標を書き換えない
- camera scaleとviewport framingだけを変える
- nearest / linear filteringも同時比較する
- 完全pixel artとhigh-resolution dot-styleを混同しない

---

# 2. 必須Viewport

```txt
360x800
375x812
390x844
393x852
412x915
430x932
```

追加確認:

```txt
768x1024 tablet portrait
1024x768 tablet landscape
1280x720 desktop narrow
1440x900 desktop
```

スマホ6種を合格せずにdesktopだけで決めない。

---

# 3. Prototype scene set

最低限、次のsceneを同じlayoutから生成する。

## Scene P0: Empty / Stage 0

- 全主要feature stage 0
- labels ON / OFF
- day / clear
- animation OFF

目的:

- dataが少なくても空虚に見えすぎないか
- 未開放土地が失敗表現に見えないか

## Scene P1: Mixed Growth

```txt
cinema stage 2
story stage 1
market stage 2
port stage 1
warehouse stage 1
square stage 1
```

目的:

- stage差が分かるか
- 大きい建物だけが画面を支配しないか

## Scene P2: Maximum Initial Growth

- 6主要feature stage 2
- 四季overlayなし
- labels OFF

目的:

- parcel / visual overflow / silhouetteが破綻しないか

## Scene P3: Seasonal Stress

- winter snow
- night palette
- rainまたはsnow effect
- reduced motion

目的:

- readability低下
- contrast
- texture memory

## Scene P4: Decoration Stress

- tree 40
- flower 120
- furniture 30
- lamps 20
- path 200 cells

目的:

- long-term上限付近の描画
- hit test
- clutter

## Scene P5: Missing Asset

- structure 1件missing
- prop 2件missing
- seasonal overlay missing

目的:

- fallbackでも棚へ移動できるか
- layoutを失わないか

## Scene P6: Static Fallback

- WebGLなし
- DOM object list
- same feature binding

目的:

-全機能へ到達可能か

---

# 4. Visual acceptance metrics

## 4.1 Building identification

5秒表示後に確認する。

```txt
映画館
物語館
市場
港
倉庫
中央広場
```

目標候補:

- labelあり: 90%以上が正しく選択
- labelなし: 主要4建物で70%以上
- 倉庫 / 中央広場はlabel必須でも許容

ユーザーテスト前に数値を最終KPIへしない。

## 4.2 Tap target

- DOM equivalent targetは最低44 CSS px相当を目標
- visible spriteよりhit polygonを広げてよい
- neighboring target overlapを禁止
- 誤タップ時に破壊操作へ直結しない
-建物選択は1tapで可能

## 4.3 Stage readability

各建物についてStage 0 / 1 / 2を順不同で提示する。

確認:

- 未開放 / 小 / 成長が区別できる
- 数字表示なしでも変化が分かる
- Stage 2が「偉い」「勝者」に見えすぎない
- Stage 0が寂しい罰に見えない

## 4.4 Information density

Town overviewに常時表示可能:

-建物名label
- selected highlight
-小さなnew badge

禁止:

-件数の常時大量表示
-複数badgeの積み重ね
- private title
-人名
-赤い警告だらけ

---

# 5. Camera matrix

## Overview

合格条件:

-主要6建物が一度に把握できる
-海岸 / 港の関係が分かる
- bottom navigationで重要建物が隠れない
- safe areaを侵食しない

## Focus

候補:

```txt
scale 1.10
scale 1.20
scale 1.30
```

比較:

- selected buildingがbottom sheetで隠れない
- 200〜400ms以内
- reduced motionでは即時
- focus完了を待たずsheet操作可能

## Pan

MVP:

-自由panなし
- mapが収まらない候補は不採用または小範囲補助pan

将来拡張:

- logical focus targetを保存
- pixel camera位置は保存しない

---

# 6. Map / parcel evaluation

各profileで確認:

```txt
map width / height
主要parcel余白
中央広場面積
道路幅
港と海岸の接続
future expansion zone
visual overflow overlap
```

Decision rules:

- Stage 2 assetがparcelへ収まらないmapは不採用
- 追加予定3建物分の拡張余地がないmapは不採用
- overviewで空白が多すぎる場合、mapを縮める前にterrain / pathの生活感を検討
-建物追加のために既存stable parcel IDを意味変更しない

---

# 7. Growth envelope evaluation

各主要建物で記録する。

| Item | Stage 0 | Stage 1 | Stage 2 | Later assumption |
|---|---|---|---|---|
| occupied cells | required | required | required | candidate |
| entrance cells | required | required | required | stable |
| visual overflow | required | required | required | candidate |
| shadow bounds | required | required | required | candidate |
| overlay slots | required | required | required | candidate |

合格条件:

- occupied cellsはEnvelope内
- primary entrance安定
- path connectivity維持
- user grid decorationの自動退避なし
- neighboring parcelの主要建物を完全に隠さない

---

# 8. Performance measurement plan

実機prototype後に測る。

## Device classes

```txt
recent iPhone
older supported iPhone
mid-range Android
low-end supported Android
modern desktop
```

特定modelは実装開始時にsupport policyと市場状況を確認して固定する。

## Scenarios

```txt
cold town open
warm town open
overview idle 5 min
background 5 min → foreground
focus repeated 50 times
route enter / leave 50 times
context loss / restore
P4 decoration stress
winter night stress
static fallback
```

## Metrics

```txt
first meaningful town paint
input response latency
steady frame pacing
peak texture memory
JS heap growth
GPU context loss recovery
battery / heat qualitative grade
bundle transfer size
decode time
```

## Initial gates

数値はprototype前の候補。

- shelf画面の初期bundleへtown assetを混ぜない
- route leaveでticker停止
- hidden tabでanimation停止
- 30分idle後に継続的heap増加なし
- context lossでapp全体が落ちない
- low powerでambient effectを停止可能
- 60fps固定より操作応答と発熱を優先

最終閾値は実機baseline後に固定する。

---

# 9. Accessibility matrix

| Test | WebGL | Static fallback | DOM list |
|---|---:|---:|---:|
| 建物名を確認 | required | required | required |
| 棚へ移動 | required | required | required |
| keyboard操作 | DOM bridge | DOM hotspot | required |
| screen reader | DOM alternative | DOM hotspot | required |
| reduced motion | required | n/a | n/a |
| high contrast selection | required | required | required |
| text zoom 200% | sheet / list | buttons | required |

WebGL canvasだけを唯一の操作面にしない。

---

# 10. User test tasks

1. 映画棚を開く
2. 未整理Inboxを開く
3. 今月の振り返りを開く
4. 最近変化した建物を見つける
5. 通常navigationから同じ棚へ行く
6. 町を使わず検索する
7. 「この町が放置で荒れると思うか」を確認
8. Stage 2 / current count 0の説明を読んで違和感を聞く
9. decoration slotを1つ選ぶprototypeを試す
10. 自由配置が欲しいか、単に見た目変更で十分かを聞く

誘導質問を避ける。

---

# 11. Decision record template

```txt
Decision ID:
Date:
Profiles compared:
Viewports:
Assets used:
Device classes:
Observed problems:
Metrics:
User test evidence:
Chosen value:
Rejected alternatives:
Revisit trigger:
Affected fixture versions:
```

口頭決定だけでfixtureを更新しない。

---

# 12. Prototype exit gate

```txt
[ ] A/B/C tile metric比較
[ ] mobile 6 viewport比較
[ ] P0〜P6 scene比較
[ ] Stage 0〜2 silhouette
[ ] Growth Envelope整合
[ ] tap target overlapなし
[ ] static fallback到達性
[ ] reduced motion
[ ] device class baseline
[ ] user test task成功率
[ ] decision record
[ ] Map / Catalog / Template fixture version更新
```

---

# 結論

```txt
数値を先に信じない。

同じlogical layoutを、複数metric・viewport・assetで比較し、
見やすさ、愛着、操作性、発熱、将来余白の証拠から固定する。
```
