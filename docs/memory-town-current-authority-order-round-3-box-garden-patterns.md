# Memory Town Current Authority Order — Round 3 Box-Garden Patterns

最終更新: 2026-07-14

## Current verdict

```txt
box-garden research: completed
all 13 patterns: formally adopted
permanent non-goals: locked
visual evidence: pending
implementation: NO-GO
```

## Authority order

矛盾時は上を優先する。

1. `memory-town-full-pattern-adoption-and-permanent-non-goals-round-4.md`
2. `memory-town-current-authority-order-round-3-box-garden-patterns.md`
3. `memory-town-adopted-box-garden-patterns-round-3.md`
4. `memory-town-box-garden-pattern-research-round-3.md`
5. `memory-town-design-readiness-gate-round-3-box-garden-patterns.md`
6. `memory-town-current-authority-order-round-2-environment.md`
7. `memory-town-environment-and-seasonal-life-contract.md`
8. `memory-town-current-authority-order-round-1.md`
9. prior Memory Town contracts and fixtures

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
MT-ADOPT-011 Quiet Surprise
MT-ADOPT-012 One-tap Beautify
MT-ADOPT-013 On-demand Memory Window
```

P0 / P1 / P2は採否ではなく導入順を示す。全項目が長期製品方針として採用済み。

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

### Quiet Surprise
- no FOMO
- no reward
- preview再現可能
- motion off / accessibility equivalent必須

### One-tap Beautify
- Draft Townまたはpreview上で適用
- Undo必須
- user object非破壊
- access / Growth Envelope validation必須

### On-demand Memory Window
- explicit consent
- private processing
- sourceへ戻れる
- hallucination disclosure
- person simulation禁止
- delete / export必須

## Permanent explicit rejections

- daily quests / 毎日の依頼
- login rewards
- currency
- materials / crafting
- furniture gacha
- placement / adjacency score
- town / life rank
- NPC affection
- hunger / sickness / care obligation
- town decay
- forced cleaning
- inactivity penalty
- limited-time reward / decoration FOMO
- public town feed
- follower competition
- streak
- building wait timer
- paid growth acceleration

通常のfeature判断で復活させない。変更にはRound 4 decision documentを更新する明示ADRとwellbeing / privacy / adversarial reviewを必要とする。

## Prototype expansion

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
P20 One-tap Beautify preview / undo
P21 Memory Window consent / source / deletion
```

## Implementation prohibition

本採用決定を理由にMemory Town実装を開始しない。

開始前に必要:
- Round 1 / 2 machine validation
- Round 2 visual evidence
- Round 3 P11〜P21 evidence
- derived-detail source boundary
- Draft Town command fixture
- postcard privacy projection
- Ambient Nature emotional-safety review
- Memory Window privacy / consent contract
- unresolved P0ゼロ
