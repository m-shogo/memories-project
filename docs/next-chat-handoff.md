# Next Chat Handoff

このファイルは、次のChatGPT/Codex/GitHub作業チャットで、同じ前提のまま設計を続けるための実務用引き継ぎである。

## Repository

- Repo: `https://github.com/m-shogo/memories-project.git`
- Branch: `so`
- Rule: 作業したら毎回 GitHub に commit / push する

## Important Current Instruction

実装はまだ始めない。

現在のフェーズは、Memory OS の設計を100点に近づけるための最終設計・学習・仕様固定フェーズである。

## Product Goal

ChatGPT / Claude / Gemini の代替ではなく、AI時代に「自分の人生の文脈」を持ち続ける Memory OS を作る。

本人の記憶を作るサービスであり、本人を分析するサービスではない。

## Core Philosophy

- AIは人生を評価しない
- AIは人生を忘れないための索引になる
- ラーメン、焼肉、帰り道、卒業式後の写真も全部人生
- 重要度をAIが決めない
- 保存時に分析しすぎない
- 保存時は安全チェック、ソース、日付、検索性が中心
- 分析はユーザーが求めた時だけ行う
- 小さな記録を捨てない
- 大きなイベントも押し付けない
- 本人の記憶を作るサービスであり、本人を分析するサービスではない

## Absolute Non-goals

- ChatGPT代替
- Character.AI化
- 故人再現
- 親/妻/恋人の本人シミュレーション
- AI恋人化
- 人格診断
- 人生ランキング
- パスワード管理
- 会社情報検索
- 他人の秘密の記憶化
- 監視/証拠探し
- 本人なりすまし
- AI本人代弁

## DB Hardening Verdict

新規追加済み:

- `docs/db-edge-cases-and-hardening.md`
- `docs/db-implementation-preflight-checklist.md`

現時点の判定:

```txt
ready_with_known_risks
```

「完璧」とは言わない。

大枠は強いが、実装前に以下を必ず確認する:

- sensitive dedupe/tombstone keys must use HMAC, not plain SHA.
- dedupe_key / deletion_tombstone must carry key_algorithm and key_version.
- source_account_ref is needed for multi-account / shared-profile imports.
- occurred_at_precision / timezone / timezone_source are needed for ambiguous dates.
- parser_id / parser_version / adapter_id / adapter_version / source_schema_version are needed for reprocessing and schema drift.
- key_reference is needed for raw object encryption, OAuth token encryption, dedupe HMAC, tombstone HMAC, export package encryption.
- RLS is defense-in-depth only; app runtime role must not be table owner.
- shared profile contamination must be visible in Import Preview.
- large import blast radius must be limited.
- restore drill must replay deletion_tombstones and invalidate derived search/embedding.

Blocking before DB implementation:

- Import Preview missing.
- dedupe_key missing.
- deletion_tombstone missing.
- raw expiration missing.
- token/key encryption plan missing.
- private/sealed/deleted lifecycle does not affect search/export.
- embedding all imported rows is planned.
- RLS/admin role plan missing.

Recommended first migration slice:

```txt
app_user
source_ref
source_account_ref
import_job
import_input_file
import_detection_result
import_preview
import_preview_candidate
raw_object_ref
dedupe_key
deletion_tombstone
policy_decision
lifecycle_event
audit_event
outbox_event
key_reference
```

## Long-term Database Architecture

追加済み:

- `docs/db-long-term-architecture.md`
- `docs/db-table-design-v1.md`
- `docs/import-deduplication-and-entity-resolution.md`
- `docs/db-operational-guardrails.md`
- `docs/db-edge-cases-and-hardening.md`
- `docs/db-implementation-preflight-checklist.md`

最重要結論:

- PostgreSQLをsystem of recordにする。
- raw本体はobject storageへ分離する。
- source_item / user_activity / memory_record を分ける。
- canonical_itemは作品/店/曲などの現実対象、user_activityはユーザーが見た/聴いた/読んだ/行ったという活動。
- memory_recordは人間が見返す記憶単位。
- search_document / embedding_record は派生データ。source of truthではない。
- dedupe_keyで多層重複排除する。
- deletion_tombstoneで再Import復活を防ぐ。
- Import/merge/delete/export/policy/lifecycleはevent/auditとして残す。ただしrawは残さない。
- UUIDは基本。PostgreSQL対応環境ではUUIDv7を優先検討。
- 拡張子やtitle/dateだけで重複判定しない。
- embeddingはImport時に乱発しない。safe summary/memory_recordに限定し、lazy/budgetedにする。

Durable core:

