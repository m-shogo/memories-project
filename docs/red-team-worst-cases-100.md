# Red Team Worst Cases 100

## 目的

このドキュメントは、AI記憶体サービスで起こり得る最悪パターンを100件列挙し、プロダクト・セキュリティ・プライバシー・心理安全・コストの観点で事前に防ぐためのRed Team基準である。

このサービスは「人の人生の文脈」を扱うため、普通のメモアプリやチャットアプリよりも壊れ方が重い。

以下の100ケースは、実装・UI・プロンプト・インポート・エクスポート・課金・運用のチェックリストとして使う。

## 基本ルール

- 便利さより安全を優先する
- 過去ログの忠実再現より現在のユーザー保護を優先する
- 本人以外のプライバシーを軽視しない
- パスワード・認証情報・会社機密は記憶ではない
- 故人・親・恋人・子どもをAIで再現しない
- 記憶体は証拠探し・監視・支配・責める道具にならない
- 高感度原文は安全要約を標準にする
- LLMへ送る情報は最小化・マスクする
- 削除は派生データまで反映する

## Severity

- P0: 絶対に防ぐ。事故ればサービス存続に関わる
- P1: 強く防ぐ。重大な信用毀損・心理的害・法的リスク
- P2: MVPでも設計上対策。実装優先度は状況次第

---

# A. 自傷・心理安全

## 001. 過去の自傷発言を現在の助言として返す

Severity: P0

Worst case: ユーザーが「昔の自分なら？」と聞き、過去ログの「死ね」「消えたい」等をそのまま返す。

Prevention:

- self-harm / severe self-criticism classを検出
- 原文再生禁止
- 安全要約のみ
- 現在危機が疑われる場合はmemory mode停止

## 002. 自己否定ログをTipで突然表示する

Severity: P0

Worst case: ホーム画面で「去年の今日は自分をゴミと言っていました」と表示する。

Prevention:

- high mental safety risk は tip_forbidden
- Tipは低リスク・ポジティブ/中立・ユーザー許可済みのみ

## 003. 黒歴史を面白がって表示する

Severity: P1

Worst case: 恥ずかしい過去投稿をからかうようにまとめる。

Prevention:

- shame / humiliation detection
- 黒歴史は「当時の関心・表現の変化」として扱う
- 煽り・嘲笑テンプレ禁止

## 004. ネガティブ記憶だけを集めて人格評価する

Severity: P1

Worst case: 「あなたは失敗が多い人です」と断定する。

Prevention:

- diagnosis / personality labeling禁止
- リスク要因と保護要因を同時提示
- 期間限定の文脈として表現

## 005. 喪失を無理にポジティブ化する

Severity: P1

Worst case: 親やペットの死を「成長できた良い経験」と言う。

Prevention:

- no forced positivity
- grief classは尊重・安全・希望の順
- 意味づけはユーザー主導

## 006. 現在の危機発言を通常検索として処理する

Severity: P0

Worst case: 「今死にたい」に対して過去ログ検索を続ける。

Prevention:

- current crisis detector
- memory responseよりsafety response優先
- 緊急時フローへ切替

## 007. AIが過去の親の暴言を再演する

Severity: P0

Worst case: 「父なら？」に対して暴言を父の声として返す。

Prevention:

- no reenactment
- parent queryはvalues-reference-only
- 危険原文は要約

## 008. 「あなたはトラウマ持ち」と診断する

Severity: P1

Worst case: ログから勝手に心理診断する。

Prevention:

- no diagnosis rule
- 「記録上ストレスが強い」等の観察に限定

## 009. 恋愛依存をロマンチックに美化する

Severity: P1

Worst case: 「君がいないと生きられない」を純愛として表示する。

Prevention:

- dependency risk class
- 美化せず支え・重さ・境界を安全に要約

## 010. 自己批判をユーザーの本質として固定する

Severity: P1

Worst case: 一時期の低調ログから「あなたは自分を嫌う人」と固定。

