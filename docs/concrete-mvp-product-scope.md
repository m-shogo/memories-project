# Concrete MVP Product Scope

## 目的

この文書は、Memory OS の最初のMVPに実際に何を入れるかを、画面・機能・保存データ・Import形式・戻る理由まで具体化する。

参考機能一覧ではない。

実装対象を固定する。

## MVP Product Promise

```txt
タイトル、URL、進行、簡単な履歴を入れる
→ 保存前にPreviewできる
→ 自分の棚・地図・進行表として見える
→ 後から検索、更新、Exportできる
```

## MVP Navigation

下部ナビゲーションは4つ。

```txt
ホーム
発見
振り返り
日常
```

ただしMVP初期は、発見の高度な枝分かれ図は実装しない。

発見画面は、確定した関連と最近の追加を一覧表示する簡易版から始める。

---

# 1. ホーム

## 役割

自分の棚が見える場所。

巨大dashboardにはしない。

## 表示するもの

### 1.1 今週の箱

Home最上部に1枚だけ表示。

候補:

```txt
漫画棚で1作品だけ進行を更新できます
未整理のURLが1件あります
食の地図に新しい店が2件追加されました
同じ映画が2つのsourceで見つかりました
```

Rules:

- 1枚だけ。
- sensitive source除外。
- 同じ種類を連続表示しない。
- 該当がなければカード自体を出さない。
- streak、未利用日数、罪悪感copy禁止。

### 1.2 Shelf Grid

MVPで表示する棚:

1. 漫画・アニメ棚
2. 映画・視聴棚
3. 食の地図
4. あとで見る棚
5. 未整理Inbox

P1 placeholder:

- 音楽棚
- ラジオ棚
- 旅行箱
- 写真箱

MVPではplaceholderを大量に並べない。

### 1.3 Shelf Card

各カードに表示:

```ts
interface ShelfCardView {
  shelfType: string;
  title: string;
  itemCount: number;
  recentChange?: string;
  pendingCount?: number;
  emptyStateCopy?: string;
  primaryAction?: string;
}
```

Examples:

```txt
漫画・アニメ棚
12作品
進行更新できる作品 3件
```

```txt
食の地図
横浜 8件 / 川崎 5件
店を1つ追加
```

```txt
未整理Inbox
2件
あとで棚を決められます
```

## Homeでやらないこと

- 人生スコア
- 今日の達成率
- 連続記録日数
- mood判定
- AI personality summary
- 大量の統計
- 枝分かれ関係図

---

# 2. 日常

## 役割

毎日でも使える軽い入力と更新。

毎日使うことは要求しない。

## 2.1 Quick Add

1つの入力欄。

```txt
タイトル、URL、進行、短いメモを貼る
```

Accepted examples:

```txt
SPY×FAMILY 12巻まで
葬送のフリーレン 8話まで
https://tabelog.com/...
PERFECT DAYS 見た
鎌倉のカレー屋 行きたい
```

Buttons:

```txt
貼り付け
ファイルを選ぶ
Previewを見る
```

保存前に必ずImport Previewへ進む。

## 2.2 Progress Quick Update

表示対象:

- 漫画
- アニメ

操作:

```txt
+1巻
+1話
数値を直接変更
完了
保留
```

MVPで保存する値:

```ts
interface ProgressState {
  itemId: string;
  progressUnit: 'volume' | 'episode' | 'chapter';
  currentValue: number;
  totalValue?: number;
  status: 'planned' | 'in_progress' | 'completed' | 'paused';
  updatedAt: string;
}
```

表示しない:

- 全カテゴリ合算進捗率
- 1日目標
- 目標未達

## 2.3 Food Quick Add

入力:

- 店名
- URL
- 地域
- 行きたい / 行った

Optional:

- user note
- favorite

MVPでは同伴者、正確な訪問日時、詳細GPSを必須にしない。

## 2.4 Inbox

Detectorが分類できないもの、ユーザーが後で決めたいものを置く。

Inbox item actions:

```txt
棚へ移す
タイトル修正
source確認
削除
保留
```

一括整理を要求しない。

---

# 3. Import Preview

## 役割

保存前の安全確認と、Import後の見え方を示す。

## 3.1 Preview Header

表示:

```txt
検出した形式
候補件数
保存される棚
source
confidence
warning
```

Example:

```txt
漫画進行として3件見つかりました
保存先: 漫画・アニメ棚
```

## 3.2 Candidate Row

```ts
interface ImportCandidateView {
  id: string;
  selected: boolean;
  title: string;
  medium: string;
  sourceLabel: string;
  sourceDate?: string;
  status?: string;
  progress?: string;
  confidence: 'high' | 'medium' | 'low';
  warnings: string[];
  duplicateCandidate?: boolean;
}
```

Actions:

```txt
保存対象から外す
タイトル修正
棚を変更
進行値を修正
重複候補を見る
```

## 3.3 Save Result

保存成功後:

```txt
漫画・アニメ棚に3件追加しました
```

さらに表示:

```txt
棚を見る
続けて追加
戻る
```

派手なachievementではなく、棚が増えたことを明確に見せる。

---

# 4. 棚詳細

## 4.1 漫画・アニメ棚

Tabs:

```txt
進行中
見たい
完了
保留
```

Row:

```txt
作品名
媒体
現在値 / 合計値
status
source stamp
updated date
```

Actions:

```txt
+1
数値変更
status変更
note
sourceを見る
Export対象確認
```

