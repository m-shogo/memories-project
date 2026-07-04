# Implementation Roadmap

## 目的

このロードマップは、Memory OS を思想から実装へ落とすための段階計画である。

Memory OS は ChatGPT / Claude の代替ではない。人生ランキング、人格診断、故人再現、AI恋人、会社検索、監視、パスワード管理に変質させない。

実装順序は便利さではなく、**安全・削除・出典・検索性・低コスト・小さな記録の保存**を優先する。

## Roadmap Principle

### 1. Safe core before smart AI

AI分析より先に、保存・出典・削除・Policy・Export を作る。

### 2. Small input before large import

MVPは share/manual から始める。ZIP / Takeout / Gmail / Slack は後回し。

### 3. Metadata before raw

raw全文を保存する前に、SourceRef / date / safe summary / searchable text を整える。

### 4. Deletion before backup

バックアップより先に、削除・封印・tombstone・re-import guard を設計する。

### 5. Search before proactive tip

ユーザーが求めた検索を先に作る。勝手に思い出を出す Tip は後で厳格に作る。

## Milestone 0: Design Lock

Goal: 実装前に思想と境界を固定する。

Required docs:

- `memory-constitution-v1.md`
- `memory-schema-v1.md`
- `policy-engine.md`
- `source-adapter-sdk.md`
- `export-specification.md`
- `cost-engine.md`
- `search-ranking-engine.md`
- `deletion-backup-semantics.md`
- `security-architecture.md`
- `privacy-architecture.md`
- `ux-guidelines.md`
- `memory-rfc-series.md`

Exit criteria:

- MVP scope fixed.
- never-build list fixed.
- P0 tests listed.
- schema delta listed.

## Milestone 1: Core Data Foundation

Goal: AIなしでも成立する記憶の箱を作る。

Build:

- User
- SourceRef
- ImportJob
- RawRecord
- NormalizedRecord
- Memory
- Evidence
- PolicyDecision
- Visibility/Lifecycle
- DeletionTombstone

Do not build yet:

- persona profile
- relationship diagnosis
- proactive tip
- large import
- image analysis
- full embedding

Exit criteria:

- record can be created with SourceRef.
- memory can be deleted.
- raw can be omitted.
- evidence can be shown.
- hidden/sealed states exist.

## Milestone 2: Policy + Safety Gate

Goal: 保存・検索・LLM・Export・Tip の前に必ずPolicyを通す。

Build:

- PolicyContext
- PolicyDecision
- hard deny rules
- summary-only rules
- masked-only rules
- warning rules
- audit-light logs

P0 hard deny:

- secret_or_credential -> store/search/LLM/export deny
- corporate_confidential raw -> deny
- third_party_private raw share/export -> deny
- surveillance/blame intent -> deny
- deceased impersonation intent -> deny
- minor sensitive tip/share -> deny

Exit criteria:

- policy tests run standalone.
- every critical action calls policy.
- denied decision has safe user message.

## Milestone 3: Manual Capture MVP

Goal: ユーザーが小さな記録を安全に残せる。

Build:

- manual paste
- share text
- simple memory form
- occurredAt/importedAt
- source label
- optional tag
- raw storage preference
- hide/seal/delete controls

UX rules:

- importance score is not required.
- emotion analysis is not forced.
- user can save tiny records.
- AI summary is optional or safe-only.

Exit criteria:

- user can save short memory.
- user can search it by text/date/source.
- user can delete it.
- no LLM required for core flow.

## Milestone 4: Source Adapter MVP

Goal: selected small imports can enter through a safe adapter boundary.

Build adapters:

1. `manual.paste.v1`
2. `manual.share_text.v1`
3. `generic.conversation_text.v1`
4. `openai.chatgpt_export_subset.v1`

Adapter flow:

```txt
detect -> inspect -> estimateCost -> userScope -> extract -> normalize -> policy -> index
```

Exit criteria:

- unknown source is inspect-only.
- secret finding is redacted.
- cost estimate shown before extraction.
- SourceRef exists for every record.
- large input stops partial.

