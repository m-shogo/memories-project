# Memory Town Attachment-first Scenic Design Principles — Round 6

最終更新: 2026-07-14

## Decision

Memory Townの景観は、情報を並べる背景ではなく、ユーザーが町へ愛着を持つための中核デザインとする。

ただし、愛着は記録を水増しさせる報酬設計では作らない。

```txt
記憶を残したい
→ 自分の棚として持ち続けられる
→ 後から町として見える
→ その景色を好きになる
```

```txt
Memory is the product.
Scenery creates attachment.
Town remains the visible side effect.
```

実装はまだ開始しない。

---

# 景観デザイン原則 10

## Principle 1 — 景色を情報で埋めない

建物、装飾、ラベル、particleを増やすことを完成度とみなさない。

優先するもの:

- 空
- 水
- 光
- 地面
- 四季樹
- 建物間の余白
- 視線が抜ける方向

禁止:

- 画面を機能一覧のように埋める
- 空地を未完成として自動装飾で消す
- すべてのcellへ意味を割り当てる
- 賑やかさだけで成熟を表現する

町の価値は、物量ではなく「好きな余白」があることに置く。

## Principle 2 — 海・川・空を主役級に扱う

海、川、水路、空は建物の背景ではない。

初期景観prototypeでは次を必須比較対象とする。

```txt
sea / coast / beach
+ narrow river or stream
+ bridge
+ wide sky band
```

水景は、町の開放感、生活感、時間帯変化、視線誘導を担う。

建物を増やすために水面や空を削らない。

## Principle 3 — 一画面へ無理に収めない

すべての建物、海、川、空、四季樹を一画面へ圧縮しない。

```txt
single-screen fit
≠
acceptance criterion
```

景観の余白と建物の識別性を守るため、町はviewportより広いlogical sceneとして設計する。

ユーザーは指で静かに移動して景色を見る。

## Principle 4 — 中心となる帰還地点を持つ

町を開いた時に迷わせない。

初期camera anchor候補:

```txt
中央広場
+ 四季樹
+ 複数の主要建物の一部
+ 川または海へ続く視線
```

ここを町の「帰ってきた場所」とする。

四季樹は成長meterではなく、長期利用の象徴と景観上のanchorである。

## Principle 5 — 光で時間を感じさせる

朝、昼、夜、夜中を単なる全面color filterにしない。

時間帯差分:

- 空のgradient
- 水面反射
- contact shadow
- 建物窓・看板・街灯
- 太陽または月
- 星と霞
- 四季樹のrim light

夜と夜中も、暗くして見えなくするのではなく、暖かい灯りと月光で眺められる状態を維持する。

## Principle 6 — 水は複数速度の動きで生かす

海と川を一枚のtexture scrollだけで表現しない。

推奨layer:

```txt
sea:
  distant drift
  surface reflection
  shoreline foam

river:
  base flow
  small highlight
  edge ripple
```

橋、岸、砂浜のgeometryはanimationで変えない。

水の動きは機能やcollisionと分離する。

## Principle 7 — 動きは少なく、統一し、止められる

常時動くものを増やしすぎない。

動きの優先順位:

```txt
1. water
2. cloud
3. tree / grass
4. rare ambient nature
5. seasonal particles
```

一つのambient wind fieldで方向とphaseを揃える。

必須状態:

- full
- reduced
- off
- low power

motion offでも、時間帯、季節、水辺、地区を静止画だけで認識できること。

## Principle 8 — ランドマークと視線で迷わせない

自由panを許可しても、探索ゲームにはしない。

主要ランドマーク:

- 四季樹と中央広場
- 映画館
- 市場
- 港とビーチ
- 川と橋
- Inbox倉庫

各areaはsilhouette、地面cue、灯り、水景で識別する。

mini-mapを前提にせず、風景そのものから方向を理解できる構図を優先する。

## Principle 9 — 町は静かに個人化する

愛着は大量の家具catalogではなく、小さな選択の積み重ねから作る。

使用するもの:

- Curated Style Pack
- Personal Display Slot
- Private Postcard
- 地区ごとの小さな差分
- user-selected color / flag / abstract motif

使用しないもの:

- AIが選ぶ最重要記憶
- 人物名やprivate titleの常時表示
- 通貨、gacha、限定装飾
- 他人との町比較

## Principle 10 — 長く見ても疲れず、長く使っても古びにくい

瞬間的な派手さより、数年見続けられることを優先する。

- 彩度を上げすぎない
- 強いparticleを常用しない
- UI contrastを景観の暗さへ依存させない
- 小画面でも建物silhouetteを潰さない
- 流行のeffectだけへ依存しない
- static fallbackでも魅力が残る
- Town OFFでもMemory OSの価値を失わない

景観は、毎日開かせる圧力ではなく、開いた時に「ここが好き」と思える理由を作る。

---

# Scenic composition direction

初期構図候補:

```txt
upper / rear:
  wide sky
  cloud layers
  distant water or horizon

center:
  central square
  Memory Tree
  primary route landmarks

middle / lower:
  narrow river or stream
  bridge
  riverbank path

lower-right candidate:
  port
  beach
  open sea

left / lower-left candidate:
  quiet green space
  cinema / market approach
  visual breathing room
```

川と海を同時に入れる場合、川は地図を分断する障害ではなく、橋と岸辺を作る景観軸として使う。

---

# Attachment acceptance questions

Visual prototypeでは、機能理解だけでなく次を評価する。

- 海を数十秒眺めていたいと思えるか
- 川沿いを指で移動して見たいと思えるか
- 朝と夜中の両方に魅力があるか
- 四季樹の周辺を町の中心として覚えられるか
- 建物が少ない状態でも町を好きになれるか
- motion offでも景色が成立するか
- 町を閉じても記憶保存の価値が残るか

数値化する場合も、滞在時間最大化だけを成功指標にしない。

---

# Permanent prohibitions

- 一画面へ全要素を圧縮することを必須にしない
- 空、海、川を建物追加の余剰領域として扱わない
- 暗さで夜中の利用を罰しない
- particle量を成長や記憶価値の指標にしない
- 景色を見るために記録を要求しない
- 川や海へ収集、釣り、通貨を自動接続しない
- scenic cameraを自由歩行gameへ変えない

---

# Current verdict

```txt
attachment-first scenic principles:
locked at design level

river / sea / sky direction:
adopted for prototype

camera and navigation:
separate Round 6 contract

visual evidence:
pending

implementation:
NO-GO
```
