# Next Chat — Memory OS Capture / Import Implementation Round 8

最終更新: 2026-07-15

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

## Read first

1. `docs/memory-os-capture-and-import-surface-authority-round-8.md`
2. `docs/memory-os-capture-import-implementation-architecture-round-8.md`
3. `docs/memory-town-current-authority-order-round-8-ios-native.md`
4. `docs/ios-native-technology-stack-decision-round-8.md`

## Binding correction

Capture / Import implementation must not duplicate parser logic across Swift, browser TypeScript and Go.

```txt
iOS Share / Files
+ Desktop Import Portal
→ one Import Job API
→ one server adapter / parser / dedupe / preview / apply pipeline
```

## Technology split

```txt
iOS product:
Swift 6 + SwiftUI + GRDB

Share intake:
MemoryShare.appex + App Group

Import backend:
Go + PostgreSQL + S3-compatible quarantine storage

Desktop Portal:
Vite + React + TypeScript thin client

Town:
SpriteKit after Capture / Import vertical slice
```

## Portal boundary

The Portal owns only:

- pairing
- drag and drop
- upload progress
- source / mapping options
- preview presentation
- cancellation

The Portal does not own:

- parser implementations
- dedupe authority
- confirmed Memory data
- shelves
- search
- Memory Town
- final apply in P0

## Import Job states

```txt
created
→ awaiting_upload
→ uploaded
→ quarantined
→ scanning
→ detecting_source
→ parsing
→ preview_ready
→ awaiting_confirmation
→ applying
→ applied
```

Terminal / failure states:

```txt
rejected
failed_retryable
failed_terminal
cancelled
expired
superseded
```

## Upload rule

```txt
client
→ Go API creates server-owned object key and upload authorization
→ client uploads directly to quarantine object storage
→ API verifies completion metadata
→ isolated worker scans and parses
```

Do not proxy large archive bytes through the public Go API process.

## Preview integrity

Final confirmation must include:

```txt
previewId
previewHash
idempotencyKey
user duplicate choices
```

Reject confirmation after source hash, adapter version, parsing options, account or preview expiry changes.

## Minimal backend

```txt
Go net/http or small router
pgx
sqlc
PostgreSQL-backed job queue
one import worker
OpenAPI
```

Do not start with Redis, Kafka, RabbitMQ or a large service framework.

## Initial adapters

```txt
1. Generic CSV
2. Generic JSON array
3. Memory OS export package
4. first service-specific adapter
5. second service-specific adapter
```

## Correct implementation sequence

```txt
1. Import Job schema
2. Import Preview / confirmation schema
3. adapter manifest / interface
4. pairing session contract
5. quarantine upload contract
6. expiry / deletion contract
7. Go Import Job API
8. PostgreSQL job tables
9. object-storage upload
10. one worker
11. Generic CSV adapter
12. preview + idempotent apply
13. Share Extension URL / text
14. App Group recovery
15. iOS main Preview
16. iOS fileImporter upload
17. Generic JSON adapter
18. Desktop Portal pairing and upload
19. duplicate-safe evidence
20. TownSceneSnapshot and SpriteKit prototype
```

## Current status

```txt
implementation architecture:
created

single parser authority:
locked

Go import vertical slice:
not implemented

iOS Share vertical slice:
not implemented

iOS file intake:
not implemented

Desktop Portal:
not implemented

Town implementation:
blocked behind Capture / Import vertical slice
```
