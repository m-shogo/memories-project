# Next Chat Addendum — Memory Town Round 6 Attachment Scenery

最終更新: 2026-07-14

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

## Absolute conditions

- 実装はまだ開始しない
- 毎回commit / pushする
- Memory-first hierarchyを維持する
- 景観は愛着を作る中核だがMemoryより上位にしない
- 一画面に全景を圧縮しない
- bounded panを採用し、自由歩行gameへ変えない
- 海、川、空を建物追加の余白として潰さない
- 川や海へ釣り、素材、通貨を接続しない
- MemoryDiorama型の生成sceneを事実やMemory Domainの正本にしない

## Read first

1. `docs/memory-town-current-authority-order-round-6-attachment-scenery.md`
2. `docs/memory-town-attachment-first-scenic-design-principles-round-6.md`
3. `docs/memory-town-bounded-pan-camera-and-scenic-navigation-contract-round-6.md`
4. `docs/memorydiorama-research-implications-for-memory-town-round-6.md`
5. `docs/memory-town-current-authority-order-round-5-memory-first.md`
6. `docs/memory-first-capture-motivation-contract-round-5.md`

## Scenic principles

```txt
1. 景色を情報で埋めない
2. 海・川・空を主役級に扱う
3. 一画面へ無理に収めない
4. 中心となる帰還地点を持つ
5. 光で時間を感じさせる
6. 水は複数速度の動きで生かす
7. 動きは少なく、統一し、止められる
8. ランドマークと視線で迷わせない
9. 町は静かに個人化する
10. 長く見ても疲れず古びにくい
```

## Camera decision

```txt
adopt:
  one-finger bounded pan
  central-grove Home action
  authored landmark anchors
  optional weak anchor attraction
  DOM route equivalence

not initial:
  free rotation
  avatar walking
  infinite pan
  mandatory pinch zoom
  long fly animation
```

## Landscape direction

Prototypeに含める。

- wide sky
- sea / coast / beach
- narrow river or stream
- bridge
- riverbank path
- Memory Tree and central square
- open ground / negative space
- morning / day / night / midnight
- spring / summer / autumn / winter

## MemoryDiorama research interpretation

Adopt:

- cue diversity
- dynamic water / light / particleが感覚的想起を支える可能性
- glanceable diorama
- source-grounded cue

Do not adopt directly:

- 写真外の出来事を事実として生成
- 人物のsimulation
- inferred locationを確定保存
- generated sceneをMemory Domainへ保存
- false-memory risk説明なしの自動表示

Source:

```txt
arXiv:2604.06773v1
submitted 2026-04-08
preprint扱い
```

## Prototype scenes

```txt
S0 compressed one-screen comparison
S1 balanced scenic extent
S2 expanded scenic extent
S3 central grove
S4 river and bridge
S5 harbor / beach / open sea
S6 morning water and sky
S7 midnight water and lights
S8 motion off landscape
S9 maximum-density negative-space debug

C0 central return
C1 central → river pan
C2 river → harbor pan
C3 tap / drag ambiguity
C4 edge bounds
C5 bottom sheet collision
C6 reduced motion
C7 DOM shortcut equivalence
```

## Next correct sequence

```txt
1. scenic composition rough A/B/C
2. river route and bridge placement A/B/C
3. map extent 1.3–3.0 viewport comparison
4. central-grove opening composition
5. harbor / beach / open-sea composition
6. bounded pan interaction storyboard
7. tap-versus-drag threshold prototype
8. landmark orientation comprehension review
9. motion off / reduced motion comparison
10. MemoryDiorama-inspired cue safety review
11. six mobile viewport evidence
12. external multidisciplinary review
13. unresolved P0 correction
14. implementation authorization judgment
```

## Current status

```txt
10 scenic principles:
created and committed

bounded pan contract:
created and committed

MemoryDiorama implications:
created and committed

visual evidence:
not created

interaction prototype:
not created

implementation:
NO-GO
```
