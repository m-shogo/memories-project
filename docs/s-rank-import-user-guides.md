# S Rank Import User Guides

## 目的

この文書は、Memory OS のSランクImportについて、サービスごとにユーザーが実際に行える取り込み方法を具体化する。

対象:

- Apple Music
- Spotify
- Twitter / X
- Netflix
- Amazon Prime Video
- Disney+
- U-NEXT
- LINE
- 食べログ
- RADIO / radiko系
- GERA
- Podcast
- Filmarks
- 漫画
- 映画
- ラジオ
- アニメ
- これまで候補に入れた主要Import

前提:

- 1サービスにつき複数の取り込みルートを許可する。
- APIがない/弱いサービスでも、コピペ・URL・公式Export・手入力を正式ルートにする。
- 「APIがないので非対応」ではなく、「安全に取れる入口」を探す。
- login scraping は禁止。
- 取り込む前にImport Previewを必ず表示する。
- private/sensitive候補は既定でAI分析・Tip・Exportから除外する。

## 共通Importルート

### Route A: API接続

使う場面:

- 公式APIがある。
- OAuthまたはAPI keyが正規に取得できる。
- read-only scopeで足りる。
- 利用規約上、個人のImport用途に問題がない。

基本手順:

1. サービスのDeveloper Consoleでアプリを作る。
2. Redirect URIを設定する。
3. 必要最小限のread-only scopeを選ぶ。
4. OAuthでユーザーに接続許可をもらう。
5. tokenを暗号化して保存する。
6. Import Previewで件数・範囲・private候補を表示する。
7. ユーザーが確認した範囲だけMemoryにする。

禁止:

- 書き込みscopeをMVPで要求する。
- DM/個人チャット/第三者情報を広く取る。
- APIで取れるものをそのままAI分析に送る。

### Route B: 公式Export / CSV / Takeout

使う場面:

- 公式APIが弱い。
- ユーザーが公式画面からExportできる。
- CSV/JSON/ZIP/HTMLなどのファイルを取得できる。

基本手順:

1. ユーザーがサービス公式画面からExportを作る。
2. ZIP/CSV/JSON/HTMLをMemory OSにアップロードする。
3. まずmanifestを読む。
4. サポート対象ファイルだけ抽出する。
5. active contentを実行しない。
6. Import Previewを出す。
7. private/sensitive候補を既定で除外またはowner_sensitiveにする。

### Route C: 履歴画面・一覧画面からコピー貼り付け

使う場面:

- APIがない。
- 公式Exportがない/面倒。
- 履歴画面や一覧画面からテキストとしてコピーできる。

基本手順:

1. サービスの履歴/一覧/マイリスト画面を開く。
2. 画面内のタイトル一覧を選択してコピーする。
3. Memory OSのUniversal Paste Importへ貼り付ける。
4. サービス名を選ぶ。
5. Parserがtitle/date/status/episode/urlらしきものを抽出する。
6. ユーザーが修正する。
7. Import Previewで確認する。

対応すべき貼り付け例:

```txt
2026/07/01 作品名
作品名 シーズン1 エピソード3
店名 2026年7月 横浜
番組名 #123 タイトル
漫画タイトル 12巻まで
```

### Route D: URL Clip

使う場面:

- 作品/店/番組/投稿/レシピなどにURLがある。
- 一覧ではなく、1件ずつ残したい。

基本手順:

1. 対象ページURLをコピーする。
2. Memory OSのURL Clipへ貼る。
3. サービス判定をする。
4. title/url/domainだけ保存する。
5. 必要ならcatalog APIで補完する。
6. 本文やページ全体は自動取得しない。

### Route E: Manual Entry

使う場面:

- APIもExportもコピーも弱い。
- 今見ている/聴いている/読んでいる状態を手早く残したい。

基本項目:

- domain
- title
- status
- progress
- date
- source label
- memo

## S Rank Services

## Apple Music

### Method 1: Apple Music / MusicKit API

用途:

- library
- playlists
- catalog metadata
- current/favorite music if supported by scope

実装者側の手順:

1. Apple Developer Programを確認する。
2. MusicKit / Apple Music APIの利用条件を確認する。
3. Developer Tokenを発行する設計にする。
4. Music user tokenをユーザー認可で取得する。
5. read-only相当の用途に限定する。
6. playlist/library/catalog metadataをImport Previewへ出す。

注意:

- 「完全な再生履歴が取れる」と約束しない。
- Appleの取得可能範囲はOS・API・権限で変わる前提にする。
- 最初はresearch spike扱い。

