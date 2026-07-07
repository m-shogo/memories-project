# Hobby Import Source Research

## 目的

この文書は、Memory OS に「趣味系インポート」を入れるための調査・設計メモである。

対象は、音楽、映画、アニメ、漫画、本、図書館、料理、ゲーム、Web bookmarks、動画視聴、今見ているもの、過去に見たものなど。

Memory OSでは、趣味データは単なる嗜好分析ではなく、人生の文脈である。

例:

- その時期に聴いていた曲
- 見ていたアニメ
- 読んでいた漫画
- 図書館で借りた本
- 作った料理
- 後で見たい映画
- クリアしたゲーム
- 保存した記事

ただし、趣味データは本人性・生活リズム・メンタル状態・人間関係を推測できるため、軽く扱わない。

## 基本方針

### 1. API直結だけを前提にしない

趣味サービスは公開APIが弱い、または個人履歴APIがないことが多い。

そのため、Memory OSでは以下を同列のImport Sourceとして扱う。

```ts
type ImportConnectionMode =
  | 'official_oauth_api'
  | 'official_read_only_api'
  | 'official_csv_export'
  | 'official_takeout_export'
  | 'rss_feed'
  | 'public_catalog_api'
  | 'user_uploaded_file'
  | 'manual_entry'
  | 'email_receipt_import'
  | 'unavailable_no_scraping';
```

### 2. Scraping firstにしない

公式API・公式Export・ユーザー提供ファイルがない場合、原則としてスクレイピングをしない。

理由:

- 規約違反になりやすい。
- ユーザーのログイン情報を危険にさらす。
- サービス側の仕様変更で壊れやすい。
- Memory OSの信頼を落とす。

### 3. Catalog metadata と Personal activity を分ける

作品情報APIと、個人履歴は別物。

```ts
type HobbyDataKind =
  | 'catalog_metadata'
  | 'user_activity'
  | 'user_rating'
  | 'user_review'
  | 'user_bookmark'
  | 'user_collection'
  | 'user_current_state'
  | 'receipt_or_purchase'
  | 'manual_claim';
```

例:

- TMDb / Google Books / Open Library / NDL / MusicBrainz は catalog metadata に強い。
- Last.fm / AniList / Letterboxd CSV / Steam は user activity に使いやすい。
- Amazon Music / Cookpad / Filmarks は個人履歴APIが弱いため、user uploaded file / manual entry中心にする。

### 4. 今見ているもの・今読んでいるものを独立状態にする

「今見てる」「途中」「積み」は人生文脈としてかなり強い。

```ts
type HobbyProgressState =
  | 'want_to_start'
  | 'currently_using'
  | 'paused'
  | 'completed'
  | 'dropped'
  | 'revisited'
  | 'unknown';
```

### 5. AIに好みを断定させない

禁止:

- あなたはこういう作品が本質的に好きです。
- あなたの趣味レベルは高いです。
- この作品群から性格が分かります。

許可:

- この時期によく記録されていた作品です。
- この作品と同じシリーズの記録があります。
- この検索に近い趣味記録です。

## 共通Schema案

```ts
type HobbyDomain =
  | 'music'
  | 'movie'
  | 'tv'
  | 'anime'
  | 'manga'
  | 'book'
  | 'library'
  | 'recipe'
  | 'cooking'
  | 'game'
  | 'podcast'
  | 'video'
  | 'web_bookmark'
  | 'event'
  | 'place'
  | 'other';

interface HobbyItemRef {
  domain: HobbyDomain;
  title: string;
  originalTitle?: string;
  creators?: string[];
  externalIds: Record<string, string>;
  imageUrl?: string;
  catalogSource?: string;
}

interface HobbyActivity {
  id: string;
  domain: HobbyDomain;
  item: HobbyItemRef;
  activityType:
    | 'listened'
    | 'currently_playing'
    | 'watched'
    | 'watching'
    | 'read'
    | 'reading'
    | 'borrowed'
    | 'returned'
    | 'cooked'
    | 'want_to_try'
    | 'bookmarked'
    | 'played'
    | 'completed'
    | 'purchased'
    | 'rated'
    | 'reviewed'
    | 'saved';
  occurredAt?: string;
  sourceRef: string;
  progress?: {
    state: HobbyProgressState;
    episode?: number;
    chapter?: number;
    page?: number;
    percent?: number;
    playtimeMinutes?: number;
  };
  userText?: {
    rating?: number;
    review?: string;
    memo?: string;
  };
  privacyLevel: 'owner_only' | 'owner_sensitive' | 'restricted';
  rawStored: boolean;
}
```

