# Memory Town Full Pattern Adoption and Permanent Non-goals — Round 4

最終更新: 2026-07-14

## Decision

Round 3で抽出したMemory Town向け箱庭パターンを、候補ではなくすべて正式採用する。

```txt
product adoption: approved
implementation timing: phased
visual evidence: pending
implementation: NO-GO
```

「正式採用」は今すぐ全機能を実装する意味ではない。長期製品方針から落とさず、各Gateを満たした段階で導入する意味である。

## Fully adopted patterns

### P0 — 初期prototypeと基盤設計へ必ず含める

1. Derived Micro-details
2. Draft Town
3. Negative Space and Sightline
4. Empty Town Baseline Life
5. Curated Style Packs

### P1 — Town基盤成立後に導入する

6. Private Postcard / Town History
7. District Identity
8. Ambient Nature
9. Personal Display Slot
10. Gentle Change Summary

### P2 — 正式採用済みの将来機能。安全・性能Gate後に導入する

11. Quiet Surprise
12. One-tap Beautify
13. On-demand Memory Window

P2は研究候補ではなく、長期方向として採用済み。ただし次の条件を満たすまで実装しない。

- explicit consent
- private processing
- sourceへ戻れる
- deletion / export
- hallucination disclosure
- person simulation禁止
- no FOMO / no reward
- accessibility equivalent
- performance budget

## Product sentence

```txt
ユーザーは大きな意図を選ぶ。
町は小さな細部を静かに整える。
試す時は本番を壊さない。
過去の町は私的に残せる。
空白にも自然な生活感がある。
戻らなくても、町は責めない。
```

## Permanent non-goals

以下はMemory Townの価値と衝突するため、箱庭ゲームの定番であっても採用しない。

- 毎日の依頼 / daily quests
- ログイン報酬
- 通貨
- 素材集め
- クラフト
- 家具ガチャ
- 住人の好感度
- 空腹・病気・世話義務
- 町の荒廃・decay
- 片付け義務・強制清掃
- 隣接点数・配置スコア
- 町ランキング・人生ランキング
- 期間限定イベント報酬
- 期間限定装飾の取り逃し
- 公開Town feed
- follower競争
- streak
- missed-day penalty
- inactivityで住人が去る演出
- 建築待ち時間
- 成長加速課金
- 公開を前提とした町評価

## Why these are rejected

### 1. Memory OSを日課へ変えない

記録は人生のために行う。アプリの維持作業のために人生を使わせない。

### 2. 不在を罰しない

数日、数か月、数年使わなくても、町は荒れず、住人は病まず、報酬も失わない。

### 3. 記憶量を競争へ変えない

保存量は町の粗い成長へ使えるが、他人比較、順位、得点、幸福度評価へ使わない。

### 4. 愛着を課金圧力へ変えない

大切な町や思い出を、人質にした限定商品、ガチャ、成長待ち、復旧課金を作らない。

### 5. 私的な町をSNSへ変えない

共有はshare-safeな明示操作だけ。公開feed、フォロワー数、反応数を中心にしない。

## Change-control rule

恒久的非採用項目を将来導入する提案は、通常のfeature提案では扱わない。以下をすべて必要とする。

1. 本書を変更する明示ADR
2. Memory Constitution / Product Boundariesとの整合説明
3. dependency / wellbeing / privacy review
4. adversarial review
5. user research evidence
6. ownerによる明示承認

「他のゲームでは普通」「retentionが上がる」「収益化しやすい」だけでは変更理由にならない。

## Implementation impact

- Round 3のMT-ADOPT-001〜013をすべてactive design decisionとする
- P2もcandidate表記を廃止し、adopted-futureへ変更する
- 実装順はP0 → P1 → P2を維持する
- renderer実装許可は別Gateで判断する
- 本決定だけを理由に実装開始しない
