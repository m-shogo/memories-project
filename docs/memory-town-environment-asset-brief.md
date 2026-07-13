# Memory Town Environment Asset Brief

最終更新: 2026-07-13

## 目的

朝・昼・夜・夜中、四季、ビーチ、波、雲、太陽・月、Memory Treeを、asset爆発と描き直しを避けながら静止visual prototypeへ落とす。

実装・production asset制作はまだ開始しない。

---

# 1. Asset strategy

禁止:

```txt
4時間帯 × 4季節 = 16枚の完成背景を個別制作
```

採用:

```txt
base terrain
+ sky gradient
+ cloud sprites
+ sun / moon / stars
+ water / coast animation layers
+ seasonal ground overlay
+ Memory Tree seasonal stage sprite
+ building light overlay
+ global light / shadow preset
```

時間帯は主にpalette・空・灯り・影で変える。
季節は主にMemory Tree・地面cue・小さなparticleで変える。

---

# 2. Initial asset inventory

## 2.1 Sky

```txt
sky gradient token mock: 4
  morning
  day
  night
  midnight

cloud sprite shape: 4
cloud back/front composition: 2 layers
sun: 1
moon: 1
star field: 2
  subtle
  visible
atmospheric haze: 2
```

雲の形は時間帯ごとに作り直さず、tint・opacity・speedで再利用する。

## 2.2 Beach and sea

```txt
water base tile family: 1
coast transition tile family: 1
sand tile family: 1
shore foam loop: 1 family
distant water drift: 1 family
surface reflection overlay: 4
  morning
  day
  night
  midnight
```

Prototypeでは3〜6 frame loop候補を比較する。
実際の潮位差分は作らない。

## 2.3 Memory Tree

```txt
3 growth stages × 4 seasons = 12 principal sprites
fallback silhouette: 3
contact shadow: 3
season ground cue: 4
particle profile mock: 3
  spring petals
  autumn leaves
  winter light snow
```

時間帯別のTree spriteは作らない。
light / shadow overlayで対応する。

## 2.4 Building lights

主要building 6種について、Stage 0〜2の灯りmask候補を作る。

```txt
cinema
story house
market
port
warehouse
central square
```

最大候補:

```txt
6 buildings × 3 stages = 18 light masks
```

ただしprototypeでは、まずStage 2の6種だけ作り、night / midnightの違いをopacity・色温度で比較する。
Stage 0〜1はGeometry候補が承認された後に制作する。

## 2.5 Global lighting

```txt
contact shadow direction preset: 4
global color overlay: 4
moon reflection band: 1
window warmth token: 2
  night
  midnight
```

dynamic realtime shadow mapは作らない。

## 2.6 Seasonal ground cues

```txt
spring: small flower patch / pale grass
summer: deep grass / bright shore sparkle
autumn: fallen leaf patch / warm ground tint
winter: snow cap / winter grass / warm lamp accent
```

地面全体を別mapとして4枚作らず、base terrain＋overlayで比較する。

---

# 3. Memory Tree design requirements

## Common silhouette

- 3段階が小画面でも明確
- Stage 0も失敗・空地に見えない
- Stage 2でも中央広場・建物targetを隠さない
- 4季で幹・pivot・contact pointを変えない
- 桜とモミジの色だけでなく、花・葉形状でも季節差を出す
- 冬もStage差を判別可能

## Spring

- 桜色は背景と同化しない
- 花量はStageに応じて増える
- 花びらなしでも春と分かる

## Summer

- 緑一色の塊にしない
- 明暗2〜3 bandで葉の奥行きを出す
- 建物の緑と識別できる

## Autumn

- モミジ調の赤・橙・黄
- 赤一色で警告色に見せない
- 落ち葉なしでも秋と分かる

## Winter

- 完全な枯死表現を避ける
- 小さな雪帽子・実・灯り等で温かさを残す
- 白背景化で輪郭が消えない

---

# 4. Motion briefs

## Cloud

```txt
full: back 70–120 sec / front 45–90 sec loop candidate
reduced: one layer 120–240 sec
motion off: static
```

数値はprototype candidate。

## Shore foam

```txt
full: 3–6 sec subtle loop candidate
reduced: 6–12 sec
motion off: approved still frame
```

激しい波・海面上下は使わない。

## Tree sway

```txt
full: small canopy sway with long rest
reduced: rare 1–2 px equivalent sway
motion off: static
```

常に左右へ揺らし続けない。

## Sun / moon

screen positionはtime band progressから更新するが、毎frame動かす必要はない。

```txt
full: minute-level or coarse interpolation
reduced: discrete position updates
motion off: fixed representative position
```

---

# 5. Static prototype exports

必須composite:

```txt
E0 spring morning / Tree Stage 0
E1 summer day / Tree Stage 1
E2 autumn night / Tree Stage 2
E3 winter midnight / Tree Stage 2
E4 four time modes / same season and layout
E5 four seasons / same time and layout
E6 motion off visual state
E7 layered fallback
E8 200% text zoom at midnight
E9 low-power composition
E10 privacy reset / current count high / Tree Stage 0
```

各compositeへ添付:

- layer list
- used asset keys
- logical position
- projected bounds
- target overlay
- contrast notes
- motion substitution notes
- asset status

---

# 6. What is worth adding but not P0

## Strong P1 candidates

1. **小さな街灯・窓灯りの個性**
   - 夜の町が一枚の青filterに見えるのを防ぐ

2. **風の統一方向**
   - 雲、木、花びら、落ち葉が別方向へ動く違和感を防ぐ

3. **季節の地面cue**
   - 木だけが衣替えする不自然さを防ぐ

4. **optional ambient sound**
   - 波・風・朝鳥・夜虫
   - default OFF / autoplayなし

5. **星と水面の月光**
   - nightとmidnightを暗さ以外で区別する

6. **小さな自然物**
   - 貝殻、流木、蝶、鳥
   - 収集物にはしない

## Later candidates

- 夏の蛍
- 冬の軽い雪
- 春の花びら
- 秋の落ち葉
- rare sky event
- moon phase variation
- distant island silhouette

---

# 7. Excluded asset scope

初期asset briefへ含めない。

- 釣り道具
- 採集item
- 素材inventory
- 天候別の町全描き直し
- 実在人物avatar
- user memoryの内容を描いた看板
- 位置情報から生成した実空
- 実潮汐animation
- dynamic 3D lighting

---

# 8. Approval gate

Asset制作へ進める条件:

```txt
1. tile metric A/B/C候補が比較可能
2. Memory Treeの最大Growth Envelope候補がある
3. beach位置がmap候補上で承認可能
4. 4時間帯palette roughが揃う
5. 4季Tree silhouette roughが揃う
6. layered fallbackで同じ状態を表現できる
7. motion off stateが成立する
```

実assetをapprovedへ進める条件:

- provenance
- license
- SHA-256
- dimensions
- visual anchor
- depth anchor
- render bounds
- fallback key
- season / stage family compatibility
- contrast evidence

---

# 9. Decision

```txt
最初の環境assetは、
空・海・ビーチ・四季樹・灯り・季節地面cueに集中する。

16枚の完成背景は作らない。

時間帯はoverlayとsky profile、
季節はTreeとground cue、
動きは統一wind / motion profileで組み立てる。
```
