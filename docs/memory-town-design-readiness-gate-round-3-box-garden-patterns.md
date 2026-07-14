# Memory Town Design Readiness Gate — Round 3 Box-Garden Patterns

最終更新: 2026-07-14

## Verdict

```txt
box-garden research: completed
pattern adoption decision: completed
contract integration: partial
visual prototype: pending
implementation: NO-GO
```

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

## R3-8 Quiet Surprise

Status: P2 CANDIDATE

- [✓] no FOMO
- [✓] no reward
- [✓] no completion rate
- [✓] replayable in preview
- [ ] deterministic condition fixture
- [ ] accessibility equivalent
- [ ] performance budget

## Stop conditions

実装へ進まず設計へ戻る:
- derived detailをuser layout objectとして保存したくなる
- auto beautifyがuser objectを移動・削除する
- Draft Townがserver validationを迂回する
- postcardへraw memory titleや人物名を入れる
- ambient animalへ好感度や空腹を追加する
- districtを別ゲームmapへ増殖させる
- quiet surpriseへ限定報酬を付ける
- decoration catalogへ通貨・素材・gachaを入れる

## Next required evidence

```txt
1. derived-detail rule catalog
2. negative-space visual debug
3. Draft Town atomic apply fixture
4. P11〜P19 static prototype scenes
5. postcard privacy projection
6. ambient nature emotional-safety review
7. district identity comparison
8. external design review
```
