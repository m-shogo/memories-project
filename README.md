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

最終更新: 2026-07-20

Read first:

1. [Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)
2. [Current Implementation Status and Roadmap](docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md)
3. [Apply / Memory Persistence Checkpoint](docs/memory-os-apply-memory-checkpoint-2026-07-23.md)
4. [Executable HTTP Server Checkpoint](docs/memory-os-http-server-checkpoint-2026-07-23.md)
4. [Runtime-Role Repository Checkpoint](docs/memory-os-runtime-role-repository-checkpoint-2026-07-23.md)
4. [importctl Harness Checkpoint](docs/memory-os-importctl-checkpoint-2026-07-23.md)
4. [Canonical Record Checkpoint](docs/memory-os-canonical-record-checkpoint-2026-07-21.md)
4. [Supervised Import Flow Checkpoint](docs/memory-os-import-flow-checkpoint-2026-07-20.md)
4. [Parser Supervisor Checkpoint](docs/memory-os-parser-supervisor-checkpoint-2026-07-20.md)
5. [Object Storage Checkpoint](docs/memory-os-object-storage-checkpoint-2026-07-19.md)
6. [Preview Commit Repository Checkpoint](docs/memory-os-preview-commit-repository-checkpoint-2026-07-19.md)
7. [Preview PostgreSQL Domain Checkpoint](docs/memory-os-preview-domain-checkpoint-2026-07-18.md)
8. [Preview Spool Reconciliation Checkpoint](docs/memory-os-preview-spool-reconciliation-checkpoint-2026-07-18.md)
9. [Preview Spool Verifier Checkpoint](docs/memory-os-preview-spool-verifier-checkpoint-2026-07-17.md)
10. [Preview Spool Seal Checkpoint](docs/memory-os-preview-spool-seal-checkpoint-2026-07-17.md)
11. [Preview Spool and Atomic Commit Contract](docs/memory-os-preview-spool-commit-contract-round-9.md)
12. [Import API Security Slice](services/import-api/README.md)
13. [Security Status](SECURITY.md)

<!-- MEMORY_OS_STATUS_BLOCK:BEGIN -->

```txt
product priority:
Capture / Import first

security architecture:
DEFINED

machine-readable contracts:
26 schemas / 23 positive fixtures
31 structural + 8 semantic rejection cases

Go backend:
PARTIAL SECURITY VERTICAL SLICE
not a production backend

Preview spool:
manifest contract hardened
Linux attempt filesystem lifecycle created
bounded accepted/rejected writer created
stream fsync + no-replace manifest publication created
independent decode / count / re-hash verifier created
startup reconciliation + TTL cleanup created

PostgreSQL:
RLS / upload security foundations created
production Preview domain schema created with live SQL tests
atomic Go Preview commit repository created (live-tested)

object storage adapter:
created (live-tested against MinIO)

parser supervisor:
process boundary created (live-tested; network namespace is deployment work)

supervised import flow:
composed and live-tested end to end (fetch → parse → verify → commit)

canonical adapter record contract:
reviewed contract created; real adapter wired through the supervised worker

importctl harness (first visible end-to-end run):
created and executed for real: local CSV → committed Preview printed to the terminal

runtime-role database access:
pgx scoped executor + concrete upload repository proven under FORCE RLS (non-superuser path)

executable HTTP server:
bearer-session auth over the strict upload handlers; exercised for real with curl (Apple exchange remains a later boundary)

Apply / Memory persistence:
idempotent exact-hash apply into memory_item over HTTP; preview read API; rich Memory domain model remains future work

account deletion fencing:
epoch bump fences every surface; authorized sweep erases all owned rows, sessions and stored object versions (live-tested over HTTP + MinIO)
a resumable background deletion runtime remains future work

iOS / Portal:
not implemented

current full-repository Go suite:
PASS in a local golang:1.23 Linux container at the recorded HEAD

remote Actions:
deletion-fencing-and-object-erasure HEAD 99cd3d4 CONFIRMED green (Import API run 30052126998, Security Contracts run 30052126969)

production:
NO-GO
```

<!-- MEMORY_OS_STATUS_BLOCK:END -->

“Go backend未実装” is stale, but “backend complete” is also wrong. The exact status is **partial security vertical slice**.

“PostgreSQL migration/test created” means the RLS and upload-security foundation exists; it does not mean Preview/Apply/Memory production persistence is complete.

