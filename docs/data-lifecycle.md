# Data Lifecycle

## 目的

Data Lifecycle は、ユーザーのデータがこのサービス内でどのように受け取られ、変換され、検索され、表示され、削除されるかを定義する。

このサービスでは、削除・非表示・エクスポート・AI送信制御が信頼の中心になる。

そのため、ライフサイクルを後付けにしない。

## 全体フロー

```text
Receive
  -> Inspect
  -> Classify
  -> Scope Selection
  -> Extract
  -> Normalize
  -> Safety Filter
  -> Index
  -> Search
  -> Interpret on Demand
  -> Display
  -> Hide / Archive / Delete / Export
```

## Stage 1: Receive

入力を受け取る。

- Share text
- URL
- Manual paste
- Uploaded ZIP
- Uploaded file
- API import
- Photo metadata

保存するもの:

- ImportJob
- temporary input reference
- userId
- source guess

保存しないもの:

- まだ未検査のrawを永続保存しない

## Stage 2: Inspect

中身を棚卸しする。

- ファイル一覧
- サイズ
- 期間
- データ種別
- 高感度カテゴリ
- 除外予定

この時点でLLMへ送らない。

## Stage 3: Classify

安全・コスト・扱い方を分類する。

- secret scan
- third-party risk
- minor risk
- corporate risk
- medical/mental risk
- self-harm risk
- media type
- source confidence

## Stage 4: Scope Selection

ユーザーに解析範囲を選ばせる。

例:

- 最近100件だけ
- 自分の発言だけ
- DM除外
- 画像本体除外
- 高感度カテゴリ除外
- 原文保存しない

## Stage 5: Extract

RawRecordを作る。

注意:

- RawRecordは最小限
- 高感度rawは短期保持または保持しない
- contentHashを持つ
- sourceRefを持つ

## Stage 6: Normalize

検索可能な形式へ整える。

- 文字コード統一
- 日付正規化
- speaker分離
- URL正規化
- token除去
- 個人情報マスク
- source metadata付与

## Stage 7: Safety Filter

EmbeddingやLLM送信の前に必ず通る。

禁止:

- secretをEmbeddingする
- 会社機密をLLMへ送る
- 他人の秘密を原文保存する
- 高感度原文をTip対象にする

## Stage 8: Index

検索用インデックスを作る。

- full text search
- embedding search
- date index
- source index
- person hint index
- topic hint index

重要:

- indexも削除対象
- indexにsecretを入れない
- vector DBにもuserId scope必須

## Stage 9: Search

ユーザーが質問する。

- query intentを解析
- source/time/safety filterを適用
- related recordsを取得
- 必要に応じてLLMで要約

保存時に人生価値を決めず、検索時に文脈をつなぐ。

## Stage 10: Interpret on Demand

分析は常時生成しない。

ユーザーが求めた時だけ行う。

- 妻ってどんな人？
- 去年の俺ならどう思う？
- この時期何を考えていた？

出力では以下を分ける。

- 記録
- 要約
- 推測
- 不確実性

## Stage 11: Display

表示方針。

- 低リスク: 通常表示
- 関係性: 要約中心
- 高感度: 非表示デフォルト
- 自傷/危機: 原文非表示
- 第三者秘密: 表示禁止または最小化

## Stage 12: Hide / Archive

削除せず隠す。

用途:

- 今は見たくない
- Tipに出したくない
- 検索に出したくない
- 家族共有から外したい

非表示対象:

- Memory
- Interpretation
- Tip
- Search result

## Stage 13: Delete

削除はcascade。

削除対象:

- RawRecord
- NormalizedRecord
- Memory
- Interpretation
- Evidence
- Embedding
- Tip
- Summary cache
- Export cache
- Person inference
- Topic inference

削除ログには本文を残さない。

## Stage 14: Export

エクスポートはユーザー権利。

ただし、第三者秘密・会社機密・認証情報は除外または警告。

出力:

- JSON
- Markdown
- Source references
- Safety notes
- Not for impersonation metadata

## Stage 15: Backup Deletion

バックアップは即時削除できない場合がある。

必要:

- バックアップ保持期間を明示
- 論理削除後は復元不可扱い
- 期限後に物理削除
- ユーザーへ説明

## State Machine

```ts
type DataLifecycleState =
  | 'temporary_received'
  | 'inspected'
  | 'classified'
  | 'scope_selected'
  | 'extracted'
  | 'normalized'
  | 'indexed'
  | 'visible'
  | 'hidden'
  | 'archived'
  | 'exported'
  | 'deletion_requested'
  | 'deleted'
  | 'backup_pending_deletion'
  | 'fully_purged';
```

## Hard Gates

以下を通らないデータは次ステージへ進めない。

- secret scan before embedding
- source detection before extraction
- inspection before LLM
- safety policy before Tip
- user approval before high sensitive save
- deletion cascade before completion

## Audit Events

記録する。

- import received
- inspection completed
- secret detected
- raw excluded
- embedding created
- llm called
- memory created
- memory hidden
- memory exported
- deletion requested
- deletion completed

記録しない。

- 本文
- 原文LINE
- 医療内容
- secret値

## Failure Modes

### Import途中で失敗

- temporary data cleanup
- partial records marked invalid
- user visible error

### Embedding失敗

- search text indexだけで継続
- retry可能

### Deletion失敗

- deletion request stays pending
- userに状態表示
- retry job

### LLM失敗

- 記録保存は継続
- 分析だけ失敗扱い

## 結論

Data Lifecycle は、単なるバックエンド処理順ではない。

ユーザーの人生文脈を安全に預かるための信頼設計である。

特に削除・非表示・AI送信前フィルタ・派生データ削除は、MVPから設計に入れる。