### Method 2: Apple Data & Privacy export

ユーザー手順:

1. AppleのData & Privacyページへ行く。
2. Apple Accountでサインインする。
3. “Request a copy of your data” を選ぶ。
4. Apple Media Services / Apple Music / purchase/download関連を選べる場合は選ぶ。
5. 準備完了後、ファイルをダウンロードする。
6. Memory OSにアップロードする。

取り込める可能性:

- purchased/downloaded media records
- Apple MusicやMedia Services関連のusage情報
- store browsing/purchase context

注意:

- Appleは購入済みコンテンツ本体ではなく、購入/ダウンロード項目リストを提供する方針。
- データ範囲は国・地域・時期で変わる。

### Method 3: Playlist/library copy-paste

ユーザー手順:

1. Apple MusicでPlaylistまたはLibraryを開く。
2. 曲一覧を表示する。
3. 可能なら選択してコピーする。
4. Memory OSに貼り付ける。
5. `Apple Music` をsourceとして選ぶ。
6. title / artist / album / order を確認する。

Fallback:

- スクショからの手入力補助。
- 「今聴いている曲」だけ手入力。
- Last.fm scrobbleを併用。

## Spotify

### Method 1: Spotify Web API

実装者側の手順:

1. Spotify Developer Dashboardにログインする。
2. Appを作成する。
3. Web APIを選ぶ。
4. Redirect URIを登録する。
5. Authorization Code + PKCEを使う。
6. 必要最小scopeだけ要求する。

候補scope:

- `user-read-recently-played`
- `user-library-read`
- `playlist-read-private`
- `playlist-read-collaborative`
- `user-top-read`
- `user-read-currently-playing`

Import候補:

- recently played
- saved tracks
- saved albums
- playlists
- top tracks/artists
- currently playing
- saved shows/episodes

注意:

- read-onlyにする。
- playback controlはMVP不要。
- explicit flag等はprivate扱い。

### Method 2: Playlist/album/track URL paste

ユーザー手順:

1. Spotifyで曲/アルバム/プレイリストを開く。
2. ShareからURLをコピーする。
3. Memory OSのURL Clipに貼る。
4. Spotify URLとして解析する。
5. APIまたはmetadata lookupでtitle/artistを補完する。

### Method 3: 画面コピー貼り付け

ユーザー手順:

1. PlaylistまたはLiked Songsの一覧を開く。
2. 表示されている曲一覧をコピーする。
3. Universal Paste Importに貼る。
4. 曲名/アーティスト/アルバムらしき列を確認する。

## Twitter / X

### Method 1: X archive ZIP

ユーザー手順:

1. Xを開く。
2. Settings and privacyへ行く。
3. Your accountを開く。
4. Download an archive of your dataを選ぶ。
5. パスワード/認証を完了する。
6. 準備完了後、ZIPをダウンロードする。
7. Memory OSにZIPをアップロードする。

Import候補:

- own posts
- retweets/reposts
- likes/bookmarks if included and user selects
- media references
- account metadata

注意:

- likes/bookmarksはowner_sensitive default。
- DMsは取り込まない、または別docのLINE/DMルール同様にsummary-only default。
- 他人への監視用途は禁止。

### Method 2: Post/thread URL clip

ユーザー手順:

1. 残したいpost/threadのURLをコピーする。
2. Memory OSに貼る。
3. 自分の投稿か、他人の投稿かを選ぶ。
4. 他人の投稿はpublic referenceとして保存し、人格分析しない。

### Method 3: Post text copy-paste

ユーザー手順:

1. post/threadの本文をコピーする。
2. Memory OSに貼る。
3. sourceを`X copied post`にする。
4. URLがあれば一緒に貼る。

## Netflix

### Method 1: Viewing Activity CSV

ユーザー手順:

1. WebブラウザでNetflix Account pageを開く。
2. Profilesから対象profileを選ぶ。
3. Viewing activityを開く。
4. 必要ならShow Moreで一覧を広げる。
5. ページ下部のDownload allを押す。
6. CSVをMemory OSにアップロードする。

Import候補:

- watched title
- watched date
- profile name if user confirms

注意:

- family/shared profileに注意。
- AI分析off default。
- 同居人や家族の視聴履歴を混ぜない。

### Method 2: Viewing Activity画面コピー貼り付け

ユーザー手順:

1. Viewing activity画面を開く。
2. 表示されている範囲をコピーする。
3. Memory OSに貼り付ける。
4. title/dateを確認する。

### Method 3: 今見ているもの手入力

ユーザー手順:

1. Netflixで見ている作品名を開く。
2. title、season、episode、statusをMemory OSに入れる。
3. statusは`watching`にする。

## Amazon Prime Video

### Method 1: 視聴履歴画面コピー貼り付け

ユーザー手順:

1. Prime Videoをブラウザで開く。
2. Account & Settings周辺のWatch history / 視聴履歴相当を探す。
3. 表示されている作品一覧をコピーする。
4. Memory OSに貼る。
5. title/date/statusを確認する。

注意:

- 公式CSVが確認できない場合はcopy-pasteを正式ルートにする。
- profile/shared accountに注意。

### Method 2: 購入/レンタルメール取り込み

ユーザー手順:

1. Amazonからの購入/レンタル/注文確認メールを探す。
2. メール本文をMemory OSに貼る、または転送する。
3. title/date/order sourceを抽出する。

### Method 3: 手入力/URL Clip

ユーザー手順:

1. 作品ページURLをコピーする。
2. Memory OSに貼る。
3. `watching / watched / want_to_watch` を選ぶ。

## Disney+

### Method 1: Watchlist / Continue Watching画面コピー貼り付け

ユーザー手順:

1. Disney+でWatchlistまたはContinue Watchingを開く。
2. 作品一覧をコピーする。
3. Memory OSに貼る。
4. title/status/progressを確認する。

### Method 2: データExport / privacy request

ユーザー手順:

1. Disney+またはDisney accountのprivacy/data request画面を探す。
2. 自分のデータのコピーを請求できる場合は請求する。
3. 受け取ったファイルをMemory OSにアップロードする。

注意:

- 国・地域・契約形態で手順が変わる可能性がある。
- まずはcopy-paste/manualを実用ルートにする。

### Method 3: 手入力

- title
- season
- episode
- status
- memo

## U-NEXT

### Method 1: 視聴履歴/マイリストコピー貼り付け

ユーザー手順:

1. U-NEXTで視聴履歴、購入済み、マイリストを開く。
2. 画面上のタイトル一覧をコピーする。
3. Memory OSに貼る。
4. title/status/dateを確認する。

### Method 2: 購入/レンタルメール

ユーザー手順:

1. 購入/レンタル/ポイント利用メールを探す。
2. Memory OSに貼る、または転送する。
3. 作品名/date/sourceを抽出する。

### Method 3: 手入力

- title
- episode
- watching/completed
- memo

## LINE

### Method 1: Chat text export

ユーザー手順:

1. LINEで対象トークを開く。
2. トーク設定を開く。
3. トーク履歴の送信/保存/Export相当を選ぶ。
4. text形式で保存できる場合は保存する。
5. Memory OSにアップロードする。

Memory OS側:

- raw default off。
- third-party rawは保存しない。
- safe summary default。
- source/date/speaker方向だけを確認する。

### Method 2: 選択コピー貼り付け

ユーザー手順:

1. 残したい部分だけコピーする。
2. Memory OSに貼る。
3. `rawを残す / 要約のみ / 日付だけ` を選ぶ。
4. 相手の本心分析はしない。

### Method 3: 手動Memory化

ユーザー手順:

1. LINEの会話を見ながら、残したい出来事だけ自分の言葉でメモする。
2. 相手の原文ではなく、自分の記憶として保存する。

禁止:

- LINE Messaging APIで個人チャット履歴が読めるように扱うこと。
- 相手の嘘・本心・証拠探し。
- bulk raw import default。

## 食べログ

### Method 1: 店舗URL Clip

ユーザー手順:

1. 食べログで店舗ページを開く。
2. URLをコピーする。
3. Memory OSに貼る。
4. 店名/エリア/ジャンル/source URLを保存する。
5. 行った日、誰と行ったか、感想はユーザーが任意で追加する。

### Method 2: 行った店/保存リストコピー貼り付け

ユーザー手順:

1. 食べログの保存リスト/行った店相当の一覧を開く。
2. 表示されている店名一覧をコピーする。
3. Memory OSに貼る。
4. 店名/エリア/メモを確認する。

### Method 3: 予約/確認メール取り込み

ユーザー手順:

1. 予約確認メールをMemory OSに貼る、または転送する。
2. 店名/日付/人数/予約者情報を抽出する。
3. 人数や同行者はprivate default。

注意:

- 位置/同行者はsensitive。
- 誰とよく行くかをAIが勝手に推測しない。

## RADIO / radiko系

### Method 1: 番組URL Clip

ユーザー手順:

1. 聴いた番組のページURLをコピーする。
2. Memory OSに貼る。
3. 番組名/放送日/局/出演者を手動またはmetadataで補完する。

