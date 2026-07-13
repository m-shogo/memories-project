# Memory Town Growth Envelope and Access Contract

最終更新: 2026-07-13

## 目的

主要建物の成長により、道路、入口、ユーザー装飾、住人経路が壊れることを防ぐ。

従来の`reservedGrowthCells`だけでは、以下を区別できない。

```txt
将来建物本体が占有するcell
入口として常に空けるcell
道を維持するcell
見た目の張り出しだけが通るcell
建物付属overlayだけを置ける領域
```

本書で責務を分離する。

実装はまだ開始しない。

---

# 1. Growth envelopeを5領域に分ける

```ts
interface TownGrowthEnvelopeDefinition {
  envelopeId: string;
  envelopeVersion: number;
  definitionId: string;
  supportedStages: number[];
  maxSolidOccupiedCells: TownRelativeCell[];
  persistentEntranceCells: TownRelativeCell[];
  protectedClearanceCells: TownRelativeCell[];
  requiredAccessPathCells: TownRelativeCell[];
  visualOverflowCells: TownRelativeCell[];
  overlaySlots: TownGrowthOverlaySlot[];
}
```

## 1.1 maxSolidOccupiedCells

承認済みstageのいずれかで、建物本体がsolidとして占有し得るcell。

Rules:

- user solid objectを置けない
- physical pathを置けない
- flower / ground decorも原則置けない
- stage変更で自動退避を発生させないため、最初から保護する
- 現在stageのoccupiedCellsを必ず包含する

## 1.2 persistentEntranceCells

全stageで入口・出口として維持するcell。

Rules:

- stage間で基本位置を変えない
- solid objectを置けない
- physical pathは置ける
- pathがない状態は許容できるが、navigation connectorは維持する
- decorationはoverlay以外禁止

## 1.3 protectedClearanceCells

入口前、搬入口、枝や庇の安全余白など、solid occupancyを禁止するcell。

Rules:

- physical pathを置ける
- low-profile ground decorは定義が明示した場合だけ許可
- tree / furniture / structureは禁止
- stage assetの透明余白から自動生成しない

## 1.4 requiredAccessPathCells

主要動線として、template・migration後も接続確認を行うcell。

Rules:

-必ずpath tileが存在する、という意味ではない
- 入口から公共path networkまで到達可能かをvalidatorが確認する
- user editorでpathを消す場合、警告または拒否を返す
- MVP固定layoutではpath接続を必須にする

## 1.5 visualOverflowCells

屋根、旗、木の枝、看板などが見た目上張り出す可能性のあるcell。

Rules:

- collision正本にはしない
- z-sort / occlusion / camera framing検査に使う
- hit areaを自動的に広げない
- visual overflowが隣parcelの主要objectを完全に隠さないことをasset reviewする

---

# 2. overlay slot

```ts
interface TownGrowthOverlaySlot {
  slotKey: string;
  allowedCategories: TownObjectCategory[];
  supportedStages: number[];
  persistencePolicy:
    | 'preserve_when_supported'
    | 'store_when_unsupported'
    | 'replace_by_system_variant';
}
```

Overlayはmap cellを占有しない。

例:

- cinema poster
- story house new-volume flag
- port boat
- central square month capsule
- seasonal snow cap

Rules:

- owner instanceへ追従
- owner definition差し替え時にslot compatibilityを検証
- stage変更後にslotがなくなる場合、user-owned overlayは黙って削除せずstoredへ移す
- system-derived temporary overlayは再生成可能

---

# 3. Footprintとの関係

```txt
TownFootprint.occupiedCells
= 現在のdefinition基本占有cell

TownGrowthEnvelope.maxSolidOccupiedCells
= 承認済み全stageの最大solid占有集合
```

`reservedGrowthCells`という曖昧なfieldは、v1 contractでは次の意味へ限定する。

```txt
reservedGrowthCells
= maxSolidOccupiedCells
```

入口、clearance、path、visual overflowを含めない。

将来schema major versionでは`reservedGrowthCells`を廃止し、Growth Envelope参照だけへ移行してよい。

---

# 4. Cell coexistence matrix

| Cell class | Base terrain | Physical path | Ground flower | Furniture/tree | Structure | Overlay |
|---|---:|---:|---:|---:|---:|---:|
| maxSolidOccupied | yes | no | no | no | owner only | owner slot only |
| persistentEntrance | yes | yes | no | no | no | owner slot only |
| protectedClearance | yes | yes | rule-dependent | no | no | compatible only |
| requiredAccessPath | yes | yes | no | no | no | semantic overlay allowed |
| visualOverflow | yes | unaffected | unaffected | spatial validator unaffected | spatial validator unaffected | allowed |

