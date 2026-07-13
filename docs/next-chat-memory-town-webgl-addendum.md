# Next Chat Memory Town / WebGL Addendum

最終更新: 2026-07-13

この文書は、`docs/next-chat-handoff.md` 以降に確定した最新のプロダクト方向を引き継ぐ。

## Read First

1. `docs/current-product-direction.md`
2. `docs/memory-town-visual-design-direction.md`
3. `docs/memory-town-webgl-architecture.md`
4. `docs/memory-town-implementation-roadmap.md`
5. `docs/concrete-mvp-product-scope.md`
6. `docs/concrete-mvp-ticket-backlog.md`

READMEも2026-07-13時点へ更新済み。

## Latest Product Decision

Memory OSは単なる保管庫ではない。

実用層:

- Quick Add
- Import Preview
- 棚
- 進行
- 地図
- Search
- Export
- Weekly / Month Capsule
- 自分が明示的に追う対象の続き

感情的な副次成果物:

- 固定2.5Dの「記憶の町」

```txt
保存したものが棚になる。
棚が建物になる。
箱が町の風景になる。
つながった記憶が道になる。
```

## Technology Decision

```txt
PixiJS / WebGL
+ React / DOM
+ fixed 2.5D sprites
+ dot-style visual
+ modular/config-driven assets
```

- 生WebGLは使わない
- Three.jsによる本格3Dは使わない
- 自由配置はしない
- WebGL内でform、検索、一覧、security操作を作らない
- rendererへraw memoryを渡さない
- static fallbackを必須にする

## Town Role

町はゲーム本体ではなく、感情的なmenu。

```txt
建物tap
→ 少しfocus
→ DOM summary card
→ 対応する棚へ移動
```

通常の棚menuも必ず残す。

## Initial Map

MVP town:

- cinema
- story house
- market
- port
- inbox warehouse
- central square

各建物は3段階:

- stage 0: 未開放
- stage 1: 小
- stage 2: 成長

## Design Direction

```txt
固定2.5D
high-resolution dot-style
ミニチュア・ジオラマ感
絵本の温かさ
眺める8 : 操作2
```

カイロソフトは分かりやすさの参考。経営ゲーム、数値HUD、効率競争には寄せない。

## Growth Rules

AIの意味判断ではなく、説明可能な事実で決める。

Allowed:

- unique record count
- source count
- month capsule count
- confirmed relation count
- usage years

Denied:

- importance
- happiness
- emotion score
- personality
- relationship quality
- sensitive content quantity

## Projection Architecture

```txt
memory records
→ policy filtered aggregate
→ versioned TownProjection
→ PixiJS renderer
```

TownProjectionは再生成可能なread model。
町をsource of truthにしない。

## Updated Implementation Order

```txt
1. 安全なImport基盤
2. Import Preview
3. Manga / Anime Vertical Slice
4. Food regional list
5. Home / Shelf navigation
6. Static Memory Town prototype
7. PixiJS foundation
8. TownProjection
9. Import → town growth feedback
10. Season / time
11. Weekly / Month Capsule decoration
12. Ambient life
13. Confirmed relation roads
14. Future anticipation signs
```

町の大規模制作をImport・棚より先に進めない。

## No-Go

- free placement
- user avatar walking
- citizen dialogue
- virtual currency
- quests
- building timers
- decay
- neglected town
- streak
- social visit
- multiplayer
- paid growth acceleration
- private memory title on town

## Next Recommended Work

設計をさらに増やす前に、次は以下のどちらかへ進む。

### A. Visual Prototype

- map composition 3案
- 5 buildingsのstage 0〜2 silhouette
- 390x844でtap test
- high-resolution dot-styleの確認

### B. Implementation Preparation

- TownProjection TypeScript contract
- building config schema
- asset manifest schema
- PixiJS bootstrap ticket
- static fallback contract

現時点ではAを先に行い、町が本当に魅力的か確認してからBへ進むのが推奨。

## Commits

- `34e4a4ef9cc9eff9b24c0d4872bbb6a3910df5bf` current product direction
- `3f82ca9904c5a7fe320823d37480d5759bd743f9` visual design direction
- `0eac3fb87bfddcc2ce6f9b219c02d080a6192527` WebGL architecture
- `e417cafcc2c455b4a6860043e40bcca20589a7cd` implementation roadmap
- `7223340028523c180b99a43933a2d0c8a2bb964f` README refresh
