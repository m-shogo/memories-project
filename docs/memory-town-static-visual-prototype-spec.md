# Memory Town Static Visual Prototype Specification

最終更新: 2026-07-13

## 目的

PixiJS実装前に、固定視点2.5DのMemory Townがスマホで理解・操作できるかを、静止visual prototypeで検証する。

このphaseではproduction renderer、DB、PixiJS scene、自由配置editorを実装しない。

検証対象:

- tile metric
- map dimensions
- building silhouette
- Growth Envelope
- visual density
- DOM interaction overlay
- layered visual fallback
- accessibility presentation
- bottom sheetとの干渉

---

# 1. Deliverables

各候補について次を作る。

```txt
1. full town composite image
2. logical grid debug image
3. parcel / Growth Envelope debug image
4. DOM hit target overlay image
5. focus order image
6. layered fallback mock
7. 200% text zoom mock
8. selected building + bottom sheet mock
9. missing asset fallback mock
10. evaluation JSON
```

画像だけで判断せず、同じlogical fixtureから生成したdebug evidenceを残す。

---

# 2. Viewport matrix

必須:

```txt
360 × 800
375 × 812
390 × 844
393 × 852
412 × 915
430 × 932
```

追加:

```txt
320 × 568  legacy narrow check
768 × 1024 tablet portrait
1024 × 768 tablet landscape reference
1440 × 900 desktop panel reference
```

320pxではTown visualが完全表示できなくても、DOM listへreflowして機能を失わないことを確認する。

---

# 3. Tile metric candidates

既存候補:

```txt
A compact
48 × 24

B balanced
64 × 32

C readable
80 × 40
```

各候補で固定するのは比較用の仮値であり、承認までは正本にしない。

評価:

- 建物識別
- 主要building 6つの同時視認
- DOM target overlap
- stage 2の余白
- future expansion余地
- dot-style assetの読みやすさ
- fallback DOM imageの画質

---

# 4. Prototype scenes

## P0 Empty beginning

```txt
全feature Stage 0
記録0件
昼
clear
motion off
```

確認:

- 空虚・失敗・寂しさに見えない
- 何が育つ場所か想像できる
- 未開放でもrouteを失わない

## P1 Early town

```txt
3 feature Stage 1
残りStage 0
昼
少量の木・花
```

## P2 Mature town

```txt
主要6 feature Stage 2
装飾上限候補
夕方
```

確認:

- silhouetteが潰れない
- Growth Envelopeが足りる
- building同士のhit targetが重ならない

## P3 Explicit reset

```txt
映画棚 current 100件
映画館 Stage 0
resetEpoch 1
```

確認:

- 「100件あるのにStage 0」がバグに見えない
- Reset済みcopyの必要性
- current countと町の育ち直しを説明できる

## P4 Winter night

```txt
冬
夜
snow overlay
lights enabled
reduced motion visual
```

確認:

- 低コントラスト化しない
- snowがhit areaを変えない
- light effectが文字を邪魔しない

## P5 Missing asset

```txt
cinema Stage 2 texture missing
fallback texture
他object正常
```

確認:

- scene全体が壊れない
- route利用可能
- errorをユーザーへ過剰表示しない

## P6 Layered visual fallback

```txt
WebGL unavailable
base map image
per-object DOM images
DOM buttons
```

確認:

- stage差分を表現可能
- single precomposed imageに依存しない
- same feature IDs

## P7 Accessibility list mode

```txt
canvas visual hidden from accessibility tree
DOM list active
200% text zoom
keyboard only
```

確認:

- two-dimensional scrolling不要
- route / summary / back操作可能
- duplicate focus targetなし

## P8 Bottom sheet collision

各buildingを選択し、bottom sheet 40% / 55% height候補を表示。

確認:

- selected buildingが完全に隠れない
- focus ringがsheet背面へ残らない
- camera focusなしでもrouteを開ける

## P9 Stored primary binding

```txt
primary structure stored
portal fallbackあり / なし
```

確認:

- fallback portalまたはDOM-only route
- feature自体を失わない

## P10 Access path failure debug

```txt
cinema access pathを意図的に切断
```

確認:

- debug overlayでdisconnected reasonが分かる
- visual prototype自体を正常候補として承認しない

---

# 5. DOM target policy

