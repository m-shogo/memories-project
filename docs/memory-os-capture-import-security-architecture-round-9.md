# Memory OS Capture / Import Security Architecture — Round 9

最終更新: 2026-07-16

## Verdict

```txt
security perfection:
not claimable

security architecture:
defined at contract level

implementation evidence:
not created

penetration / fuzz / mobile verification:
not completed

production implementation:
NO-GO
```

「完璧なセキュリティ」は宣言しない。Memory OSは人生の文脈、画像、DM、視聴履歴、食事、健康や人間関係に関する断片を扱い得るため、設計書が揃ったことを安全性の証明として扱わない。

本書は、Capture / Importを実装する前に固定するP0 security contractである。

---

# 1. Security goals

優先順:

```txt
1. cross-user disclosureを防ぐ
2. confirmed Memoryのsilent write / overwriteを防ぐ
3. malicious importからparser・API・worker・deviceを隔離する
4. raw archiveと一時fileを短命にする
5. retry / crash / deletion後の復活を防ぐ
6. private contentをlog・analytics・notificationへ漏らさない
7. userがPreviewした内容とApply内容を一致させる
8. Capture / Search / ExportをTown rendererから独立させる
```

Securityは便利機能の追加条件であり、後付けのhardening phaseではない。

---

# 2. Assets

最重要asset:

- confirmed Memory records
- raw JSON / CSV / ZIP / image / PDF
- normalized import candidates
- Import Preview
- duplicate decisions
- source account identifiers
- Sign in with Apple account binding
- refresh credential / device secret
- local encryption key material
- pairing session / browser upload token
- signed upload authorization
- export archive
- deletion epoch / account tombstone
- audit and recovery metadata

TownSceneSnapshotはraw Memory bodyを含めないため、上記assetから一段低いprivacy exposureとする。ただしuser identityとのlinkabilityは残る。

---

# 3. Trust boundaries

```txt
untrusted host app / Files provider / browser filesystem
        ↓
iOS Share Extension / iOS fileImporter / Desktop Portal
        ↓
App Group staging or signed quarantine upload
        ↓
quarantine object storage
        ↓
scanner / archive inspector / parser worker sandbox
        ↓
normalized candidate store
        ↓
Import Preview
        ↓
explicit confirmation boundary
        ↓
Memory Domain transaction
        ↓
search / sync / reflection / Town projection
```

信頼境界を跨ぐたびに、identity、ownership、content type、size、revision、hash、stateを再検証する。

Clientで検査済みという理由でserver validationを省略しない。

---

# 4. Authentication and authorization

## 4.1 Sign in with Apple

Serverが検証するもの:

- issuer
- audience / client identifier
- signature and key ID
- expiration
- nonce when used
- authorization code single-use exchange
- account binding state

Clientが送る`userId`をtrustしない。server-side sessionからcanonical user identityを解決する。

## 4.2 Object-level authorization

以下のすべてを、IDを受け取るendpointごとにownership checkする。

- import job
- pairing session
- upload authorization
- quarantine object
- parser attempt
- preview
- preview page / rejected-row report
- confirmation
- export
- staged attachment
- Town layout / revision

```txt
request principal
+ resource.user_id
+ resource.account_epoch
+ resource.current_state
+ requested operation
→ allow / deny
```

`resourceId`が推測困難でもauthorizationの代わりにしない。

PostgreSQLはapplication authorizationに加え、可能なtableではRLSまたは同等のtenant fenceをdefense in depthとして持つ。

## 4.3 Function-level authorization

Browser pairing tokenは次だけを許可する。

- upload slot取得
- assigned objectへのupload
- own pairing import jobの状態取得
- mapping option提出
- preview summary取得
- cancellation

禁止:

- final Apply
- confirmed Memory全文取得
- unrestricted search
- account settings
- export
- pairing session追加発行
- Town operation

---

# 5. Pairing session security

## 5.1 Token properties

- cryptographically random
- minimum 128-bit effective entropy
- short-lived
- one account
- one device-generated session
- one import scope
- maximum file count / total bytes fixed
- use count bounded
- revocable
- account deletion epoch bound
- device unlink invalidates session
- successful terminal state invalidates session

QR payloadへrefresh token、account credential、long-lived API tokenを入れない。

## 5.2 Browser handling

- tokenをthird-party analyticsへ送らない
- URL queryをserver access logへ残さない設計を優先する
- pairing bootstrap後はtokenをmemory-only storageへ移す
- `localStorage`へ保存しない
- persistent IndexedDBへraw archiveやcredentialを保存しない
- browser historyへprivate filenameやtokenを残さない
- page close / expiry / cancellationでmemory stateをclearする