```txt
SourceRef
→ SourceItem
→ CanonicalItem
→ UserActivity
→ MemoryRecord
→ Evidence / Interpretation
→ Search / Embedding derived projections
```

Minimum implementation tables:

```txt
app_user
source_ref
source_account_ref
import_job
import_input_file
import_detection_result
import_preview
import_preview_candidate
raw_object_ref
source_item
source_item_key
dedupe_key
canonical_item
canonical_item_external_id
canonical_item_alias
user_activity
user_activity_source_link
memory_record
memory_source_link
evidence_record
policy_decision
lifecycle_event
deletion_tombstone
search_document
embedding_record
audit_event
outbox_event
cost_ledger_entry
key_reference
entity_match_candidate
merge_decision
```

破産防止ガードレール:

- rawは短期/明示保存。
- Importはidempotent。
- API syncは差分優先。
- search/embeddingは派生で再生成可能。
- private/sealed/deletedはsearch/tip/exportから即除外。
- GIN indexを貼りすぎない。
- partitionは必要になるまで増やしすぎない。
- partition tableのunique制約制限を避けるためdedupe_keyを独立させる。
- backup restore時はdeletion_tombstoneをreplayする。
- Export stagingはTTL必須。

## Import Architecture Decision

追加済み:

- `docs/import-architecture-decision.md`
- `docs/universal-paste-import-spec.md`
- `docs/import-preview-ux-spec.md`
- `docs/s-rank-import-adapter-specs.md`
- `docs/import-preimplementation-readiness.md`

最重要結論:

- Import機能は1つの共通Import Coreで作る。
- ただし、サービスごとのSource Adapterを持つ。
- ファイル形式ごとのParser Registryを持つ。
- Content Detectorが中身・manifest・ユーザー選択・confidenceで判定する。
- 拡張子だけでは分けない。拡張子はhintでしかない。
- Universal Paste Importはfallbackではなくfirst-class Import。
- Import Previewは必須。Previewなし保存は禁止。
- Policy Evaluation後にSafe Commitする。

採用構成:

```txt
One Import Core
+ Source Adapters
+ Parser Registry
+ Content Detectors
+ Normalizers
+ Import Preview
+ Policy Evaluation
+ Safe Commit
```

Pipeline:

```txt
1. Intake
2. Security Gate
3. Type Detection
4. Source Detection
5. Parser Selection
6. Parse to RawImportRecords
7. Normalize to CanonicalImportRecords
8. Deduplicate
9. Privacy/Safety Classification
10. Import Preview
11. User Correction / Scope Selection
12. Policy Evaluation
13. Commit to Memory Records
14. Audit without raw
```

## Import Implementation Priority

実装に入るならまずS0から。

### Phase S0: Universal paste/manual import foundation

- ImportJob model
- ImportIntake type
- SecurityGate for paste/text/file metadata
- UniversalPasteParser
- SourceSelector
- ImportPreview DTO
- Preview-only prototype first
- Safe commit later

### Phase S1: First concrete adapters

- Browser bookmarks
- Netflix CSV
- LINE text/copy
- X archive
- Filmarks paste/URL
- 食べログ URL/list
- Podcast OPML/RSS
- GERA URL/list
- Manga/anime manual progress

### Phase S2: API adapters

- Spotify API
- AniList API
- Last.fm API
- TMDb enrichment
- Google Books/Open Library/NDL/Calil enrichment
- Apple Music research spike

### Phase S3: Streaming manual bridges

- Prime Video paste/email/manual
- Disney+ paste/manual
- U-NEXT paste/email/manual

Non-negotiable gates:

- Do not implement API connectors before Import Preview exists.
- Do not implement API connectors before Policy Evaluation exists.
- Do not implement API connectors before token encryption plan exists.
- Do not implement LINE bulk import before summary-only default and Evidence Package Blocker.
- Do not implement Export from imports before Export Safety and Re-authentication.

## User Priority S Rank Imports

- `docs/user-priority-s-rank-imports.md`
- `docs/s-rank-import-user-guides.md`
- `docs/s-rank-import-adapter-specs.md`

Sランク対象:

- Apple Music
- Twitter / X
- Netflix
- Amazon Prime Video
- Disney+
- U-NEXT
- LINE
- 食べログ
- RADIO / radio apps
- GERA
- Spotify
- Podcast
- Filmarks
- manga outside listed services
- movie outside listed services
- radio outside listed services
- anime outside listed services

最重要方針:

- User-priority S Rank overrides generic technical priority.
- APIが無理でもSランクから落とさない。
- API / official export / CSV / RSS / OPML / Takeout / email / URL clip / copy-paste / manual entry をすべて正式ルートにする。
- 履歴画面・一覧画面からのコピー貼り付けをfirst-class importとして扱う。
- 1サービスにつき複数Importルートを用意する。
- API取得手順があるものはDeveloper Console / OAuth / scope / token handlingまで書く。
- Export手順があるものは公式Export画面からMemory OS uploadまで書く。
- login scraping は禁止。
- LINE raw、X likes/bookmarks、視聴履歴、食べログの同行者/位置情報はprivate/sensitive default。

## Hobby Import Docs

- `docs/hobby-import-source-research.md`
- `docs/hobby-import-service-method-matrix.md`
- `docs/import-sanitization-and-private-content.md`
- `docs/user-priority-s-rank-imports.md`
- `docs/s-rank-import-user-guides.md`
- `docs/import-architecture-decision.md`
- `docs/universal-paste-import-spec.md`
- `docs/import-preview-ux-spec.md`
- `docs/s-rank-import-adapter-specs.md`
- `docs/import-preimplementation-readiness.md`
- `docs/db-long-term-architecture.md`
- `docs/db-table-design-v1.md`
- `docs/import-deduplication-and-entity-resolution.md`
- `docs/db-operational-guardrails.md`
- `docs/db-edge-cases-and-hardening.md`
- `docs/db-implementation-preflight-checklist.md`

## Import Security

`docs/import-sanitization-and-private-content.md` は、Import入力のセキュリティとprivate/sensitive bookmark保護を扱う。

最重要ルール:

- すべてのImport入力を敵対的入力として扱う。
- imported active contentを実行しない。
- raw HTMLをImport PreviewでDOM描画しない。
- unsafe URL schemeを拒否/無害化する。
- CSV formula-like contentをre-export時に無害化する。
- archiveはmanifest inspection、size limit、file count limit、path traversal rejectを行う。
- private bookmarks は owner_sensitive default。
- private titles はbulk import summaryやlogsに出さない。

## Current State

Design readiness is extremely high, but not called perfect.

The project now has:

```txt
Philosophy / Constitution
RFC Governance
Source Adapter SDK
Export Specification
Export Safety and Re-authentication
Hobby Import Source Research
Hobby Import Service Method Matrix
Import Sanitization and Private Content
User Priority S Rank Imports
S Rank Import User Guides
Import Architecture Decision
Universal Paste Import Spec
Import Preview UX Spec
S Rank Import Adapter Specs
Import Pre-implementation Readiness
DB Long-term Architecture
DB Table Design v1
Import Deduplication and Entity Resolution
DB Operational Guardrails
DB Edge Cases and Hardening
DB Implementation Preflight Checklist
Cost Engine
Search Ranking
Deletion Backup
Security
Privacy
UX
Storage
Local-first Backup
Incident Response
DDD
Clean Architecture
Event-driven Design
AuthZ
Observability
Formal Invariants
State Machines
Threat Model
Data Governance
Compatibility Policy
API Design
Performance Budget
Reliability/SRE
Failure Injection
ADR Process
Value Sensitive Design
Privacy by Design
Safety by Design
Responsible AI
Human Data Interaction
Digital Wellbeing
AI Harm Prevention
Crisis Safety Response
Abuse / Coercive Control Prevention
Non-Reinforcement / Dependency Safety
Vulnerable User Safety
Content Safety Taxonomy
Safety Evaluation / Red Team
Human Support / Escalation
AI Safety Net Map
Safety Feature Candidates
Identity and Impersonation Safety
MVP Engineering Tasks
Policy P0 Tests
Schema v1.1 Proposal
```

## Next Recommended Non-Implementation Work

If still not implementing, useful remaining docs:

1. create parser fixture specification.
2. expand `docs/policy-test-cases.md` with DB/dedup/import P0 cases.
3. create DB migration safety checklist.
4. create token encryption / OAuth connector security spec before API implementation.
5. create concrete DB schema migration files only when implementation starts.

## Last Known Commits From This Session

- `f26e996ef6d5b81dd2ff8b2b0fa00aae4afe4e2e` docs: add database edge cases and hardening
- `9cff6815403d600256770265ed6297b2ebfbd8f8` docs: add database implementation preflight checklist

## Final Note

ここまでで、Memory OS は単なるプライバシー配慮だけでなく、人を傷つけないAI安全ネット、本人なりすまし防止、Export安全設計、趣味インポート設計、サービス別Import方式表、Import sanitize/private content保護、ユーザー優先SランクImport方針、Sランク各サービスの具体的な取込手順、実装直前のImportアーキテクチャ判断、何十年運用しても破産しにくいDB/重複排除/運用ガードレール、さらにDB edge case hardeningとpreflight checklistを持つ状態になった。

実装はまだ始めない。
