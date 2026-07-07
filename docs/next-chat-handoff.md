# Next Chat Handoff

このファイルは、次のChatGPT/Codex/GitHub作業チャットで、同じ前提のまま設計を続けるための実務用引き継ぎである。

## Repository

- Repo: `https://github.com/m-shogo/memories-project.git`
- Branch: `so`
- Rule: 作業したら毎回 GitHub に commit / push する

## Important Current Instruction

実装はまだ始めない。

現在のフェーズは、Memory OS の設計を100点に近づけるための最終設計・学習・仕様固定フェーズである。

ただし、実装開始直前の順番・gate・fixture・migration・RLS・OAuth security・Go/No-Go は固定済み。

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
- AI本人/他人/故人/恋人/家族/キャラとして話すagent化

## Current Verdict

```txt
ready_with_known_risks
```

「完璧」とは言わない。

ただし、実装前設計としてはかなり強い。

Go:

- synthetic fixture planning
- first migration slice planning
- RLS negative test planning
- Import Preview-only prototype planning
- Universal Paste / Source Adapter / Parser Registry planning
- Token encryption / OAuth security planning
- Media/persona Import/Export safety planning
- Policy P0-001〜P0-055

No-Go:

- full API connector before Import Preview + Policy + token encryption
- LINE bulk raw import
- direct import-to-memory save
- import-time full embedding
- Export package before Export Safety ceremony
- media raw archive export without re-auth/scope review
- persona bundle export / agent activation
- service scraping
- vector DB / Graph DB as source of truth
- one-table JSON memories design

## Media / Image / Persona Import Export Safety

追加済み:

- `docs/media-image-import-export-safety.md`
- `docs/persona-import-export-safety.md`
- `docs/import-export-eligibility-matrix.md`
- `docs/policy-test-cases-media-persona.md`

最重要結論:

- Import allowed does not imply Export allowed.
- Export allowed does not imply Re-import as same meaning.
- 画像はmetadata-first。EXIF/GPS stripped、OCR off、AI analysis off、Export excluded by default。
- 顔、未成年、LINE/DM/仕事/医療/金融/漫画ページはrestrictedまたはmetadata/summary-only。
- chat screenshotはraw/OCR/export default denied。
- manga/comic page rawはImport denied/metadata-only。
- 他の人格、AIキャラ、character card、roleplay logs、real person writing style、deceased/partner/family persona data は simulationAllowed=false。
- Memory OSは他人/故人/家族/恋人/AIキャラとして話すagentを作らない。
- Persona-like Exportは通常Exportより高リスク。real person/deceased/partner/family/AI companion persona bundleはdeny/default excluded。
- Memory OS exportを再Importしてもpolicy/tombstone/previewをbypassしない。

Image rules:

```txt
personal photo: owner_sensitive, EXIF stripped, export explicit selection
family/friend photo: restricted, export excluded default
minor photo: restricted, export denied/default excluded
chat screenshot: summary-only, OCR off, raw export denied
medical/financial/work screenshot: restricted/denied, export excluded
manga page: metadata-only, raw denied
cover art/thumbnail: reference/URL preferred
```

Persona rules:

```txt
fictional notes: allowed as creative notes, no real-person agent
roleplay/AI companion logs: owner_sensitive/restricted, export excluded
character card: can be stored as file/reference, no activation
real person writing style: restricted, persona export denied
partner/family/deceased: restricted summary-only, speak-as denied
public figure style: no mimic bundle
```

Additional P0 tests:

- P0-041 Image EXIF GPS stripped by default
- P0-042 Chat screenshot OCR denied by default
- P0-043 LINE screenshot raw export denied
- P0-044 Minor photo standard export denied
- P0-045 Manga page raw import denied
- P0-046 SVG active content rendering denied
- P0-047 Real person style export as persona denied
- P0-048 Deceased persona activation denied
- P0-049 Character card import does not create agent
- P0-050 AI companion logs excluded from export by default
- P0-051 Persona bundle re-import no activation
- P0-052 Memory OS export re-import must check tombstones
- P0-053 Export manifest raw private title denied
- P0-054 Persona data not merged into self identity
- P0-055 Full media archive export requires reauth and scope review

## Final Implementation Order

実装に入る場合は、この順番を守る。

```txt
1. Synthetic fixtures
2. Expected detection / preview / policy snapshots
3. First migration slice
4. RLS policies + negative tests
5. SecurityGate
6. Universal Paste Parser
7. Import Preview-only prototype
8. Dedupe/Tombstone checks in Preview
9. Safe Commit for low-risk manual/paste only
10. Browser Bookmark parser
11. Netflix CSV parser
12. LINE text parser summary-only
13. Image/media preview safety only after SecurityGate
14. Persona-like import classification only, no activation
15. API connectors only after token/OAuth gates
```

