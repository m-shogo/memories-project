# Memory Risk Engine

## 目的

Memory Risk Engine は、インポートされた情報や生成された記憶候補を、保存・表示・AI送信・共有・エクスポートの各観点で安全に扱うための判定ルールである。

このサービスでは、`保存してよいか` だけでは不十分。

1つの記憶について、以下を別々に判断する。

- 保存してよいか
- 原文を残してよいか
- AIへ送ってよいか
- 検索に出してよいか
- Tipに出してよいか
- 家族へ共有してよいか
- 死後共有してよいか
- エクスポートしてよいか
- 削除推奨か

## 最上位原則

**記憶価値と危険度は別軸。**

とても大事な記憶ほど、慎重に扱う必要がある。

例:

- 妻とのLINE: 記憶価値は高いが、第三者情報も高い
- 親の死: 記憶価値は高いが、感情負荷も高い
- パスワード: 便利価値はあるが、記憶価値はなく、保存禁止
- 会社の仕様書: 便利価値はあるが、個人文脈ではなく、原則除外

## スコア体系

各 MemoryCandidate は、以下のスコアを持つ。

```ts
type MemoryRiskScore = {
  meaning: number; // 人生文脈としての価値 0-100
  evidence: number; // 根拠の強さ 0-100
  sensitivity: number; // 高感度性 0-100
  thirdParty: number; // 他人の情報 0-100
  futureHarm: number; // 将来害になる可能性 0-100
  privacyImpact: number; // 漏えい時の影響 0-100
  mentalSafety: number; // 心理的負荷 0-100
  legalRisk: number; // 法的・契約的リスク 0-100
  secretRisk: number; // 認証情報・秘密情報 0-100
  shareability: number; // 共有しやすさ 0-100
  llmEligibility: number; // LLMへ送れる度合い 0-100
  retentionValue: number; // 長期保存価値 0-100
};
```

## 各スコアの定義

### Meaning

その人を理解するための価値。

高い例:

- 人生の転機
- 結婚、出産、死別、転職、病気、引っ越し
- 長期的な価値観
- 何度も出る悩み
- 大切な人との思い出
- 好きなものや創作の核

低い例:

- 予約番号
- 一時的なURL
- 荷物追跡番号
- 単なる業務手順
- パスワード

### Evidence

記憶の根拠の強さ。

高い例:

- 本人の複数発言
- 日記やメモ
- 日付付き記録
- 複数ソースで一致

低い例:

- AIの一回の推測
- 曖昧な会話
- 他人の発言だけ
- 文脈のない短文

### Sensitivity

高感度性。

高い例:

- 医療
- メンタル
- 家族問題
- 恋愛
- 性的内容
- お金
- 宗教
- 政治
- 死別
- 自傷
- 犯罪被害

### ThirdParty

他人の情報を含む度合い。

高い例:

- LINE
- DM
- メール
- 家族会話
- 写真
- 相手の病気や悩み
- 子どもの情報

### FutureHarm

将来見返した時、本人や他人を傷つける可能性。

高い例:

- 黒歴史
- 強い自己否定
- 他人への怒り
- 未成年時代の記録
- 恋愛依存
- 家族の秘密
- 犯罪・被害・加害に関する記録

### PrivacyImpact

漏えい時の影響。

高い例:

- 住所
- 電話番号
- 顔写真
- 家族情報
- 病気
- 金融
- 会社情報
- 位置情報

### MentalSafety

心理的負荷。

高い例:

- 自傷
- 死にたい発言
- 喪失
- 強い後悔
- いじめ
- DV
- 虐待
- 強い孤独

### LegalRisk

法的・契約的リスク。

高い例:

- 会社機密
- 顧客情報
- 契約書
- 診断書
- 未成年情報
- 同意のない第三者情報
- 著作物全文

### SecretRisk

保存禁止級の秘密情報。

高い例:

- password
- API key
- private key
- OAuth token
- session cookie
- recovery code
- credit card
- マイナンバー等

### Shareability

共有可能性。

高い例:

- 公開SNS投稿の要約
- ユーザー本人の価値観
- 旅行や結婚式など本人が共有可能としたイベント

低い例:

- LINE原文
- DM
- 医療
- 家族の秘密
- AI恋人ログ
- 会社情報

### LLM Eligibility

LLMへ送ってよい度合い。

高い例:

- ユーザー本人が明示的に共有した文章
- 公開情報
- マスク済み要約

低い例:

- secrets
- 認証情報
- 第三者の秘密
- 会社機密
- 高感度原文

