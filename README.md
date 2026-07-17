# memories-project

AI時代に「自分の人生の文脈」を持ち続けるための **Memory OS** の構想・仕様・実装をまとめるリポジトリ。

ChatGPT / Claude / Gemini / Character.AIの代替ではない。

## 一言で言うと

**保存した人生の断片を、自分の棚・地図・箱・町として持ち続け、必要な時に探し、振り返り、外へ持ち出せるMemory OS。**

```txt
Memory is the product.
Town is the visible side effect.
```

---

# Current authority and status

最終更新: 2026-07-17

Read first:

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

machine-readable contracts:
24 schemas / 23 positive fixtures
31 structural + 8 semantic rejection cases

Go backend:
PARTIAL SECURITY VERTICAL SLICE
not a production backend

Preview spool:
manifest contract hardened
Linux attempt filesystem lifecycle checkpoint created
stream writer / seal / verifier missing

PostgreSQL:
RLS / upload security foundations created
production domain schema and repositories incomplete

object storage / parser supervisor / iOS / Portal:
not implemented

current repository full/remote validation:
unconfirmed

production:
NO-GO
```

“Go backend未実装” is stale, but “backend complete” is also wrong. The exact status is **partial security vertical slice**.

“PostgreSQL migration/test created” means the RLS and upload-security foundation exists; it does not mean Preview/Apply/Memory production persistence is complete.

---

# Product direction

```txt
軽く取り込む
→ 保存前にPreviewする
→ 媒体に合う棚として見える
→ 検索・修正・更新できる
→ 月・年・つながりとして振り返れる
→ 積み重ねが記憶の町として後から見える
→ 必要なら標準形式で持ち出せる
```

Practical core:

- Universal Quick Add
- iOS Share Extension / Files intake
- Import Preview
- manga/anime progress
- movie/viewing shelf
- food/place list
- Inbox
- Search / correction
- Export / deletion
- Weekly Box / Month Capsule
- user-explicit “continue following” targets

Town is optional emotional visualization after the practical save result. Users do not record life to feed Town growth.

---

# Binding stack

```txt
iOS canonical client:
Swift 6 + SwiftUI
Share Extension
GRDB / SQLite
Keychain + App Group

limited bulk-import portal:
Vite + React + TypeScript

canonical backend:
Go API
PostgreSQL with FORCE RLS
private versioned S3-compatible quarantine
isolated parser supervisor / worker

Memory Town after Capture / Import P0:
SpriteKit
```

Earlier PixiJS/WebGL Town documents remain design exploration, not the binding runtime for the current iOS-only direction.

Parser, adapter, dedupe, Preview and Apply are canonical backend concerns and are not duplicated independently in Swift/browser/Go.

---

# Current implementation order

```txt
0. confirm exact current HEAD validators / Go format-test-vet-race-fuzz / remote workflows
1. bounded canonical accepted/rejected Preview spool stream writers
2. short-write, disk-limit and sticky cancellation tests
3. stream close/fsync + atomic manifest publication/seal
4. independent reader/decode/count/re-hash verifier
5. startup reconciliation and TTL cleanup
6. truncation/append/malformed-length/crash/tamper tests
7. production Preview candidate/rejection/ready PostgreSQL schema
8. short atomic pgx.CopyFrom repository
9. epoch recheck / rollback / retry-after-COMMIT proof
10. private versioned object storage
11. isolated parser supervisor
12. executable API + concrete Apple session/replay/repositories
13. Apply/Memory/deletion fencing
14. iOS vertical slice
15. limited Desktop Portal
16. Memory Town runtime after Capture / Import P0 reaches zero
```

Completed checkpoint:

```txt
Linux Preview spool attempt filesystem lifecycle
0700 supervisor root
mkdirat/openat
O_EXCL/O_NOFOLLOW fixed 0600 files
owner/type/mode/link checks
inode substitution rejection
partial cancellation cleanup
idempotent successful cleanup
non-Linux fail closed
```

Immediate next checkpoint:

```txt
8-byte big-endian length-prefixed canonical stream writers
+ accepted/rejected type separation
+ 100,000 aggregate row limit
+ 512 MiB aggregate byte limit
+ exact file-byte SHA-256
+ sticky cancellation/write failure
+ no goroutines/channels
```

Do not mix PostgreSQL, S3, parser-container or client work into that checkpoint.

---

# Memory-first hierarchy

```txt
1. Capture / Import
2. Retrieval / Search / Update
3. Privacy / Safety / Portability
4. Reflection / Resurfacing
5. Town visualization
6. Town customization / editor
```

Memory Town design contracts are mature, but runtime implementation remains deferred behind Capture / Import P0.

Town state remains separated into Memory Domain, Feature Progress, Layout, Environment and Render state. Normal record deletion does not punish users by shrinking unlocked Town growth. Town OFF never reduces Capture/Search/Export capability.

Town documents:

- [Current Authority Order — Round 5 Memory-first](docs/memory-town-current-authority-order-round-5-memory-first.md)
- [Capture Motivation Contract](docs/memory-first-capture-motivation-contract-round-5.md)
- [Permanent Non-goals](docs/memory-town-full-pattern-adoption-and-permanent-non-goals-round-4.md)
- [Architecture Hardening](docs/memory-town-architecture-hardening-contract.md)
- [Long-term Spatial Model](docs/memory-town-long-term-spatial-model.md)
- [Persistence / RLS / Recovery](docs/memory-town-persistence-rls-and-recovery-contract.md)

---

# Core philosophy

- AIは人生を評価しない。
- AIは人生を忘れないための索引になる。
- ラーメン、焼肉、帰り道、卒業式後の写真も全部人生。
- 重要度をAIが決めない。
- 保存時に分析しすぎない。
- 保存時は安全チェック、source、日付、検索性を中心にする。
- 分析はユーザーが求めた時だけ。
- 小さな記録を捨てない。
- 大きなイベントも押し付けない。
- 本人の記憶を作り、本人をシミュレーションしない。

# Permanent non-goals

- LLM/chat assistant replacement
- AI partner/family/deceased simulation
- personality/happiness/life-importance scoring
- monitoring, attack guidance or dependency induction
- daily quests, login rewards and streak punishment
- currency, crafting and gacha
- Town decay, care obligations or forced cleaning
- placement score, ranking or public Town feed
- limited-time reward/FOMO
- construction timers or paid acceleration
- next-stage record counts/progress bars
- Town-growth capture pressure
- mandatory Town-only fields
- multiplayer Town

```txt
記憶を入れたいと思えることが先。
保存したものが棚になる。
必要な時に探せて、続きを更新できる。
町は、その積み重ねが後から見える副次的な結果。
戻らなくても、町は荒れず、責めず、損をさせない。
必要な時は、すべて持ち出せる。
```