## First Migration Slice

最初のmigrationでは、Memory保存本体ではなく、安全なImport基盤だけを作る。

Create:

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
oauth_connection
```

Do not create first:

```txt
source_item
canonical_item
user_activity
memory_record
search_document
embedding_record
export_package
persona_agent
```

Reason:

- Preview-onlyを先に安全に作る。
- Dedupe/Tombstone/Raw TTL/Policy/Audit/Key Referenceを先に証明する。
- 本保存・検索・Embedding・Export・persona activationは後。

## RLS / Role Model

追加済み: `docs/rls-policy-and-negative-tests.md`

Role model:

```txt
memory_migration_role
memory_app_role
memory_worker_role
memory_support_role
memory_analytics_role
memory_readonly_debug_role
```

最重要ルール:

- app runtime role must not be table owner.
- all user data tables carry user_id.
- RLS is defense in depth, not the only wall.
- missing app.current_user_id must fail closed.
- support/admin cannot read raw/private titles.
- RLS negative tests are P0.

## Import Preview-only Prototype

追加済み: `docs/import-preview-prototype-plan.md`

Prototype scope:

- Universal Paste textarea
- Source selector
- Paste detector
- Basic parsers
- Import Preview summary
- Candidate list
- Candidate edit state
- Privacy defaults
- Warnings
- Cancel
- No save

Explicitly excluded:

- final DB commit
- memory_record creation
- search_document creation
- embedding
- export
- OAuth/API connectors
- persona/character activation

Success:

- paste text/list/url → structured candidates → preview
- no MemoryRecord save
- no AI analysis
- no raw logs

## API Provider OAuth Scope Review

追加済み: `docs/api-provider-oauth-scope-review.md`

API connector implementation requires:

- Import Preview exists
- Policy Evaluation exists
- key_reference exists
- oauth_connection exists
- source_account_ref exists
- token encryption helper exists
- revocation flow exists
- audit without raw exists
- provider terms reviewed
- minimal read-only scopes selected
- fixture/API response sample exists

Provider order:

1. Spotify
2. AniList
3. Last.fm
4. TMDb catalog enrichment
5. Google Books/Open Library/NDL/Calil catalog enrichment
6. Apple Music research spike
7. X API only after cost/terms review

Apple Music and X are not API-first.

- Apple Music: research/export/paste/Last.fm fallback first.
- X: archive/url/paste first.

## Policy Test Cases

Main files:

- `docs/policy-test-cases.md` P0-001〜P0-040
- `docs/policy-test-cases-media-persona.md` P0-041〜P0-055

Coverage:

- Import Previewなしcommit拒否
- LINE raw default storage拒否
- private bookmark title logging拒否
- active content rendering拒否
- deletion tombstone re-import default除外
- sensitive dedupe plain SHA拒否
- dedupe key version必須
- low-confidence merge拒否
- shared profile owner_sensitive default
- time precision mismatchはcandidate only
- schema driftはuser review
- sealed search_document拒否
- imported source_item embedding default拒否
- OAuth token plaintext storage拒否
- broad write scope拒否
- revoked connection sync拒否
- cross-user token access拒否
- migration raw logging拒否
- restore without tombstone replay拒否
- export staging without TTL拒否
- media EXIF/GPS stripped
- chat screenshot OCR/export denied
- minor media export denied
- persona bundle/activation denied
- Memory OS export re-import tombstone check

## Long-term Database Architecture

主要docs:

- `docs/db-long-term-architecture.md`
- `docs/db-table-design-v1.md`
- `docs/import-deduplication-and-entity-resolution.md`
- `docs/db-operational-guardrails.md`
- `docs/db-edge-cases-and-hardening.md`
- `docs/db-implementation-preflight-checklist.md`
- `docs/db-migration-safety-checklist.md`

最重要結論:

- PostgreSQLをsystem of recordにする。
- raw本体はobject storageへ分離する。
- source_item / user_activity / memory_record を分ける。
- canonical_itemは作品/店/曲などの現実対象、user_activityはユーザーが見た/聴いた/読んだ/行ったという活動。
- memory_recordは人間が見返す記憶単位。
- search_document / embedding_record は派生データ。source of truthではない。
- dedupe_keyで多層重複排除する。
- deletion_tombstoneで再Import復活を防ぐ。
- sensitive dedupe/tombstone keysはHMAC + key_version。
- key_referenceでraw encryption / OAuth token encryption / HMAC / export keyを分ける。
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

## Import Architecture

主要docs:

- `docs/import-architecture-decision.md`
- `docs/universal-paste-import-spec.md`
- `docs/import-preview-ux-spec.md`
- `docs/s-rank-import-adapter-specs.md`
- `docs/import-preimplementation-readiness.md`
- `docs/import-parser-fixture-specification.md`
- `docs/import-preview-prototype-plan.md`
- `docs/media-image-import-export-safety.md`
- `docs/persona-import-export-safety.md`
- `docs/import-export-eligibility-matrix.md`

最重要結論:

- Import機能は1つの共通Import Coreで作る。
- サービスごとのSource Adapterを持つ。
- ファイル形式ごとのParser Registryを持つ。
- Content Detectorが中身・manifest・ユーザー選択・confidenceで判定する。
- 拡張子だけでは分けない。拡張子はhint。
- Universal Paste Importはfallbackではなくfirst-class Import。
- Import Previewは必須。Previewなし保存は禁止。
- Import allowed / Export allowed / Re-import allowed は別判定。
- Policy Evaluation後にSafe Commitする。
- Parser実装前にfixtureとexpected snapshotsを作る。

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

## User Priority S Rank Imports

主要docs:

- `docs/user-priority-s-rank-imports.md`
- `docs/s-rank-import-user-guides.md`
- `docs/s-rank-import-adapter-specs.md`
- `docs/api-provider-oauth-scope-review.md`

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
- login scraping は禁止。
- LINE raw、X likes/bookmarks、視聴履歴、食べログの同行者/位置情報はprivate/sensitive default。

## Import Security

主要docs:

- `docs/import-sanitization-and-private-content.md`
- `docs/token-encryption-and-oauth-security.md`
- `docs/media-image-import-export-safety.md`
- `docs/persona-import-export-safety.md`

最重要ルール:

- すべてのImport入力を敵対的入力として扱う。
- imported active contentを実行しない。
- raw HTML/SVGをImport PreviewでDOM描画しない。
- unsafe URL schemeを拒否/無害化する。
- CSV formula-like contentをre-export時に無害化する。
- archiveはmanifest inspection、size limit、file count limit、path traversal reject。
- private bookmarks は owner_sensitive default。
- private titles はbulk import summaryやlogsに出さない。
- token平文保存禁止。
- key materialはDBに置かない。
- MVP API scopesはread-only/minimal。
- OCR is off by default.
- EXIF GPS stripped by default.
- Persona simulation is never enabled by import.

## Current State

Design readiness is extremely high, but still not called perfect.

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
Import Parser Fixture Specification
Import Preview Prototype Plan
Media Image Import Export Safety
Persona Import Export Safety
Import Export Eligibility Matrix
DB Long-term Architecture
DB Table Design v1
Import Deduplication and Entity Resolution
DB Operational Guardrails
DB Edge Cases and Hardening
DB Implementation Preflight Checklist
DB Migration Safety Checklist
RLS Policy and Negative Tests
First Migration Slice Plan
Token Encryption and OAuth Security
API Provider OAuth Scope Review
Pre-implementation Go/No-Go Review
Policy Test Cases P0-001 to P0-055
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
Schema v1.1 Proposal
```

