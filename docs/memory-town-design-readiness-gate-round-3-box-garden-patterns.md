# Memory Town Design Readiness Gate — Round 3 Box-Garden Patterns

最終更新: 2026-07-14

## Verdict

```txt
box-garden research: completed
all 13 pattern adoption: approved
permanent non-goals: locked
contract integration: partial
visual prototype: pending
implementation: NO-GO
```

P0 / P1 / P2は採否ではなく導入時期を表す。全13項目は採用済み。

## R3-1 Derived Micro-details

Status: DESIGN ADOPTED / CONTRACT AND VISUAL PENDING

- [✓] deterministic
- [✓] reversible
- [✓] privacy neutral
- [✓] user object non-destructive
- [✓] render-derived, not layout source of truth
- [ ] rule catalog
- [ ] migration behavior
- [ ] ON/OFF prototype
- [ ] maximum-density test

## R3-2 Draft Town

Status: PRODUCT ADOPTED / COMMAND INTEGRATION PENDING

- [✓] copy-on-write concept
- [✓] canonical layout unchanged until Apply
- [✓] compare / discard
- [✓] time / season / stage preview
- [ ] draft revision model
- [ ] expiry and cleanup
- [ ] atomic apply fixture
- [ ] cross-device conflict behavior

## R3-3 Negative Space

Status: DESIGN ADOPTED / METRIC PENDING

- [✓] landmark sightline
- [✓] coast visibility
- [✓] major silhouette separation
- [✓] motion-off readability
- [ ] open-ground candidate ratio
- [ ] front-prop density threshold
- [ ] six-viewport evidence

## R3-4 Private Postcard

Status: P1 ADOPTED / PRIVACY CONTRACT PENDING

- [✓] private default
- [✓] manual capture default
- [✓] no social feed
- [✓] raw memory excluded
- [ ] snapshot schema
- [ ] deletion / export
- [ ] stale visual label
- [ ] storage retention

## R3-5 Ambient Nature

Status: P1 ADOPTED / EMOTIONAL-SAFETY PENDING

- [✓] unnamed generic nature only
- [✓] no affection / hunger / sickness
- [✓] no inactivity reaction
- [✓] no person simulation
- [ ] initial species shortlist
- [ ] motion budget
- [ ] reduced-motion alternative

## R3-6 District Identity

Status: P1 ADOPTED / VISUAL PENDING

- [✓] six district concepts
- [✓] no separate map required
- [✓] ground / props / light / sound only
- [ ] style tokens
- [ ] overlap with Environment v2
- [ ] visual comparison

## R3-7 Personal Display Slot

Status: P1 ADOPTED / PRIVACY AND ASSET PENDING

- [✓] user-selected
- [✓] one per major feature candidate
- [✓] private text default prohibited
- [✓] AI importance selection prohibited
- [ ] catalog
- [ ] reset / export behavior
- [ ] fallback rendering

## R3-8 Gentle Change Summary

Status: P1 ADOPTED / COPY AND CONTROL PENDING

- [✓] maximum three changes
- [✓] absence duration prohibited
- [✓] backlog blame prohibited
- [✓] optional display
- [ ] copy prototype
- [ ] dismissal / disable control
- [ ] sensitive change filtering

## R3-9 Quiet Surprise

Status: P2 ADOPTED / CONDITION AND ACCESSIBILITY PENDING

- [✓] no FOMO
- [✓] no reward
- [✓] no completion rate
- [✓] replayable in preview
- [ ] deterministic condition fixture
- [ ] accessibility equivalent
- [ ] performance budget
- [ ] motion-off representation

## R3-10 One-tap Beautify

Status: P2 ADOPTED / NON-DESTRUCTIVE COMMAND CONTRACT PENDING

- [✓] style-pack based
- [✓] preview required
- [✓] Undo required
- [✓] user object non-destructive
- [✓] no currency / crafting
- [ ] safe-slot catalog
- [ ] atomic command fixture
- [ ] access-path validation
- [ ] Growth Envelope validation
- [ ] Draft Town integration

## R3-11 On-demand Memory Window

Status: P2 ADOPTED / PRIVACY, CONSENT AND TRUTHFULNESS PENDING

- [✓] user-selected source only
- [✓] on-demand only
- [✓] person simulation prohibited
- [✓] source return required
- [✓] deletion / export required
- [ ] explicit-consent flow
- [ ] private-processing architecture
- [ ] hallucination disclosure
- [ ] safe fallback without generation
- [ ] sensitive-photo policy

## R3-12 Permanent non-goals

Status: LOCKED

- [✓] daily quests rejected
- [✓] login rewards rejected
- [✓] currency rejected
- [✓] materials / crafting rejected
- [✓] furniture gacha rejected
- [✓] NPC affection / hunger / sickness rejected
- [✓] town decay / forced cleaning rejected
- [✓] score / rank rejected
- [✓] limited-time reward / FOMO rejected
- [✓] public Town feed rejected
- [✓] streak / inactivity penalty rejected
- [✓] wait timer / paid growth acceleration rejected
- [ ] automated check that product docs do not introduce these patterns

## Stop conditions

実装へ進まず設計へ戻る:

- derived detailをuser layout objectとして保存したくなる
- auto beautifyがuser objectを移動・削除する
- Draft Townがserver validationを迂回する
- postcardへraw memory titleや人物名を入れる
- ambient animalへ好感度や空腹を追加する
- districtを別ゲームmapへ増殖させる
- Quiet Surpriseへ限定報酬を付ける
- decoration catalogへ通貨・素材・gachaを入れる
- Memory Windowが明示選択なしに写真を処理する
- Memory Windowが人物を再現・simulationする
- retention目的でdaily taskやdecayを復活させる

## Next required evidence

```txt
1. derived-detail rule catalog
2. negative-space visual debug
3. Draft Town atomic apply fixture
4. P11〜P21 static prototype scenes
5. postcard privacy projection
6. ambient nature emotional-safety review
7. district identity comparison
8. One-tap Beautify non-destructive fixture
9. Memory Window privacy / consent / disclosure contract
10. permanent non-goal documentation scan
11. external design review
```