同じcellが複数classに属する場合、最も厳しいruleを採用する。

ただし`persistentEntrance + requiredAccessPath`は通常の組合せとして許可する。

---

# 5. Stage compatibility

新stageをcatalogへ追加する前に、次を検証する。

```txt
1. occupied cells ⊆ maxSolidOccupiedCells
2. entrance cells = persistentEntranceCells または互換mappingあり
3. required access pathが維持される
4. protected clearanceを侵食しない
5. visual overflowがcamera / neighboring parcel budget内
6. overlay slot compatibilityが定義される
7. supported orientationごとの同一検証
8. existing user layoutsに対するgolden migration test
```

一つでも満たさないstageは、asset manifestへ追加するだけでは公開できない。

---

# 6. Entrance stability

主要建物のprimary entranceは、原則としてstage間で同じrelative cellを使う。

変更が必要な場合:

```txt
new entrance proposal
→ route compatibility check
→ affected physical paths
→ citizen navigation migration
→ user preview
→ atomic layout migration
→ rollback snapshot
```

単なるasset都合で入口を移動しない。

---

# 7. Path connectivity validation

MVP:

```txt
各primary building entrance
→ central public path network
```

への接続を検証する。

将来editor:

- pathを消した結果、入口が孤立する場合は`ACCESS_PATH_DISCONNECTED`
- editor phaseによってwarningまたはerror
- system-fixed buildingのprimary accessは初期はerror
- decorative dead-end pathは許可

Semantic connection overlayは、この判定へ影響しない。

---

# 8. Decoration rules around growth envelope

## Grid decoration

- maxSolidOccupiedへ置けない
- persistentEntranceへ置けない
- protectedClearanceはdefinition allowlistが必要
- requiredAccessPathへ置けない

## Overlay decoration

- owner slot compatibilityのみ検証
- grid collisionへ含めない
- hit areaを重要操作の唯一手段にしない

## Temporary system decoration

月箱、季節物など再生成可能なもの。

- user-owned objectと別origin
- migrationで再配置可能
- private memory内容を埋め込まない

---

# 9. Validation issue codes

```txt
GROWTH_ENVELOPE_SOLID_RESERVED
GROWTH_ENTRANCE_OCCUPIED
GROWTH_CLEARANCE_BLOCKED
ACCESS_PATH_DISCONNECTED
STAGE_OUTSIDE_GROWTH_ENVELOPE
STAGE_ENTRANCE_INCOMPATIBLE
OVERLAY_SLOT_UNSUPPORTED_AT_STAGE
VISUAL_OVERFLOW_BUDGET_EXCEEDED
```

既存の汎用`GROWTH_ENVELOPE_RESERVED`は、UI互換用の上位categoryとして残してよい。

---

# 10. Prototype requirements

各主要建物についてStage 0〜2のsilhouette prototypeを作り、以下を記録する。

```txt
definitionId
stage
occupied cells
entrance cells
visual overflow cells
shadow bounds
signage bounds
hit polygon
mobile viewport screenshots
```

検証viewport:

```txt
360x800
375x812
390x844
393x852
412x915
430x932
```

必要な比較:

- overviewで識別可能か
- focus時にbottom sheetで隠れないか
- parcel内に収まるか
- neighboring buildingを隠さないか
- stage差が分かるか
- entranceと道が自然か

---

# 11. Current fixture status

`object-catalog.v1.json`のfootprint / reserved growth cellは、prototype候補である。

以下は正本として固定済み:

- cell class分離
- entranceとsolid growthの分離
- path coexistence rule
- overlay slot rule
- stage publish gate

以下はasset prototype後に更新可能:

- 各cell集合の具体座標
- visual overflow
- hit polygon
- shadow bounds

変更時はobject definition / envelope versionを上げる。

---

# 12. Exit gate

```txt
[ ] 6主要建物にGrowth Envelope fixtureがある
[ ] reservedGrowthCellsに入口・path cellが混ざっていない
[ ] 全stage occupiedがmaxSolidOccupied内
[ ] primary entranceがstage間で安定
[ ] path connectivity fixtureがある
[ ] overlay slot compatibility fixtureがある
[ ] mobile 6 viewportのsilhouette比較がある
[ ] neighboring parcel occlusion review済み
[ ] stage追加migration golden testがある
```

---

# 結論

```txt
建物が育つ余白を、単なる空きマスとして扱わない。

建物本体
入口
生活道路
安全余白
見た目の張り出し
overlay

を分離して初めて、長期の町が壊れない。
```
