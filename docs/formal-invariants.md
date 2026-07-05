# Formal Invariants

## 目的

Formal Invariants は、Memory OS で絶対に破ってはいけない不変条件を定義する。

これは思想を文章で語るだけではなく、将来の実装・テスト・レビュー・CIで守るための「公理」である。

Memory OS は、AIチャット代替ではなく、本人の人生文脈を持ち続けるための索引である。

そのため、以下の不変条件が破られた時点で、機能が便利に動いていても失敗とみなす。

## Invariant の考え方

Invariant とは、状態や処理の前後で必ず成り立つ条件である。

例:

```txt
Deleted memory must never appear in search.
```

これは「できれば守る」ではない。

破れたらバグであり、事故であり、リリースを止める条件である。

## Severity

```ts
type InvariantSeverity = 'P0' | 'P1' | 'P2';
```

- P0: 破ったらリリース停止。データ漏洩・思想破壊・削除権侵害。
- P1: 重大な信頼低下。速やかに修正。
- P2: 品質劣化。計画的に修正。

## P0 Invariants

### INV-P0-001 Memory must have SourceRef

```txt
Every Memory must have at least one SourceRef or Evidence linked to a SourceRef.
```

理由:

AIが勝手に作った記憶と区別するため。

テスト:

- Memory作成時にsourceRefIdsが空ならfail。

### INV-P0-002 Interpretation is not fact

```txt
MemoryInterpretation must never overwrite Memory fact fields.
```

理由:

AIの意味づけと事実を混ぜないため。

### INV-P0-003 Policy before LLM

```txt
No record may be sent to LLM without a PolicyDecision for send_to_llm.
```

理由:

秘密・会社情報・第三者情報・封印記憶のLLM送信を防ぐため。

### INV-P0-004 Policy before Export

```txt
Every exported entity must pass export_memory policy.
```

理由:

Exportはデータ出口であり、最重要漏洩点である。

### INV-P0-005 Deleted never appears

```txt
Deleted or pending_deletion records must never appear in search, tips, LLM input, share, or export.
```

理由:

削除権を守るため。

### INV-P0-006 Tombstone contains no raw

```txt
DeletionTombstone must never contain raw text, secret value, or third-party raw content.
```

理由:

tombstoneが隠れたraw保存にならないため。

### INV-P0-007 Raw must not be logged

```txt
Logs, metrics, traces, audit logs, and incident records must not contain raw memory text.
```

理由:

ログが第二の漏洩源になるため。

### INV-P0-008 Secrets are never searchable

```txt
Secret or credential data must never be stored in searchable text, embedding vectors, export packages, or logs.
```

理由:

Memory OSはパスワード管理サービスではない。

### INV-P0-009 Admin is not owner

```txt
Admin access must never imply ownership of user memory.
```

理由:

管理者がユーザーの人生文脈を普通に読める設計にしない。

### INV-P0-010 AuthZ allow cannot override Policy deny

```txt
If AuthZ allows but Policy denies, the action must be denied.
```

理由:

ユーザー本人でも第三者raw exportなどは許可されない。

### INV-P0-011 Unknown source inspect-only

```txt
Unknown or low-confidence source must not be fully extracted, embedded, or sent to LLM.
```

理由:

危険データの誤解析を防ぐ。

### INV-P0-012 No life ranking fields

```txt
Production schema and ranking code must not introduce life value fields such as importanceScore, lifeScore, personalityScore, or personRank.
```

理由:

人生ランキング化を防ぐ。

### INV-P0-013 Third-party raw is not user memory by default

```txt
Third-party raw messages must not become user Memory body by default.
```

理由:

他人の秘密を本人の資産にしない。

### INV-P0-014 Corporate confidential denied by default

```txt
Corporate confidential data must not be stored, embedded, sent to LLM, searched, or exported by default.
```

理由:

会社情報検索サービス化を防ぐ。

### INV-P0-015 Sealed stronger than hidden

```txt
Sealed records must be excluded from search, tips, LLM, share, and export unless an explicit sealed unlock flow exists.
```

理由:

封印の意味を強く保つ。

### INV-P0-016 Backup restore must replay tombstones

```txt
Backup restore must replay deletion tombstones before restored data becomes searchable or exportable.
```

理由:

削除済みデータ復活を防ぐ。

### INV-P0-017 Export raw default off

```txt
Raw content must be excluded from exports by default.
```

理由:

Exportがraw漏洩ツールになるのを防ぐ。

### INV-P0-018 No deceased speak-as

```txt
The system must not generate responses as a deceased person, family member, partner, or lover.
```

理由:

本人シミュレーション化を防ぐ。

### INV-P0-019 Minor data no proactive surfacing

```txt
Minor-sensitive data must not be proactively surfaced in tips or shared/exported by default.
```

理由:

未成年情報の保護。

### INV-P0-020 Dangerous success is failure

```txt
If a dangerous action succeeds when policy should deny it, the test must fail even if the feature output looks useful.
```

理由:

便利な事故を成功扱いしない。

## P1 Invariants

### INV-P1-001 Source date distinction

```txt
occurredAt, capturedAt, importedAt, interpretedAt must remain distinct.
```

### INV-P1-002 User label is not evidence

```txt
User-provided label must not be treated as factual evidence.
```

### INV-P1-003 Search explanation must be non-judgmental

```txt
Search explanations must not claim life importance or personality meaning.
```

### INV-P1-004 Cost estimate before medium jobs

```txt
Medium or higher cost jobs must require estimate and user confirmation.
```

### INV-P1-005 Redactions explicit

```txt
Redacted export fields must record redaction reason.
```

### INV-P1-006 Raw-only delete preserves provenance

```txt
Raw-only delete may preserve SourceRef and safe metadata but not raw text.
```

### INV-P1-007 LLM output must be labeled as interpretation

```txt
LLM-generated summaries or reflections must be labeled as generated interpretation or summary, not original fact.
```

## P2 Invariants

### INV-P2-001 Small records remain first-class

```txt
Short food, hobby, route, and ordinary-day records must not require importance classification.
```

### INV-P2-002 Empty states must not shame

```txt
Empty states must not say important memories are missing.
```

### INV-P2-003 Export packages include schema version

```txt
Every export package must include schemaVersion and policyVersion.
```

## Invariant Test Matrix

| Invariant | Test Suite |
|---|---|
| INV-P0-001 | memory creation tests |
| INV-P0-003 | LLM boundary tests |
| INV-P0-004 | export tests |
| INV-P0-005 | deletion/search/export tests |
| INV-P0-007 | observability/logging tests |
| INV-P0-008 | secret scan tests |
| INV-P0-012 | forbidden field scanner |
| INV-P0-016 | backup restore tests |
| INV-P0-018 | policy red-team tests |

## CI Rule

P0 invariant failure blocks merge.

P1 invariant failure blocks release unless explicitly waived by RFC.

P2 invariant failure creates issue.

## 結論

Formal Invariants は、Memory OS の憲法をコードに近づけるためのルールである。

100点の設計とは、きれいな文章ではなく、破ってはいけない条件が明確で、テストとCIで守れる状態である。
