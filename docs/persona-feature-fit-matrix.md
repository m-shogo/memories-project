# Persona Feature Fit Matrix

## 目的

この文書は、Memory OSの利用者を年齢だけで分けず、長く使う動機と嫌う体験で分ける。

同じ人でも、時期によってpersonaが変わる。

- 普段はCollector
- 旅行前はPlanner
- 年末はReflector
- AI乗り換え時はPortability User

したがって、personaは固定属性ではなく利用モードとして扱う。

## Persona一覧

```ts
type MemoryOsPersona =
  | 'collector_curator'
  | 'progress_tracker'
  | 'lightweight_capturer'
  | 'nostalgia_reflector'
  | 'family_event_archivist'
  | 'practical_refinder'
  | 'ai_portability_power_user'
  | 'lapsed_returning_user'
  | 'sensitive_control_first_user'
  | 'social_taste_sharer';
```

---

# P1. Collector / Curator

## 人物像

- 映画、漫画、音楽、店、旅行、写真などを集めるのが好き
- 数よりも「自分の棚」が好き
- Letterboxd、StoryGraph、Raindrop、Pinterest的な体験に惹かれる
- 年齢より趣味密度が重要

## 欲しい機能

- Memory Room
- 棚/箱/地図
- favorites
- custom list
- source stamp
- cross-source link
- Month/Year Capsule
- Empty Shelf preview
- Importで一気に埋まる

## いらない機能

- mood必須
- 人生score
- 公開ranking
- AI人格
- endless social feed

## 戻る頻度

- 週1〜月数回
- 新しい趣味にハマった時は毎日

## 通知

- 月の箱
- Import Preview ready
- 新しいcross-source connection

## 最初の成功体験

```txt
Netflix / Filmarks / 漫画リスト / 食べログURLを入れる
→ 1つの棚または地図が一気に完成
```

## Paid reason

- source数
- storage
- advanced shelf view
- cross-source link
- Export/backup

---

# P2. Progress Tracker

## 人物像

- 漫画、アニメ、本、ゲーム、Podcastなど途中状態を忘れたくない
- 懐古より実用が先
- 数字入力やstatus更新が苦ではない

## 欲しい機能

- Progress Rail
- 何巻/何話/何章/何分
- reading/watching/paused/completed
- quick update
- recently active
- next item
- platform/source別

## いらない機能

- 長文日記
- AI感情分析
- 毎日の総合進捗率
- 作品数goalの強制

## 戻る頻度

- 毎日〜週数回

## 通知

原則不要。

ユーザー設定時のみ:

- 新刊/次回確認
- user-set reminder

## 最初の成功体験

```txt
作品名と「12巻まで」を5〜20件貼る
→ 進行表ができる
```

## Paid reason

- source同期
- more categories
- advanced filters
- backup

---

# P3. Lightweight Capturer

## 人物像

- 面倒なことは続かない
- Journalを始めても文章入力で離脱
- URL、写真、タイトルを残したいだけ
- 共有メニューなら使う

## 欲しい機能

- one-tap share
- Inbox
- URL保存
- auto source detection
- 後で整理
- 1件だけ処理
- voice/short memo optional

## いらない機能

- 最初のfolder選択
- tag必須
- 長いonboarding
- 毎日prompt
- 入力項目が多いform

## 戻る頻度

- 捕捉は随時
- アプリ本体は週1以下

## 通知

- Inboxが一定量たまった時のopt-in digest
- Import Preview ready

## 最初の成功体験

```txt
Safari / X / 食べログ / Spotifyから共有
→ Inboxへ入り、棚previewが出る
```

## Paid reason

- larger Inbox
- auto classify
- full-text search
- archive

---

# P4. Nostalgia Reflector

## 人物像

- 写真、旅行、昔の音楽、過去の時期を見返したい
- Google Photos Memories、Day One On This Day、Timehop系が好き
- 毎日書くより、後で見つかることに価値を感じる

## 欲しい機能

- Last Year This Week
- Month/Year Capsule
- Travel Box
- period timeline
- music/movie/food from the same period
- hide people/dates/sources
- “今は見せない”

