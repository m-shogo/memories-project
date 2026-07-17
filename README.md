# memories-project

AI時代に「自分の人生の文脈」を持ち続けるための **Memory OS** の構想・仕様・実装をまとめるリポジトリ。

ChatGPT / Claude / Gemini / Character.AIの代替ではない。

## 一言で言うと

**保存した人生の断片を、自分の棚・地図・箱・町として持ち続け、必要な時に探し、振り返り、外へ持ち出せるMemory OS。**

AI・モデル・サービスが変わっても、ユーザー自身の人生の文脈を特定サービスへ閉じ込めない。

```txt
Memory is the product.
Town is the visible side effect.
```

---

# Current authority and status

最終更新: 2026-07-17

最初に読む:

1. [Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)
2. [Current Implementation Status and Roadmap](docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md)
3. [Preview Spool and Atomic Commit Contract](docs/memory-os-preview-spool-commit-contract-round-9.md)
4. [Import API Security Slice](services/import-api/README.md)
5. [Security Status](SECURITY.md)

```txt
product priority:
Capture / Import first

security architecture:
DEFINED

machine-readable security contracts:
ADVANCED

Go backend:
PARTIAL SECURITY VERTICAL SLICE
not a production backend

PostgreSQL:
RLS / upload security foundations created
production domain schema and repositories incomplete

Preview spool:
contract hardened
runtime not implemented

object storage / parser runtime / iOS / Portal:
not implemented

current HEAD remote Actions result:
unconfirmed

production:
NO-GO
```

Current machine evidence:

```txt
registered schemas:              24
positive contract fixtures:      23
structural rejection cases:      31
semantic rejection cases:         8
```

“Go backend未実装”は古いが、“backend完成”も誤り。現在は **partial security vertical slice**。

“PostgreSQL migration/test作成済み”はRLS・upload security foundationについて正しいが、Preview candidate/rejection/ready、Apply、Memoryのproduction schema/repository完成を意味しない。

---

# Current product direction

```txt
軽く取り込む
→ 保存前にPreviewする
→ 媒体に合う棚として見える
→ 検索・更新・振り返りができる
→ 記録の積み重ねが「記憶の町」として後から見える
→ 必要なら標準形式で持ち出せる
```

## 実用の本体

- Universal Quick Add
- Import Preview
- 漫画・アニメ進行
- 映画・視聴棚
- 食の地図
- 未整理Inbox
- Search
- Export
- Weekly Box / Month Capsule
- ユーザーが明示的に追う「続き」

ユーザーは町を育てるために人生を記録しない。忘れたくない作品、場所、日常、進行を残し、その積み重ねが後から町として見える。

## First experience

初回にZIPや複雑なAPI連携を要求しない。

```txt
SPY×FAMILY 12巻まで
PERFECT DAYS 見た
鎌倉のカレー屋 行きたい
```

保存前にImport Previewを表示する。

保存後:

```txt
保存した内容
→ 入った棚・進行
→ optionalな小さな町の反応
→ 棚を見る / 続きを更新 / 閉じる
```

API connectorや大規模Importは、安全なPreview、Policy Evaluation、token管理、Export、削除・再実行性が成立した後に追加する。

---

# Binding technology direction

```txt
iOS canonical client:
Swift 6 + SwiftUI
Share Extension
GRDB / SQLite
Keychain + App Group

limited bulk-import support:
Desktop Import Portal
Vite + React + TypeScript

canonical backend:
Go API
PostgreSQL with FORCE RLS
private versioned S3-compatible quarantine
isolated parser supervisor / worker

Memory Town later:
SpriteKit
Metal only after a measured blocker
```

Parser、adapter、dedupe、Preview、ApplyをSwift・browser・Goへ重複実装しない。

Earlier React/PixiJS/WebGL Town documents are retained as design exploration. They are not the current binding runtime choice for the iOS-only product unless a later explicit authority changes the decision.

---

# Current implementation order

Feature additions do not precede boundary correctness.

```txt
0. confirm exact current HEAD validators / Go checks / remote workflows
1. supervisor-owned Preview spool attempt directory and terminal cleanup
2. bounded canonical accepted/rejected stream writers
3. manifest writer, seal and independent reader/re-hash
4. cancellation / crash / tamper / symlink / cross-attempt / expiry tests
5. production Preview candidate/rejection/ready PostgreSQL schema
6. short atomic pgx.CopyFrom commit repository
7. epoch recheck / rollback / retry-after-COMMIT proof
8. concrete private versioned object-storage signer and HEAD adapter
9. isolated parser supervisor and reviewed artifact verification
10. executable API + concrete Apple exchange/session/replay repositories
11. concrete Apply / Memory persistence and deletion fencing
12. iOS Share Extension and safe final confirmation
13. limited Desktop Import Portal
14. Memory Town runtime only after Capture / Import P0 reaches zero
```