## MVP Priority

### Tier 1: かなり入れたい

- AniList
- Last.fm
- Spotify
- Letterboxd CSV / RSS
- Google Books
- Open Library
- NDL Search
- Calil
- Steam
- Browser bookmarks file
- Google Takeout / YouTube Takeout

理由:

- APIまたはExportが比較的現実的。
- 趣味文脈として濃い。
- Memory OSの思想に合う。
- 無理なスクレイピングを避けやすい。

### Tier 2: 入れたいが慎重

- Apple Music
- MyAnimeList
- Kitsu
- Trakt
- Simkl
- Goodreads CSV
- StoryGraph CSV
- Kindle highlights / My Clippings
- Readwise
- Pocket
- Raindrop.io
- Instapaper
- YouTube liked/saved/watch history via Takeout
- Netflix viewing activity file

理由:

- 実現性はあるが、認証・規約・Export形式・API制限の確認が必要。

### Tier 3: 原則 manual / file-first

- Amazon Music
- Filmarks
- Cookpad
- Bookmeter / 読書メーター
- Booklog / ブクログ
- BookWalker
- ebookjapan
- Kindle purchase/library history
- Manga app reading history
- U-NEXT / Prime Video / Disney+ / Hulu / TVer / ABEMA

理由:

- 公開APIが弱い、または個人履歴取得が困難。
- ログインスクレイピングは避けるべき。
- ユーザー提供CSV、公式ダウンロード、手入力、URL保存、購入/予約メールから始める。

## Music Imports

### Spotify

Status: Tier 1 / official OAuth API

取れる候補:

- saved tracks
- saved albums
- playlists
- recently played tracks
- top artists / top tracks
- currently playing

Memory OSでの価値:

- その時期に聴いていた曲。
- 旅行・通勤・作業・失恋・結婚式準備などの文脈とつながりやすい。

注意:

- API制限変更が起きうる。
- AI/LLM用途や分析用途には規約確認が必要。
- 音楽趣味を人格診断に使わない。

### Last.fm

Status: Tier 1 / public API + scrobble history

取れる候補:

- recent tracks
- loved tracks
- top artists
- top albums
- top tracks
- weekly charts

Memory OSでの価値:

- 複数音楽サービスをまたいだ listening history を作れる。
- Apple Music / Spotify / local player を直接つなげない場合の中間レイヤーになる。

注意:

- 商用利用は要確認。
- scrobbleは本人が設定している場合だけ。

### ListenBrainz

Status: Tier 1.5 / open scrobble ecosystem

取れる候補:

- listens
- imported Last.fm listens
- listening history

Memory OSでの価値:

- Last.fm代替・補完。
- open data志向。

### MusicBrainz

Status: Tier 1 / catalog metadata only

取れる候補:

- artist / release / recording metadata
- identifiers
- cover art linkage

Memory OSでの価値:

- 音楽履歴の名寄せ。
- Spotify / Last.fm / Apple Music の曲名揺れを正規化。

### Apple Music

Status: Tier 2 / official Apple Music API and MusicKit, but implementation review needed

取れる候補:

- library items
- playlists
- catalog metadata
- maybe recently played / playback state depending on available authorization and platform

Memory OSでの価値:

- Apple Music利用者には強い。

注意:

- Apple Developer / MusicKit / user authorization が必要。
- 日本ユーザーには重要だが、MVPではLast.fm/Spotifyより後でよい。
- 取れない履歴は、Apple privacy export / manual import / Last.fm scrobble連携で補う。

### Amazon Music