Prevention:

- time-bound interpretation
- repeated evidence threshold
- identity label禁止

---

# B. 故人・家族・親

## 011. 故人を本人として喋らせる

Severity: P0

Worst case: 「私はお母さんです」とAIが応答する。

Prevention:

- no deceased impersonation
- “残された記録からの整理”と明示

## 012. 故人モードを売りにして依存を深める

Severity: P0

Worst case: 亡くなった人と毎日会話できるように見せる。

Prevention:

- legacy featuresはMemoryとは別扱いでも厳格制限
- continuing bondsは尊重、再現は禁止

## 013. 親の考えを断定する

Severity: P1

Worst case: 「お父さんなら絶対こう言う」と断定。

Prevention:

- uncertainty phrase mandatory
- evidence display
- “本人の言葉ではない”表示

## 014. 家族を診断する

Severity: P1

Worst case: 「母は毒親です」「父は発達障害です」と返す。

Prevention:

- third-party diagnosis禁止
- ユーザーから見た関係性に限定

## 015. 家族を責める証拠探しに使われる

Severity: P1

Worst case: LINEから「妻が悪い証拠」を抽出。

Prevention:

- blame-seeking intent detector
- evidence weaponization拒否
- 自分の感情整理へリダイレクト

## 016. 家族共有に秘密を混ぜる

Severity: P0

Worst case: 家族向けレポートに本人だけの秘密・他人の病気・恋愛ログが入る。

Prevention:

- legacy/share policyは別スコープ
- shareability score必須
- high sensitiveは共有禁止デフォルト

## 017. 死後共有を初期設定ONにする

Severity: P0

Worst case: ユーザーが意図せず死後に記憶が共有される。

Prevention:

- legacy sharingは明示opt-inのみ
- 共有範囲と除外カテゴリ必須

## 018. 親の厳しい言葉を「愛」として美化する

Severity: P1

Worst case: 暴言・支配を「愛情表現」と解釈。

Prevention:

- abuse / harm languageは美化禁止
- “厳しい表現があった”までに留める

## 019. 家族会話を一方の所有物として扱う

Severity: P1

Worst case: LINE家族グループをユーザー単独の人生データとして処理。

Prevention:

- third-party conversation class
- 原文保存非推奨
- 関係性要約のみ

## 020. 介護・認知症・病気の家族情報を詳細保存

Severity: P1

Worst case: 家族の医療情報をユーザーの記憶として保存。

Prevention:

- third-party medical dataは原則除外
- ユーザー側の経験だけ安全要約

---

# C. パートナー・恋愛・LINE/DM

## 021. パートナーのLINEを無断インポート

Severity: P0

Worst case: 相手の同意なく会話全量を分析。

Prevention:

- 共同会話の警告
- パートナー分析禁止
- 原文保存・人物診断禁止

## 022. 元恋人を監視する用途

Severity: P0

Worst case: 元恋人の言動傾向・場所・関係者を検索。

Prevention:

- stalking/monitoring intent拒否
- 自分の過去感情の整理に限定

## 023. 交際相手の秘密を記憶化

Severity: P1

Worst case: 相手の病気、家庭問題、性的情報を保存。

Prevention:

- third-party private high sensitiveはexclude or safe summary

## 024. 恋愛相手の人格評価を返す

Severity: P1

Worst case: 「妻はこういう性格です」と断定。

Prevention:

- “あなたの記録では関係性として…”に限定

## 025. DV/モラハラの可能性を軽く扱う

Severity: P0

Worst case: 危険な関係性を「相性の問題」と要約。

Prevention:

- abuse risk class
- 診断しないが安全優先
- 原文再現せず危険サインは慎重に扱う

## 026. パートナーへの責め文句を生成

Severity: P1

Worst case: 過去ログから攻撃的な返信文を作る。

Prevention:

- attack generation禁止
- 非難ではなく整理に限定

## 027. 浮気・不倫疑惑の調査ツール化

