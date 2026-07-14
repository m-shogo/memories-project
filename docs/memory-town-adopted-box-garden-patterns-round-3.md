# Memory Town Adopted Box-Garden Patterns — Round 3

最終更新: 2026-07-14

## Verdict

```txt
research: completed
all pattern adoption: approved
visual evidence: pending
implementation: NO-GO
```

全13パターンを正式採用する。P0 / P1 / P2は採否ではなく、導入時期と必要Gateの違いを表す。

## P0 — prototypeへ必ず入れる

### MT-ADOPT-001 Derived Micro-details

隣接関係から小さな美観detailを導出する。

例:
- 港＋ビーチ → 木道、ロープ、低い灯り
- 建物＋道 → 小さな植栽、案内板
- 四季樹＋ベンチ → 木陰・落ち葉・雪帽子
- 道＋水 → bridge visual

Rules:
- deterministic
- reversible
- privacy neutral
- user objectを削除しない
- derived render stateとして扱う
- detailがなくても機能は変わらない

### MT-ADOPT-002 Draft Town

canonical layoutを変更せず、配置・季節・時間・stage・style packを試せるcopy-on-write draftを持つ。

```txt
Open draft
→ Edit / Preview
→ Compare
→ Apply atomic batch or Discard
```

MVP editorには入れないが、長期空間モデルとcommand contractはDraft Townを前提にする。

### MT-ADOPT-003 Negative Space and Sightline

小画面で過密化させない。

必須:
- Memory Treeのsilhouetteを維持
- 海岸線を隠し切らない
- 主要建物間の視覚分離
- 前景props上限
- open ground候補
- motion offでも識別可能

具体比率はvisual prototypeで決める。

### MT-ADOPT-004 Empty Town Baseline Life

記録0件でも町を未完成・失敗・寂しさとして描かない。

初期状態に含める:
- 波
- 雲
- 四季樹Stage 0
- 基本灯り
- 少量の花・低木
- generic bird / fish silhouette候補

### MT-ADOPT-005 Curated Style Packs

大量catalogより先に、8〜12点程度の統一packを提供する。

候補:
- paper harbor
- quiet garden
- night cinema
- warm market
- silver coast
- mint morning

Rules:
- preview一括適用
- 個別微調整可能
- currencyなし
- craftingなし
- limited-time販売なし

## P1 — Town基盤成立後に導入

### MT-ADOPT-006 Private Postcard / Town History

町の時間帯・季節・stage・layoutを私的な写真帳として残す。

Default:
- manual capture
- private
- raw memory title / person name / private URLを含めない
- export / delete可能

Opt-in:
- stage成長時のcapture suggestion
- 季節初回のcapture suggestion

禁止:
- 自動公開
- social feed
- ranking
- raw memory screenshot

### MT-ADOPT-007 District Identity

主要建物周辺に小さな地区の空気を持たせる。

```txt
cinema → culture lane
story → story garden
market → market square
port → harbor edge
inbox → archive lane
reflection → reflection grove
```

独立mapにはせず、ground cue、props、灯り、音で表現する。

### MT-ADOPT-008 Ambient Nature

identityを持たない小動物・自然animationで生活感を作る。

候補:
- 海鳥
- 蝶
- 魚影
- 小さなカニ
- 遠景の船

禁止:
- 名前
- 好感度
- 空腹・病気
- user inactivityへの反応
- 本人、家族、故人の代理

### MT-ADOPT-009 Personal Display Slot

各主要featureに、ユーザー自身が選ぶ象徴物を1つ置ける。

選択可能:
- 色
- 旗
- 抽象アイコン
- 汎用小物

Default禁止:
- private title
- 人物名
- AIが選ぶ「最重要記憶」

### MT-ADOPT-010 Gentle Change Summary

復帰時に、町の変化を最大3件だけ任意表示する。

例:
- 季節が秋になりました
- 映画館が育ちました
- 港に夜の灯りが増えました

禁止:
- 離れていた日数
- backlog
- 未処理件数の責め
- streak

## P2 — 正式採用済みの将来機能

### MT-ADOPT-011 Quiet Surprise

見つけなくても困らない小さな変化。

- previewで再現可能
- no FOMO
- no reward
- no completion rate
- deterministic condition
- accessibility equivalent必須

### MT-ADOPT-012 One-tap Beautify

safe decoration slotsへ、選択したstyle packを自動配置する。

必須:
- Preview
- Undo
- user object非破壊
- Growth Envelope非侵入
- access path非遮断
- Draft Town上で比較可能

### MT-ADOPT-013 On-demand Memory Window

ユーザーが明示的に選んだ写真を、振り返り時だけ小さなsceneとして表示する将来機能として正式採用する。

実装Gate:
- explicit consent
- private processing
- hallucination disclosure
- 人物simulation禁止
- deletion / export
- source photoへ戻れる
- auto-generation default禁止
- raw private contentのTown常駐禁止

## Permanent rejected patterns

- daily quests / 毎日の依頼
- login rewards
- currency
- materials / crafting
- furniture gacha
- placement score / adjacency score
- town rank / life rank
- NPC affection
- hunger / sickness / care obligation
- town decay
- forced cleaning
- inactivity penalty
- time-limited seasonal rewards
- limited-time decoration FOMO
- public town feed
- follower competition
- streak
- building wait timers
- paid growth acceleration

これらの変更には`memory-town-full-pattern-adoption-and-permanent-non-goals-round-4.md`を変更する明示ADRが必要。

## Required prototype additions

```txt
P11 Derived detail ON / OFF
P12 Empty Town baseline life
P13 District identity comparison
P14 Personal Display Slot
P15 Curated style pack preview
P16 Private Postcard mock
P17 Draft Town compare / discard
P18 Quiet Surprise with motion off
P19 maximum-density sightline debug
P20 One-tap Beautify preview / undo
P21 On-demand Memory Window consent / source / deletion mock
```

## Implementation authorization impact

Memory Town implementation remains NO-GO。

Before renderer authorization:
- derived detail rules must have source-of-truth boundary
- negative-space prototype must pass
- Draft Town must not bypass atomic command / validation
- postcard privacy projection must be defined
- ambient nature must pass emotional-safety review
- Quiet Surprise must have accessibility equivalent
- One-tap Beautify must be non-destructive
- Memory Window must pass privacy / consent / hallucination review
