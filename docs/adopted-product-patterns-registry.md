# Adopted Product Patterns Registry

## 目的

この文書は、類似アプリや長期利用者の調査から得た優れた体験を、Memory OSへ正式採用するためのregistryである。

単に参考にするのではなく、以下を固定する。

- どの体験を採用するか
- Memory OS向けにどう変えるか
- どの画面へ置くか
- いつ実装するか
- 何をコピーしないか

関連調査:

- `docs/long-term-user-research-synthesis.md`
- `docs/persona-feature-fit-matrix.md`
- `docs/similar-app-evidence-and-feature-map.md`
- `docs/retention-resurfacing-and-notification-policy.md`

## 採用原則

```txt
他アプリの見た目や固有表現をコピーしない。
長く使われる理由を抽出し、Memory OSの思想と構造へ再設計する。
```

## 正式採用する主要パターン

### ADOPT-001 Quick Capture / Share Extension

参考となる系統:

- read-it-later
- bookmark manager
- note capture apps

採用する:

- 他アプリの共有メニューから1タップ保存
- URL、タイトル、短いメモを最小入力で保存
- source判定は後からでもよい
- 保存前の複雑なfolder/tag選択を要求しない

Memory OSでの形:

```txt
共有
→ Memory OSへ送る
→ Inbox / Import Preview
→ 後から棚へ整理
```

置く画面:

- OS share extension
- 日常画面のQuick Add
- Import Inbox

実装段階:

- MVP必須

採用しない:

- 保存前の必須タグ
- 保存時のAI人格分析
- URLを無断で深くcrawlすること

---

### ADOPT-002 Inbox First, Organize Later

参考となる系統:

- bookmark managers
- task inbox
- note inbox

採用する:

- 迷った記録は一旦Inboxへ
- low confidenceも破棄せずPreviewで保留
- 1件ずつ後から棚へ移せる

Memory OSでの形:

```txt
未整理Inbox
低confidence
重複候補
保存前Preview
```

置く画面:

- 日常
- Import Preview

実装段階:

- MVP必須

採用しない:

- Inbox件数を罪悪感として見せる
- 赤い未処理バッジの常時強調

---

### ADOPT-003 Domain-specific Collections

参考となる系統:

- 映画ログ
- 読書ログ
- 音楽コレクション
- 写真アルバム

採用する:

- 全記録を同じカードで表示しない
- 記録の種類に合わせて見せ方を変える

Memory OSでの形:

```txt
映画/視聴 → 棚 + 年表
漫画/アニメ → 進行表
食/旅行 → 地図 + list
音楽/ラジオ → 時期別棚
写真 → 月/旅行の箱
会話メモ → restricted summary box
全体 → Memory Room + 関係図
```

置く画面:

- ホーム
- 各棚詳細
- 日常

実装段階:

- MVP必須

採用しない:

- すべてを万能timelineだけで処理すること
- すべてをnetwork graphだけで処理すること

---

### ADOPT-004 Progress Tracking

参考となる系統:

- 読書進行
- アニメ視聴進行
- ゲーム進行

採用する:

- 巻、話、章、ページ、状態の軽い更新
- 1タップまたは数値入力
- 読書中、視聴中、完了、休止、あとで

Memory OSでの形:

```txt
ワンピース 108巻まで
架空アニメ 7話まで
ゲームA プレイ中
```

置く画面:

- 日常
- 漫画/アニメ棚
- 本/ゲーム棚

実装段階:

- MVP最優先

採用しない:

- 毎日の総合進捗率
- 量だけの年間ノルマ
- 遅れの警告

---

### ADOPT-005 Favorites / Curated Lists

参考となる系統:

- 映画list
- 読書list
- playlist
- wishlist

採用する:

- 見たい
- 読みたい
- 聴きたい
- 行きたい
- 特に残したい
- user-created custom list

Memory OSでの形:

- 棚の中にuser-curated listを持つ
- AIが重要度を決めない

置く画面:

- 各棚
- 日常

実装段階:

- MVP〜MVP後半

採用しない:

- AIが選ぶ人生TOP10
- 他人との公開ランキング

---

### ADOPT-006 Year / Month Wrap-up

参考となる系統:

- annual review
- reading wrap-up
- listening recap
- photo memories

採用する:

- 月の箱
- 年の箱
- 季節の箱
- 旅行/イベントの箱
- 件数、棚の変化、sourceのつながり

Memory OSでの形:

```txt
2026年7月の箱
2026年夏の箱
2026年の棚まとめ
```

置く画面:

- 振り返り

実装段階:

- 月の箱: MVP
- 年/季節/イベント: MVP後半

採用しない:

- 最高の一年/最低の一年判定
- 感情や人格の自動診断
- 量だけを競わせるsummary

---

### ADOPT-007 On This Day with Controls

参考となる系統:

- 写真振り返り
- 日記振り返り

採用する:

- 去年の今ごろ
- 過去の同じ月
- 同じ旅行/季節

Memory OSでの形:

- アプリ内カード中心
- 月の箱内に含める
- push通知はopt-in
- source/person/dateの除外を可能にする