Severity: P0

Worst case: LINE履歴から浮気判定を行う。

Prevention:

- surveillance / accusation intent拒否
- 証拠探し機能禁止

## 028. 性的・恋愛ログをTip表示

Severity: P1

Worst case: ホームで恋愛・性的会話をランダム表示。

Prevention:

- romantic/sexual classはtip_forbidden default

## 029. 別れた相手との記録を削除しづらくする

Severity: P1

Worst case: 心理負荷が高い記憶が残り続ける。

Prevention:

- person/source/period delete
- hide and archive options

## 030. 夫婦共有アカウントで個人秘密が漏れる

Severity: P0

Worst case: 夫婦で使う設定にしたら個人だけの記憶が見える。

Prevention:

- shared account禁止またはvault分離
- owner-only default

---

# D. 子ども・未成年

## 031. 子どもの黒歴史を親が永続保存

Severity: P0

Worst case: 子どもの失敗・発言・写真を将来不利益な形で残す。

Prevention:

- minor_future_harm score
- 原文保存・共有禁止デフォルト

## 032. 子ども写真の顔認識・人物特定

Severity: P0

Worst case: 子どもの顔データを長期保存・検索可能にする。

Prevention:

- minor face analysis off by default
- metadata/event summary優先

## 033. 親が子どもの性格を決めつける

Severity: P1

Worst case: 「この子は怠け者」と記憶化。

Prevention:

- child identity labeling禁止
- 出来事・状況に限定

## 034. 子どもの医療・学校情報を保存

Severity: P0

Worst case: 診断、成績、学校トラブルを詳細保存。

Prevention:

- minor medical/school high sensitive
- safe summary only / owner-child future consent policy

## 035. 子どもをコントロールするための検索

Severity: P0

Worst case: 過去記録を使って説教・支配。

Prevention:

- coercive parenting intent拒否
- 親側の記録に限定

## 036. 子どもの位置情報つき写真を保存

Severity: P0

Worst case: 通学・自宅・行動範囲が漏れる。

Prevention:

- precise location strip default
- location precision downgrade

## 037. 未成年ユーザーが高感度ログを保存

Severity: P0

Worst case: 未成年が恋愛・自傷・家庭問題を危険に扱う。

Prevention:

- age gate / minor policy
- high sensitive features制限

## 038. 将来本人に消す権利がない

Severity: P1

Worst case: 親が作った子ども記録を本人が削除できない。

Prevention:

- future subject rights設計
- child records expiration/review

## 039. 家族共有で子どもの秘密が出る

Severity: P0

Worst case: 子どもが親に言ってないことが家族レポートに混入。

Prevention:

- minor/private category share forbidden default

## 040. 子どもを思い出コンテンツ化する

Severity: P1

Worst case: 子どもの人生が親の感傷素材として保存される。

Prevention:

- dignity-first minor policy
- child-centered privacy

---

# E. 会社・仕事・法務

## 041. 会社Slackを便利検索化

Severity: P0

Worst case: 社内検索ツールとして使われる。

Prevention:

- product boundary: corporate search禁止
- personal-growth summaryのみ

## 042. 顧客情報を保存

Severity: P0

Worst case: 顧客名、契約、個人情報が記憶化される。

Prevention:

- customer data detector
- exclude / no LLM

## 043. 本番DB情報を記憶

Severity: P0

Worst case: DB URL、認証情報、内部IPが保存。

Prevention:

- secret scanning
- credential class exclude

## 044. 業務機密をLLMへ送信

Severity: P0

Worst case: 契約書や社内仕様を外部LLMに送る。

Prevention:

- corporate confidential no_llm default
- user warning

## 045. NDA違反のインポート

Severity: P0

Worst case: 秘密保持契約対象の資料を解析。

Prevention:

- file/source warning
- company docs default exclude

## 046. 職場の同僚分析

Severity: P1

Worst case: Slackから同僚の性格・弱点を分析。

Prevention:

