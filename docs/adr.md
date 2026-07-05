# Architecture Decision Records

## 目的

ADR（Architecture Decision Record）は、重要な設計判断を小さく記録するための仕組みである。

RFCは大きな仕様提案に向いている。

ADRは、日々の技術選定や設計判断を「なぜそうしたか」まで残すために使う。

## ADRを一言で言うと

```txt
未来の自分に向けた、設計判断のメモ。
```

## RFC と ADR の違い

| Type | Use when | Example |
|---|---|---|
| RFC | 大きな仕様・プロダクト方針 | Source Adapter SDK |
| ADR | 具体的な技術/設計判断 | SQLiteをMVPで使う |

## ADR Directory

```txt
docs/adrs/
  0000-template.md
  0001-use-jsonl-for-export.md
  0002-raw-default-off.md
  0003-keyword-search-before-vector.md
```

## ADR Status

```ts
type AdrStatus = 'proposed' | 'accepted' | 'superseded' | 'deprecated' | 'rejected';
```

## ADR Template

```md
# ADR-XXXX: Title

## Status

accepted

## Context

What problem are we solving?

## Decision

What did we decide?

## Consequences

What becomes easier?
What becomes harder?
What risk remains?

## Alternatives Considered

## Links
```

## When to Write ADR

Write ADR when deciding:

- DB choice
- export format
- backup format
- search engine
- vector DB
- LLM vendor boundary
- raw storage policy
- encryption strategy
- API style
- framework choice
- local-first approach
- event/outbox strategy

## Required ADRs Before Implementation

Recommended initial ADRs:

1. JSONL + Markdown as export formats.
2. Raw default off for risky sources.
3. Keyword search before vector search.
4. PolicyEvaluator as pure domain service.
5. No LLM in core capture path.
6. Tombstone for deleted record resurrection prevention.
7. SQLite/PostgreSQL choice for MVP.
8. Object storage for raw files.
9. Outbox pattern for deletion/export events.
10. Forbidden phrase scanner in CI.

## ADR Rules

- Keep ADR short.
- One decision per ADR.
- Include rejected alternatives.
- Include safety/privacy/cost consequence if relevant.
- Supersede old ADR instead of editing history heavily.

## Example ADR

```md
# ADR-0001: Use JSONL and Markdown for Safe Export

## Status

accepted

## Context

Memory OS must let users take their life context outside the service.
The export must be both machine-readable and human-readable.

## Decision

Use JSONL for structured migration and Markdown for readable archive.
Raw content is excluded by default.

## Consequences

Easier:
- Long-term readability
- Migration
- Diffing

Harder:
- Rich media export requires separate package
- Large exports need job handling

## Alternatives Considered

- Proprietary binary format: rejected due to lock-in.
- JSON only: rejected because less human-readable.
```

## ADR Review Checklist

1. Does this decision affect Memory Constitution?
2. Does it affect deletion?
3. Does it affect Export or backup readability?
4. Does it affect third-party/minor/corporate data?
5. Does it increase LLM/cost dependency?
6. Does it make future migration harder?
7. Does it introduce forbidden ranking/personality concepts?

## Acceptance Criteria

- ADR template exists.
- Required ADR list exists.
- ADRs are linked from handoff when created.
- Major implementation choices have ADRs.

## 結論

ADRは、Memory OSの設計判断を忘れないための記録である。

Memory OS自体が「忘れないための索引」なら、プロジェクトの設計判断も忘れないように残す。
