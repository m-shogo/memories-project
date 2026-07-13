# Next Chat Memory Town Spatial Foundation Addendum

最終更新: 2026-07-13

## Decision

Memory Townの箱庭イメージは、Minecraftのような1block建築ではなく、どうぶつの森のように自分の場所へ愛着を持てる2.5D箱庭に近い。

ただし、特定作品のUI、アート、ゲームsystemを複製しない。

```txt
MVPの見た目: 固定2.5D town
MVPの操作: 建物tap menu
内部空間: logical grid / parcel / footprint
将来: 木、花、家具、道、建物移動を段階的に解放
```

## Canonical Docs

優先して読む。

1. `docs/current-product-direction.md`
2. `docs/memory-town-long-term-spatial-model.md`
3. `docs/memory-town-webgl-architecture.md`
4. `docs/memory-town-spatial-foundation-tickets.md`
5. `docs/memory-town-implementation-roadmap.md`

## Key Architecture

```txt
Memory Domain State
Town Projection State
Town Layout State
Town Render State
```

4状態を混ぜない。

### Domain

棚、Import、箱、進行、connection。

### Projection

建物stage、badge、recent delta。

### Layout

map上のobject position、parcel、orientation、user customization。

### Render

PixiJS sprite、camera、animation、selection。

## Spatial Granularity

```txt
terrain / road / flower = tile
small prop / tree / furniture = object
building = multi-cell completed sprite
```

建物を1blockごとの壁、床、屋根へ分解しない。

## MVP Boundary

内部で最初から作る:

- logical grid
- map definition
- parcel
- footprint
- placement layer
- orientation
- versioned layout template
- stable object IDs
- layout revision
- placement validator foundation
- scene snapshot

MVP UIでは作らない:

- free placement editor
- path painting
- building move
- terrain edit
- inventory
- currency
- crafting

## Long-term Customization Sequence

```txt
Phase 0: fixed template
Phase 1: decoration slots
Phase 2: free decor in editable zones
Phase 3: paths and plants
Phase 4: building relocation between parcels
Phase 5: map / district expansion
```

## Critical Rules

- screen x/yを永続化しない
- component内の座標直書きを正本にしない
- major buildingは最大stageのparcelを予約
- stage変更でinstanceIdを変えない
- user decorationをprojection rebuildで消さない
- physical roadとsemantic connectionを分離
- rendererへraw memoryを渡さない
- user placementをmigrationで黙って削除しない

## First Tickets

```txt
MT-SP-001 stable IDs / versions
MT-SP-002 logical coordinate
MT-SP-003 map / parcels
MT-SP-004 object definition catalog
MT-SP-005 footprint / layers
MT-SP-006 layout template
MT-SP-007 placement validator
MT-SP-008 layout commands / revision
MT-SP-009 projection + layout composition
MT-SP-010 Pixi renderer adapter
MT-SP-011 path foundation
MT-SP-012 fallback
MT-SP-013 migration harness
MT-SP-014 test suite
```

## Reject in Review

以下は長期破綻につながる。

```txt
<Building x={320} y={180} /> を保存上の正本にする
sprite boundsでcollision判定
stageごとに別building instance
TownProjection内へuser layoutを保存
roadとmemory relationを同じmodelで管理
固定mapをPixi componentへ直書き
```

## Commits

- `5d426c71a65546a22e4a8cd72dc327d9ec36f859` docs: define long term spatial model for memory town
- `fb9ab59d8e4dbecd80b0a73d28284f21482b2245` docs: align WebGL architecture with long term spatial model
- `63a442787535c5a7a566e7d84bc59ba6b4951714` docs: update product direction for extensible town spatial model
- `3f3964645a00de30cad2e622af15d8add862fa3b` docs: add memory town spatial foundation ticket plan

## Final Rule

```txt
MVPの表面は固定。
内部は最初から将来編集できる。

後からeditorを足す。
空間modelは後から作り直さない。
```