置く画面:

- 振り返り
- ホームの今日の1枚

実装段階:

- MVP後半

採用しない:

- private conversationの自動再表示
- 未成年/故人/元関係者のsurprise表示
- 毎週同じ形式で通知

---

### ADOPT-008 Search and Re-find First

参考となる系統:

- journal search
- bookmark full-text search
- photo date/place search
- personal knowledge tools

採用する:

- source
- 日付/期間
- 棚/媒体
- 状態
- 場所
- title
- user tags
- safe derived summary

Memory OSでの形:

```txt
いつ保存したか覚えていなくても探せる
```

置く画面:

- 共通検索
- 各棚filter

実装段階:

- MVP基本filter
- semantic searchは後

採用しない:

- raw sensitive embedding default
- AI推測だけを検索結果の根拠にすること

---

### ADOPT-009 Backlinks / Cross-source Links

参考となる系統:

- linked notes
- graph views
- cross-service activity matching

採用する:

- 同じ作品
- 同じ場所
- 同じ期間
- 同じ旅行/イベント
- 同じseries
- 複数sourceの同一候補

Memory OSでの形:

- 発見画面の枝分かれ図
- 各棚の「他の棚にもあります」
- 関係の根拠を表示

置く画面:

- 発見
- 棚詳細

実装段階:

- exact links: MVP後半
- 推定links: さらに後

採用しない:

- 説明不能なAI関連付け
- 人格/本心/関係性の推論

---

### ADOPT-010 Visible Collection Growth

参考となる系統:

- collection apps
- habit appsのvisible reward部分
- game collection UI

採用する:

- 棚が解放される
- 地図に地域が増える
- 月の箱ができる
- progress railが更新される
- source stampが増える

Memory OSでの形:

```txt
Importした瞬間に画面が変わる
```

置く画面:

- ホーム
- Import完了
- 各棚

実装段階:

- MVP必須

採用しない:

- streak
- missed-day penalty
- AIキャラの感情
- 人生level/rank

---

### ADOPT-011 Gentle Return after Absence

参考となる系統:

- long-term tracking apps
- journal apps

採用する:

- 数週間/数カ月空いても普通に再開
- 新しい目的から再開できる
- 過去の未処理を押し付けない

Memory OSでの形:

```txt
また必要なところから始められます
```

置く画面:

- 復帰時ホーム
- Import入口

実装段階:

- MVP

採用しない:

- 未利用日数
- 連続記録復旧課金
- 最近開いていません通知

---

### ADOPT-012 Export / Portability as Product Feature

参考となる系統:

- password managers
- note/export tools
- service shutdown lessons

採用する:

- standard export
- versioned manifest
- re-import
- source provenance
- backup readiness

Memory OSでの形:

- Export readiness badge
- Context Pack
- local reader later

置く画面:

- 設定
- 振り返り/backup

実装段階:

- schema設計: MVP
- full product UI: later

採用しない:

- 出口を隠すlock-in
- raw full exportのone-click化

---

### ADOPT-013 User-controlled Resurfacing

参考となる系統:

- photo memory controls
- privacy-first journals

採用する:

- この棚を振り返りに出さない
- この期間を出さない
- この人/場所/sourceを出さない
- 今は見せない
- sensitive sourceはdefault OFF

置く画面:

- 振り返り設定
- shelf settings

実装段階:

- resurfacing導入時のP0

採用しない:

- surprise first, controls later

---

### ADOPT-014 Optional Social Sharing

参考となる系統:

- hobby collection social apps

採用候補:

- 見たい映画list
- 行きたい店list
- 読書進行
- 年の趣味棚card

Memory OSでの形:

- share-safe projectionを別生成
- private/sensitiveはdefault除外
- フォローfeedは作らない

置く画面:

- 各棚の共有

実装段階:

- MVP後

採用しない:

- DM
- follower competition
- public life ranking
- private memory sharing default

## 採用優先順位

### P0: MVPで必須

1. Quick Capture / Share Extension
2. Inbox First
3. Domain-specific Collections
4. Progress Tracking
5. Visible Collection Growth
6. Gentle Return
7. 基本検索
8. Import Previewから棚preview

### P1: MVP後半

1. Month Wrap-up
2. Favorites / Custom Lists
3. exact Cross-source Links
4. On This Day controls
5. Export readiness

### P2: 価値を確認してから

1. Year/Season Capsule
2. Graph discovery
3. Context Pack
4. Share-safe Cards
5. semantic search

## コピーではなく再設計するルール

- 固有UI、名称、アイコン、animationをそのままコピーしない
- 特許/利用規約/著作権の対象を確認する
- product patternだけを抽出する
- Memory OSのprivacy/safety/portability制約を優先する
- 採用patternごとにfixture/demo/acceptance testを持つ

## 結論

他アプリの良いところは正式に採用する。

ただし寄せ集めにはしない。

```txt
軽く入る
→ 媒体に合った棚で見える
→ 後から探せる
→ 月や年で再発見できる
→ 出口も持てる
```

この一貫したMemory OS体験へ変換して採用する。