## Next Recommended Work

If still not implementing:

1. media/persona fixture concrete contents when coding begins.
2. Import Preview mobile wireframe notes.
3. API provider-specific detailed reviews one by one when needed.

If implementing next:

1. create synthetic fixtures first.
2. create first migration slice.
3. add RLS negative tests.
4. implement SecurityGate.
5. implement Universal Paste + Preview-only prototype.
6. add image/persona policy classification as Preview flags only, not activation/export.

## Last Known Commits From This Session

- `14ad2e6ef6bb0df49b81047b3fe434f3a991db81` docs: add media image import export safety
- `fc5016edf43653c6f4a2ff8d79d8b8463982a822` docs: add persona import export safety
- `c1abecd145c27e5851be064ed2e8350744dcf50f` docs: add import export eligibility matrix
- `b327729ffb2b277263f3ccda4953a1b60cd8ed83` docs: add policy tests for media persona import export

## Final Note

ここまでで、Memory OS は単なるプライバシー配慮だけでなく、人を傷つけないAI安全ネット、本人なりすまし防止、Export安全設計、趣味インポート設計、サービス別Import方式表、Import sanitize/private content保護、ユーザー優先SランクImport方針、Sランク各サービスの具体的な取込手順、実装直前のImportアーキテクチャ判断、何十年運用しても破産しにくいDB/重複排除/運用ガードレール、DB edge case hardening、preflight checklist、parser fixture仕様、migration安全checklist、token/OAuth暗号化仕様、RLS negative tests、first migration slice、Import Preview-only prototype plan、API scope review、画像/他人格/Export/Re-import安全設計、P0-055までのpolicy testsを持つ状態になった。

実装はまだ始めない。
