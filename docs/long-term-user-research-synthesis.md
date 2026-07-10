# Long-term User Research Synthesis

## 目的

この文書は、Memory OSに近い長期利用アプリについて、公式機能、レビュー記事、公開コミュニティ/SNS上の意見、長期利用者の体験、関連研究を横断し、以下を整理する。

- なぜ長く使われるか
- どこで離脱するか
- どの機能が必要か
- どの機能が不要/危険か
- Memory OSへ何を移植するか

調査時点: 2026-07-10

## 調査対象

### 日記 / ライフログ

- Day One
- Journey
- Daylio
- DailyBean
- 1 Second Everyday
- Apple / GoogleのJournal・Photos Memories系

### コレクション / 趣味ログ

- Letterboxd
- StoryGraph
- Goodreads
- Bookly / Bookmory

### 保存 / 後で読む / 個人情報管理

- Raindrop.io
- Pocket
- Instapaper
- Readwise Reader
- Pinboard

### 習慣化 / ゲーミフィケーション

- Finch
- Habitica
- Streaks系

### 関連研究

- Personal Information Management
- Personal informatics / self-tracking
- digital archiving
- gamification / streaks
- nostalgia / automatic resurfacing
- re-engagement after inactivity

## 調査上の注意

- 公開SNSやコミュニティの意見は、利用者全体を代表しない。
- 強い肯定・強い不満は投稿されやすい。
- 直接Reddit全文を安定取得できなかったため、検索で公開されている議論、SNS利用者を取材した記事、レビュー記事、アプリストア評価の集約、関連研究を組み合わせた。
- 数値よりも、複数媒体で繰り返し出る行動パターンを重視する。

---

# 1. Day One / デジタル日記

## 長く使われる理由

### 入力が軽い

Day Oneは、文章だけでなく写真、位置、日時、天気、運動リンクなどを利用し、日記を書く負担を減らしている。

長期利用者に近いレビューでは、以下が評価されている。

- 検索できる
- 過去の記録を時期/場所で探せる
- 写真や運動記録を一緒に残せる
- 紙より入力が軽い
- privateでsocial feedではない
- Exportできる
- 暗号化や端末同期への信頼

ランニング日記として2年以上使う利用者は、Stravaリンク、地図、装備、補給、過去トレーニングの検索が「記録した後に実用へ戻る」理由になっている。

## 離脱 / 不満要因

### AIが勝手に意味づけする

長年日記を書く人の中には、AIによる感情判定、要約、personalized promptを「自分で考える行為を薄める」「privateな文章へ余計に入ってくる」と感じる層がいる。

重要なのは、AI機能そのものより、以下への拒否感。

- 勝手に感情を採点する
- 自分の文章を要約して解釈する
- 書く前にAIがテーマを決める
- privateな記録が分析対象になる

### subscription / platform依存

長期保存するほど、料金変更、端末制限、サービス継続、Export互換性が気になる。

## Memory OSへの示唆

採用:

- 文章を書かなくても残るmetadata
- 検索、場所、期間、source
- private-first
- Export
- 運動/趣味/店などdomain別の記録

条件付き:

- Promptはユーザーが選ぶ
- AI summaryは明示操作時のみ
- original factとAI interpretationを分離

不採用:

- Import直後の感情分析
- 自動人格分析
- default weekly psychological summary

---

# 2. Daylio / DailyBean / Micro Journal

## 長く使われる理由

- 数タップで記録できる
- 長文不要
- Calendarが埋まる
- icon/色で蓄積が見える
- 月単位の簡単な傾向が見える
- 年齢やIT習熟度を問わず使いやすい

DailyBeanのようなアプリは、simpleなmood icon、activity、短文、写真、calendarで継続障壁を下げている。

## 離脱 / 不満要因

- moodを5段階へ押し込む
- 毎日の入力が義務になる
- streakが切れると戻りにくい
- 数値や色が「今日を評価された」感覚になる
- 長文を残したい人には浅い
- customizationが少ないと飽きる