WCAG 2.2 AAのminimum floorは24 × 24 CSS px。

Memory Townの主要building targetはproduct targetとして次を目指す。

```txt
preferred: 44 × 44 CSS px以上
absolute design floor: 32 × 32 CSS px
WCAG conformance floor: 24 × 24 CSS pxまたは十分なspacing / equivalent control
```

主要buildingは重要controlなので、24px exceptionを常用しない。

DOM listに同じactionを持つ十分なtargetを必ず提供する。

Target評価:

- target bounds
- adjacent target distance
- bottom sheet overlap
- safe area
- 200% zoom
- device pixel ratioに依存せずCSS pxで測定

---

# 6. Accessibility visual evidence

各viewportで出力:

- DOM focus target rectangle
- accessible name
- tab order number
- selected state
- overlay mode / list mode active state
- canvas `aria-hidden`
- inactive mode `inert`

禁止:

- Pixi accessible overlayとReact DOM overlayを同時active
- z-index順をTab順として使用
- building画像内文字だけでfeature名を伝える

---

# 7. Building stage asset prototype

各主要building:

```txt
Stage 0
Stage 1
Stage 2
```

同一familyで確認:

- pivot
- entrance location
- depth anchor
- render bounds
- visual overflow
- overlay slot
- contact shadow
- light direction
- supported orientation
- fallback silhouette

Stage間で入口のlogical位置を動かさない。

Stage 0は「何もない」「失敗」に見せず、landmark sign / foundation / small functional objectとして成立させる。

---

# 8. Art style comparison

比較:

```txt
A. complete low-resolution pixel art
B. high-resolution dot-style illustration
C. soft miniature illustration
```

現推奨はBだが、prototype結果前に確定しない。

評価:

- 小画面識別
- stage差分
- animationしやすさ
- asset差し替え
- AI生成後の人間修正量
- 3年後の古さ
- visual density
- fallback再現性

---

# 9. Layered fallback mock

Layers:

```txt
base terrain
physical paths
rear props
structures
front props
overlays
selection
DOM controls
```

CSS fallbackはPixiと同じlogical projection functionの出力を使用する想定。

Prototypeでは手作業配置でもよいが、各objectにlogical position / projected positionの表を添付する。

---

# 10. Evaluation JSON

```json
{
  "prototypeId": "memory-town-static-B-P2-390x844",
  "tileMetricCandidate": "B",
  "sceneId": "P2",
  "viewport": { "width": 390, "height": 844 },
  "majorTargets": [
    {
      "featureId": "shelf.movie",
      "widthCssPx": 52,
      "heightCssPx": 48,
      "overlapsAnotherTarget": false,
      "occludedByBottomSheet": false
    }
  ],
  "findings": [],
  "status": "candidate"
}
```

実測前の数値をPASSとして埋めない。

---

# 11. Acceptance gates

## Gate VP-1 Geometry

- all major structures inside parcel
- all approved stages inside Growth Envelope
- required access paths connected
- no major target overlap

## Gate VP-2 Comprehension

- buildingとfeatureの対応を説明可能
- labels ON / OFF比較
- warehouse / squareの理解率を確認

## Gate VP-3 Accessibility

- one authoritative DOM tree
- keyboard route activation
- list mode complete
- 200% text zoom
- target size evidence
- reduced motion representation

## Gate VP-4 Fallback

- WebGLなしで全featureへ到達
- layered visual fallbackがstageを反映
- missing assetでscene全体を失わない

## Gate VP-5 Emotional safety

- Stage 0が寂しさ・失敗・罰に見えない
- inactivityで荒れない
- current count 0でも責めない
- explicit resetが壊れた町に見えない

---

# 12. Output directories — future implementation convention

```txt
reports/memory-town-static-prototype/
├─ candidate-a/
├─ candidate-b/
├─ candidate-c/
├─ overlays/
├─ fallback/
├─ accessibility/
├─ evaluation/
└─ summary.md
```

現時点ではdirectory作成や画像生成を必須にしない。

---

# Decision

```txt
PixiJSを先に作らない。
まず同じlogical fixturesで静止比較する。

見た目、hit target、Growth Envelope、DOM fallback、a11yを同時に検証し、
証拠が揃った候補だけを実装値へ昇格する。
```