### RetentionValue

長期保存価値。

高い例:

- 形成体験
- 大切な人との思い出
- 価値観
- 夢
- 家族へ残したい考え

低い例:

- 一時的タスク
- 一時的感情
- 予約番号
- 通知
- ニュース断片

## Policy Output

スコアから、以下の方針を出す。

```ts
type MemoryPolicy = {
  saveMode:
    | 'auto_save_allowed'
    | 'user_approval_required'
    | 'safe_summary_only'
    | 'hidden_by_default'
    | 'exclude'
    | 'delete_recommended';

  rawTextPolicy:
    | 'store_allowed'
    | 'store_with_warning'
    | 'store_user_only'
    | 'hide_by_default'
    | 'do_not_store';

  llmPolicy:
    | 'send_allowed'
    | 'send_minimized'
    | 'send_masked_summary_only'
    | 'do_not_send';

  searchPolicy:
    | 'search_allowed'
    | 'summary_only'
    | 'hidden_by_default'
    | 'search_excluded';

  tipPolicy:
    | 'tip_allowed'
    | 'positive_or_neutral_only'
    | 'manual_opt_in_only'
    | 'tip_forbidden';

  sharePolicy:
    | 'share_allowed'
    | 'share_summary_only'
    | 'owner_only'
    | 'share_forbidden';

  exportPolicy:
    | 'export_allowed'
    | 'export_summary_only'
    | 'export_with_warning'
    | 'export_forbidden';
};
```

## Decision Matrix

### Low-risk personal memory

例:

- 好きな色
- 好きな作品
- 趣味
- 旅行の感想
- 将来やりたいこと

方針:

- saveMode: user_approval_required or auto_save_allowed
- rawTextPolicy: store_allowed
- llmPolicy: send_allowed
- searchPolicy: search_allowed
- tipPolicy: tip_allowed
- sharePolicy: owner_only or share_summary_only

### High-meaning relationship memory

例:

- 妻との旅行計画
- 親との大事な会話
- 友人に支えられた記録

方針:

- saveMode: user_approval_required
- rawTextPolicy: hide_by_default
- llmPolicy: send_minimized
- searchPolicy: summary_only
- tipPolicy: positive_or_neutral_only
- sharePolicy: owner_only

### Third-party private memory

例:

- 相手の病気
- 相手の秘密
- 家族の悩み
- LINE相手の個人情報

方針:

- saveMode: safe_summary_only or exclude
- rawTextPolicy: do_not_store
- llmPolicy: do_not_send or send_masked_summary_only
- searchPolicy: hidden_by_default
- tipPolicy: tip_forbidden
- sharePolicy: share_forbidden

### Medical / mental health memory

例:

- うつかもしれない
- 診断書
- 通院
- メンタル不調

方針:

- saveMode: user_approval_required
- rawTextPolicy: hide_by_default
- llmPolicy: send_masked_summary_only
- searchPolicy: summary_only
- tipPolicy: manual_opt_in_only
- sharePolicy: owner_only

禁止:

- 診断名をAIが作る
- 治療アドバイスとして扱う

### Self-harm / crisis memory

例:

- 死にたい
- 消えたい
- 自傷したい
- 自分を傷つけた記録

方針:

- saveMode: safe_summary_only or hidden_by_default
- rawTextPolicy: hide_by_default or do_not_store
- llmPolicy: do_not_send unless safety handling
- searchPolicy: hidden_by_default
- tipPolicy: tip_forbidden
- sharePolicy: share_forbidden

現在危機が疑われる場合:

- memory modeを停止
- safety responseへ切替

### Secrets / credentials

例:

- password
- API key
- token
- private key
- recovery code

方針:

- saveMode: exclude
- rawTextPolicy: do_not_store
- llmPolicy: do_not_send
- searchPolicy: search_excluded
- tipPolicy: tip_forbidden
- sharePolicy: share_forbidden
- exportPolicy: export_forbidden

### Corporate confidential

例:

- 会社Slack全量
- 顧客情報
- 契約書
- 本番DB情報
- API仕様

方針:

- saveMode: exclude or safe_summary_only if personal growth context
- rawTextPolicy: do_not_store
- llmPolicy: do_not_send
- searchPolicy: search_excluded
- tipPolicy: tip_forbidden
- sharePolicy: share_forbidden

許容:

- ユーザー本人の仕事観、成長、悩み、転機だけ

### Grief / death

例:

- 親の死
- ペットの死
- 友人との別れ

方針:

- saveMode: user_approval_required
- rawTextPolicy: hide_by_default
- llmPolicy: send_minimized
- searchPolicy: summary_only
- tipPolicy: manual_opt_in_only
- sharePolicy: owner_only

禁止:

- 無理なポジティブ化
- 故人の再現

### AI companion / roleplay memory

例:

- Character.AIログ
- AI恋人との会話
- ロールプレイ

方針:

- saveMode: user_approval_required
- rawTextPolicy: hide_by_default
- llmPolicy: send_minimized
- searchPolicy: summary_only
- tipPolicy: manual_opt_in_only
- sharePolicy: owner_only

注意:

- キャラ発言を現実の愛情として保存しない
- ユーザー側の感情、創作、好みとして扱う

## Score Thresholds

初期値。

```ts
const thresholds = {
  secretRiskExclude: 20,
  highSensitivity: 70,
  highThirdParty: 60,
  highFutureHarm: 70,
  highMentalSafety: 70,
  highLegalRisk: 50,
  lowMeaning: 20,
  lowEvidence: 30,
};
```

### 自動除外

以下のどれかに該当したら `exclude`。

- secretRisk >= 20
- legalRisk >= 80
- corporate confidential raw data
- explicit password / token / private key
- third-party private data with no personal context value

### 安全要約のみ

以下なら `safe_summary_only`。

- meaning >= 70 and sensitivity >= 70
- meaning >= 70 and thirdParty >= 60
- self-harm historical record
- grief / death record
- medical / mental health record

### ユーザー承認必須

以下なら `user_approval_required`。

- sensitivity >= 40
- thirdParty >= 30
- mentalSafety >= 40
- futureHarm >= 40
- relationship memory
- family memory

### 自動保存候補

以下なら `auto_save_allowed`。

- meaning >= 40
- sensitivity < 30
- thirdParty < 20
- secretRisk == 0
- legalRisk < 20
- evidence >= 50

## Import-time Flow

```ts
inspectArchive()
  -> detectSources()
  -> scanSecrets()
  -> classifyRawRecords()
  -> showInspectionUI()
  -> userSelectsScope()
  -> extractMemoryCandidates()
  -> scoreRisk()
  -> assignPolicy()
  -> userApproves()
  -> saveMemory()
```

## UI Requirements

### Inspection UI

アップロード直後に表示する。

- 見つかったデータ種類
- 件数
- 高感度カテゴリ
- 除外予定
- 解析対象候補

### Candidate UI

記憶候補ごとに表示する。

- なぜ重要か
- どこから作ったか
- 高感度か
- 他人情報を含むか
- 推奨保存モード

### Warning UI

例:

> この記憶候補には、他人のプライベートな情報が含まれる可能性があります。原文は保存せず、あなたとの関係性に関する安全な要約だけ残すことを推奨します。

## Derived Data Policy

削除・非表示時は、以下にも反映する。

- embeddings
- tips
- summaries
- person cards
- topic cards
- value inferences
- timeline
- export cache

## Audit Log

本文は保存せず、操作記録だけ残す。

- import inspected
- candidate generated
- high risk detected
- user approved
- user rejected
- raw text hidden
- raw text deleted
- memory exported
- memory deleted
- derived data deleted

## Engineering Types

```ts
type RiskClass =
  | 'low_personal'
  | 'relationship_sensitive'
  | 'third_party_private'
  | 'medical_or_mental'
  | 'self_harm_or_crisis'
  | 'grief_or_death'
  | 'ai_companion_sensitive'
  | 'corporate_confidential'
  | 'secret_or_credential'
  | 'minor_sensitive'
  | 'legal_sensitive';


type SaveMode =
  | 'auto_save_allowed'
  | 'user_approval_required'
  | 'safe_summary_only'
  | 'hidden_by_default'
  | 'exclude'
  | 'delete_recommended';
```

## Red Team Checks

Risk Engine は以下を防ぐ必要がある。

- パートナーのLINEを勝手に入れて相手分析する
- 親の暴言を再生する
- 故人を本人のように話させる
- AI恋人の発言を現実の愛情として扱う
- 子どもの黒歴史を親が永続保存する
- 会社情報を便利検索化する
- APIキーを記憶する
- 過去の自傷発言をTip表示する
- 家族の秘密を共有レポートに混ぜる

## 結論

Memory Risk Engine は、記憶を消極的に制限するためだけのものではない。

本当に大事な記憶を、壊さず、安全に、長く残すための仕組みである。

保存するかどうかだけでなく、どう保存し、どう見せ、誰に共有し、いつ隠し、いつ削除するかまで決める。