## Memory OSへの示唆

採用:

- 1件だけ追加
- URLだけ追加
- 進行だけ更新
- calendar / month box
- optional icon

不採用:

- 1日をgood/badで評価
- mood必須
- daily completion percentage
- streak

---

# 3. 1 Second Everyday / Calendar Accumulation

## 長く使われる理由

- 1秒という明確で軽い入力
- Calendarの穴が視覚的に分かる
- 月/年のcompilationが強い報酬
- その日には弱い記録でも、時間が経つと価値が増す
- 完成物が見える

## 離脱 / 不満要因

- 毎日必須に見える
- 穴が罪悪感になる
- 撮るために体験する状態になる
- 日常が記録ノルマ化する

## Memory OSへの示唆

採用:

- Month Capsule / Year Capsule
- 入力後の完成物preview
- 細かい記録がまとまる報酬

不採用:

- 日次穴埋め
- 毎日撮影必須
- 空白をfailure表示

---

# 4. Google Photos / Apple Photos Memories

## 長く使われる理由

- 自分で整理しなくても時期/旅行/場所がまとまる
- 過去を偶然再発見できる
- 写真という強い素材がある
- 検索と自動collectionが便利
- 月/年/旅行単位の振り返りが自然

## 離脱 / 不満要因

自動的なMemoriesは強いが、以下の事故がある。

- 元恋人
- 亡くなった人
- 中止した結婚式
- 病気/事故/喪失
- 見たくない時期

Apple/Google系で「人を減らす」「日付を除外する」「通知を止める」といったcontrolが必要になったのは、automatic resurfacingが便利なだけでなく感情的リスクを持つため。

## Memory OSへの示唆

採用:

- 去年の今ごろ
- 旅行箱
- 月/年の箱
- user-selected safe shelfからのresurfacing

必須control:

- 人/期間/source/shelfを除外
- hidden/sealed/restricted除外
- notifications off
- sensitive source default off
- “今は見せない”
- resurfacing履歴から除外

不採用:

- sensitiveな会話/写真をsurprise表示
- AIが「大切な思い出」を選ぶ

---

# 5. Letterboxd / Movie Logging

## 長く使われる理由

Letterboxdの強さは、映画というdomainへ絞り、以下を一体化したこと。

- 見た日をlog
- diary
- rating/review
- favorites
- watchlist
- list作成
- year review / stats
- 他人のlistから発見
- 映画好きとしての自分が見える

利用者インタビューや記事では、algorithmic infinite feedやDMがない/弱いことも魅力として語られる。

「映画のSNS」ではあるが、中心は会話ではなく映画collection。

## 長期利用の強い特徴

- 見た直後に1アクションでlogできる
- 後から自分の映画史になる
- favorites/listでcuration欲を満たす
- 年間まとめが報酬になる
- 他人のcollectionが次の行動につながる

## 離脱 / 不満要因

- ratingを考えすぎて作品体験に集中できない
- 本数/評価/レビューが競争になる
- 一言review文化が内容を浅くする
- rankingやtop listのルール変更へ強い反発
- domainを広げすぎると既存体験が崩れる不安

## Memory OSへの示唆

採用:

- domain-specific shelf
- favorites
- want-to-watch / watched
- list/curation
- month/year capsule
- cross-source movie link

条件付き:

- ratingは任意
- socialは後回し
- public sharingはsafe shelfだけ

不採用:

- 人生全体rating
- collection数のpublic ranking
- endless social feed

---

# 6. StoryGraph / Goodreads / Book Tracking

## 長く使われる理由

StoryGraphは、GoodreadsよりcleanなUI、reading stats、mood/pace/genre、goal/challenge、wrap-upを評価されている。

特に以下が強い。