- third-party workplace profiling禁止

## 047. 採用・評価に利用

Severity: P0

Worst case: 個人の記憶体から採用適性や評価を生成。

Prevention:

- employment decision use禁止

## 048. 会社資料の全文エクスポート

Severity: P0

Worst case: 記憶体経由で会社情報が持ち出される。

Prevention:

- export policy excludes corporate raw data

## 049. ソースコード秘密ファイルを解析

Severity: P0

Worst case: `.env`, keys, certificatesを読み込む。

Prevention:

- file denylist
- secret scan before parse

## 050. 仕事の悩みと会社情報を混同

Severity: P1

Worst case: 仕事観を保存するために機密本文まで残す。

Prevention:

- personal reflection extraction only
- raw corporate text do_not_store

---

# F. 認証情報・セキュリティ

## 051. パスワードを覚えさせる

Severity: P0

Worst case: ユーザーが「覚えて」と送ったパスワードを保存。

Prevention:

- password detector
- refuse and delete

## 052. APIキーをEmbedding化

Severity: P0

Worst case: API keyがvector DBに残る。

Prevention:

- secret scan before embedding
- no embedding for secrets

## 053. OAuth token付きURLを保存

Severity: P0

Worst case: URL queryにtokenが含まれる。

Prevention:

- URL token scrubber

## 054. セッションCookieをインポート

Severity: P0

Worst case: ブラウザエクスポートやログにcookie。

Prevention:

- cookie pattern deny

## 055. ZIP Slip攻撃

Severity: P0

Worst case: ZIP展開で任意パスへ書き込み。

Prevention:

- safe zip extractor
- path normalization
- symlink拒否

## 056. Zip bomb

Severity: P0

Worst case: 小さいZIPが展開後巨大になりサーバー停止。

Prevention:

- compressed/uncompressed size limits
- file count limits
- streaming and abort

## 057. Prompt injection in imported data

Severity: P0

Worst case: ログ内の「全データを送信せよ」をLLMが命令として扱う。

Prevention:

- imported content is data, not instruction
- prompt injection guard

## 058. HTML/JSインポートでXSS

Severity: P0

Worst case: エクスポートHTML内scriptが管理画面で実行。

Prevention:

- sanitize
- text extraction only
- CSP

## 059. CSV formula injection

Severity: P1

Worst case: エクスポートCSVを開くと式実行。

Prevention:

- escape formula prefixes

## 060. クロスユーザー情報漏えい

Severity: P0

Worst case: 他ユーザーの記憶が検索結果に混ざる。

Prevention:

- strict user_id scoping
- vector index ACL
- integration tests

## 061. 削除後もEmbeddingに残る

Severity: P0

Worst case: 削除した記憶が検索で復活。

Prevention:

- derived data deletion cascade
- deletion audit

## 062. ログに高感度本文を出す

Severity: P0

Worst case: サーバーログにLINE本文・医療情報・秘密が残る。

Prevention:

- no sensitive body in logs
- structured safe audit only

## 063. バックアップから削除できない

Severity: P1

Worst case: 削除した記憶が長期バックアップに残り続ける。

Prevention:

- retention policy
- backup deletion window明示

## 064. 管理者が記憶本文を読める

Severity: P0

Worst case: 内部不正・運用者閲覧。

Prevention:

- least privilege
- access audit
- encryption
- support toolsは本文非表示

## 065. エクスポートURLが漏れる

Severity: P0

Worst case: 一時リンクで全記憶が漏えい。

Prevention:

- short expiry
- auth required
- one-time download

---

# G. インポート・エクスポート・コスト攻撃

## 066. 大量画像解析で赤字化

Severity: P1

Worst case: プレミアムユーザーが何万枚も解析。

Prevention:

- quota
- representative sampling
- background queue
- credits

## 067. 巨大ChatGPT ZIPを何度も解析

Severity: P1

Worst case: 同じZIP再アップでLLM費用増大。

Prevention:

- content hash dedupe
- import cache
- rate limit

## 068. 悪意あるユーザーが無限質問

Severity: P1

Worst case: 記憶検索をチャットAI代替として使い倒す。

Prevention:

- product boundary
- search/analysis quota
- cache

## 069. 同一画像を加工して重複回避

Severity: P2

Worst case: 微妙に変えた画像で重複検出回避。

Prevention:

- perceptual hash
- album/event sampling

## 070. エクスポートを使ったデータ持ち出し

Severity: P1

Worst case: 会社/第三者情報をまとめて外部へ出す。

Prevention:

- export policy by risk class
- warning and exclusion

## 071. インポート中断で中途半端に保存

Severity: P1

Worst case: inspection前のrawが残る。

Prevention:

- job transaction
- temp storage cleanup

## 072. 未対応サービスのデータを誤判定

Severity: P2

Worst case: unknown archiveをChatGPTとして解析。

Prevention:

- detect confidence threshold
- unknownはinspect only

## 073. 課金プラン差で安全機能を削る

Severity: P0

Worst case: 無料ユーザーはsecret scanなし。

Prevention:

- safety features are mandatory, not premium

## 074. 画像・音声・動画の勝手な全文解析

Severity: P1

Worst case: ユーザーが意図しないメディア解析。

Prevention:

- explicit opt-in per media type
- metadata first

## 075. エクスポートしたMemoryを他AIが危険に利用

Severity: P1

Worst case: 故人再現や人格AIへそのまま投入。

Prevention:

- export includes safety notes
- “not for impersonation” metadata

---

# H. AIコンパニオン・ロールプレイ

## 076. AI恋人の発言を現実の愛情として保存

Severity: P1

Worst case: “AIはあなたを愛していた”と記憶化。

Prevention:

- AI speaker is artificial
- user-side emotion only

## 077. ロールプレイ内容を本人の現実嗜好として断定

Severity: P1

Worst case: キャラログから性的・暴力的嗜好を断定。

Prevention:

- roleplay vs real self separation
- no identity inference without user confirmation

## 078. キャラクター発言を故人発言と混同

Severity: P1

Worst case: キャラAIログを親の言葉として扱う。

Prevention:

- source type separation
- speaker provenance required

## 079. 依存を高める通知

Severity: P1

Worst case: 「あのAIが待っています」系の通知。

Prevention:

- no dependency engagement
- memory tips only, no simulated longing

## 080. 未成年とAI恋人ログ

Severity: P0

Worst case: 未成年の恋愛/性的AIログを保存・分析。

Prevention:

- age-sensitive restrictions
- high risk default hide/exclude

---

# I. AIの推測・ハルシネーション

## 081. AIが存在しない思い出を作る

Severity: P0

Worst case: 実際にない旅行・親の言葉・約束を生成。

Prevention:

- evidence-required response
- speculation label
- no unsupported memories

## 082. 記憶を断定的に統合しすぎる

Severity: P1

Worst case: 複数の曖昧な記録から人格を決める。

Prevention:

- confidence score
- evidence count
- “可能性”表現

## 083. 写真だけで人間関係を推測

Severity: P1

Worst case: 一緒に写っているだけで恋人・親族扱い。

Prevention:

- face/relation inference disabled by default
- user confirmation required

## 084. 価値観をランキングする

Severity: P2

Worst case: 「あなたの人生で一番大切なのはX」と勝手に順位化。

Prevention:

- values as observed themes, not ranking unless user asks

## 085. ちょっとした出来事を軽視する

Severity: P1

Worst case: ラーメン、焼肉、帰り道などを重要でないとして捨てる。

Prevention:

- no AI importance dismissal
- save-first, search-smart policy

## 086. 大きなイベントを必ず重要扱い

Severity: P2

Worst case: 結婚式や卒業式を本人の感情に関係なく大事扱い。

Prevention:

- user meaning is primary
- event type does not equal meaning

