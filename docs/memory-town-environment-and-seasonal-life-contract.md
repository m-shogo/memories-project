# Memory Town Environment and Seasonal Life Contract

最終更新: 2026-07-13

## 目的

Memory Townを、建物だけが並ぶ静止メニューではなく、空・光・海・風・季節の木が静かに生きている場所として成立させる。

本契約は次を固定する。

- 現在時刻に連動する4つの時間帯
- 雲・太陽・月・波の継続的な動き
- ビーチと海岸線
- 情報量に応じて育つ町の象徴樹
- 春の桜、秋の紅葉を含む四季表現
- reduced motion / low power / fallback
- inactivityや記憶内容を環境の罰表現へ使わないこと

実装はまだ開始しない。

---

# 1. Product intent

```txt
町は建物だけでなく、空・海・光・木で生きている。

時間は現在時刻に寄り添う。
季節は一年の流れを感じさせる。
木は保存した情報量の積み重ねを、評価せず粗い段階で表す。
```

環境演出は次を目的とする。

- 町へ戻った瞬間に「今の時間」を感じる
- 四季による長期利用の変化を作る
- 記録が少ない時でも空虚に見せない
- 操作しなくても眺められる
- Memory OS本体の検索・棚・Importを邪魔しない

環境演出は報酬回収、放置ゲーム、streak、幸福度表現ではない。

---

# 2. Time model

## 2.1 Canonical four modes

正式な時間帯は次の4つとする。

```txt
morning   朝

day       昼

night     夜

midnight  夜中
```

`evening`を独立した第5状態にはしない。
夕方の色味は`night`への遷移区間として表現する。

## 2.2 Device-local resolver

初期resolverは端末のlocal timeを使用する。

```txt
05:00–10:59  morning
11:00–16:59  day
17:00–22:59  night
23:00–04:59  midnight
```

この境界はvisual prototype候補であり、比較後に承認する。

Rules:

- precise locationを要求しない
- GPSを使用しない
- 天文学的な日の出・日の入りを正確に再現すると主張しない
- timezoneは端末設定に従う
- 旅行等でtimezoneが変われば次回resolve時に追従する
- local time自体をMemory Domainへ保存しない

## 2.3 Manual override and preview

ユーザーは次を選べる。

```txt
auto
morning fixed
day fixed
night fixed
midnight fixed
```

デザイン確認用のpreview modeはTown Render Stateにのみ存在し、保存設定と混ぜない。

```txt
preview morning
preview day
preview night
preview midnight
preview spring / summer / autumn / winter
```

Preview終了時は元のeffective stateへ戻る。

## 2.4 Transition

時間境界でsceneを瞬間的に全面交換しない。

候補:

```txt
palette crossfade
sky gradient crossfade
building light fade
shadow preset crossfade
celestial object handoff
```

太陽・月のscreen positionは、各time band内の進行率から視覚的に動かす。

ただし:

- 本物の天体位置とは表現しない
- 影は連続物理simulationではなく4 preset間のcrossfade
- background tabでは進行を停止し、復帰時に現在stateへsnapまたは短時間補間

---

# 3. Sky system

空は一枚背景へ焼き込まない。

```txt
sky gradient
cloud back layer
cloud front layer
sun or moon
star layer
atmospheric haze
```

## 3.1 Morning

- 低い位置から暖色の光
- 雲の端に薄い金色
- 建物灯りは一部だけ残る
- 海面の反射は柔らかい
- 強い赤焼けにはしない

## 3.2 Day

- 最も高い視認性
- 空は明るいが白飛びしない
- 建物識別色を潰さない
- 木陰と海の青を感じる

## 3.3 Night

- 夕方から夜へ入る深い青
- 建物窓・街灯が点く
- 港と海岸の輪郭を失わない
- UIのcontrastを環境paletteへ依存させない

## 3.4 Midnight

- 夜より深い空色
- 月と星が明確
- 建物灯りをすべて消さない
- 海面に月明かりの帯を出せる
- 暗さを罰・孤独・不安の演出へ寄せない

## 3.5 Cloud motion

雲は常にゆっくり移動する。

```txt
full motion:
  2 layers / different speed / subtle parallax

reduced motion:
  1 layer / very slow drift

motion off:
  static cloud composition
```

雲の移動は建物のtap targetやhit polygonへ影響しない。

---

# 4. Unified wind field

雲、木、波、花びら、落ち葉を別々の乱数で動かさない。

Town Environment Stateから一つのambient wind fieldを導出する。

```ts
interface TownAmbientWindSnapshot {
  directionBand: 'left' | 'right' | 'calm';
  intensityBand: 'calm' | 'soft' | 'normal';
  phaseSeed: string;
}
```

Rules:

- gameplay physicsではない
- precise weatherとは主張しない
- scene内の動きに統一感を与えるためだけに使う
- motion offでは全visual motionを停止
- low powerではcloud / waveの最低限だけ残すか静止する
- phaseSeedへuser memory contentを使わない

---

# 5. Beach and shoreline