- 読書中/読みたい/読了
- page/time progress
- 年間まとめ
- stats
- recommendation
- challenge
- socialが強すぎない

利用者レビューでは、social communityが弱いことを欠点と見る人と、静かなdata-first体験を長所と見る人が分かれる。

## 重要な学び

冊数goalだけだと、短い本を選ぶ、未完了の読書が無価値になるなど、数が目的を置き換える。

StoryGraphがpage/time/open-ended challengeを持つ考え方は、Memory OSにも合う。

## Memory OSへの示唆

採用:

- progress
- status
- page/time/volume/episodeなどdomainに合う単位
- month/year wrap-up
- open-ended collection challenge

不採用:

- 記録件数goal
- 年間何件を必達
- collection completion率で人生を評価

良い課題例:

- 旅行前に店を集める
- 所有している本を棚へ入れる
- 2020年代の映画棚を作る
- 地域別の食の地図を作る

---

# 7. Raindrop.io / Pocket / Readwise / Bookmarking

## 長く使われる理由

- 他アプリから一瞬でsave
- deviceをまたいで使える
- folders/tags/view modes
- search
- full-text archive
- diverse content: article/video/audio/PDF/social post
- Import/Export

Raindropのvisual collectionやMoodboard、Readwise Readerのannotation/search、Pinboardのsimple/private設計など、利用者動機は異なる。

## 最大の問題

保存は簡単だが、再訪しない。

Personal Information Management研究でも、情報をkeepした後に存在自体を忘れ、保存努力が無駄になる問題が指摘されている。

Pocket終了は、長期collectionサービスでportabilityと事業継続が機能価値そのものになることを示した。

## Memory OSへの示唆

採用:

- share extension
- URL one-tap save
- Inbox / 未整理置き場
- full-text search where safe
- Import/Export
- visual collections
- broken-link / source status

必須:

- 保存しただけで終わらないweekly resurfacing
- “先週保存した未処理URL”
- shelfへの自動/半自動分類
- 1件だけ整理

不採用:

- 無制限に貯めるだけ
- AI tag大量生成
- folder整理を最初に要求

---

# 8. Finch / Habitica / Gamified Self-care

## 長く使われる理由

- virtual pet / character growth
- 小さなtaskでもreward
- unlock items/adventures
- self-careを楽しくする
- executive functionが弱い時でも行動の入口になる
- friend encouragement

Finchは、care taskとpet growthを結びつけることで、普通のhabit trackerより情緒的な動機を持つ。

## 離脱 / リスク

- petを放置する罪悪感
- streak維持が目的になる
- rewardのためにtaskを細かく作る
- appとの関係が実生活の目的を上回る
- notificationが叱責に感じられる

Gamification研究では、streak表示が行動を強く変える一方、想定外のsingle-actionや休日行動を誘発し、目的自体を変える可能性が示されている。

## Memory OSへの示唆

採用:

- shelf unlock
- map expansion
- month capsule unlock
- visible before/after
- small action completion

不採用:

- petが弱る
- relationship meter
- daily streak
- missed-day penalty
- emotional notification

---

# 9. 長期利用者に共通する特徴

## A. 入力より後の価値がある

長期利用されるアプリは、入力自体ではなく後から以下が返る。

- search
- timeline
- map
- stats
- progress
- yearly wrap-up
- resurfacing
- collection identity

Memory OSでは、Import後にShelf/Map/Timeline/Progressが必須。

## B. その人の目的が再発すると戻る

activity tracking研究では、長期離脱した人の75%以上が再利用し、再開時は以前の続きというより「新しい利用期」のような動きを見せた。

Memory OSは毎日固定利用より、複数回の利用人生を前提にするべき。

例:

- 旅行前に食の地図へ戻る
- 結婚式前後にLife Event Boxへ戻る
- AI乗り換え時にContext Packへ戻る
- 新しい漫画にハマって進行棚へ戻る
- 年末にYear Capsuleへ戻る