## 5.3 CSRF / XSS / clickjacking

Portal:

- CSPをdefault-denyで設定
- inline script禁止
- third-party scriptを原則置かない
- frame-ancestors 'none'
- MIME sniffing禁止
- Referrer-Policyをno-referrerまたはstrict policyへ固定
- state-changing requestはsame-origin + anti-CSRF strategy
- credentialed CORSをallowlist
- mapping value、filename、warning、preview cellをtextとしてrender
- raw HTMLを表示しない
- MarkdownはP0でrenderせずplain text

Pairing tokenだけでfinal Applyできないため、browser compromise時もconfirmed Memory writeまで到達させない。

---

# 6. Signed upload authorization

Signed URLは単なるbucket write tokenではない。

Serverが固定する:

- generated object key
- owner user ID / account epoch metadata
- import job ID
- expected maximum size
- allowed content type set
- checksum algorithm and expected checksum when available
- expiration
- single upload intent
- encryption policy
- quarantine prefix

Client filenameをobject keyへ使わない。filenameはlength制限・Unicode normalization・control character除去後もuntrusted display metadataとして扱う。

Upload完了後、serverは以下を確認する。

- object exists
- key matches authorization
- object size within approved bound
- checksum matches
- metadata matches import job
- job state is uploadable
- object was not already consumed

Quarantine objectをrenameだけでconfirmed attachmentへ昇格させない。承認後にcopy / re-encrypt / new object identityを作る。

Object storage bucketはpublic accessを禁止し、browserへraw objectのpermanent URLを渡さない。

---

# 7. File and archive security

## 7.1 Allowlist

P0で明示的に許可するformatだけを受け付ける。

```txt
URL / plain text
UTF-8 or detected bounded text
JSON
CSV / TSV
ZIP containing approved data formats
one image / screenshot
Memory OS export package
```

実行可能file、application bundle、installer、script、macro document、disk image、unknown packageを拒否する。

## 7.2 Multi-signal type validation

単一signalをtrustしない。

```txt
extension
+ declared MIME / UTType
+ magic bytes
+ bounded content sniff
+ adapter expectation
```

不一致はrejectまたはmanual-safe pathへ送る。

## 7.3 Archive extraction

必須reject:

- `../` traversal
- absolute path
- Windows drive / UNC path
- encoded traversal
- Unicode separator confusion
- symbolic link
- hard link
- device file
- FIFO / socket
- sparse-file abuse
- nested archive beyond limit
- duplicate normalized path
- case-folding collision
- filename length excess
- entry count excess
- per-entry size excess
- total expanded size excess
- compression ratio excess

Extraction先はjob専用のempty temporary root。pathをnormalizeした後、resolved destinationがroot配下であることを確認してからwriteする。

Archive entryを実行しない。extracted fileへexecute permissionを与えない。

## 7.4 JSON limits

- maximum file bytes
- maximum nesting depth
- maximum token count
- maximum object key length
- maximum string length
- maximum array length
- duplicate-key policy固定
- number precision policy固定
- streaming parse優先
- schema-recursive explosion防止

## 7.5 CSV limits

- maximum rows / columns
- maximum cell bytes
- maximum total decoded bytes
- encoding allowlist / explicit override
- delimiter detection bound
- multiline field bound
- formula-prefix neutralization for downloadable reports
- no spreadsheet execution in parser

## 7.6 Image handling

- decode with bounded dimensions / pixel count
- orientation and metadata parse bound
- strip or separately gate EXIF / precise location
- re-encode thumbnail instead of serving original bytes as preview
- original retention requires explicit user choice

## 7.7 Malware scanning

Scanner / sandbox integrationを可能なinterfaceにする。

P0でscannerが未導入の場合も、format allowlist、parser sandbox、no-execute、network deny、strict limitsを必須とする。scanner導入後も他controlを外さない。

Public third-party scanning APIへprivate archiveを送らない。hash reputation照会もprivacy reviewなしで導入しない。

---

# 8. Parser worker sandbox

Parserはpublic API process内で動かさない。

Worker execution contract:

- non-root user
- read-only root filesystem
- job-specific writable temp directory only
- no host filesystem mount
- no container runtime socket
- no cloud metadata endpoint access
- outbound network deny by default
- object storage readはjob-specific scoped credential
- normalized output writeはlimited API / DB role
- CPU limit
- memory limit
- process count limit
- file descriptor limit
- wall-clock deadline
- extracted byte quota
- output candidate quota
- seccomp / platform sandbox where available
- worker image immutable and signed in release pipeline

Adapterに任意script、template execution、dynamic plugin downloadを許可しない。Adapterはreviewed build artifactとしてdeployする。