Detailed gates: [Current Implementation Status and Roadmap](docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md)

Immediate checkpoint:

```txt
server-generated spoolId
+ exclusive 0700 attempt directory
+ fixed exclusive 0600 files
+ descriptor-relative no-follow operations
+ file type / ownership / mode / link-count validation
+ idempotent cleanup on success / failure / cancellation / expiry
```

Do not mix PostgreSQL persistence, S3 networking, parser containers or client features into that first checkpoint.

---

# Memory Town

固定視点2.5Dの **Memory Town** を採用する。ただしTownはゲーム本体ではなく、保存された記憶が後から見える感情的な可視化・入口。

```txt
棚の機能 → 建物へbinding
箱 → 町の風景
確定したつながり → semantic overlay
Reset後の新しい積み重ね → 建物の育ち直し
月・季節 → 装飾と空気の変化
```

## Memory-first hierarchy

```txt
1. Capture / Import
2. Retrieval / Search / Update
3. Privacy / Safety / Portability
4. Reflection / Resurfacing
5. Town visualization
6. Town customization / editor
```

Town contracts and adoption decisions are mature, but machine/visual/runtime evidence remains incomplete. **Design adoption does not authorize immediate implementation.**

Current Town implementation verdict:

```txt
Memory-first authority:
LOCKED

contracts and design decisions:
ADVANCED

runtime implementation priority:
DEFERRED behind Capture / Import P0

production:
NO-GO
```

## Town state model

```txt
1. Memory Domain State
2. Town Feature Progress State
3. Town Layout State
4. Town Environment State
5. Town Render State
```

Important boundaries:

- building meaning and visual representation are separate;
- normal record deletion does not punish the user by shrinking unlocked growth;
- explicit Reset changes the growth origin without deleting memories;
- season/time/camera do not enter Memory Projection authority;
- environment does not use importance, emotion or streak scores;
- physical paths and semantic connections remain separate;
- template updates do not overwrite user layout;
- Town OFF does not reduce Capture/Search/Export capability;
- account deletion leaves no Town state, job or cache;
- Draft Town cannot bypass server validation.

## Town documents

- [Current Authority Order — Round 5 Memory-first](docs/memory-town-current-authority-order-round-5-memory-first.md)
- [Memory-first Capture Motivation Contract](docs/memory-first-capture-motivation-contract-round-5.md)
- [Full Pattern Adoption and Permanent Non-goals](docs/memory-town-full-pattern-adoption-and-permanent-non-goals-round-4.md)
- [Architecture Hardening Contract](docs/memory-town-architecture-hardening-contract.md)
- [Long-term Spatial Model](docs/memory-town-long-term-spatial-model.md)
- [Visual Design Direction](docs/memory-town-visual-design-direction.md)
- [Persistence, RLS and Recovery Contract](docs/memory-town-persistence-rls-and-recovery-contract.md)

---

# Core philosophy

- AIは人生を評価しない。
- AIは人生を忘れないための索引になる。
- ラーメン、焼肉、帰り道、卒業式後の写真も全部人生。
- 重要度をAIが決めない。
- 保存時に分析しすぎない。
- 保存時は安全チェック、source、日付、検索性を中心にする。
- 分析はユーザーが求めた時だけ行う。
- 小さな記録を捨てない。
- 大きなイベントも押し付けない。
- 本人の記憶を作り、本人をシミュレーションしない。

---

# Permanent non-goals

- ChatGPT / Claude代替
- Character.AI化
- AI恋人・AI家族・故人再現
- 人格診断・幸福度評価
- 監視・攻撃誘導・依存誘導
- daily quests / login rewards / streak punishment
- 通貨・素材・crafting・家具ガチャ
- 空腹・病気・世話義務
- 町の荒廃・片付け義務
- 隣接点数・配置スコア
- 町ランキング・人生ランキング
- 期間限定報酬・FOMO
- 公開Town feed・follower競争
- inactivityで住人が去る演出
- 建築待ち時間・成長加速課金
- next stageまでの件数表示・成長progress bar
- Town成長目的のcapture prompt
- Town専用mandatory record field
- multiplayer town
- 実天気・実潮汐・天文位置の厳密再現

変更には明示ADR、Memory Constitution整合、wellbeing/privacy/adversarial review、owner承認が必要。

---

# Product statement

```txt
記憶を入れたいと思えることが先。
保存したものが棚になる。
必要な時に探せて、続きを更新できる。
町は、その積み重ねが後から見える副次的な結果。

通常削除では、解除した成長を罰のように失わせない。
明示Resetでは、現在の記録を残したまま町を育て直せる。
配置と記憶は別々に守られる。
戻らなくても、町は荒れず、責めず、損をさせない。
必要な時は、すべて持ち出せる。
```
