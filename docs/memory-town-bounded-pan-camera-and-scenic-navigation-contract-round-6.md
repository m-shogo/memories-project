# Memory Town Bounded Pan Camera and Scenic Navigation Contract — Round 6

最終更新: 2026-07-14

## Decision

Memory Townは一画面へ全景を圧縮しない。

ユーザーは指のdragで、viewportより広い町を静かに移動して眺められる。

ただし、自由歩行・無限scroll・自由回転を中心とするgame cameraにはしない。

```txt
bounded pan
+ authored landmarks
+ gentle anchors
+ DOM route equivalence
```

実装はまだ開始しない。

---

# 1. Camera purpose

Cameraは次のために存在する。

- 海、川、空の余白を守る
- 建物を小さく潰さない
- 景色を少しずつ見つけられる
- 町の場所へ愛着を持てる
- 主要featureへ迷わず到達できる

Cameraは次のためには使わない。

- gameplay exploration
- hidden item search
- resource collection
- navigation difficulty
- retentionのための移動時間

---

# 2. Initial input model

初期採用:

```txt
one-finger drag:
  pan town

tap:
  select building / feature

landmark shortcut:
  move to authored camera anchor

home action:
  return to central square / Memory Tree
```

初期非採用:

- free camera rotation
- perspective tilt
- infinite pan
- avatar walking
- inertiaが長く続くflick travel
- mandatory pinch zoom

Pinch zoomはvisual evidence後の候補とし、初期操作要件にはしない。

---

# 3. Scene size

Townはviewportより広くする。

ただし、広さを「画面何枚分」という固定値だけで決めない。

prototype候補:

```txt
compact scenic:
  1.3–1.6 viewport extents

balanced scenic:
  1.6–2.2 viewport extents

expanded scenic:
  2.2–3.0 viewport extents
```

評価対象:

- 景観余白
- 移動疲労
- landmark recognition
- major feature到達回数
- device別のpan距離
- static fallback再現性

無意味に広い空間は禁止する。

---

# 4. Camera bounds

CameraはMap Definition由来のbounds内だけ移動する。

```txt
hard content bounds
+ viewport-safe inset
+ optional elastic overscroll preview
```

Rules:

- scene外の空白を長く表示しない
- 端では穏やかに停止する
- elastic effectを使う場合も短く戻る
- reduced motionではelastic animationを減らす
- motion offでは即時clamp可能
- bottom sheet表示時はvisible boundsを再計算する

---

# 5. Authored camera anchors

主要areaごとに安定したcamera anchorを持つ。

初期候補:

```txt
anchor.central-grove
  central square + Memory Tree

anchor.culture-lane
  cinema + nearby water / path

anchor.market-square
  market + plaza activity

anchor.river-bridge
  river + bridge + riverbank

anchor.harbor-edge
  port + beach + open sea

anchor.archive-lane
  Inbox warehouse + quiet path
```

Anchorはlayout objectのpixel座標を直接保存せず、logical target regionから導出する。

建物stageやasset差し替えでanchor IDを変えない。

---

# 6. Gentle snap policy

Drag終了後、必ずanchorへ強制snapしない。

推奨:

```txt
free resting position
+ optional weak attraction near authored anchor
```

強いpage snapは、海や川を自由に眺める感覚を壊すため初期defaultにしない。

ただし、以下ではanchor移動を明示的に使える。

- 建物一覧から選択
- Homeへ戻る
- 「港を見る」などのshortcut
- keyboard / switch control
- accessibility list mode

---

# 7. Tap versus drag

誤操作を防ぐため、tapとpanを明確に分離する。

prototypeで検証するもの:

- movement threshold
- hold duration
- small-screen thumb jitter
- building target overlap
- bottom sheetとのgesture conflict

Rules:

- drag開始後にbuilding actionを誤発火しない
- target上からdragを開始できる
- pan中はselectionを変更しない
- pointer cancel / route leaveでgesture stateを破棄する
- multi-touch中に単独tap actionを発火しない