## 4.2 映画・視聴棚

Tabs:

```txt
見た
見たい
お気に入り
```

Row:

```txt
title
watched date if known
source
status
optional rating
```

MVPではレビュー投稿、social feed、personality analysisを入れない。

## 4.3 食の地図

MVPは地図SDK必須ではない。

最初は地域別list。

```txt
横浜 8件
川崎 5件
東京 12件
```

各店:

```txt
店名
地域
行きたい / 行った
favorite
source URL
user note
```

P1でmap pin表示。

## 4.4 あとで見る棚

共通status:

```txt
見たい
読みたい
聴きたい
行きたい
あとで整理
```

媒体を跨いだ一時collectionとして使う。

---

# 5. 発見

## MVPの役割

枝分かれ図ではなく、説明可能な関連を一覧表示。

## 表示するもの

### 5.1 Recent Additions

```txt
最近追加したもの
```

### 5.2 Confirmed Connections

初期relation:

```txt
同じexternal id
同じnormalized title + year/creator
同じrestaurant name + area
同じsource-native item
```

Card example:

```txt
NetflixとFilmarksが同じ映画棚につながりました
理由: title/year一致
```

### 5.3 Discovery Empty State

```txt
棚が増えると、同じ作品や場所のつながりがここに見えます。
```

## P2

- Memory Constellation
- line thickness
- relation graph
- candidate links

---

# 6. 振り返り

## MVPの役割

月の箱のplaceholderと、月別件数の事実表示。

## 6.1 Month Selector

```txt
2026年7月
2026年6月
```

## 6.2 Month Capsule

表示:

```txt
漫画・アニメ 3件更新
映画 2件追加
食の地図 4件追加
未整理Inbox 1件
```

禁止:

- 最高の月
- 最悪の月
- 幸福度
- 性格変化
- AIによる人生評価

## 6.3 Last Year

P1 feature。

MVPではUI placeholderのみ。

対象:

- manga/anime
- movie
- food
- low-risk manual note

通知は初期OFF。

---

# 7. Search

## MVP検索

文字列一致 + filter。

Filters:

```txt
棚
source
status
期間
地域
```

検索対象:

- title
- restaurant name
- user note
- user tag
- source label

MVPではEmbedding不要。

---

# 8. Export

## MVP Export

形式:

```txt
JSON
CSV where applicable
manifest.json
```

Manifest:

```ts
interface ExportManifest {
  schemaVersion: string;
  exportedAt: string;
  recordCount: number;
  includedShelves: string[];
  excludedCounts: Record<string, number>;
}
```

User can choose:

- shelf
- period
- status

Default exclude:

- hidden
- sealed
- deleted
- restricted raw

---

# 9. Import Forms Included in MVP

## M0 Manual / Paste

1. title-list
2. url-list
3. manga/anime progress text
4. restaurant URL/name list

## M1 File Import

1. Netflix viewing activity CSV
2. generic table-like CSV

M1はM0後に実装。

## M2 Later

- Filmarks paste adapter
- LINE selected snippet
- Spotify / Apple Music
- image metadata
- browser bookmarks

---

# 10. Data Models Required

Minimum:

```txt
user
import_job
import_source
import_preview
import_preview_candidate
shelf
collection_item
progress_state
restaurant_record
source_item
record_relation
user_note
user_tag
export_job
```

Important rule:

```txt
source dataとuser meaningを分離する。
```

Example:

```txt
source_item = Netflix CSV row
collection_item = user's movie shelf record
```

---

# 11. Notification MVP

Default ON:

- Import Preview ready
- Export ready / expiry
- security/account

Default OFF:

- Month Capsule ready
- safe confirmed connection

Not implemented:

- 最近開いていません
- 今週まだ記録していません
- streak reminder
- 1週間前なにしてた通知

---

# 12. Concrete MVP Acceptance Story

## Story A: Manga

```txt
日常で「SPY×FAMILY 12巻まで」を貼る
→ Previewでtitle/volumeを確認
→ 漫画・アニメ棚へ保存
→ Home card countが増える
→ 日常で+1巻更新できる
→ Searchで見つかる
→ Exportに含められる
```

## Story B: Food

```txt
食べログURLを貼る
→ restaurant候補Preview
→ 行きたいとして保存
→ 食の地図の地域listへ追加
→ Homeの件数が増える
→ URL/sourceを確認できる
```

## Story C: Movie

```txt
Netflix CSV fixtureをImport
→ shared profile warning
→ Preview
→ selected rowsを保存
→ 映画・視聴棚ができる
→ 月別件数が振り返りに出る
```

## Story D: Unknown URL

```txt
URLを貼る
→ 分類confidenceが低い
→ Inboxへ保存
→ 後から棚へ移せる
```

---

# 13. MVP Go / No-Go

## Go

- manual/paste
- Preview
- shelf creation
- progress update
- regional food list
- basic search
- JSON/CSV export
- simple weekly card
- month counts

## No-Go

- AI chat home
- auto diary writing
- emotional/personality analysis
- daily streak
- social feed
- DM
- recommendation engine
- full graph
- automatic LINE bulk import
- face recognition
- location history import
- API connector first

---

# 結論

最初に作るのは、巨大なMemory OSではない。

```txt
軽く入れる
→ Previewする
→ 棚として見える
→ 少し更新できる
→ 探せる
→ 持ち出せる
```

この一連が、漫画・食・映画・URLで動くMVPを作る。