### Method 2: 聴取履歴画面コピー貼り付け

ユーザー手順:

1. アプリ内の履歴/お気に入り/マイリストを開く。
2. 番組一覧をコピーできる場合はコピーする。
3. Memory OSに貼る。

### Method 3: 手入力

- station
- program
- episode/date
- listened_at
- memo

## GERA

### Method 1: Episode URL Clip

ユーザー手順:

1. GERAで番組/エピソードを開く。
2. URLをコピーする。
3. Memory OSに貼る。
4. 番組名/エピソード名/公開日/URLを保存する。

### Method 2: 履歴/お気に入り一覧コピー貼り付け

ユーザー手順:

1. GERAアプリ/サイトで履歴やお気に入りが見られる場合、その一覧をコピーする。
2. Memory OSに貼る。
3. title/program/dateを確認する。

### Method 3: 手入力

- program
- episode
- status: listened / want_to_listen
- memo

注意:

- APIが確認できるまでAPI前提にしない。
- URL/copy/manualを正式ルートにする。

## Podcast

### Method 1: OPML import

ユーザー手順:

1. PodcastアプリでOPML exportを探す。
2. 購読一覧をOPMLで保存する。
3. Memory OSにアップロードする。

Import候補:

- show title
- RSS feed URL
- folder/category if present

### Method 2: RSS URL Clip

ユーザー手順:

1. 番組のRSS URLまたは番組ページURLをコピーする。
2. Memory OSに貼る。
3. 番組名/episode listを取得する。
4. 聴いたepisodeは手動で選ぶ。

### Method 3: episode URL / list paste

ユーザー手順:

1. 聴いたepisodeのURLまたはタイトルをコピーする。
2. Memory OSに貼る。
3. listened / want_to_listenを選ぶ。

## Filmarks

### Method 1: 見た映画リストコピー貼り付け

ユーザー手順:

1. Filmarksの自分の見た映画/レビュー/クリップ一覧を開く。
2. 表示されているタイトル一覧をコピーする。
3. Memory OSに貼る。
4. title/rating/date/reviewらしきものを確認する。
5. TMDbで作品情報を補完する。

### Method 2: 作品URL Clip

ユーザー手順:

1. Filmarksの作品ページURLをコピーする。
2. Memory OSに貼る。
3. watched / want_to_watch / memoを選ぶ。

### Method 3: 手入力

- title
- watched date
- rating
- memo

注意:

- Filmarks API前提にしない。
- profile scrapingはしない。

## 漫画

### Method 1: 今読んでいる漫画手入力

項目:

- title
- current volume/chapter
- status: reading / completed / paused / want_to_read
- memo

### Method 2: 漫画アプリ一覧コピー貼り付け

ユーザー手順:

1. 漫画アプリの本棚/購入済み/お気に入りを開く。
2. タイトル一覧をコピーできる場合はコピーする。
3. Memory OSに貼る。
4. title/volume/statusを確認する。

### Method 3: 購入メール取り込み

対象:

- BookWalker
- ebookjapan
- Kindle
- コミックシーモア
- その他購入/予約メール

手順:

1. 購入メールを貼る/転送する。
2. title/volume/date/storeを抽出する。

禁止:

- app login scraping。
- 作品本文/ページ画像の取り込み。
- 非公式コンテンツの本文Import。

## アニメ

### Method 1: AniList API

実装者側:

1. AniList OAuthを確認する。
2. GraphQL queryでMediaListを取得する。
3. status/progress/scoreを取得する。
4. Import Previewで確認する。

Import候補:

- watching
- completed
- paused
- dropped
- planning
- progress episode
- score

### Method 2: 視聴中リストコピー貼り付け

ユーザー手順:

1. 配信アプリやメモの視聴リストをコピーする。
2. Memory OSに貼る。
3. title/episode/statusを確認する。

### Method 3: 手入力

- title
- episode
- season
- status
- memo

## 映画

### Method 1: Letterboxd CSV/RSS

ユーザー手順:

1. LetterboxdのExport/Import関連ページからCSVを取得できる場合は取得する。
2. RSS feedが必要なら自分のdiary/review/list feedを使う。
3. Memory OSにアップロード/登録する。

Import候補:

- watched films
- diary entries
- rating
- tags
- review
- watchlist

### Method 2: Filmarks / streaming service copy-paste

- Filmarks list paste
- Netflix CSV
- Prime/Disney+/U-NEXT list paste
- cinema ticket/reservation email

### Method 3: Manual movie memory

- title
- watched date
- theater/home
- who with optional
- memo

