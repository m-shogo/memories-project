# MVP Scope

## 目的

MVP Scope は、Memory OS の最初の実装で「やること」と「絶対にやらないこと」を固定する。

Memory OS は、AIと雑談するサービスではない。人生を評価するサービスでもない。

MVPの目的は、ユーザーが小さな記録を安全に残し、出典・日付つきで探せて、必要なら消せて、rawなしでも持ち出せることを実証することである。

## MVP North Star

```txt
ユーザーが、自分の小さな記録を、AIに評価されず、安全に残し、後から探せて、消せて、持ち出せる。
```

## MVP Must Prove

MVPで証明すること:

1. 小さな記録を捨てずに残せる。
2. 保存時にAIが人生価値を決めない。
3. SourceRef / date / searchability を持てる。
4. 原文を保存しない選択ができる。
5. dangerous data を保存・LLM・embedding・exportから止められる。
6. hidden / sealed / deleted が検索・Tip・Exportに出ない。
7. JSON/Markdownで安全に持ち出せる。
8. 全履歴解析なしでも価値が出る。

## P0 Features

### 1. Manual Memory Capture

Build:

- short text memory
- manual paste
- share text endpoint or placeholder
- occurredAt optional
- importedAt required
- source label
- optional tags
- raw storage preference

Do not require:

- importance score
- emotion score
- life category
- AI summary
- people selection

### 2. SourceRef + Evidence

Every memory must have:

- sourceRefId
- createdAt/importedAt
- evidence or user statement basis
- confidence basis

Allowed confidence basis in MVP:

- user_direct_statement
- user_confirmed
- calendar_or_metadata
- ai_summary only if clearly labeled

### 3. Policy Engine P0

Implement hard denies:

- secret_or_credential
- corporate_confidential raw
- third_party_private raw export/share
- surveillance_or_blame_intent
- deceased_impersonation_intent
- minor_sensitive share/tip
- self_harm_or_crisis tip

Implement modes:

- allow
- allow_with_warning
- summary_only
- masked_only
- hide_by_default
- deny
- require_user_approval

### 4. Basic Source Adapter Boundary

MVP adapters:

- `manual.paste.v1`
- `manual.share_text.v1`
- `generic.conversation_text.v1`

Optional P1-in-MVP if stable:

- `openai.chatgpt_export_subset.v1`

Required flow:

```txt
detect -> inspect -> estimateCost -> userScope -> extract -> normalize -> policy -> index
```

### 5. Search MVP

Build:

- keyword search
- date filter
- source filter
- tag filter
- safe snippet
- explanation

Search explanation examples:

- 検索語と一致しました
- 同じ時期の記録です
- この出典に関連しています
- 安全のため要約のみ表示しています

Forbidden:

- AIが重要と判断しました
- 人生で一番大切です
- あなたの本質を表します

### 6. Visibility and Deletion

Build:

- hide
- seal
- delete memory
- delete raw only
- exclude from AI
- exclude from tips
- exclude from export
- pending_deletion
- tombstone

Required behavior:

- pending_deletion blocks search/LLM/export immediately.
- tombstone prevents re-import resurrection.
- raw-only delete keeps SourceRef and safe summary if allowed.

### 7. Export MVP

Build:

- source_index_only export
- readable_markdown export
- JSONL safe export
- manifest
- redaction list
- short-lived download placeholder

Default exclude:

- secrets
- third-party raw
- corporate data
- minor data
- hidden/sealed
- deleted

Markdown must avoid:

- ranking
- personality analysis
- life score
- best/worst year

### 8. Cost MVP

Build:

- static cost class per source/action
- estimate before extraction
- medium+ confirmation
- blocked hard stops
- cost ledger without raw

Required hard stops:

- unknown source full analysis
- full history auto import
- LINE/Gmail/Slack raw LLM
- secrets
- corporate raw

### 9. UX MVP

Required screens or flows:

- onboarding boundary explanation
- capture
- import preview
- memory detail
- search results
- deletion confirmation
- export preview
- policy denied state

UX copy must say:

- AIは人生を評価しない
- 原文を保存しない選択ができる
- 出典と日付を残す
- 削除・非表示・封印できる