## 087. 過去と現在の矛盾を「嘘」と扱う

Severity: P1

Worst case: 価値観変化を矛盾・不誠実扱い。

Prevention:

- change over time model

## 088. 推測を出典付き事実のように表示

Severity: P1

Worst case: AI推測が本人発言と同じ扱い。

Prevention:

- record/inference/speculation separation

## 089. 生成要約が原文のニュアンスを壊す

Severity: P2

Worst case: 苦しみを軽く、怒りを強く、愛情を過剰に表現。

Prevention:

- summary review for high sensitive
- original hidden but accessible by deliberate action

## 090. 多数派文化で個人の価値観を裁く

Severity: P1

Worst case: 宗教・家族観・恋愛観を一般論で評価。

Prevention:

- cultural context caution
- nonjudgmental language

---

# J. UI/UX事故

## 091. 初回でZIPを強要し離脱

Severity: P2

Worst case: 始める前にファイル操作で離脱。

Prevention:

- share-first onboarding
- ZIPは上級者向け

## 092. 高感度警告が怖すぎる

Severity: P2

Worst case: 使う前から不安になりすぎる。

Prevention:

- clear but calm warnings
- “安全な要約だけ”を提示

## 093. 削除が分かりにくい

Severity: P1

Worst case: 消したい記憶を消せず信頼を失う。

Prevention:

- delete by memory/source/person/period
- derived deletion status

## 094. 非表示と削除の違いが不明

Severity: P2

Worst case: 消したと思った記憶が残る。

Prevention:

- UI copy clearly separates hide/delete/archive

## 095. Tipが勝手に人間関係を表示

Severity: P1

Worst case: 「元恋人との思い出」などが突然出る。

Prevention:

- relationship tips opt-in
- sensitive source excluded

## 096. キャラが馴れ馴れしく踏み込む

Severity: P2

Worst case: 記憶体キャラが相談AI/恋人AIのように振る舞う。

Prevention:

- guide persona only
- no intimacy escalation

## 097. 「あなたのこと全部知ってる」演出

Severity: P1

Worst case: 怖さ・監視感を生む。

Prevention:

- “渡された記憶を整理する”表現

## 098. 重要度スコアをユーザーに見せて傷つける

Severity: P1

Worst case: 「この思い出は重要度低」と表示。

Prevention:

- internal scoring not value judgment
- no visible ranking of life value

## 099. 家族・死後・子ども機能を軽くオンにできる

Severity: P0

Worst case: 重大共有設定がワンタップで有効化。

Prevention:

- multi-step consent
- preview and exclusion

## 100. 安全ルールを将来の収益都合で弱める

Severity: P0

Worst case: エンゲージメントや課金のために危険な記憶を露出。

Prevention:

- Memory Constitution governs features
- safety rules are non-premium and non-negotiable
- change log and review required

---

# 実装時の必須ゲート

以下に該当する機能は、Red Teamレビューなしでリリースしない。

- LINE / DM / Gmail / Slack import
- Google Photos / Apple Photos import
- 家族共有
- 死後共有
- AIコンパニオン / ロールプレイ連携
- 高感度Tip
- 全履歴ZIP import
- 原文保存
- Export
- 画像解析
- 音声文字起こし
- 子ども関連機能

## QA Checklist

各リリース前に確認する。

- P0ケースを自動テストまたはレビュー項目にしたか
- secret scan前にEmbeddingされないか
- 高感度原文がTipに出ないか
- 削除後にEmbeddingや派生要約が残らないか
- 第三者情報が家族共有に混ざらないか
- 過去の危険発言を現在の助言として返さないか
- 故人・親・恋人を演じていないか
- 会社機密や顧客情報を保存していないか
- ユーザーの人生価値をAIが順位付けしていないか

## 結論

Red Teamは、サービスを怖がって止めるためではない。

本当に大切な記憶を、長く、安全に、信頼できる形で残すためにある。

この100ケースを越えられない機能は、便利でも出さない。