## これまでの主要Import候補

## Last.fm

### Method 1: API

実装者側:

1. Last.fm API accountを作る。
2. API keyを取得する。
3. user.getRecentTracks / user.getLovedTracks / user.getTopArtists / user.getTopAlbums / user.getTopTracksを使う。
4. Import Previewで期間と件数を確認する。

### Method 2: username manual link

ユーザー手順:

1. Last.fm usernameを入力する。
2. public profileから取れる範囲だけ取り込む。
3. privateデータはAPI/OAuthが必要な場合だけ扱う。

## Google Takeout / YouTube

### Method 1: Takeout archive

ユーザー手順:

1. Google Takeoutを開く。
2. YouTube / YouTube Musicを選ぶ。
3. 必要なデータだけ選ぶ。
4. Exportを作成する。
5. ZIPをダウンロードする。
6. Memory OSにアップロードする。

Import候補:

- watch history
- search history only if explicitly selected
- liked videos
- playlists
- subscriptions

注意:

- search historyはprivate/sensitive default。
- AI分析off default。

### Method 2: YouTube URL Clip

- watched video URL
- playlist URL
- channel URL

## Browser Bookmarks

### Method 1: HTML bookmark export

ユーザー手順:

1. Chrome / Safari / FirefoxでBookmark exportを行う。
2. HTMLまたはJSONをMemory OSにアップロードする。
3. folder単位で import / sensitive / skip を選ぶ。

Security:

- raw HTMLはDOM描画しない。
- active contentは実行しない。
- private folderはowner_sensitive default。

### Method 2: URL list paste

- 複数URLを改行区切りで貼る。
- domain/titleを抽出する。

## Google Books / Open Library / NDL / Calil

### Method 1: catalog enrichment

使い方:

- manual book title
- ISBN
- purchase/loan memo
- CSV本棚

を受け取り、以下で補完する。

- Google Books
- Open Library
- NDL Search
- Calil

Import候補:

- title
- author
- ISBN
- publisher
- publication date
- cover URL
- library availability

注意:

- Calilは蔵書/貸出可否であり、本人の貸出履歴ではない。
- 図書館履歴はmanual/file-onlyでrestricted寄り。

## Goodreads / StoryGraph / 読書メーター / ブクログ

### Method 1: CSV export if available

- CSVをアップロードする。
- title/author/rating/read date/statusを確認する。

### Method 2: list copy-paste

- 本棚一覧をコピーする。
- Memory OSに貼る。

### Method 3: manual reading log

- title
- author
- status
- page/progress
- memo

## Steam / Games

### Method 1: Steam API

実装者側:

1. Steam API key / user profile visibilityを確認する。
2. owned games / recently played / playtimeを取得する。
3. Import Previewで確認する。

### Method 2: profile/library copy-paste

- library list
- played recently list
- manual current playing

### Method 3: purchase email

- Steam purchase receipt
- Nintendo/PlayStation/Xbox purchase email

## Cookpad / Recipes

### Method 1: URL Clip

ユーザー手順:

1. レシピURLをコピーする。
2. Memory OSに貼る。
3. title/source URL/cooked date/memo/photoだけ保存する。

注意:

- レシピ本文の丸ごとコピーは避ける。
- 自分のメモと写真を中心にする。

### Method 2: manual cooked memory

- 料理名
- 日付
- 誰と食べたか optional
- 家族の反応 optional
- また作りたいか

## Acceptance Criteria

- Sランク各サービスに最低2ルート以上のImport方法がある。
- APIがないサービスでも、copy-paste / URL / manualで対応できる。
- Export方法があるサービスはExport手順を書く。
- API方法があるサービスはDeveloper/API取得の流れを書く。
- 履歴画面/一覧画面コピーを正式なImportとして扱う。
- private/sensitive候補を既定で保護する。
- login scrapingはすべて禁止。
- Import Previewは必須。

## 結論

Memory OSのImportは、サービスごとの現実に合わせる。

Apple MusicやSpotifyはAPI/Export/貼り付けを併用する。
NetflixはViewing Activity CSVを使う。
XはArchive ZIPとURL/pasteを使う。
LINEはtext export/copy/manualだけにする。
Filmarksや食べログやGERAはURL/一覧コピー/手入力で十分始められる。
漫画・アニメ・映画・ラジオは、まず「今見ている/読んでいる/聴いている」状態を手入力または貼り付けで入れられるようにする。

最初に必要なのは、万能な自動連携ではなく、ユーザーが今使っている画面からMemory OSへ安全に移すための複数の入口である。