## いらない機能

- 1週間前の頻繁な通知
- sensitive surprise
- AIによる重要な思い出選定
- 感情score

## 戻る頻度

- 月1
- 季節/旅行/イベント時

## 通知

- 月の箱: opt-in
- 去年の今ごろ: app内中心

## 最初の成功体験

```txt
視聴/音楽/写真metadataをImport
→ 1年前・数年前の同じ月が見える
```

## Paid reason

- longer history
- more media metadata
- year capsules
- export/print/local archive

---

# P5. Family / Event Archivist

## 人物像

- 結婚、旅行、引っ越し、卒業、家族行事をまとめたい
- 自分だけでなく複数人が関わる
- 写真と予定と店を一緒に見たい

## 欲しい機能

- Life Event Pack
- Travel Box
- safe photo metadata
- calendar/event link
- place map
- selected safe sharing
- public/private separation

## いらない機能

- partner personality analysis
- relationship score
- automatic face hierarchy
- private chat surprise
- family AI simulation

## 戻る頻度

- イベント前後に集中
- 普段は月1以下

## 通知

- user-set event reminder
- Import completion
- shared pack update if opt-in

## 最初の成功体験

```txt
予定 + 店URL + 写真metadata
→ 旅行/イベント箱ができる
```

## Paid reason

- event storage
- encrypted export
- safe share card
- backup

---

# P6. Practical Re-finder

## 人物像

- 過去を眺めたいより「前に保存したあれ」を探したい
- Bookmark、Notion、Raindrop、メール検索を使う
- 整理よりsearch派

## 欲しい機能

- fast search
- source/date/domain filter
- partial context search
- URL archive
- broken-link status
- recent search
- source provenance

## いらない機能

- decorative graph first
- category入力必須
- AIがsearch queryを勝手に拡張
- resultsの感情interpretation

## 戻る頻度

- 必要時

## 通知

ほぼ不要。

- link/archive失効
- Export expiry
- connector error

## 最初の成功体験

```txt
複数sourceをImport
→ 曖昧な言葉で目的の記録を再発見
```

## Paid reason

- full-text search
- archive
- OCR optional later
- source coverage

---

# P7. AI Portability Power User

## 人物像

- ChatGPT / Claude / Geminiなど複数AIを使う
- AIが変わるたびに文脈が消えることへ不満
- Export format、provenance、securityを気にする

## 欲しい機能

- AI Context Pack
- selected shelf export
- fact/user statement/inference separation
- versioned Export
- source provenance
- local backup
- compatibility checker

## いらない機能

- Memory OS内の万能chat
- AI personality clone
- 全履歴を無差別にAIへ送る
- black-box summary

## 戻る頻度

- AI乗り換え
- 月1 maintenance
- project開始時

## 通知

- connector failure
- context pack outdated
- Export package expiry

## 最初の成功体験

```txt
安全な棚を選ぶ
→ 他AIへ渡せるContext Packができる
```

## Paid reason

- larger context pack
- scheduled export
- local archive
- compatibility tools

---

# P8. Lapsed / Returning User

## 人物像

- 何度も記録アプリを始めてやめる
- 数週間〜数カ月空く
- 空白を埋めるよう求められると離脱する
- 新しい目的ができた時だけ戻る

関連研究では、長期離脱後に再利用する人が多く、再開は以前の続きより新しい利用期に近い。

## 欲しい機能

- guilt-free return
- “空白を埋めなくてよい”
- new goal/sourceからrestart
- previous shelf summary
- 1 action only
- inactive period hide

## いらない機能

- streak lost
- missed days
- backlog全部処理
- “最近記録していません”
- daily notification

## 戻る頻度

- 不規則
- 数カ月空いても正常

## 通知

デフォルトOFF。

ユーザーが設定したevent/Exportのみ。

## 最初の成功体験

```txt
久しぶりに開く
→ 責められず、新しいImportまたは1件だけ更新
```

## Paid reason

継続課金より、annual/archive/backup型と相性がよい。

---

# P9. Sensitive Control-first User

