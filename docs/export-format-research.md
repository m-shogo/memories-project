# Export Format Research

## 目的

このサービスは、各サービスのエクスポートデータを安全に読み込み、人生の文脈へ変換する。

そのため、実装前に以下を把握する。

- エクスポートの取得方法
- アーカイブ形式
- 中に含まれる可能性があるデータ
- 最初に読むべきファイル
- 読まない方がよいファイル
- 個人情報・高感度データ
- MVPでの対応優先度

## 共通方針

各サービスのエクスポートZIPは、ユーザーの人生データそのものに近い。

便利に読み込む前に、必ず安全なパーサーを作る。

### 必須ルール

- ZIPをそのまま永続保存しない
- まずmanifest / file listだけ読む
- ファイルサイズ上限を設ける
- 拡張子・MIMEを検証する
- zip slip対策をする
- 巨大ファイルはストリーミング処理する
- 画像・動画・音声は初期MVPで本文解析しない
- DM / メール / 住所録は初期ではデフォルト除外
- Rawデータ保存はオプトイン
- 抽出したMemoryCandidateはユーザー承認を基本にする

## ChatGPT Export

### 取得

OpenAIのPrivacy PortalまたはChatGPT設定からエクスポート可能。

ChatGPT設定からのエクスポートは、Free / Plus / Pro / eligible Edu で利用可能。Business / Enterprise workspace では利用不可の場合がある。

エクスポートは最大7日かかる可能性があり、ダウンロードリンクは受信後24時間で期限切れ。

### 形式

- ZIP
- チャット履歴と関連アカウントデータを含む
- 実装時は `conversations.json` や会話単位JSONの存在を検出する

### MVPで読むもの

- 会話タイトル
- 作成日時 / 更新日時
- メッセージ本文
- 会話量

### MVPで避けるもの

- 添付ファイルの本文解析
- 画像解析
- 全会話の無条件Embedding

### 処理方針

1. ZIPをアップロード
2. ZIP内のファイル一覧を表示
3. ChatGPT形式か検出
4. まず会話メタデータだけ抽出
5. 人生記憶っぽい会話を候補化
6. ユーザーに解析対象を選ばせる
7. 選ばれた会話だけ記憶候補化

### セキュリティ注意

- 会話には非常に高感度な悩み・個人情報が含まれる
- 全文保存は避ける
- Raw保存はユーザー明示許可がある場合のみ

## Claude Export

### 取得

個人のClaudeユーザーは、Free / Pro / Maxのアクティブアカウントでエクスポート可能。

WebアプリまたはClaude Desktopの Settings > Privacy から実行する。

iOS / Androidアプリからはエクスポート不可。

エクスポート完了後、メールでダウンロードリンクが届き、リンクは24時間で期限切れ。

Team / Enterprise はPrimary Ownerのみが組織データのエクスポートへアクセスできる。

### 形式

- ダウンロードアーカイブ
- 会話データとアカウントユーザーデータを含む

### MVPで読むもの

- 会話タイトル
- 作成日時
- メッセージ本文
- プロジェクト/会話単位のメタデータがあれば読む

### MVPで避けるもの

- 添付ファイル全文
- 組織データ
- Team / Enterprise export

### 処理方針

ChatGPTと同じImportAdapterに寄せる。

`ConversationSourceAdapter` として共通化する。

## X / Twitter Archive

### 取得

Xの設定から本人確認後、アーカイブをリクエストできる。

準備完了後、メールまたはアプリ通知で知らせが届き、ZIPファイルとしてダウンロードする。

XはHTMLとJSONの機械可読アーカイブを提供する。

### 含まれる可能性があるもの

公式ヘルプ上、以下が含まれる可能性がある。

- プロフィール情報
- 投稿
- Direct Messages
- Moments
- 投稿/DM/Momentsに添付した画像・動画・GIF
- フォロワー
- フォロー中アカウント
- アドレス帳
- Lists
- 推定された興味・デモグラ情報
- 表示・反応した広告情報

### MVPで読むもの

- 自分の投稿
- 返信
- 投稿日時
- いいね数など公開投稿に近いメタデータ

### MVPで避けるもの

- DM
- アドレス帳
- 添付メディア本体
- 広告ターゲティング情報
- 推定デモグラ情報

