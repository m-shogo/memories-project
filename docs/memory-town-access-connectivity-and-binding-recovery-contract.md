# Memory Town Access Connectivity and Binding Recovery Contract

最終更新: 2026-07-13

## 目的

入口前が空いているだけで、建物が町のpath networkから孤立する問題を防ぐ。

同時に、primary feature binding先のobjectがstored / retired / missingになっても、棚への入口を失わないようにする。

実装はまだ開始しない。

---

# 1. Three different concepts

```txt
Entrance cell
= 建物の出入口位置

Access cell
= 入口からpath networkへ接続するために必要なcell

Path network
= physical road / footpath / plaza / bridgeの接続graph
```

これらを同じfieldへまとめない。

---

# 2. Access root

Map Definitionは一つ以上のsystem access rootを持つ。

```ts
interface TownAccessRootDefinition {
  accessRootId: string;
  position: TownGridPosition;
  rootType:
    | 'central_plaza'
    | 'map_entry'
    | 'district_entry'
    | 'dock_network';
  enabled: boolean;
}
```

MVP main island候補:

- central square access root
- port dock network root

同一buildingが複数rootへ接続してもよい。

---

# 3. Structure access requirement

```ts
interface TownStructureAccessContract {
  definitionId: string;
  accessContractVersion: number;
  primaryEntranceCells: TownRelativeCell[];
  requiredAccessCells: TownRelativeCell[];
  acceptablePathTypes: Array<'road' | 'footpath' | 'plaza' | 'bridge'>;
  minimumConnectedRoots: number;
  accessibilityRequired: boolean;
}
```

主要Featureを持つstructureは`accessibilityRequired = true`。

---

# 4. Canonical validation order

```txt
schema
→ ownership
→ permission
→ definition availability
→ map bounds
→ parcel
→ footprint collision
→ placement layer
→ growth envelope
→ entrance clearance
→ required access cell occupancy
→ path graph construction
→ access root connectivity
→ category / quota
```

`entrance clearance`と`access root connectivity`を省略しない。

---

# 5. Path graph

Graph node:

```txt
placed path cell
+ enabled access root
+ structure access connector
```

Edge:

- N / E / S / W adjacency
- bridge connector
- dock connector
- explicit map connector

禁止:

- diagonal adjacencyを暗黙接続
- visual sprite overlapだけで接続判定
- semantic connection overlayをphysical pathとして使用

---

# 6. Future path editor rule

User commandがpathを削除・置換する場合、apply前に全required structureを再検証する。

```txt
apply draft command
→ affected graph region再構築
→ required structure access check
→ disconnectedならbatch reject
```

最後のaccess pathを消す操作は拒否する。

Issue code:

```txt
ACCESS_PATH_DISCONNECTED
ACCESS_ROOT_UNREACHABLE
REQUIRED_ACCESS_CELL_BLOCKED
```

---

# 7. Visual path is not functional dependency

Memory Townはmenuであり、建物へのrouteはphysical pathに依存しない。

```txt
path disconnected
≠
feature route unavailable
```

Path validationは町の空間整合のためである。

棚・Inbox・Reflectionは通常DOM navigationから常に到達可能にする。

---

# 8. Primary feature binding availability

Primary bindingのscene利用条件:

```txt
binding exists
AND target instance exists
AND placementState = placed
AND definition available or visual fallback available
AND target allowed for feature
```

利用不可の場合、scene composerは以下を順に試す。

```txt
1. valid primary binding
2. valid portal binding
3. valid secondary binding marked route-capable
4. system fallback portal
5. no visual object, DOM feature route only
```

機能自体を失わせない。

---

# 9. System fallback portal

```ts
interface TownFeatureFallbackPortal {
  featureId: TownFeatureId;
  fallbackDefinitionId: string;
  preferredParcelId?: string;
  canRemainStored: false;
}
```

Rules:

- small neutral sign / portal
- sensitive feature名を画像へ焼き込まない
- routeはDOM側で解決
- major structureの代替として自動成長しない
- user objectを勝手に退避して設置しない
- placement不能ならDOM-only routeへ落とす

---

# 10. Binding migration

Definition廃止・instance migration時:

```txt
old binding
→ replacement instance candidate
→ compatibility validation
→ Preview
→ binding update
```

禁止:

- instance ID変更だけでbinding消失
- stored instanceへprimary bindingを残したまま正常扱い
- routeをdefinitionへ埋め込む

---

# 11. Required fixtures

- all six initial structures reach an access root
- port has dock network access
- path deletion isolates cinema and is rejected
- semantic overlay does not satisfy access
- primary instance stored, portal fallback selected
- primary and portal missing, DOM-only route remains
- definition deprecated with replacement binding
- user path edit preserves all required access

---

# Decision

```txt
入口が空いているだけではPASSにしない。
Physical path graphからaccess rootまで到達できることを検証する。

それでもFeature routeは道や建物のvisual状態に依存させない。
Visual入口が壊れてもDOM navigationは残す。
```