ビーチは初期mapへ含める。

## 5.1 Spatial role

推奨位置:

```txt
map lower side or lower-right
portと連続
中央広場と主要建物の視認を圧迫しない
```

ビーチは背景画像へ焼き込まず、Map Definition上のterrainとして扱う。

```txt
water
coast
sand
```

将来mapを拡張しても海岸線を再利用できる構造にする。

## 5.2 Wave layers

波は最低3層へ分ける。

```txt
1. distant water drift
2. surface sparkle / reflection
3. shoreline foam loop
```

Rules:

- waveは短いseamless loop
- shoreline foamが砂へ入りすぎない
- wave animationでcoastline geometryを変更しない
- interaction collisionはanimationから独立
- actual tide levelとは主張しない
- real tide APIは初期採用しない

## 5.3 Beach details

初期に入れる候補:

- 小さな貝殻
- 流木1つ
- 砂の淡い足跡
- 港へ続く木道
- 海面の時間帯反射

初期に入れない:

- 素材採集
- 釣り
- 貝拾い報酬
- 潮汐gameplay
- beach inventory

ビーチは生活感と開放感のためであり、別ゲームの入口にしない。

---

# 6. Memory Tree / 四季樹

## 6.1 Role

町の中心または中央広場付近に、象徴となる一本の木を置く。

正式な仮称:

```txt
Memory Tree
四季樹
```

現実の単一樹種を厳密に再現しない、絵本的な架空樹とする。

これにより次を両立する。

```txt
春: 桜のような花
夏: 深い緑
秋: モミジのような紅葉
冬: 枝・雪・暖かな灯り
```

「春は桜、秋はモミジ」が一つの木に現れることを、意図的な幻想表現として扱う。

## 6.2 Growth source

木は情報の内容や価値ではなく、eligibleな保存量の粗いaggregateで育つ。

使用可能:

- eligible memory record count
- eligible shelf / box item countの重複排除aggregate

使用禁止:

- AI importance score
- 感情の強さ
- 人生の幸福度
- 特定人物への愛情量
- streak
- 課金額
- ログイン日数

hidden / sealed / restricted / deleted dataはaggregateから除外する。

## 6.3 Growth stages

初期は3段階。

```txt
Stage 0: 小さな若木
Stage 1: 町に根付いた木
Stage 2: 町の象徴となる大木
```

Stage thresholdの具体数値はvisual / product prototype候補であり、まだ固定しない。

## 6.4 Non-shrinking and privacy

通常のrecord削除やImport取り消しでは、木を罰のように縮ませない。

ただし、木の大きさは過去の情報量を粗く推測させる可能性があるため、次を必須にする。

```txt
木の成長履歴をReset
木の成長表現を非表示
町全体の成長履歴をReset
privacy reset時に木の履歴も消す
```

木のStageから正確な件数を逆算できるUIを提供しない。

## 6.5 Seasonal variants

### Spring

- 桜色の花
- 葉は淡い緑
- 花びらはfull motionのみ少量
- 花びらで建物やDOM labelを隠さない

### Summer

- 深い緑
- 木陰を感じる
- 生命力は出すが、記録数競争の誇張をしない

### Autumn

- 赤・橙・黄のモミジ調
- 葉の落下は少量
- 地面を全面落ち葉で埋めない

### Winter

- 葉が減る
- 雪帽子または小さな灯り
- 完全に枯死・荒廃した見た目にしない
- Stage差が判別できるsilhouetteを維持

## 6.6 Asset multiplication control

初期asset family:

```txt
3 growth stages
× 4 seasons
= 12 principal tree sprites
```

時間帯ごとの別spriteは作らず、light / shadow overlayで対応する。

---

# 7. Seasonal environment beyond the tree

木だけを差し替えると町全体の四季が弱いため、地面と小物へ小さな季節差分を持たせる。

## P0

```txt
spring: small flower patches / pale grass
summer: deep grass / bright shore reflection
autumn: small fallen-leaf patches / warm ground tint
winter: light snow caps / winter grass / warm lamps
```

## P1

```txt
spring: drifting petals
summer: butterflies or fireflies at night
autumn: occasional falling leaves
winter: light snow
```

## P2

```txt
seasonal beach props
rare sky events
moon phase variation
small migratory birds
```

P1 / P2はambient densityとperformance evidence後に採用判断する。

---

# 8. Lighting and shadow

今の設計に追加必須とする。

## 8.1 Four lighting presets

```txt
morning
  warm low-angle light

day
  neutral high light

night
  cool ambient + warm windows

midnight
  deep cool ambient + moon rim + selected warm lights
```

## 8.2 Shadow policy

- 物理的なdynamic shadow simulationを初期採用しない
- structureごとにcontact shadowを持つ
- 時間帯でshadow direction / opacity presetを切り替える
- transition時だけcrossfade
- shadowはhit polygonへ影響しない
- dark mode UI contrastをscene shadowへ依存させない

## 8.3 Building lights