Parser crash、timeout、OOMはjob failureとして扱い、API availabilityと他tenant jobへ波及させない。

---

# 9. Preview and Apply integrity

Previewはsecurity boundaryである。

Materialized Previewへ固定する:

- user ID
- account epoch
- job ID
- source object hash
- adapter ID / version
- parser image version
- parsing options hash
- duplicate ruleset version
- candidate-set hash
- preview hash
- expiry

Apply request:

- exact preview ID
- exact preview hash
- idempotency key
- duplicate strategy
- explicit user decisions
- reauthentication marker when required

Apply前にownership、account epoch、job state、expiry、hash、adapter versionを再検証する。

ParserをApply時に再実行して結果をsilent変更しない。

Bulk Applyはlogical atomicityを持つ。chunk処理する場合も、partial successをconfirmed stateとして見せず、resume journalとrollback / compensation contractを持つ。

同じidempotency keyで異なるrequest hashが来た場合はrejectする。

---

# 10. Local iOS and App Group security

AppleのApp Group shared containerはappとextensionの双方がread / write可能であるため、sharedであることを安全と同義にしない。

## 10.1 Data minimization

Share Extensionが保存するもの:

- generated intake ID
- normalized minimal metadata
- staged file reference
- received timestamp
- safe status

保存しないもの:

- refresh token
- full account credential
- raw body in UserDefaults
- Town data
- unrestricted API cache
- AI result

## 10.2 Coordination

- SQLite transaction / WAL policyを明示
- app / extensionのwriter responsibility分離
- schema migrationはmain appのみ
- extensionはsupported schema range外ならsafe failure
- staged fileをwrite完了後atomic rename
- DB rowとfile moveのrecovery journal
- orphan reconciliation on launch
- background URLSession identifierをapp / extensionで分離

## 10.3 Keychain

- secretをUserDefaultsへ保存しない
- Keychain access groupを最小targetだけへ付与
- access control / accessibility classをsecret用途ごとに選ぶ
- device secretとserver refresh credentialを分離
- key rotation / logout / unlink / deletion behaviorを定義
- hardcoded key禁止

## 10.4 Data Protection and backup

- database、staged file、export、cacheへ適切なiOS Data Protection class
- background access要件のないraw intakeはdevice unlock後のみaccess可能を優先
- raw intake、temporary preview、download cacheをbackup対象から除外
- app switcher snapshotへprivate Previewを残さないmaskingを検討
- notification本文へMemory title / filename / source内容を出さない
- keyboard suggestionへsensitive textを学習させない入力設定を高感度fieldで検討

## 10.5 Logging

禁止:

- Memory body
- selected text
- filename全文
- URL query / fragment
- Apple identity token
- refresh token
- pairing token
- signed URL
- object key全文
- rejected CSV row
- image metadata

安全な識別子はserver-generated opaque IDを使用する。

---

# 11. API and backend security

## 11.1 Request controls

- TLS required
- strict JSON content type
- body size limit before decode
- schema validation
- unknown field policy固定
- per-user / per-device / per-IP rate limits
- upload bytes / jobs / candidate count quota
- expensive endpoint concurrency limit
- request timeout
- pagination maximum
- idempotency key validation

## 11.2 BOLA / tenant isolation

すべてのrepository queryはtenant contextを含む。

```txt
bad:
WHERE preview_id = $1

good candidate:
WHERE user_id = $principal
  AND account_epoch = $epoch
  AND preview_id = $1
```

Composite FK / unique constraintでcross-user referenceをDBでも拒否する。

## 11.3 SSRF

URL Capture後のenrichmentはuntrusted URL fetchである。

- scheme allowlist `https` / bounded `http` decision
- localhost / private / link-local / metadata IP拒否
- DNS rebinding対策
- redirect count limit
- redirect先再検証
- response bytes / time limit
- content type allowlist
- no credential forwarding
- isolated fetcher
- parser workerから直接fetch禁止

P0ではURL本文取得を行わず、URLとuser noteだけ保存する選択も許容する。

## 11.4 Database roles

最低限分離:

- API role
- import worker role
- migration role
- read-only operational role
- deletion worker role

Workerへaccount-wide unrestricted read権限を与えない。

---

# 12. Encryption and secrets

## 12.1 In transit

- TLS for all client / API / storage traffic
- iOS App Transport Securityを弱めない
- arbitrary trust-all certificate handler禁止
- signed upload URLもTLS only

Certificate pinningはP0 mandatoryにしない。運用failureとrotation riskを比較し、明示ADRと実機recovery設計なしで導入しない。

## 12.2 At rest