## Milestone 5: Search MVP

Goal: 記憶を安全に探せる。

Build:

- keyword search
- date filter
- source filter
- memory kind filter
- result explanation
- safe snippet
- hide/seal/delete from result

Do not build yet:

- life importance ranking
- people ranking
- proactive memory resurfacing
- complex semantic ranking as only search path

Exit criteria:

- hidden/sealed/deleted excluded.
- third-party risky result is summary-only.
- explanation avoids importance language.
- surveillance query denied/redirected.

## Milestone 6: Export MVP

Goal: ユーザーが自分の記憶を安全に持ち出せる。

Build:

- source_index_only export
- readable_markdown export
- safe JSONL export
- manifest
- redaction log
- short-lived download
- export audit log

Default exclusions:

- raw LINE/DM
- Gmail raw
- Slack/company raw
- secrets
- minor data
- hidden/sealed unless explicit

Exit criteria:

- export respects policy.
- redactions are visible.
- download expires.
- Markdown has no ranking headings.

## Milestone 7: Deletion + Backup Foundation

Goal: 消した記憶が復活しない。

Build:

- pending_deletion state
- delete memory
- raw-only delete
- seal
- hide
- tombstone
- re-import tombstone check
- embedding disable hook
- backup restore replay markers design

Exit criteria:

- pending deletion blocks search/LLM/export immediately.
- re-import does not restore tombstoned records.
- raw delete sets rawStored=false.
- deletion audit has no raw text.

## Milestone 8: Cost Engine MVP

Goal: 大量処理を勝手に走らせない。

Build:

- cost estimate
- cost class
- hard stops
- confirmation requirement
- cost ledger without raw
- plan limit stubs

Exit criteria:

- medium+ jobs require confirmation.
- full history import default blocked.
- unknown full analysis blocked.
- cost ledger contains no raw.

## Milestone 9: Early Safe Integrations

Goal: 低リスク・高価値のsourceを追加する。

Build:

- Google Calendar metadata
- Photos metadata only
- LINE text summary-only
- GitHub metadata only for selected personal repos

Do not build:

- Gmail full import
- Slack full import
- image face recognition
- precise location default
- private repo code indexing

Exit criteria:

- each integration has adapter fixture tests.
- third-party/corporate/minor cases tested.
- no raw dangerous defaults.

## Milestone 10: Reflection v1

Goal: ユーザーが求めた時だけ、安全に振り返れる。

Build:

- user-requested summary
- source-cited reflection
- fact / inference separation
- confidence explanation
- safe refusal/redirect for diagnosis/simulation/blame

Do not build:

- always-on chat
- persona simulation
- life diagnosis
- partner/family analysis
- deceased message generation

Exit criteria:

- every reflection cites evidence/source.
- inference is labeled.
- dangerous requests denied safely.

## Post-MVP Candidates

Only after P0 safety is stable:

- larger ChatGPT export import
- advanced semantic search
- seasonal memories opt-in
- local backup/export
- family share with strict consent/scope
- deceased/legacy safe archive without simulation
- Gmail reservation/event summary only
- Slack personal career transition metadata only

## Never Build

- AI companion chat
- deceased simulation
- parent/wife/lover speak-as
- personality diagnosis
- life score
- importance ranking
- partner surveillance
- blame evidence search
- password manager
- company knowledge search
- child personality prediction
- raw DM family sharing

## Release Gates

### Alpha Gate

- manual capture works
- SourceRef exists
- delete works
- basic search works
- policy hard deny works

### Beta Gate

- export works
- cost estimate works
- adapter fixtures pass
- tombstone works
- security tests pass

### v1 Gate

- multiple safe adapters
- privacy audit logs
- deletion/backup semantics implemented
- markdown/json export stable
- UX copy reviewed

## 結論

Memory OS の実装は、AI機能から始めない。

まず、ユーザーが小さな記録を安全に残し、出典つきで探し、必要なら消し、持ち出せることを作る。

AI分析は、その後にユーザーが求めた時だけ、安全境界の内側で追加する。
