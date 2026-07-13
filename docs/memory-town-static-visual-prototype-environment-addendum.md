# Memory Town Static Visual Prototype — Environment Addendum

最終更新: 2026-07-13

## 目的

既存の静止visual prototypeへ、4時間帯・四季・Memory Tree・ビーチ・波・空・灯りを追加し、PixiJS実装前に環境デザインを比較可能にする。

このphaseではanimation code、renderer、DB、asset production pipelineを実装しない。

---

# 1. Map placement candidates

## 1.1 Beach

優先候補:

```txt
lower-right coast
```

理由:

- 港と自然につながる
- 中央広場の視認を邪魔しない
- 画面下部で波の動きが見えやすい
- 将来の港拡張と海岸decorをまとめられる

比較候補:

```txt
A. lower-right beach + port
B. full lower-edge beach
C. lower-left beach + right-side port
```

Gate:

- 主要6建物が同時視認可能
- bottom sheetで海岸全体が隠れない
- port access pathを維持
- Growth Envelopeと衝突しない

## 1.2 Memory Tree

優先候補:

```txt
central squareの横
中央より少し奥側
```

中央広場そのものを木で占有しない。

比較候補:

```txt
T-A square rear-left
T-B square rear-center
T-C square side parcel
```

Gate:

- Stage 2 canopyが建物targetを隠さない
- Tree自身のDOM targetを44 × 44 CSS px候補で確保可能
- 4季のsilhouetteが背景へ埋もれない
- 中央広場のroute理解を邪魔しない

---

# 2. Environment scene matrix

## E0 Spring Morning Beginning

```txt
season: spring
time: morning
Memory Tree: Stage 0
buildings: Stage 0
weather: clear
motion: off visual reference
```

確認:

- 初期町が空虚に見えない
- 桜の若木が「育つ余地」に見える
- 朝の光がStage 0看板を読みにくくしない

## E1 Summer Day Early Town

```txt
season: summer
time: day
Memory Tree: Stage 1
3 buildings: Stage 1
beach: visible
weather: clear
```

確認:

- 海と空が青一色にならない
- 深い緑のTreeが建物を隠さない
- shore reflectionがtargetを邪魔しない

## E2 Autumn Night Mature Town

```txt
season: autumn
time: night
Memory Tree: Stage 2
all buildings: Stage 2
building lights: enabled
```

確認:

- モミジ調の赤が警告色に見えない
- 暖色灯りと紅葉が飽和しない
- cinema / market / portの識別を維持

## E3 Winter Midnight Mature Town

```txt
season: winter
time: midnight
Memory Tree: Stage 2
stars: visible
moon reflection: enabled
building lights: midnight profile
```

確認:

- 町が死んだ・放置された印象にならない
- 雪と月光でtarget contrastを失わない
- nightとの差が暗さ以外で分かる

## E4 Four Time Modes

同じlayout、同じ季節、同じstageで比較する。

```txt
morning
day
night
midnight
```

同時に確認:

- sky
- celestial position
- star visibility
- building lights
- shadow direction
- water reflection
- label contrast

## E5 Four Seasons

同じlayout、同じday mode、同じTree stageで比較する。

```txt
spring
summer
autumn
winter
```

particleなし版を正本比較に使う。
粒子なしでも季節が分かること。

## E6 Motion Profiles

同じsceneで次の静止frameを用意する。

```txt
motion off
reduced motion
full motion
low power
```

静止画でも、どのlayerが動く予定かdebug overlayで示す。

## E7 Layered Fallback

```txt
sky CSS layer
terrain / beach image
water layer
path layer
building images
Memory Tree seasonal image
light overlay
DOM feature controls
```

WebGLなしでも同じeffective time / season / Tree stageを反映する。

## E8 Text Zoom Midnight

```txt
viewport: 320 × 568 and 390 × 844
text zoom: 200%
time: midnight
bottom sheet: open
```

確認:

- Canvas visualはaria-hidden
- active DOM modeは一つ
- feature listへreflow可能
- dark sceneでもfocus ringを識別可能

## E9 Low Power

```txt
cloud: static or one layer
wave: approved still or slow minimum
Tree: static
particles: off
celestial position: discrete
```

低電力でも「壊れた画面」に見せない。

## E10 Tree Privacy Reset

```txt
current eligible count: high
Memory Tree stage: 0
growth reset epoch: incremented
growth origin cursor: current projection cursor
```

確認:

- Stage 0がバグに見えない
- current countと育ち直しをDOM copyで説明可能
- exact historic quantityを露出しない

---

# 3. Time-boundary candidates

比較候補は1系統のみとし、境界そのものより色味の自然さを検証する。

```txt
05:00 morning
11:00 day
17:00 night
23:00 midnight
```

境界前後のmock:

```txt
04:59 → 05:00
10:59 → 11:00
16:59 → 17:00
22:59 → 23:00
```

確認:

- scene全交換のflashがない想定
- building lightのON/OFFが不自然でない
- sun / moon handoffが一瞬で飛んだ印象にならない
- screen reader announcementを毎分発生させない

---

# 4. Environment debug overlays

各sceneへ次を出力する。

```txt
sky layer bounds
cloud motion arrows
celestial path candidate
shadow direction
shore animation bands
Memory Tree pivot
Memory Tree render bounds
Memory Tree Growth Envelope
building light masks
DOM target rectangles
bottom sheet reserved area
```

---

# 5. Comprehension questions

ユーザーテストで聞く。

1. 今は朝・昼・夜・夜中のどれに見えるか
2. 今は何季に見えるか
3. この木は何を表していると思うか
4. 冬の町は寂しい・失敗・放置に見えるか
5. 波や雲の動きは落ち着くか、邪魔か
6. 海辺は町の一部に見えるか、背景に見えるか
7. 木が大きいと情報の価値が高いと誤解するか
8. 時間帯を固定したいと思うか
9. motion offでも魅力が残るか
10. nightとmidnightの違いが分かるか

---

# 6. Acceptance gates

## EVP-1 Layout

- beachとportが自然に連続
- Tree Stage 2が主要targetを遮らない
- 主要6建物が最小viewportでも到達可能

## EVP-2 Time

- 4時間帯を区別可能
- night / midnightを暗さ以外で区別
- manual previewとauto modeを混同しない

## EVP-3 Season

- particleなしで4季を区別可能
- spring = 桜、autumn = モミジ調が伝わる
- winterに罰・死・放置感がない

## EVP-4 Motion

- motion offで意味を失わない
- reduced motionが十分静か
- full motionでも複数layerが競合しない
- low power候補が成立

## EVP-5 Accessibility

- one authoritative DOM tree
- 200% zoom
- target size evidence
- midnight contrast
- fallbackで全route利用可能

## EVP-6 Privacy and philosophy

- Treeは情報量の粗いaggregateのみ
- AI importanceや感情scoreを使わない
- exact countをTree stageから表示しない
- Reset / hideが可能

---

# 7. Required output convention

```txt
reports/memory-town-static-prototype/environment/
├─ time-modes/
├─ seasons/
├─ beach/
├─ memory-tree/
├─ motion-profiles/
├─ fallback/
├─ accessibility/
├─ debug-overlays/
└─ evaluation/
```

現時点では画像生成・directory作成を実施しない。

---

# 8. Decision

```txt
既存のGeometry prototypeに、環境を後付けしない。

Beach位置とMemory Tree最大silhouetteを含めた状態で、
tile metric・map寸法・building配置を比較する。

環境なしで承認したmap候補を、後から海と大木のために作り直すことを防ぐ。
```
