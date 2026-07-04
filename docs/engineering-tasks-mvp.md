# Engineering Tasks MVP

## 目的

Engineering Tasks MVP は、Memory OS のMVPを実装するための作業を、Codex / Claude Code / 人間エンジニアが小さく進められる粒度に分解する。

このタスク表は `docs/mvp-scope.md` と `docs/implementation-roadmap.md` に従う。

## 実装原則

- 小さくcommitする。
- 1PR/1commitで1つの境界を作る。
- AI機能より先に、SourceRef / Policy / Delete / Export / Test を作る。
- raw text をログに出さない。
- importanceScore / lifeScore / personalityScore を作らない。
- 便利でも never build に触れるものは入れない。

## Phase 0: Repo Setup and Guardrails

### T0-001 Add docs index

Create or update docs index linking core docs.

Acceptance:

- README or docs index links MVP docs.
- never-build list visible.

### T0-002 Add forbidden phrase scanner

Add static scan for dangerous UX/code terms.

Forbidden examples:

- importanceScore
- lifeScore
- personalityScore
- 人生TOP10
- 一番大切な人
- 故人からのメッセージ
- 妻の性格

Acceptance:

- scanner fails on forbidden terms.
- allowlist mechanism exists for docs that discuss forbidden terms as prohibitions.

### T0-003 Add fixture directory structure

Create test fixture folders.

```txt
tests/fixtures/policy
tests/fixtures/adapters/manual
tests/fixtures/adapters/share_text
tests/fixtures/security
tests/fixtures/export
tests/fixtures/deletion
tests/fixtures/privacy
tests/fixtures/cost
```

Acceptance:

- no real personal data.
- fixture metadata format documented.

## Phase 1: Schema v1.1 Additive Types

### T1-001 Add TypeScript schema types

Implement additive types from `schema-v1-1-proposal.md`.

Types:

- AdapterMetadata
- ImportScope
- SurfaceVisibility
- PrivacyContext
- PolicyDecisionRecord
- DeletionTombstone
- CostEstimateRecord
- CostLedgerEntry
- ExportJob
- EmbeddingRecord

Acceptance:

- types compile.
- no forbidden ranking/personality fields.

### T1-002 Add lifecycle helpers

Implement helpers:

```ts
isSearchVisible(memory)
isTipEligible(memory)
isLlmEligible(memory)
isExportEligible(memory)
isDeletedOrPending(entity)
```

Acceptance:

- hidden/sealed/deleted/pending behavior tested.

### T1-003 Add safe redaction type helpers

Implement redaction primitives.

Acceptance:

- secrets produce `[REDACTED]`.
- summary-only produces `[SUMMARY_ONLY]`.
- no raw value in redaction logs.

## Phase 2: Policy Engine P0

### T2-001 Implement PolicyContext and PolicyDecision

Implement core policy types and evaluator shell.

Acceptance:

- `evaluatePolicy(context)` returns PolicyDecision.
- default deny for unknown dangerous actions.

### T2-002 Implement hard deny rules

Rules:

- secret_or_credential
- corporate_confidential raw LLM
- third_party_private raw quote/export/share
- surveillance_or_blame_intent
- deceased_impersonation_intent
- minor_sensitive tip/share
- self_harm_or_crisis tip

Acceptance:

- P0 hard deny tests pass.

### T2-003 Implement summary/masked/warning rules

Rules:

- LINE/DM relationship summary
- medical/mental summary
- grief/deceased values reference
- self-harm historical safe summary

Acceptance:

- summary_only and masked_only modes tested.

### T2-004 Add policy test cases

Convert `docs/policy-test-cases.md` P0-001〜P0-020 into executable tests.

Acceptance:

- all pass.
- snapshots contain no raw sensitive data.

## Phase 3: Manual and Share Adapters

### T3-001 Implement adapter interface

Methods:

```ts
detect
inspect
estimateCost
plan
extract
normalize
```

Acceptance:

- interface compiles.
- unknown source can return inspect-only.

### T3-002 Implement manual paste adapter

Acceptance:

- detects manual input.
- creates SourceRef draft.
- creates RawRecord optional.
- creates NormalizedRecord.
- runs secret scan before raw storage.

### T3-003 Implement share text adapter

Acceptance:

- share text small input works.
- importedAt captured.
- user label kept separate from fact content.

### T3-004 Add adapter fixture tests

Cases:

- safe short memory
- secret text
- third-party private hint
- missing date
- huge input partial

Acceptance:

- no LLM call needed.
- every output has SourceRef.

## Phase 4: Memory Creation MVP

### T4-001 Implement create memory use case

Flow:

```txt
adapter output -> policy -> create SourceRef -> create records -> create Memory -> create Evidence
```

Acceptance:

- memory created without AI summary.
- SourceRef required.
- Evidence required.

