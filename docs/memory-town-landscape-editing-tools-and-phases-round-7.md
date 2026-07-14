# Memory Town Landscape Editing Tools and Phases — Round 7

最終更新: 2026-07-14

## 目的

海、川、道、森、家、砂浜、地区増築を、mobileで無理なく編集できる段階と操作へ分解する。

```txt
自由度を一度に全部渡さない。
景観を壊しにくい順に解放する。
```

実装はまだ開始しない。

---

# 1. Editor principle

Memory Town editorは専門的なmap editorではない。

ユーザーが理解する言葉:

- 草地にする
- 砂浜を広げる
- 川を曲げる
- 道を引く
- 森を増やす
- 家を移す
- 新しい地区を足す

内部用語のtile ID、edge mask、WFC、chunkは通常UIへ出さない。

---

# 2. Common editor shell

全tool共通:

```txt
Draft Townを開く
→ tool選択
→ edit
→ undo / redo
→ before / after
→ validate
→ Apply or Discard
```

必須UI:

- 現在tool
- 編集対象layer
- undo
- redo
- reset current stroke
- compare
- Apply
- Discard
- Home / landmark shortcut
- invalid area説明

禁止:

- edit gestureごとのserver save
- confirmation dialogの連発
- user objectのsilent deletion
- 失敗時に町全体をreset
- coin / material消費

---

# 3. Tool catalog

## 3.1 Ground Brush

編集対象:

- grass
- soil
- sand
- stone
- forest floor
- plaza surface

操作:

```txt
指でなぞる
→ semantic terrain regionを更新
→ edge / cornerを自動再描画
```

Modes:

- small
- medium
- area fill
- erase to district default

Rules:

- building footprint下はpaint不可またはwarning
- path上はbase terrainだけ変更しpathを保持
- sandをpaintしても自動でseaにならない
- style variationはuserへtile単位で選ばせない

## 3.2 Coast and Beach Tool

編集対象:

- land / shallow-water boundary
- beach width
- small cove
- small cape
- rocks / dune style

操作候補:

```txt
coast bandを選ぶ
→ boundary handleをdrag
→ sand bufferを自動生成
→ Preview
```

Brushだけでlandを大量に消すより、coast bandとcontrol handlesを優先する。

Hard rules:

- distant seaへ接続
- isolated one-cell ocean禁止
- protected building parcel侵入禁止
- harbor pier anchor維持
- access path維持

Optional profiles:

- soft sandy coast
- rocky coast
- mixed coast
- harbor edge

## 3.3 River / Stream Tool

操作:

```txt
sourceまたはexisting nodeを選択
→ fingerでrouteをdraw
→ outlet / pondへ接続
→ width選択
→ bank / bridge crossingを自動生成
```

User controls:

- route
- width: narrow / standard / broad
- style: stream / river / canal
- bank softness

System controls:

- flow continuity
- invalid crossing
- bridge candidate
- bank clearance
- district socket connection

One-cell water paintingをmain interactionにしない。

## 3.4 Road / Path Tool

操作:

```txt
start node
→ fingerでdraw
→ end node
→ junction / curve / plaza join自動生成
```

Kinds:

- main road
- footpath
- river promenade
- boardwalk
- plaza link

Options:

- surface style
- width profile
- lamp style
- edge planting profile

System must:

- nearest valid nodeへ弱くsnap
- accidental loopをwarning
- building entranceへconnect候補を表示
- path graph到達性をvalidate

## 3.5 Forest / Vegetation Brush

操作:

```txt
森にしたい範囲をpaint
→ density選択
→ tree cluster preview
```

Kinds:

- forest
- grove
- flower field
- shrub border

User can:

- density変更
- species style変更
- specific treeをpin
- clearingを作る

System must:

- path / river / parcel clearance
- repeated pattern軽減
- deterministic placement
- season variant
- silhouette density limit

## 3.6 Building and House Move Tool

操作:

```txt
building選択
→ approved parcel候補表示
→ parcelへdrag / tap
→ orientation preview
→ road connection preview
```

User can:

- parcel変更
- orientation
- skin
- surrounding style pack

System must preserve:

- feature binding
- route
- instance ID
- progress stage
- user data
- entrance accessibility

