# memories-project

AI時代に「自分の人生の文脈」を持ち続けるための **Memory OS** の構想・契約・実装を管理するリポジトリです。

ChatGPT / Claude / Gemini / Character.AIの代替ではありません。AIは人生を評価する主体ではなく、忘れないための索引として扱います。

```txt
Memory is the product.
Town is the visible side effect.
```

## Current authority

最終更新: 2026-07-25

Production readinessを判断するときは、次の順で読みます。

1. [Round 10 Production Operability Authority](docs/memory-os-current-authority-order-round-10-operability.md)
2. [Machine-readable Production Operability Status](contracts/operations/production-operability-status.json)
3. [Production Operability Audit](docs/memory-os-production-operability-audit-2026-07-24.md)
4. [Round 9 Security Authority](docs/memory-os-current-authority-order-round-9-security.md)
5. [Current Implementation Status and Roadmap](docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md)
6. [Import API Security Slice](services/import-api/README.md)
7. [Security Status](SECURITY.md)

Historical checkpoint documents are evidence for their recorded commit only. They do not override Round 10, current code, or current machine-readable status.

## Exact current verdict

```txt
product priority:
Capture / Import first

backend:
PARTIAL SECURITY VERTICAL SLICE
executable HTTP server exists
not a production backend

implemented and live-tested foundations:
- FORCE RLS runtime-role access
- version-bound signed upload and object verification
- bounded isolated parser supervision
- durable Preview spool and independent verification
- atomic Preview commit
- executable bearer-session HTTP server
- idempotent exact-hash Apply into minimal memory persistence
- account deletion fencing and resumable deletion worker
- Apple code exchange against a fake Apple boundary
- provenance / interpretation invariants

not implemented or not production-proven:
- rich Memory domain and user-facing retrieval/update model
- iOS canonical client and limited Desktop Portal
- real-Apple integration evidence
- structured production observability, metrics and alert routing
- endpoint-specific distributed rate limiting
- production-shaped load and capacity evidence
- backup/PITR and isolated restore rehearsal
- migration lifecycle and operator recovery runbooks
- mixed-version compatibility proof
- critical system-level failure drills

productionDecision: `NO_GO`
```

A passing local or remote test suite proves only the tested commit and scope. It does not prove production observability, backup restore, migration recovery, capacity, or operational readiness.

## Development priority

**Operations hardening before feature breadth.**

The next work must reduce production risk before adding broad user-facing scope:

1. stable error taxonomy and privacy-safe structured events;
2. request/job correlation and bounded-cardinality metrics;
3. endpoint-specific rate limiting;
4. migration and incident-recovery runbooks;
5. production-shaped sustained/burst load tests;
6. PostgreSQL PITR, object retention and isolated restore rehearsal;
7. compatibility matrix and mixed-version tests;
8. critical API/DB/object-store/parser interruption drills;
9. exact-HEAD CI evidence and independent review.

The release gate is machine-readable. A P0 area may become `READY` only when its evidence references exist and the operability validator accepts them.

## Product direction

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

## Binding stack

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

Earlier PixiJS/WebGL Town documents remain design exploration, not the binding runtime for the current iOS-only direction. Parser, adapter, dedupe, Preview and Apply remain canonical backend concerns rather than independent Swift/browser/Go implementations.

## Safety and product non-goals

The system must not become:

- a substitute personality or imitation of a living/deceased person;
- an AI partner designed to create dependency;
- a life-ranking or importance-scoring authority;
- a surveillance or coercive monitoring system;
- a public social feed, leaderboard, login-reward loop or punitive Town mechanic.

Small records are not discarded because an AI considers them unimportant. Analysis is performed when the user asks for it, not aggressively at save time.

## Validation entrypoints

```bash
python -m pip install -r requirements-security-validation.txt
python scripts/validate-memory-os-security.py
python scripts/validate-memory-os-authorization.py
python scripts/validate-memory-os-postgresql-rls.py
python scripts/validate-memory-os-apple-auth.py
python scripts/validate-memory-os-signed-upload-openapi.py
python scripts/validate-memory-os-parser-security.py
python scripts/validate-memory-os-preview-spool.py
python scripts/validate-memory-os-canonical-records.py
python scripts/validate-memory-os-memory-provenance.py
python scripts/validate-memory-os-operability.py
python scripts/validate-memory-os-entry-docs.py

cd services/import-api
test -z "$(gofmt -l .)"
go vet ./...
go test ./...
go test -race ./...
```

Historical PASS records must never be silently carried forward to a newer HEAD. Record exact commit IDs and exact workflow/test scope.

## Key implementation evidence

Detailed checkpoints remain useful as scoped evidence:

- [Apply / Memory Persistence](docs/memory-os-apply-memory-checkpoint-2026-07-23.md)
- [Executable HTTP Server](docs/memory-os-http-server-checkpoint-2026-07-23.md)
- [Runtime-role Repository](docs/memory-os-runtime-role-repository-checkpoint-2026-07-23.md)
- [Importctl Harness](docs/memory-os-importctl-checkpoint-2026-07-23.md)
- [Canonical Record](docs/memory-os-canonical-record-checkpoint-2026-07-21.md)
- [Supervised Import Flow](docs/memory-os-import-flow-checkpoint-2026-07-20.md)
- [Parser Supervisor](docs/memory-os-parser-supervisor-checkpoint-2026-07-20.md)
- [Object Storage](docs/memory-os-object-storage-checkpoint-2026-07-19.md)
- [Preview Commit Repository](docs/memory-os-preview-commit-repository-checkpoint-2026-07-19.md)
- [Preview PostgreSQL Domain](docs/memory-os-preview-domain-checkpoint-2026-07-18.md)
- [Preview Spool Reconciliation](docs/memory-os-preview-spool-reconciliation-checkpoint-2026-07-18.md)

## Production rule

Production remains blocked until all P0 operability gates have executable evidence and the machine-readable decision is deliberately reviewed. Do not equate:

- transaction rollback with migration rollback;
- object versioning with backup completion;
- component fault injection with chaos completion;
- CI green with production observability;
- authentication with rate limiting;
- dependency pinning with compatibility proof.
