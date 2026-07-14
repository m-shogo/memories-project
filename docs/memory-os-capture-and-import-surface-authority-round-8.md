# Memory OS Capture and Import Surface Authority — Round 8

最終更新: 2026-07-14

## Correction

Memory OSの中核はMemory Townではなく、次の順序である。

```txt
1. Capture / Import
2. Retrieval / Search / Update
3. Privacy / Safety / Portability
4. Reflection / Resurfacing
5. Town visualization
6. Town customization / editor
```

`iOS only`は、すべての取り込み作業をiPhone画面だけで完結させるという意味ではない。

```txt
iOS only
=
full product experience and canonical client are iOS-first
```

```txt
iOS only
!=
bulk JSON / CSV / ZIP migration must be performed on an iPhone
```

Share ExtensionだけをCapture全体として扱う設計は不十分であり、本書で修正する。

---

# 1. Binding product decision

Memory OSは、取り込みを三つのsurfaceへ分離する。

```txt
A. iOS Quick Capture
B. iOS File Intake
C. Desktop Web Import Portal
```

将来のAPI connectorは第四経路として扱う。

```txt
D. Connected Import
```

各surfaceは同じ`Import Intake -> Preview -> Explicit Confirmation -> Memory Domain`契約へ合流する。

```txt
capture source
→ immutable intake
→ validation / quarantine
→ source adapter detection
→ normalized preview candidate
→ user confirmation
→ Memory Domain write
→ optional enrichment
```

OS共有、ファイル選択、Web upload、API connectorのいずれも、受信しただけで確定Memoryを作らない。

---

# 2. Surface A — iOS Quick Capture

対象:

- Safariや他アプリのURL
- 選択テキスト
- URL + 選択テキスト
- screenshot / image 1枚
- 短いplain text

入口:

```txt
MemoryShare.appex
```

目的:

```txt
数秒で人生の断片を落とさず受け取る
```

Share Extensionで行うこと:

- `NSItemProvider` / `UTType`検査
- URL / text / imageの最小正規化
- size / count / filename / MIME検査
- App Group staging
- minimal ShareIntake transaction
- 成功 / 失敗を明確に表示
- 速やかに終了

行わないこと:

- 大量archive展開
- 長時間AI処理
- 大規模DB migration
- service-specific全履歴解析
- final Memory Domain write
- Town成長確定

共有画面はCaptureを軽くするための入口であり、bulk migration UIではない。

---

# 3. Surface B — iOS File Intake

対象:

- JSON
- CSV / TSV
- ZIP
- TXT / Markdown
- OPML
- PDF candidate
- 画像複数 candidate
- Memory OS export package

入口:

```txt
SwiftUI fileImporter
Files app -> Share / Open in Memory OS
registered document types
```

用途:

- ユーザーがiPhoneのFilesに保存済みのexport file
- Safariでdownloadした小〜中規模archive
- iCloud Drive / Dropbox / Google Drive等のFile Providerから選ぶfile
- AirDrop等で端末へ届いたfile

P0:

```txt
JSON
CSV
ZIP
Memory OS export package
```

UX:

```txt
追加
→ ファイルから取り込む
→ Files picker
→ file検査
→ source推定
→ Import Preview
→ 確定
```

大きいfileや複雑なmappingが必要なfileでは、iPhone上で無理に完結させない。

```txt
このファイルはPCで確認した方が安全です
→ PC取り込みへ引き継ぐ
```

を正規flowとして用意する。

---

# 4. Surface C — Desktop Web Import Portal

## 4.1 Role

Desktop Web Import Portalは、Memory OSのWeb版ではない。

```txt
Not:
- Web版の棚
- Web版Memory Town
- Web版の日常利用
- browser local stateを正本にするproduct

Yes:
- bulk import
- archive inspection
- mapping
- import preview
- migration support
- export download / recovery candidate
```

目的:

```txt
スマートフォンでは扱いにくい大量JSON / CSV / ZIPを
PCの大きな画面とfile systemで安全に取り込む
```

## 4.2 Pairing flow

推奨flow:

```txt
iOS app
→ 「PCで取り込む」
→ one-time pairing sessionを作る
→ QR code / short URL / short codeを表示

Desktop browser
→ pairing sessionへ接続
→ fileをdrag and drop
→ upload / scan / source detect
→ preview生成

iOS app
→ import ready通知
→ 最終Preview
→ explicit confirmation
→ Memory Domain write
```

代替flow:

```txt
Desktop browser
→ Sign in with Apple
→ trusted session
→ upload
→ iOSへ確認要求
```

shared PCを想定し、pairing sessionを優先する。

## 4.3 Portal limits

Portalで許可:

- file drag and drop
- directory / multi-file candidate
- resumable upload
- archive contents summary
- source adapter selection
- encoding選択
- column mapping
- duplicate strategy preview
- parsing warnings
- rejected row download
- before / after count
- import cancellation

Portalで禁止:

- Memory本文の常時閲覧
- Town操作
- unrestricted search
- confirmed Memoryのsilent edit
- final confirmationなしのbulk write
- persistent browser cacheへのprivate archive保存
- third-party analyticsへfilenameやcontentを送る

---

# 5. Surface D — Connected Import

将来候補:

```txt
OAuth / API connector
scheduled export ingestion
email export link handoff
service-specific browser flow
```

Connected Importも次を迂回しない。

```txt
source authorization
→ fetch summary
→ Import Preview
→ explicit scope confirmation
→ sync cursor creation
→ Memory Domain write
```

APIがないsourceや規約上自動取得できないsourceは、export file importを第一選択とする。

screen scrapingを標準手段にしない。

---

# 6. Installation and onboarding decision

## 6.1 Installation burden

App Storeからのアプリinstallは一度だけ必要である。

理由:

- Share Extension
- secure App Group intake
- background transfer recovery
- local search
- private local cache
- Town renderer
- notifications
- final confirmation

しかし、install直後に大量export fileの準備を要求しない。

初回体験:

```txt
1. appをinstall
2. URLまたは短いtextを一件保存
3. 棚への反映を確認
4. Share Extensionを有効にする案内
5. bulk importは後で任意
```

禁止:

- 初回にZIP exportを要求
- 初回に複数service連携を要求
- 初回にPCを必須化
- importしないとTownが空で罰する
- migration完了まで検索やQuick Addを隠す

## 6.2 Value before migration

ユーザーはbulk migrationなしでも価値を得られなければならない。

```txt
Share one item
→ safe preview
→ shelf appears
→ searchable
→ optional quiet Town reaction
```

過去データ移行は価値増幅器であり、初回利用の関門ではない。

---

# 7. Import source adapter model

すべてのservice-specific parserは共通adapter契約へ従う。

```ts
interface ImportSourceAdapterManifest {
  adapterId: string;
  adapterVersion: number;
  sourceId: string;
  acceptedContentTypes: string[];
  acceptedExtensions: string[];
  detectionSignatures: DetectionSignature[];
  supportedExportVersions: string[];
  parserVersion: string;
  normalizerVersion: string;
  dedupeStrategyId: string;
  previewProjectionVersion: string;
  maximumInputBytes: number;
  maximumExpandedBytes: number;
  networkAccessDuringParse: 'forbidden' | 'allowlisted';
  rawArchiveRetentionDefault: 'delete_after_confirmation' | 'user_choice';
}
```

Adapterが返すもの:

- source evidence
- detected export version
- parsed item candidates
- unsupported rows
- warnings
- duplicate candidates
- required user decisions
- provenance fields

Adapterが決めないもの:

- 人生上の重要度
- 感情
- 人間関係の意味
- Town growth priority
- hidden / sensitive recordの公開

---

# 8. Generic import fallback

service-specific adapterがない場合も、generic importを用意する。

対応candidate:

- JSON array
- JSON Lines
- CSV / TSV
- ZIP containing supported text files

Generic mapper:

```txt
field detection
→ user column mapping
→ date / URL / title candidates
→ sample preview
→ validation
→ save mapping profile locally / account scope
```

PC Portalでは表形式mappingを提供できる。

iPhoneでは簡易mappingだけ提供し、複雑な場合はPC Portalへ誘導する。

AI mappingは候補提示に限定し、確定mappingを勝手に適用しない。

---

# 9. Bulk import security contract

必須検査:

- extension / MIME / magic byte一致
- maximum compressed size
- maximum expanded size
- compression ratio
- maximum entry count
- nested archive depth
- path traversal
- absolute path
- symbolic link
- duplicate filename
- invalid UTF encoding
- excessively deep JSON
- excessively large token / field
- formula injection in CSV export
- HTML / script content isolation
- executable / package rejection
- content hash
- malware scanning where available

ZIP防御:

```txt
compressed bytes cap
expanded bytes cap
entry cap
ratio cap
nested archive cap
CPU / wall-time budget
```

Raw upload:

```txt
quarantine
→ scan
→ parse copy
→ preview
→ confirmation
→ retention policy
```

raw archiveを永久保存しない。

default:

```txt
Import confirmed or cancelled
→ retention grace period
→ secure deletion job
```

ユーザーが原本保管を明示した場合だけ、暗号化object storageへ移す。

---

# 10. Pairing and session security

PC pairing session:

- random high-entropy token
- one-time use
- short TTL
- account / device binding
- upload scope only
- no general account browse permission
- explicit device confirmation candidate
- CSRF protection
- origin validation
- rate limit
- audit without private payload
- session revoke button
- upload completion revokes write token