## C. 空白から戻りやすい

長期アプリで重要なのは継続日数ではなく、戻った時の再開負担。

必要:

- welcome backだけで責めない
- 以前の続き候補
- 新しいImportを最初から選べる
- inactive期間を埋めなくてよい

## D. collectionの意味が見える

件数だけでなく、domainの意味が必要。

- 42件のrecord

より、

- 漫画42作品、進行未更新3件
- 食の地図31店、横浜8店
- 映画126本、去年の今ごろ4本

の方が戻る理由になる。

## E. user controlがある

長期でprivate dataを預けるために必要。

- Export
- delete
- hide
- seal
- notification settings
- resurfacing exclusion
- AI analysis off
- source disconnect

---

# 10. 離脱要因の共通パターン

1. 入力が重い
2. 毎日を要求される
3. 数値目標が本来の楽しさを置き換える
4. 保存したものを再利用できない
5. AIが勝手に意味づけする
6. 過去を勝手に表示する
7. social/rankingが中心になる
8. subscriptionが上がるのにExportが弱い
9. service終了/買収への不安
10. collectionが増えすぎて整理不能
11. empty stateのまま価値が出ない
12. 戻った時に未記録期間を責められる

---

# 11. Memory OSへの最重要判断

## 強く採用

- Share extension / one-tap keep
- Importで一気に棚を作る
- domain-specific shelf
- Progress Rail
- Food Map
- Movie/Streaming Timeline
- Weekly Box
- Month/Year Capsule
- Last Year This Week
- Search / re-find
- Export / portability
- source/date/provenance
- resurfacing controls
- long absenceからのeasy restart

## 条件付き採用

- Stats: 事実量のみ
- Challenges: open-ended / user-selected
- Social: safe collection sharingのみ
- Notifications: opt-in / low frequency
- AI reflection: user-requested only
- relationship graph: explainable fact link only

## 不採用

- streak
- daily completion percentage
- AI mood score
- life score
- forced daily log
- surprise sensitive resurfacing
- AI psychological weekly report
- public collection ranking
- infinite social feed
- “最近来ていません” notification

---

# 12. Research References

主要な参照資料:

- Day One Makes Keeping a Journal Delightfully Easy — WIRED, 2016
- Day One brings its digital journaling app to Windows — The Verge, 2025
- AI doesn't belong in journaling — The Verge, 2025
- Marathon training? You should keep a running journal — Tom's Guide, 2026
- I Called Off My Wedding. The Internet Will Never Forget — WIRED, 2021
- The Seductiveness of Insta-Nostalgia — The New Yorker, 2019
- How to Turn Off Memories on iPhone — Lifewire
- Film bro finds and crash out cinema — The Guardian, 2025
- The Fight That Nearly Destroyed the Letterboxd Community — WIRED, 2024
- Four book logging apps to keep you reading — The Verge, 2025
- Last year I read 137 books — The Guardian, 2026
- Pocket alternatives for bookmarking your content — The Verge, 2025
- A fan-favorite app for reading things later is going dark — The Washington Post, 2025
- What's in People's Digital File Collections? — Dinneen & Julien, 2024
- The Long Term Fate of Our Digital Belongings — Marshall, Bly & Brun-Cottan, 2007
- I'll Be Back: On the Multiple Lives of Users of a Mobile Activity Tracking Application — Lin, Althoff & Leskovec, 2018
- How Gamification Affects Software Developers — Moldon, Strohmaier & Wachs, 2020
- Investigating the effects of Goodreads challenges on reading habits — Jafari, Sabri & Bahrak, 2020
- Personal Information Management literature

## 結論

長期利用を作るのは、毎日開かせる圧力ではない。

```txt
軽く入れられる
→ 自分のcollectionになる
→ 後から探せる
→ 時期/場所/進行で再発見できる
→ 空白期間があっても戻れる
```

Memory OSは、このloopを中心にする。