## 3.7 Bridge Tool

Bridgeをriver上の任意pixelへ置かない。

```txt
road / pathとwaterのcrossing
→ approved bridge anchor生成
→ bridge type選択
```

Types:

- stone arch
- small wooden bridge
- boardwalk bridge
- simple flat bridge

Bridge change must not rewrite river source data.

## 3.8 District Expansion Tool

操作:

```txt
町の端を開く
→ expansion socket表示
→ district template選択
→ rotate / preview
→ connection validation
→ attach
```

District candidates:

- forest edge
- quiet residential
- culture hill
- extended harbor
- beach cove
- river upstream
- reflection garden
- future media district

User can later edit terrain inside the district according to phase.

Attach must:

- keep existing coordinates
- connect required road / river / coast sockets
- preserve view corridor
- avoid abrupt asset seam
- create rollback snapshot

## 3.9 Area Reset / Clear Tool

One-by-one removalを強制しない。

Options:

- selected decoration only
- vegetation region
- path segment
- district user edits
- district to template baseline

Removed user objects:

```txt
stored
not deleted
```

---

# 4. Editing phases

## Phase 0 — Authored town

- fixed initial layout
- bounded pan
- no editor
- internal semantic landscape model only

目的:

- scenery quality
- navigation
- Memory-first response

## Phase 1 — Style and safe slots

Editable:

- Personal Display Slot
- flag
- lamp
- bench
- flower slot
- bridge skin
- district style pack

No terrain edit.

## Phase 2 — Vegetation and ground surface

Editable:

- grass / soil / stone / forest floor
- forest / grove / flower regions
- clearing

Still fixed:

- coast
- main river
- primary road
- main buildings

## Phase 3 — Paths and minor water

Editable:

- footpath
- promenade
- boardwalk
- minor canal / pond candidate
- bridge choices

Fixed:

- main coast
- river source / outlet

## Phase 4 — Coast and river reshape

Editable:

- beach width
- small cove / cape
- river route within approved corridor
- stream branch
- bridge position at generated crossing

Requires strong Draft / validation / rollback.

## Phase 5 — Building relocation

Editable:

- major building parcel
- house parcel
- orientation
- surrounding access path

Not free pixel movement.

## Phase 6 — District expansion

Editable:

- expansion socket
- district template
- attached orientation
- district internal landscape

Map extent grows.

## Phase 7 — Terrace / elevation bands

Research phase.

Possible:

- flat
- low terrace
- high terrace
- cliff edge
- approved stairs / ramp

Not arbitrary continuous height sculpt.

---

# 5. Mobile gesture rules

Town browse mode:

- one-finger drag = camera pan
- tap = select feature

Edit mode:

- one-finger draw = active brush / line
- two-finger drag candidate = camera pan
- explicit hand tool = camera pan fallback
- long press禁止を基本とし、discoverabilityを優先

Because two-finger gestures may be inaccessible, every edit scene must provide:

- visible Pan tool
- landmark shortcuts
- zoom-free completion path
- DOM list / command equivalent where applicable

Tap versus draw threshold must be prototyped.

---

# 6. Preview language

Good:

- 「ここまで砂浜になります」
- 「川は港へつながります」
- 「この家は市場地区へ移動します」
- 「橋を追加すると道がつながります」
- 「この地区を町の東側へ追加します」

Bad:

- `mask 0110`
- `WFC conflict`
- `tile rule missing`
- `chunk invalid`

Internal codeはstable issue codeとして保持し、user messageは具体的な結果を説明する。

---

# 7. Required edit prototypes before images

画像生成より先に、構造diagramとして次を作る。

```txt
E0 landscape layers exploded view
E1 ground brush before / after
E2 coast reshape before / after
E3 river draw and bridge candidate
E4 road draw and junction update
E5 forest region and pinned tree
E6 building parcel move
E7 district expansion socket
E8 area reset to stored objects
E9 asset style swap with same semantic layout
```

その後の景観画像:

```txt
V0 authored initial town
V1 same town after coast edit
V2 same town after forest edit
V3 same town after building move
V4 same town after new district expansion
```

全画像は「同じsemantic townが編集された」ことを比較できるようにする。