A published spool manifest is untrusted until its independent verification passes. The full supervised flow (fetch → parse → seal → verify → canonical decode → commit) is composed and live-tested with the real Generic CSV adapter; the missing layers are the executable server, Apply/Memory persistence and the clients.

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
0. remote workflows confirmed for the apply-memory HEAD — done
1. deletion fencing: epoch bump + deletion-runtime sweep (live fencing proof)
2. Apple code exchange / replay store (needs real Apple credentials)
3. iOS vertical slice
4. limited Desktop Portal
5. Memory Town runtime after Capture / Import P0 reaches zero
```

Completed Preview spool checkpoints:

```txt
private Linux attempt filesystem lifecycle
+ exact bounded accepted/rejected writer
+ stream fsync
+ exclusive manifest.tmp
+ deterministic manifest JSON
+ linkat no-replace publication
+ temp unlink and attempt-directory fsync
+ rollback / durability-uncertain error boundary
+ independent strict-decode / re-count / re-hash verifier
+ truncation / append / malformed-length / substitution proofs
+ startup crash-residue reconciliation and TTL cleanup
```

Completed database checkpoint:

```txt
preview_ready / preview_candidate / preview_rejection
+ deterministic commit key and per-job/per-spool uniqueness
+ immutable ready-only state under FORCE RLS
+ structurally safe rejections
+ assert_preview_complete contiguity gate
+ live PostgreSQL 16 SQL tests
```

Completed commit-repository checkpoint:

```txt
atomic worker-role commit transaction (live PostgreSQL 16)
+ deterministic commit key (spool-attempt independent)
+ idempotent retry / conflicting-retry rejection / full rollback
+ RLS-compatible parameterized bulk insert (COPY is forbidden under RLS)
+ end-to-end spool → seal → verify → commit proof
```

Completed object-storage checkpoint:

```txt
SDK-free SigV4 presigned PUT (length/type/checksum as signed headers)
+ versioned exact-metadata HEAD with checksum mode
+ tampering / substitution / expiry rejected by the store itself
+ live MinIO round-trip and versioning proof
```

Completed parser-supervisor checkpoint:

```txt
digest-pinned worker process in its own process group
+ credential-free minimal environment (credential-shaped names rejected)
+ prlimit AS/CPU/NOFILE/FSIZE=0/CORE=0 kernel bounds
+ synchronous tagged frame protocol into the bounded spool writer
+ wall-clock and output caps, kill + fail-closed cleanup
+ end-to-end supervised parse → seal → independent verify
(network namespace isolation remains deployment work)
```

Completed import-flow checkpoint:

```txt
HEAD version recheck → version-pinned verified fetch
→ supervised parse → seal → independent verify → evidence cross-check
→ verified record collection + canonical decode
→ atomic commit — all as one live-tested flow (PostgreSQL 16 + MinIO)
drift / checksum / crash / bad-record all fail closed with no durable state
```

Completed canonical-record checkpoint:

```txt
one reviewed record contract (schema + 22-case fixture + validator)
+ cross-language enforcement: Go tests and the Python validator share the fixture
+ canonical byte serialization with fingerprint recomputation on encode and decode
+ real Generic CSV adapter emitting canonical frames inside the supervised worker
+ importflow decodes commit rows under the contract (interim decode deleted)
```

Completed importctl checkpoint — the first visible end-to-end run:

```bash
scripts/dev-up.sh
scripts/dev-import.sh   # local CSV → committed Preview printed to the terminal
```

```txt
separate digest-pinned parser-worker binary (cmd/parser-worker)
+ importctl harness: migrations → job → presigned upload → supervised parse
  → seal → independent verify → canonical decode → atomic commit → printout
+ executed for real against the dev stack (sample CSV with Japanese titles)
+ one-preview-per-job conflict and worker-pin mismatch proven through the CLI
```

Completed runtime-role repository checkpoint:

```txt
pgx scoped executor: SET LOCAL ROLE to NOLOGIN/NOBYPASSRLS runtime roles
+ concrete PostgreSQL upload repository (issue/read/consume/revoke/scan-enqueue)
+ FORCE RLS proven live: 42501 privilege probe, tenant isolation,
  full Issue → presigned PUT → Complete lifecycle through runtime roles
```

Immediate next checkpoint:

```txt
HTTP server main + session-principal middleware
with a concrete PostgreSQL session store — Apple code exchange remains a
later boundary because it needs real Apple credentials; still no client work
```

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