夜・夜中は建物に個別の灯りoverlayを持てる。

- cinema sign
- story-house window
- market lantern
- port light
- warehouse guide light
- square lamps

灯りは未整理件数や利用頻度で消さない。

---

# 9. Ambient sound foundation

音は初期からasset contractだけ用意するが、defaultはOFF。

候補:

```txt
shore wave
soft wind
morning birds
evening insects
quiet midnight sea
```

Rules:

- autoplay禁止
- user gesture後のみ開始
- soundEnabled falseがdefault
- route leaveで停止
- background tabで停止
- 個人情報やmemory contentから音を生成しない
- 音がなくても情報欠落なし

---

# 10. What should be included first

## P0 — Initial visual prototypeに必須

- 4 time modes
- time-linked palette
- sun / moon position progression
- cloud drift
- building light overlays
- beach terrain
- 3-layer wave concept
- Memory Tree 3 growth stages
- Memory Tree 4 seasonal variants
- seasonal ground cues
- unified wind field
- motion off / reduced / full
- manual time / season preview
- functional fallback

## P1 — First ambient enhancement候補

- spring petals
- autumn falling leaves
- light winter snow
- summer fireflies
- small birds
- optional ambient sound
- subtle water reflection animation

## P2 — Evidence後のみ

- moon phases
- rare sky events
- richer beach props
- generic citizens
- district-specific climate

## Explicitly not initial

- real weather sync
- real tide sync
- astronomical sun position
- GPS location
- collecting / fishing / crafting
- weather affecting memory value
- inactivity decay
- emotional weather inferred by AI

---

# 11. Performance and motion budget

全部を常時動かさない。

Motion priority:

```txt
1. shoreline foam
2. cloud drift
3. tree sway
4. sun / moon progression
5. seasonal particles
6. minor props
```

Low power時:

```txt
shoreline animation reduced or static
cloud one layer or static
tree static
particles off
sun / moon position updated discretely
```

Route leave / hidden tab:

- ticker停止
- animation clock停止
- async asset completionはsession fence確認
- 復帰時に現在のeffective timeへ再resolve

---

# 12. Accessibility and fallback

DOM interaction treeは環境animationと独立する。

- Canvasはaria-hidden
- 雲・太陽・月・波・木の揺れをscreen reader targetにしない
- Memory Treeを押せる場合はDOM targetを別途持つ
- motion offでも季節と時間帯を色だけに依存せず、必要ならDOM labelで確認可能
- high contrastではsky / seaの装飾contrastを下げても、建物targetとfocus ringを維持

Layered fallback:

```txt
sky layer
terrain / beach layer
water layer
path layer
building layer
Memory Tree seasonal sprite
light overlay
DOM controls
```

一枚の固定背景だけをfallback正本にしない。

---

# 13. Required prototype scenes

既存P0〜P10に次を追加する。

```txt
E0 spring morning / Tree Stage 0
E1 summer day / Tree Stage 1 / beach visible
E2 autumn night / Tree Stage 2 / building lights
E3 winter midnight / Tree Stage 2 / no dead-town impression
E4 all four time modes side-by-side
E5 all four seasons side-by-side
E6 motion off / reduced / full comparison
E7 layered fallback with Tree and beach
E8 200% text zoom over midnight scene
E9 low power static environment
E10 privacy reset: many current records / Tree Stage 0
```

---

# 14. Acceptance gates

## ENV-1 Time clarity

- 4 time modesをラベルなしでも概ね区別可能
- nightとmidnightが暗さだけでなく月・星・灯りで違う
- morningとdayが暖色filterだけの違いにならない

## ENV-2 Seasonal clarity

- 4季をMemory Treeと地面の両方で区別可能
- springは桜、autumnはモミジ調と認識できる
- winterが失敗・死・放置の罰に見えない

## ENV-3 Beach quality

- 港との関係が自然
- 波がloop seamを目立たせない
- beachが中央buildingを圧迫しない
- actual tide / real weatherと誤認させない

## ENV-4 Motion safety

- motion offで完全静止可能
- reduced motionで意味を失わない
- particlesなしでも季節を判別可能
- low power候補で視覚品質を維持

## ENV-5 Growth safety

- 木の成長が情報の価値評価に見えない
- 粗い3段階で十分な差がある
- privacy reset後にStage 0を維持可能
- current countが多くてもReset直後に即復帰しない

## ENV-6 Accessibility

- DOM targetとCanvas hit areaが二重focusにならない
- 200% text zoomで主要機能へ到達可能
- midnightでもfocus ringとlabel contrastを満たす

---

# 15. Final decision

```txt
初期Memory Townへ、
朝・昼・夜・夜中、雲、太陽・月、ビーチ、波、四季樹を含める。

環境は一枚背景へ焼き込まず、layered systemとして定義する。

さらに、
風の統一制御、時間帯ごとの光と影、季節の地面差分、
手動preview、motion budget、optional sound foundationを最初から契約へ含める。

実天気・潮汐・天文位置・収集gameplayは初期採用しない。
```