## Explicitly Out of MVP

### Large Imports

Do not build in MVP:

- Gmail Takeout
- Slack export
- Discord export
- full LINE archive automation
- Apple Photos full import
- Google Photos image content analysis
- full ChatGPT history auto import

### AI-heavy Features

Do not build in MVP:

- always-on chat
- proactive AI reflection
- automatic personality analysis
- automatic life summary
- automatic top memories
- advanced relationship analysis
- grief/deceased AI messages

### Social / Sharing

Do not build in MVP:

- family share
- public profile
- shared memory albums
- partner account linking
- child account memories

### Risky Search

Do not build:

- person ranking
- evidence against person search
- coworker/customer search
- password search
- location history search for others

## P1 After MVP

P1 candidates:

- ChatGPT selected export subset
- LINE text summary-only with strict preview
- Google Calendar metadata
- Photos metadata only
- GitHub selected personal repo metadata
- better search explanation
- local export download
- red-team fixture automation

P1 still excludes:

- Gmail raw
- Slack raw
- image face recognition
- deceased simulation
- personality diagnosis

## P2 / Later

Only after security/privacy/export/deletion stable:

- Gmail reservation/event summary only
- Slack personal work transition summary only
- larger archive async inspect
- seasonal low-risk tips opt-in
- family share with strong consent/scope
- legacy archive without simulation
- local-first backup

## Never Build

These are not post-MVP. They are product boundary violations.

- ChatGPT/Claude replacement chat
- Character.AI-like personas
- deceased person simulation
- wife/parent/lover speak-as
- AI girlfriend/boyfriend
- personality diagnosis
- life score
- important people ranking
- memory importance ranking
- partner surveillance
- family blame evidence search
- password manager
- company knowledge search
- raw DM export/share by default
- child personality prediction

## MVP Data Model Minimum

Required entities:

- User
- SourceRef
- ImportJob
- RawRecord optional
- NormalizedRecord
- Memory
- Evidence
- PolicyDecisionRecord
- DeletionTombstone
- CostEstimateRecord
- ExportJob

Required fields:

- userId
- sourceType
- importedAt
- occurredAt optional
- contentHash for raw/normalized
- rawStored
- rawRetentionPolicy
- riskClasses
- privacyLevel or privacy context
- llmEligibility
- embeddingEligibility
- visibility
- lifecycle

## MVP Test Minimum

Must pass before alpha:

- policy hard deny tests
- manual/share adapter tests
- secret scan tests
- search hidden/sealed/deleted tests
- delete tombstone tests
- export redaction tests
- cost hard stop tests
- UX forbidden phrase scan

## MVP Success Metrics

Good metrics:

- records saved without required AI analysis
- source/date coverage
- successful search rate
- delete/hide/seal usage works
- export success
- policy-denied risky actions caught
- cost per user stable

Bad primary metrics:

- chat time
- emotional intensity
- number of AI messages
- number of memories auto-generated
- percentage of full histories imported

## MVP Anti-patterns

Reject implementation if it:

- asks user to rank importance on every save
- auto-generates life summary at onboarding
- imports full history by default
- stores raw DM by default
- uses importanceScore for search
- sends unknown source to LLM
- hides deletion controls
- makes export raw-first
- shows “大切な思い出を消しますか？” guilt copy

## MVP Launch Checklist

- [ ] Constitution boundaries shown in onboarding.
- [ ] Manual capture works.
- [ ] SourceRef exists for every memory.
- [ ] Policy hard deny works.
- [ ] Secret scan works.
- [ ] Search excludes hidden/sealed/deleted.
- [ ] Delete creates tombstone.
- [ ] Export excludes secrets/third-party raw/corporate/minor default.
- [ ] Cost estimate appears before medium+ processing.
- [ ] UX copy scan passes.
- [ ] Admin/support cannot read raw by default.

## 結論

MVPは「AIが全部読んで、重要な人生記憶を作る」ものではない。

最初に作るべきは、ユーザーが小さな記録を安心して残し、後から探し、消し、持ち出せる最小のMemory OSである。

AI分析は、その後に、ユーザーが求めた時だけ、安全境界の中で足す。
