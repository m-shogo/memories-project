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

## Import Architecture Decision

新規追加済み:

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

Design readiness is extremely high.

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
2. expand `docs/policy-test-cases.md` with S Rank import and paste import P0 cases.
3. create UI wireframe notes for Import Preview mobile.
4. create token encryption / OAuth connector security spec before API implementation.
5. create DB schema proposal for ImportJob / ImportPreview / SourceRef.

## Last Known Commits From This Session

- `430c52acee968f3e044cfa210198ca34f4ae0713` docs: add import architecture decision
- `8f2f20b88a10cceb8df908b0287a9ed59cb6f89b` docs: add universal paste import spec
- `dabd5eba651b6c281e785865399b5ceca254e7fd` docs: add import preview ux spec
- `d1bf8c715dabd32c727996bee58c806567731533` docs: add s rank import adapter specs
- `7cba4d488139a228d3db275907c9b67e020d3677` docs: add import preimplementation readiness checklist

## Final Note

ここまでで、Memory OS は単なるプライバシー配慮だけでなく、人を傷つけないAI安全ネット、本人なりすまし防止、Export安全設計、趣味インポート設計、サービス別Import方式表、Import sanitize/private content保護、ユーザー優先SランクImport方針、Sランク各サービスの具体的な取込手順、そして実装直前のImportアーキテクチャ判断を持つ状態になった。

実装はまだ始めない。