具体thresholdは実機prototype後に固定する。

---

# 8. Initial and return position

初回default:

```txt
anchor.central-grove
```

ここには次を含める。

- 四季樹
- 中央広場
- 主要建物の一部
- 川または海へ向かう視線

Session再訪時の候補:

```txt
A. every time central return
B. restore last scenic position
C. restore last position only within short session window
```

privacy上、camera positionから閲覧featureを推測できる可能性があるため、長期analyticsや共有snapshotへlast camera positionをdefaultで含めない。

---

# 9. Building focus

建物を選択しても、大きなcamera animationを必須にしない。

候補:

- current positionでbottom sheetを開く
- 必要な時だけ短いrecenter
- buildingがsheetに隠れる場合だけ補正

禁止:

- 毎tapで長距離fly animation
- camera animation終了まで操作不能
- selectionのたびにzoom in / out
- animationをskipできない設計

---

# 10. Keyboard and accessibility equivalence

Canvas gestureを使えなくても、全featureへ到達できる。

必須:

- React / DOM list
- landmark shortcut
- Home action
- next / previous landmark action候補
- selected feature summary
- keyboard activation
- focus orderはDOM正本

Canvasは視覚rendererであり、pan操作だけがfeature到達手段にならない。

---

# 11. Reduced motion and low power

## Full

- short eased pan
- subtle weak anchor attraction
- water / cloud / tree motion

## Reduced

- pan duration短縮
- overscroll抑制
- anchor animation抑制
- ambient motion低減

## Off

- camera shortcutは即時移動または極短fade
- overscroll bounceなし
- sceneryは静止でも識別可能

## Low power

- drag中のexpensive effect停止
- reflection / particle更新を削減
- camera停止後に必要layerだけ再描画

---

# 12. Scenic continuity

Panしてareaが切り替わっても、別screenを横に並べたように見せない。

連続性を作るもの:

- river flow
- physical path
- vegetation gradient
- sky / light continuity
- district transition props
- water sound crossfade候補

地区ごとの個性は持たせるが、scene全体の光源・風・季節は共有する。

---

# 13. Prototype scenes

```txt
C0 central return
C1 central → river bridge pan
C2 river bridge → harbor pan
C3 cinema → market short pan
C4 maximum bound edge
C5 bottom sheet open while panning
C6 tap / drag ambiguity
C7 reduced motion anchor shortcut
C8 motion off immediate navigation
C9 DOM list → harbor anchor
C10 320px narrow fallback
```

必要viewport:

- 360 × 800
- 375 × 812
- 390 × 844
- 393 × 852
- 412 × 915
- 430 × 932
- tablet portrait reference

---

# 14. Acceptance gates

## Gate CAM-1 Scenic quality

- 一画面圧縮版より空・水・建物が読みやすい
- 海、川、四季樹に十分な滞在可能な構図がある
- panによって景色の発見が生まれる

## Gate CAM-2 Orientation

- central anchorを覚えられる
- 港、川、映画館の方向が理解できる
- Home actionで即座に戻れる
- mini-mapなしでも基本利用できる

## Gate CAM-3 Friction

- 主要featureへ過剰なdrag回数を要求しない
- tap / drag誤発火が許容範囲
- bottom sheetとgestureが競合しない

## Gate CAM-4 Accessibility

- gestureなしで全routeへ到達
- motion offで同等操作
- list modeで二次元scrollを強制しない

## Gate CAM-5 Memory-first

- pan時間がCapture / Searchを邪魔しない
- Townを経由しなくても主要機能へ到達
- 隠し要素探索を記憶追加動機にしない

---

# Current verdict

```txt
one-screen compression:
rejected as default requirement

bounded finger pan:
adopted for prototype

free rotation / avatar walk:
not adopted

scene extent:
prototype candidate

implementation:
NO-GO
```