- managed database / volume encryption
- object storage server-side encryption with managed key policy
- quarantine and confirmed objectでkey / prefix / retention policy分離
- backups encrypted
- key access audited
- production keyをsource code / CI logへ置かない

Application-level envelope encryptionやE2EEは、search、multi-device recovery、export、AI processing、account deletionを含む完全protocolなしにclaimしない。

## 12.3 Secrets management

- CI / production secret manager
- least-privilege cloud credentials
- short-lived workload identityを優先
- secret rotation runbook
- repository secret scanning
- test fixtureへreal token / private data禁止

---

# 13. Deletion, retention and resurrection fence

Account deletionはDB row削除だけではない。

削除または無効化対象:

- active sessions
- device registrations
- pairing sessions
- upload authorizations
- pending / retrying jobs
- worker leases
- quarantine objects
- extracted temp objects
- Preview materializations
- rejected-row reports
- confirmed attachments
- search index
- vector index if later adopted
- exports
- local App Group files
- background transfer manifests
- push tokens
- caches / CDN objects
- scheduled notifications

`account_deletion_epoch`または同等のmonotonic fenceをjob、session、upload、worker applyへ伝播する。

Deletion開始前epochのworkerは、完了時に再確認してwriteを拒否する。

Backupについて:

- retention期間を公開contract化
- deletion対象をrestore後に再削除するtombstone / erase ledger
- backupから通常serviceへsilent復活させない
- cryptographic erasureを採用する場合はkey scopeとrestore手順を検証

Raw import fileとPreviewは短いTTLをdefaultとし、confirmed Memoryより先に削除する。

---

# 14. Audit without surveillance

Audit eventへ含めてよいもの:

- opaque user / job / preview ID
- event type
- safe state transition
- adapter ID / version
- count band or bounded count
- error code
- service / build version
- timestamp

含めないもの:

- Memory body / title
- raw URL query
- filename
- CSV row
- person name
- image bytes / EXIF
- selected text

Audit accessはrole制限し、retentionを無制限にしない。

---

# 15. Supply-chain and secure development

必須:

- dependency lockfiles
- automated dependency vulnerability scanning
- SAST
- secret scanning
- license / provenance review
- SBOM generation for release
- container image scanning
- minimal base images
- reproducible or traceable release artifacts
- signed release / provenance where available
- branch protection and review
- production migration review
- security regression fixtures
- fuzzing of archive, JSON, CSV and adapter detection

Generated code / AI-produced patchも通常reviewとtestを迂回しない。

Critical dependency advisory時のpatch SLAとemergency release手順を持つ。

---

# 16. External services and analytics

Import PortalとiOS Captureへthird-party analytics SDKを安易に入れない。

導入条件:

- exact event inventory
- private field denylist
- no content / filename / URL query
- regional and retention review
- opt-out / consent policy
- vendor deletion behavior
- SDK network inspection
- privacy manifest / App Store disclosure consistency

Crash reportもbreadcrumbやattachmentへprivate contentを含めないようscrubする。

AI providerへraw archiveを直接渡さない。AIはnormalized・user-confirmed・必要最小限の入力だけを明示flowで受け取る。

---

# 17. Security implementation stop conditions

以下が一つでも成立する場合、Production implementation authorizationを出さない。

- object IDだけでresourceへaccessできる
- pairing tokenでfinal Applyできる
- signed upload URLが任意object key / unlimited sizeを書ける
- object owner metadataをcompletion時に再検証しない
- parserがpublic API process内で動く
- parserにunrestricted outbound networkがある
- archive path / link / expansion limitsがない
- PreviewとApplyのhash bindingがない
- App Groupへraw tokenをUserDefaults保存する
- main appとextensionがmigration ownershipなしで同じDB schemaを変更する
- private contentがlog / analytics / pushへ入る
- raw archiveにTTL / cleanup evidenceがない
- deletion前workerがaccount削除後にwriteできる
- browserへconfirmed Memory全文をpairing tokenだけで返す
- third-party scannerへprivate fileを無断送信する
- production secretがrepositoryまたはclient bundleへ入る
- security testなしでservice-specific adapterを追加する

---

# 18. Reference baseline

設計・検証時のbaseline:

- Apple App Extension Programming Guide: app / extension container separation、App Groups、shared-container synchronization、background URLSession
- OWASP File Upload Cheat Sheet
- OWASP API Security Top 10
- OWASP MASVS / MASTG for iOS storage、crypto、auth、network、platform、privacy
- NIST SP 800-218 Secure Software Development Framework

これらはチェックリストをコピーするためではなく、Memory OS固有のthreat modelとverification evidenceを補強するために使う。