Status: Tier 3 / public personal listening API weak or unavailable

方針:

- API直結をMVPにしない。
- Amazon data download / purchase history / manual playlist export / Last.fm scrobbleがあれば使う。
- ログインスクレイピングしない。

## Movie / TV Imports

### Letterboxd

Status: Tier 1 / CSV export + RSS; API access by request only

取れる候補:

- watched films
- diary entries
- ratings
- reviews
- tags
- watchlist
- lists
- RSS for new diary/reviews/lists

Memory OSでの価値:

- 映画人生ログとして非常に強い。
- CSV中心なら安全に実装しやすい。

注意:

- APIはrequest-onlyで、LLM/GPT・private/personal・recommendation用途が拒否される可能性がある。
- CSV/RSS firstにする。

### TMDb

Status: Tier 1 / public catalog metadata API

取れる候補:

- movie / tv metadata
- cast / crew
- posters
- release dates
- external ids

Memory OSでの価値:

- Filmarks / Letterboxd / Netflix / manual entries の名寄せ。
- user historyではなくcatalog enrichmentとして使う。

### Trakt

Status: Tier 2 / official API, watch history-oriented

取れる候補:

- watched history
- watchlist
- ratings
- progress
- collections

Memory OSでの価値:

- 映画・海外ドラマ・アニメの「見た/見てる」を一箇所化できる。

### Simkl

Status: Tier 2 / API; anime/movie/tv tracking

取れる候補:

- watch history
- anime tracking
- lists

Memory OSでの価値:

- Traktの補完。

### Filmarks

Status: Tier 3 / no public API found; manual/file-first

方針:

- 公式APIが確認できるまで直結しない。
- スクレイピングしない。
- ユーザーが自分のページURL、CSV、手入力、スクショから取り込む方式を検討。
- TMDbで作品名寄せを行う。

### Netflix / Prime Video / Disney+ / Hulu / U-NEXT / TVer / ABEMA

Status: Tier 3 / official user history API generally weak

方針:

- 各サービスの公式Exportや視聴履歴ダウンロードがある場合のみfile import。
- Google Takeout相当やNetflix viewing activity fileがあれば取り込む。
- ログインスクレイピングしない。

## Anime / Manga Imports

### AniList

Status: Tier 1 / GraphQL API

取れる候補:

- anime list
- manga list
- watching / reading / completed / paused / dropped / planning
- score
- progress
- favourites
- reviews / activity depending on scope

Memory OSでの価値:

- アニメ・漫画趣味インポートの第一候補。
- 作品数も多く、APIが強い。

注意:

- scoreを人生価値や性格判断に使わない。
- private listへの配慮。

### MyAnimeList

Status: Tier 2 / official API exists, OAuth and rate limit review needed

取れる候補:

- anime list
- manga list
- status
- score
- progress

Memory OSでの価値:

- 日本ユーザーにも馴染みがある。

### Kitsu

Status: Tier 2 / API exists, details review needed

取れる候補:

- library entries
- anime/manga status

### MangaDex

Status: Tier 3 caution / not first MVP

理由:

- APIは存在するが、非公式翻訳・権利まわりの注意が大きい。
- Memory OSが漫画本文や違法性のある読書履歴を取り込むように見えるのは避ける。

方針:

- 公式・合法カタログを優先。
- MangaDexはURL bookmark / title metadata程度に留める。
- raw chapter contentは保存しない。

### Manga app histories

対象:

- MANGA Plus
- Shonen Jump+
- BOOK WALKER
- ebookjapan
- Kindle manga
- コミックシーモア
- ピッコマ
- LINEマンガ

Status: Tier 3 / official user history API weak

方針:

- user uploaded export / purchase email / manual entry / screenshot OCR-free manual correction。
- ログインスクレイピングしない。
- 購入履歴はsensitive扱い。

## Book / Library Imports

### Google Books

Status: Tier 1 / catalog + personal bookshelves API

取れる候補:

- book metadata
- viewability
- eBook availability
- personal bookshelves if user auth is available

Memory OSでの価値:

- 本の名寄せ。
- manual/CSV本棚の補完。

### Open Library

Status: Tier 1 / open book APIs + public reading log/lists

取れる候補:

- book search
- covers
- work/edition metadata
- public reading log
- lists

注意:

- APIは高トラフィック商用バックエンド用ではない。
- low-volume, human-facing, cache-friendly usageにする。

### NDL Search

Status: Tier 1 / Japanese book metadata API

取れる候補:

- 書誌メタデータ
- OpenSearch / SRU / OpenURL
- OAI-PMH harvest

注意:

- 営利利用や継続利用は手続き・条件確認が必要。
- クレジット表記が必要。

### Calil

Status: Tier 1 / Japanese library availability API

取れる候補:

- ISBNから図書館蔵書検索
- 貸出可/貸出中などの蔵書状態
- 近い図書館情報

注意:

- 借りた履歴そのものではなく、蔵書/ availability。
- アプリケーションキー申請が必要。

### Goodreads

Status: Tier 2 / CSV export, API deprecated/no new keys

方針:

- API前提にしない。
- Goodreads export CSV importを使う。
- Open Library / Google Booksで名寄せ。

### StoryGraph

Status: Tier 2 / CSV export/import oriented

方針:

- CSV import/exportがあれば取り込む。
- API前提にしない。

### 読書メーター / ブクログ

Status: Tier 3 / no public API found; manual/file-first

方針:

- CSV exportがあれば取り込む。
- なければ手入力、URL、スクショからのユーザー確認付き手動 import。
- スクレイピングしない。

### Library loan history / 図書館履歴

Status: Tier 3 / highly sensitive, no standard API

方針:

- 図書館の貸出履歴は非常にプライベート。
- 自動連携は基本しない。
- ユーザーが保存したCSV/レシート/メール/手入力のみ。
- 家族カードや子どもの貸出履歴は取り込まない、またはrestricted。

## Cooking / Recipe Imports

### Cookpad

Status: Tier 3 / no public personal API found; manual/file-first

取り込み候補:

- 作った料理
- 保存したレシピURL
- つくれぽ相当の自分メモ
- 家族の反応メモ
- 写真

方針:

- Cookpad公式APIが確認できるまで直結しない。
- recipe URL + user memo + date + photo metadataで十分価値がある。
- レシピ本文の丸ごと保存は著作権リスクがあるため避ける。
- ingredients / title / source URL / personal note中心。

### Rakuten Recipe

Status: Tier 2 / Rakuten Web Service review needed

方針:

- recipe category/rankingなどcatalog寄りに使える可能性。
- ユーザー個人履歴ではなく、レシピ名寄せ/候補に使う。

### Edamam / Spoonacular

Status: Tier 2 / paid/freemium recipe APIs

方針:

- 海外レシピ・栄養・アレルゲン分析には強い。
- 日本ユーザーMVPでは優先度低め。
- ライセンス・キャッシュ制限が厳しいため、Memory OS内にコピーしすぎない。

## Games Imports

### Steam

Status: Tier 1 / official Web API for owned/recent games when visible

取れる候補:

- owned games
- recently played games
- playtime
- badges / level

Memory OSでの価値:

- その時期に遊んでいたゲーム。
- 友人との思い出、生活時期、趣味変遷に強い。

注意:

- public visibility / auth key が必要。
- プレイ時間で人生評価しない。

### IGDB

Status: Tier 1 / catalog metadata

取れる候補:

- game metadata
- cover
- release date
- platform
- genre

方針:

- Steam / manual entries の補完に使う。

### Nintendo / PlayStation / Xbox

Status: Tier 3 / limited personal public API

方針:

- Nintendo Switch play activity screenshot/manual.
- PlayStation wrapped/export/manual.
- Xbox APIは詳細確認。
- ログインスクレイピングしない。

## Web Bookmark / Article Imports

### Browser bookmarks

Status: Tier 1 / file import

対象:

- Chrome bookmarks HTML/JSON
- Safari bookmarks export
- Firefox bookmarks export

Memory OSでの価値:

- その時期に興味があったもの。
- 技術、旅行、結婚式、趣味、買い物の文脈。

注意:

- bookmarksは思想/健康/家族/仕事を含むためsensitive。
- AI要約はユーザーが求めた時だけ。

### Pocket / Instapaper / Raindrop.io

Status: Tier 2 / API or export review needed

取り込み候補:

- saved articles
- tags
- archived/read status

方針:

- OAuth/API or export file。
- content全文ではなくtitle/url/tags/date中心。

## YouTube / Video / Podcast

### Google Takeout / YouTube

Status: Tier 1 / official export

取れる候補:

- watch history
- search history
- liked videos
- playlists
- subscriptions
- YouTube Music data

方針:

- YouTube Data APIより、まずTakeout file import。
- watch historyは非常にsensitive。
- Shorts/深夜視聴/健康/政治/恋愛など、人格推測しやすいためAI分析off default。

### YouTube Data API

Status: Tier 2 / catalog and account data, not full personal history replacement

方針:

- playlists / subscriptions / liked videosなどに限定。
- full watch historyはTakeout優先。

### Podcast

候補:

- Apple Podcasts: API弱め、manual/export中心。
- Spotify podcast listening: Spotify側で一部取得。
- Pocket Casts / Overcast: OPML export, subscriptions import。

方針:

- OPML + manual listening history。

## Import UI Ideas

### 趣味インポート画面

Sections:

- 音楽
- 映画/ドラマ
- アニメ/漫画
- 本/図書館
- 料理
- ゲーム
- Web記事/Bookmark
- YouTube/動画
- Podcast

Each card:

- 公式APIで接続
- ファイルをアップロード
- URLを貼る
- 手入力
- 今は非対応

### User-facing copy

Use:

- このサービスは公式APIで接続できます。
- このサービスは公式Exportファイルから取り込めます。
- このサービスは公開APIが確認できないため、手入力またはファイル取込のみ対応します。
- 作品情報だけを補完します。あなたの評価や感想は勝手に作りません。
- 趣味から性格や人生価値を判断しません。

Do not use:

- あなたの本当の趣味を分析します。
- あなたの性格に合う作品です。
- あなたの人生を変えた作品ランキングです。
- この作品群からあなたの本質が分かります。

## Safety / Privacy Rules

- 趣味データはowner_only default。
- 視聴履歴/読書履歴/料理履歴はprivate。
- 政治、宗教、健康、性的、メンタル、家族、未成年に関わる趣味記録はsensitive。
- 図書館履歴はrestricted寄り。
- 子どもの読書/視聴履歴は取り込み慎重。
- Public profile importでも、Memory OS内ではprivate扱い。
- reviews/commentsはraw保存off default。
- API tokenはscoped, encrypted, revocable。
- 取り込み直後にAI分析しない。

## MVP Import Set

### MVP-A: file-first

- Letterboxd CSV
- Goodreads CSV
- Browser bookmarks export
- Google Takeout YouTube history
- Kindle My Clippings
- manual recipe URL
- manual/currently watching/reading/listening

### MVP-B: safe API connectors

- AniList
- Last.fm
- Spotify
- Open Library
- Google Books
- NDL Search
- Calil
- Steam
- TMDb
- MusicBrainz

### MVP-C: later

- Apple Music
- MyAnimeList
- Trakt
- Simkl
- Pocket/Raindrop/Instapaper
- Readwise
- StoryGraph

### Avoid for MVP

- Amazon Music direct API
- Filmarks direct API
- Cookpad direct API
- Manga app login scraping
- streaming service login scraping
- unauthorized full recipe scraping

## 結論

趣味系インポートはMemory OSと相性が良い。

ただし、公式APIだけに寄せると穴が多い。

Memory OSでは、API・CSV・Takeout・RSS・手入力を同じImport Sourceとして扱い、無理なスクレイピングは避ける。

最初に作るべきは、趣味サービス直結の数よりも、どの趣味データでも扱える共通schemaとImport Previewである。

趣味は人生の索引になるが、AIが好み・人格・価値を断定する材料にしてはいけない。