## 人物像

- privateな日記/写真/会話を扱う
- 過去の自動表示が怖い
- AI分析を信用しない
- support/admin accessを気にする

## 欲しい機能

- analysis off default
- hide/seal
- source-level exclusion
- person/date/period exclusion
- no surprise resurfacing
- Export review
- clear deletion
- support without raw

## いらない機能

- automatic memories
- weekly emotional summary
- mood score
- AI-only understanding claims
- raw chat import default

## 戻る頻度

- 必要時

## 通知

- security/account/Export only

## 最初の成功体験

```txt
Import Previewで何を保存しないか選べる
```

## Paid reason

- encryption
- sealed archive
- local backup
- longer audit/history

---

# P10. Social Taste Sharer

## 人物像

- 自分の映画/本/店listを人に見せたい
- public SNS全般ではなく、趣味だけ共有したい
- Letterboxd/StoryGraph的なcommunityが好き

## 欲しい機能

- safe share card
- favorites/list
- private/public toggle
- invite-only shared shelf
- shareable Year Capsule

## いらない機能

- DM
- follower growth pressure
- infinite feed
- public ranking
- private shelf accidental share

## 戻る頻度

- 趣味活動後
- 週1程度

## 通知

- invited/shared shelf update only

## 最初の成功体験

```txt
自分の見たい映画listをsafe cardとして共有
```

## Paid reason

- custom share design
- private group
- export/high-res card

---

# Persona × Feature Matrix

| Feature | Collector | Progress | Lightweight | Nostalgia | Family | Re-finder | AI Power | Returning | Sensitive | Social |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Memory Room | ◎ | ○ | △ | ○ | ○ | △ | △ | ○ | ○ | ◎ |
| Progress Rail | ○ | ◎ | ○ | △ | △ | △ | △ | ◎ | ○ | ○ |
| Food Map | ◎ | ○ | ◎ | ○ | ◎ | ○ | △ | ○ | ○ | ◎ |
| Timeline/Capsule | ◎ | ○ | △ | ◎ | ◎ | ○ | ○ | ○ | △ | ◎ |
| Branch Graph | ◎ | △ | × | ◎ | ○ | △ | ◎ | △ | △ | ○ |
| One-tap Share | ◎ | ○ | ◎ | ○ | ○ | ◎ | ◎ | ◎ | ◎ | ○ |
| Search | ○ | ○ | ○ | ◎ | ○ | ◎ | ◎ | ◎ | ◎ | ○ |
| Weekly Box | ◎ | ◎ | ○ | ○ | ○ | △ | △ | ○ | △ | ○ |
| Daily Streak | × | × | × | × | × | × | × | × | × | × |
| AI Auto Summary | △ | × | × | △ | × | △ | △ | × | × | △ |
| Safe Sharing | ○ | ○ | △ | ○ | ◎ | △ | ○ | △ | × | ◎ |
| Export/Backup | ◎ | ○ | ○ | ◎ | ◎ | ◎ | ◎ | ◎ | ◎ | ○ |

Legend:

- ◎: core value
- ○: useful
- △: optional / careful
- ×: generally unnecessary or harmful

---

# Onboarding Branches

最初に年齢を聞くより、目的を選ばせる。

```txt
何を最初に作りたいですか？
```

Options:

- 漫画/アニメの進行棚
- 映画/ドラマ棚
- 食の地図
- 音楽/ラジオ棚
- 旅行/イベント箱
- 写真/昔の記録
- 保存したURLを探せる棚
- AIに渡すContext Pack

この選択でpersonaを仮推定する。

人格診断ではなく、最初の利用モード選択。

---

# 結論

Memory OSのpersonaは、若者/高齢者だけでは足りない。

長期利用を左右するのは、

```txt
集めたい
進行を管理したい
軽く保存したい
過去を見たい
家族イベントを残したい
探し直したい
AIへ持ち出したい
久しぶりに戻りたい
安全を自分で制御したい
趣味だけ共有したい
```

という動機である。

機能は全員へ同じように出さず、最初の目的と利用状況で見せ方を変える。