QRやshort codeへaccount identifierやprivate filenameを含めない。

shared PCでは、browser storageへrefresh credentialを残さないflowを優先する。

---

# 11. Import state machine

```ts
type ImportIntakeStatus =
  | 'received'
  | 'uploading'
  | 'uploaded'
  | 'quarantined'
  | 'scanning'
  | 'source_detection'
  | 'parsing'
  | 'preview_ready'
  | 'decision_required'
  | 'confirmed'
  | 'applying'
  | 'completed'
  | 'partially_completed'
  | 'rejected'
  | 'cancelled'
  | 'expired'
  | 'cleanup_pending'
  | 'cleaned';
```

状態遷移を一つのboolean `imported`で表さない。

必須ID:

- intakeId
- uploadId
- parserJobId
- previewRevision
- confirmationId
- applyBatchId
- cleanupJobId

retryでMemory recordを重複作成しない。

---

# 12. Preview contract

Previewに表示:

- source
- file count
- candidate item count
- accepted count
- skipped count
- unsupported count
- duplicate candidate count
- date range
- detected categories
- parser warnings
- raw archive retention choice
- estimated storage use candidate

Previewで隠す / 制限:

- hidden contentの不必要な全文
- archive内secret token
- cookie
- session file
- browser credential export
- OS metadata unrelated to Memory

Bulk Previewは全件を一画面に羅列しない。

```txt
summary
+ sampled rows
+ warning groups
+ filterable decisions
+ downloadable rejection report
```

---

# 13. Confirmation authority

原則:

```txt
final confirmation authority = iOS app
```

理由:

- trusted installed client
- private local state
- device authentication
- retention decision
- account binding
- accidental shared-PC confirmation防止

例外候補:

個人所有PCとして明示的にtrusted browserへ昇格した場合のみ、Web confirmationを将来検討できる。

初期版では採用しない。

---

# 14. Offline and recovery behavior

## iOS local file

```txt
file selected
→ local quarantine
→ local parse where supported
→ preview
→ confirm locally
→ sync later
```

## Web bulk upload

```txt
upload completed
→ server parse continues
→ iOS may go offline
→ preview waits safely
→ confirmation after reconnect
```

Rules:

- app終了でupload済みfileを失わない
- parse失敗でraw fileを即削除せずgrace periodを持つ
- confirmation timeoutでMemoryへ自動適用しない
- account deletionでintake / upload / preview / raw / jobsを全削除
- cancelled importをTown growthへ反映しない

---

# 15. Server architecture impact

Go backend modules:

```txt
ImportSessionService
UploadService
QuarantineService
ArchiveInspector
SourceDetector
AdapterRegistry
ParserWorker
PreviewProjector
ImportApplyService
CleanupService
```

PostgreSQL:

- import_session
- import_upload
- import_job
- import_preview
- import_decision
- import_apply_batch
- import_rejection
- import_cleanup_job

Object storage:

- quarantine object
- parser working copy
- optional retained original
- rejection report

large binaryをPostgreSQL rowへ保存しない。

---

# 16. Product hierarchy impact

Memory Town implementationより前に検証する。

```txt
P0
- Share URL / text / image
- iOS JSON / CSV / ZIP file import
- PC pairing
- desktop upload
- source detection
- preview
- cancel / expiry / cleanup
- duplicate-safe apply

P1
- service-specific major adapters
- resumable multi-GB candidate
- generic column mapper
- rejected-row repair

P2
- API connectors
- scheduled imports
- trusted desktop confirmation
```

TownはImport確定後の静かな副作用である。

```txt
Import success
→ Memory / shelf confirmation
→ optional quiet Town response
```

PortalでTown報酬、進捗bar、件数煽りを表示しない。

---

# 17. Hard stop conditions

次の状態では実装認可しない。

- Share ExtensionだけでCapture戦略を完結させる
- iPhoneだけで全bulk importを行わせる
- Web Portalを無制限なWeb版Memory OSへ拡張する
- upload完了をMemory確定とみなす
- PCだけで最終確定しshared-device事故を防げない
- unknown ZIPを無制限展開する
- parserがnetworkへ任意accessする
- raw archiveを期限なく保持する
- parser retryでduplicate Memoryを作る
- generic AI mappingを無確認で確定する
- failed importがTownを成長させる
- account deletion後にquarantine objectやjobが残る

---

# 18. Current decision summary

```txt
Canonical product client:
iOS native

Daily lightweight capture:
iOS Share Extension

Local export file import:
iOS Files / fileImporter

Large and complex migration:
Desktop Web Import Portal

Final confirmation:
iOS app

Canonical service source:
Go API + PostgreSQL

Town:
Import and Memory utilityに従属
```