### 処理方針

Xは黒歴史・炎上・政治・人間関係が入りやすい。

最初は「公開投稿だけ」を対象にする。

DMは明示的に別スイッチにする。

### 価値

- 昔の価値観
- 趣味の変化
- 投資や開発への興味の始まり
- 特定年の自分の考え
- 人生イベント前後の発言

## Google Takeout

### 取得

Google Takeoutから、Google製品のデータを選択してアーカイブを作成できる。

Google公式ヘルプでは、メール、ドキュメント、カレンダー、写真、YouTube動画、登録・アカウント活動などを例示している。

配信方法として、メールリンク、Google Drive、Dropbox、OneDrive、Boxなどが選べる。

### 形式

- 複数サービスを含むアーカイブ
- サービスごとのフォルダ
- ZIPなど

### MVPで読む優先度

#### Google Photos

初期は画像本体を保存・解析しない。

読む候補:

- ファイル名
- 撮影日時
- アルバム名
- 場所メタデータがある場合
- JSONメタデータ

#### Google Calendar

相性が良い。

読む候補:

- イベント名
- 日時
- 場所
- 説明

旅行・結婚式・予定・記念日を抽出できる。

#### Google Drive / Docs

初期はユーザーが明示的に選んだファイルだけ。

#### Gmail

高感度すぎるためMVPでは非推奨。

航空券・ホテル予約などは将来的には価値が高いが、権限と怖さが大きい。

### MVPで避けるもの

- Gmail全量
- 住所録
- YouTube視聴履歴全量
- 位置履歴全量
- 画像・動画本体の大量解析

## GitHub Export / API

### 方針

GitHubはエクスポートよりAPI連携の方が現実的。

OAuthで以下を読み取る。

- repository
- commits
- pull requests
- issues
- releases

### MVPで読むもの

- public repository metadata
- selected repository only
- commit messages
- PR titles / bodies
- issue titles / bodies

### 避けるもの

- private repository全量の初期取得
- secretsを含む可能性があるファイル本文
- `.env` や設定ファイル

### 価値

エンジニアにとっては、人生の開発履歴になる。

## Notion Export / API

### 方針

NotionはAPIまたはエクスポートで対応可能。

MVPではAPI連携より、共有・貼り付け・ファイルアップロードを優先する。

### 注意

Notionには日記、仕事、顧客情報、個人メモが混ざりやすい。

ページ単位で明示的に選ばせる。

## Import Adapter設計

入力元ごとにAdapterを作る。

```ts
type ImportAdapter = {
  sourceType: SourceType;
  detect(input: UploadedArchive | SharedPayload): Promise<DetectResult>;
  inspect(input: UploadedArchive | SharedPayload): Promise<ImportInspection>;
  extractRecords(input: UploadedArchive | SharedPayload, options: ImportOptions): AsyncIterable<RawRecord>;
};
```

### detect

アーカイブがどのサービス由来か判定する。

### inspect

中身の概要だけ出す。

例:

- ChatGPT会話 1,240件
- X投稿 8,300件
- DM 12,000件（初期除外）
- 写真 42,000枚（本文解析しない）

### extractRecords

ユーザーが許可した範囲だけRawRecord化する。

## Import Inspection UI

アップロード直後に、すぐ解析しない。

まず以下を表示する。

> このアーカイブから見つかったもの
>
> - ChatGPT会話: 1,240件
> - 添付ファイル: 18件（今回は読み込みません）
> - アカウント情報: 1件（保存しません）
>
> 最初は最近100件だけ解析します。

これにより、ユーザーが安心できる。

## 初期対応順

1. Share text
2. Manual paste
3. ChatGPT ZIP inspection
4. ChatGPT selected conversation import
5. Claude ZIP inspection
6. X archive public posts import
7. Google Calendar Takeout import
8. Google Photos metadata import
9. GitHub selected repository API import
10. Notion selected page import

## 結論

あらゆるエクスポートに対応することは現実的。

ただし、最初から全量解析するのではなく、

1. 形式検出
2. 中身の棚卸し
3. 危険データを除外
4. ユーザーに範囲選択
5. 低コストに候補抽出
6. 承認後に保存

という流れを必須にする。
