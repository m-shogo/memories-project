# Memory Town Current Authority Order — Round 2 Environment

最終更新: 2026-07-13

## 目的

4時間帯、ビーチ、波、空、Memory Tree、四季表現を追加したため、旧3時間帯Environment v1と新Environment v2が同時に存在する。

実装担当が旧`day / evening / night`仕様へ戻らないよう、環境領域の現在正本を固定する。

実装はまだ開始しない。

---

# 1. Current verdict

```txt
environment product direction:
contract locked

environment schema / fixture:
v2 created, machine validation pending

Memory Tree:
contract and fixture created, assets pending

visual prototype:
specification updated, evidence pending

implementation:
NO-GO
```

---

# 2. Authority order

環境・時間・季節・海岸・象徴樹について矛盾する場合、上を優先する。

```txt
1. memory-town-current-authority-order-round-2-environment.md
2. memory-town-environment-and-seasonal-life-contract.md
3. memory-town-environment-asset-brief.md
4. memory-town-static-visual-prototype-environment-addendum.md
5. memory-town-current-authority-order-round-1.md
6. memory-town-p0-runtime-accessibility-fallback-contract.md
7. memory-town-static-visual-prototype-spec.md
8. memory-town-visual-design-direction.md
9. environment-theme-catalog.v2 schema / fixture
10. memory-tree-catalog.v1 schema / fixture
11. legacy environment v1
```

Environment以外のstate、Reset、worker fence、RLS、access graphはRound 1正本を維持する。

---

# 3. Active environment contract

Active:

```txt
docs/schemas/memory-town/environment-theme-catalog.v2.schema.json
docs/fixtures/memory-town/environment-theme-catalog.v2.json
```

Legacy / implementation禁止:

```txt
docs/schemas/memory-town/environment-theme-catalog.v1.schema.json
docs/fixtures/memory-town/environment-theme-catalog.v1.json
```

理由:

- v1は`day / evening / night`の3状態
- v2はユーザー要望どおり`morning / day / night / midnight`の4状態
- v2はsky、shore、building light、manual preview、low powerを契約化

---

# 4. Active Memory Tree contract

```txt
docs/schemas/memory-town/memory-tree-catalog.v1.schema.json
docs/fixtures/memory-town/memory-tree-catalog.v1.json
```

Memory Treeは次を表す。

```txt
情報の内容・価値ではなく、
eligibleな保存量の粗いaggregateによる町全体の成長
```

禁止:

- AI importance
- emotion strength
- login streak
- payment amount
- exact count表示
- inactivity shrink

---

# 5. Active time modes

```txt
morning
05:00–10:59 candidate

day
11:00–16:59 candidate

night
17:00–22:59 candidate

midnight
23:00–04:59 candidate
```

`evening`は独立状態ではなく、nightへ入るvisual transitionとして扱う。

境界値はprototype candidateであり、machine validationだけでproduct承認しない。

---

# 6. Active environment layers

```txt
sky gradient
cloud back / front
sun or moon
stars
atmospheric haze
base terrain
beach / coast / water
shore foam
surface reflection
season ground cue
Memory Tree seasonal stage sprite
building light overlays
global light / shadow preset
DOM controls
```

16枚の完成背景へ焼き込まない。

---

# 7. Initial inclusion

P0 visual prototypeへ含める。

- 4時間帯
- current device local time連動
- manual time / season preview
- 雲の移動
- 太陽 / 月の視覚移動
- 夜・夜中の建物灯り
- ビーチ
- 3-layer shoreline concept
- Memory Tree 3 growth stages
- 春の桜
- 夏の深緑
- 秋のモミジ調紅葉
- 冬の暖かい休眠表現
- 季節の地面cue
- unified wind field
- motion off / reduced / full / low power
- layered fallback

---

# 8. Not initial

- real weather API
- GPS
- real tide API
- astronomical sun position
- fishing / collecting
- moon phase accuracy
- rare sky event
- generic residents
- emotion-based weather

---

# 9. Implementation authorization

Environment implementation remains prohibited until:

```txt
1. Environment v2 and Memory Tree fixture machine validation passes
2. active fixture graph contains no Environment v1 dependency
3. beach placement candidate is approved
4. Memory Tree Stage 0〜2 silhouettes exist
5. four time-mode palette rough exists
6. four-season Tree rough exists
7. EVP-1〜EVP-6 minimum evidence exists
8. layered fallback expresses the same environment state
9. no unresolved P0 from external review
```

---

# 10. Stop conditions

次の場合は設計へ戻る。

- `evening`を第5状態として無断追加する
- 16枚の完成背景を正本にする
- Tree growthへAI importanceを混ぜる
- 冬を枯死・放置・罰として表現する
- actual weather / tideと誤認させる
- motion offで季節や時間が分からなくなる
- beachを背景画像へ焼き込み、map expansion不能にする
- current timeをMemory Domainへ保存する
- Pixi Canvasだけでtime / season設定を操作させる

---

# 11. Final statement

```txt
Memory Townの初期環境は、
朝・昼・夜・夜中、空、雲、太陽・月、海、ビーチ、波、四季樹を持つ。

それらはMemory内容の評価や利用頻度に支配されず、
現在時刻と季節に寄り添う静かな生活感として存在する。
```
