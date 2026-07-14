# Memory Town Current Authority Order — Round 3 Box-Garden Patterns

最終更新: 2026-07-14

## Current verdict

```txt
box-garden research:
completed

pattern adoption:
completed at design level

visual evidence:
pending

implementation:
NO-GO
```

## Authority order

矛盾時は上を優先する。

1. `memory-town-current-authority-order-round-3-box-garden-patterns.md`
2. `memory-town-adopted-box-garden-patterns-round-3.md`
3. `memory-town-box-garden-pattern-research-round-3.md`
4. `memory-town-design-readiness-gate-round-3-box-garden-patterns.md`
5. `memory-town-current-authority-order-round-2-environment.md`
6. `memory-town-environment-and-seasonal-life-contract.md`
7. `memory-town-current-authority-order-round-1.md`
8. prior Memory Town contracts and fixtures

## Active adopted patterns

```txt
MT-ADOPT-001 Derived Micro-details
MT-ADOPT-002 Draft Town
MT-ADOPT-003 Negative Space and Sightline
MT-ADOPT-004 Empty Town Baseline Life
MT-ADOPT-005 Curated Style Packs
MT-ADOPT-006 Private Postcard / Town History
MT-ADOPT-007 District Identity
MT-ADOPT-008 Ambient Nature
MT-ADOPT-009 Personal Display Slot
MT-ADOPT-010 Gentle Change Summary
```

P2 candidates:

```txt
MT-ADOPT-011 Quiet Surprise
MT-ADOPT-012 One-tap Beautify
MT-ADOPT-013 On-demand Memory Window
```

## Binding decisions

### Derived details

- layout source of truthへ保存しない
- same scene inputからdeterministicに生成
- user objectを削除・移動しない
- migration時に再生成可能
- interaction targetにしない

### Draft Town

- canonical layoutのcopy-on-write draft
- Apply前にserver validation
- atomic command batchで反映
- discard可能
- preview stateをMemory Domainへ保存しない

### Postcard

- private default
- raw memory禁止
- manual capture default
- social feed禁止
- export / delete必須

### Ambient nature

- unnamed generic nature
- affection / hunger / sicknessなし
- user inactivityへ反応しない
- person simulationなし

### Personal display

- user selected
- AI importance selection禁止
- private title default禁止

## Explicit rejections

- daily quest
- login reward
- currency
- crafting
- materials
- placement score
- town rank
- NPC affection
- town decay
- forced cleaning
- limited-time reward
- public town feed
- gacha decoration

## Prototype expansion

既存Environment prototypeへ次を追加する。

```txt
P11 Derived detail ON / OFF
P12 Empty Town baseline life
P13 District identity
P14 Personal Display Slot
P15 Curated style pack
P16 Private Postcard
P17 Draft Town compare / discard
P18 Quiet Surprise motion-off
P19 Maximum-density sightline debug
```

## Implementation prohibition

Round 3 patternを理由にMemory Town実装を開始しない。

開始前に必要:
- Round 1 / 2 machine validation
- Round 2 visual evidence
- Round 3 P11〜P19 evidence
- derived-detail source boundary
- Draft Town command fixture
- postcard privacy projection
- unresolved P0ゼロ