### T4-002 Add raw storage preference

Options:

- none
- metadata_only
- safe_raw
- ask_each_time

Acceptance:

- rawStored accurately reflects choice.
- raw no/default for risky data.

### T4-003 Add confidence basis

MVP basis:

- user_direct_statement
- user_confirmed
- calendar_or_metadata
- ai_summary

Acceptance:

- confidence displayed/explainable.

## Phase 5: Visibility and Deletion

### T5-001 Implement hide

Acceptance:

- hidden excluded from search default.
- can be unhidden.

### T5-002 Implement seal

Acceptance:

- sealed excluded from search/tip/LLM/export default.
- requires explicit unlock.

### T5-003 Implement delete memory

Acceptance:

- lifecycle pending_deletion immediately.
- then deleted/tombstoned.
- search/LLM/export blocked at pending.

### T5-004 Implement raw-only delete

Acceptance:

- raw content removed.
- SourceRef remains.
- rawStored=false.
- safe summary may remain if policy allows.

### T5-005 Implement tombstone check

Acceptance:

- re-import matching contentHash/externalId skipped.
- tombstone has no raw text.

## Phase 6: Search MVP

### T6-001 Implement keyword search

Acceptance:

- searches normalized safe text.
- userId scoped.
- lifecycle filter applied before ranking.

### T6-002 Implement date/source/tag filters

Acceptance:

- occurredAt/importedAt distinction preserved.
- source filter uses SourceRef.

### T6-003 Implement safe snippets

Acceptance:

- show_raw_quote policy required.
- risky data summary-only/no snippet.

### T6-004 Implement explanations

Allowed reasons:

- keyword_match
- same_time_period
- source_match
- user_tagged
- safe_summary_only

Acceptance:

- no life importance language.

### T6-005 Deny surveillance search

Acceptance:

- requestIntent `surveillance_or_blame` denied/redirected.

## Phase 7: Export MVP

### T7-001 Implement export manifest

Acceptance:

- schemaVersion/policyVersion/exportSpecVersion included.
- counts included.
- filters included.

### T7-002 Implement JSONL safe export

Acceptance:

- ExportEnvelope per line.
- policy per entity.
- redactions recorded.

### T7-003 Implement readable markdown export

Acceptance:

- no ranking/personality headings.
- SourceRef summary included.
- hidden/sealed/deleted excluded default.

### T7-004 Implement export audit log

Acceptance:

- no raw content.
- created/downloaded/expired/deleted states.

## Phase 8: Cost MVP

### T8-001 Implement static cost estimate

Acceptance:

- share/manual small = free_or_tiny/low.
- unknown full analysis = blocked.
- full history = requires_credit or blocked.

### T8-002 Implement confirmation gate

Acceptance:

- medium+ requires user confirmation.
- Policy deny cannot be overridden.

### T8-003 Implement cost ledger

Acceptance:

- stores counts/units only.
- no raw text.

## Phase 9: UX MVP Copy

### T9-001 Onboarding copy

Must include:

- AIは人生を評価しない
- 原文を保存しない選択
- 出典と日付
- 削除/非表示/封印

### T9-002 Import preview copy

Must include:

- first inspect
- no full analysis before scope
- cost estimate
- exclusions

### T9-003 Deletion copy

Must be guilt-free.

Bad:

```txt
本当にこの大切な思い出を消しますか？
```

Good:

```txt
この記録を削除できます。削除後は検索・Tip・Exportに表示されません。
```

## Phase 10: MVP CI Gate

### T10-001 Add test:p0 script

Runs:

- policy tests
- adapter tests
- deletion tests
- search safety tests
- export tests
- cost tests
- UX copy scan

Acceptance:

- CI fails on dangerous success.

## Suggested Commit Order

1. schema types
2. lifecycle helpers
3. policy core
4. policy P0 tests
5. manual adapter
6. share adapter
7. memory creation
8. visibility/delete/tombstone
9. keyword search
10. export manifest/jsonl
11. cost estimate
12. UX copy scan
13. test:p0

## Do Not Implement Yet

- Gmail full import
- Slack full import
- Discord full import
- image content analysis
- face recognition
- AI chat UI
- proactive tips
- family share
- deceased/legacy workflows
- semantic search over all data

## Definition of MVP Done

MVP is done when:

- user can manually save a small memory
- SourceRef/Evidence exists
- Policy P0 denies dangerous cases
- user can search safe memories
- hidden/sealed/deleted respected
- user can export safe archive
- user can delete/raw-delete
- cost estimate prevents large jobs
- P0 tests pass
- no forbidden ranking/personality fields or UX copy

## 結論

MVP実装はAI機能から始めない。

まず、記憶を安全に入れる・探す・消す・持ち出す・危険を止める。

それができてから、ユーザーが求めた時だけAI分析を足す。
