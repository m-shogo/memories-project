# Found — Current Product Direction

最終更新: 2026-10-08

> Working direction, not an immutable requirement. Validate with real usage and revise when evidence contradicts it.

## Primary problem

People already create many "save for later" records, but those records are fragmented across X bookmarks, Instagram saved posts/reels, TikTok favorites/shares, YouTube Watch Later/playlists, Qiita/Zenn, GitHub, 食べログ/maps, recipe sites, shopping wishlists, browser bookmarks, blogs and articles.

The main pain is not that users lack another place to save. It is that:

- they forget which service contains the saved item;
- each service has a different save model;
- they rarely create and maintain categories consistently;
- wishlists, restaurants, recipes, media recommendations and IT references become separate silos;
- later, they remember the thing itself but not where it was saved.

Found's first job is to make existing later-use information visible and organized with minimal maintenance.

## Product hierarchy

P0 value:

~~~txt
scattered favorites / later items / wishlists
→ one visible library
→ automatic category / genre / place / topic organization
→ source still visible
→ easy browse and search
~~~

P1/P2 intelligence such as intent clustering, decision memory, resume state and outcome learning may build on this foundation, but they are not required to explain the first product value.

## Problem detail

Useful later-use information is fragmented across X bookmarks, Instagram saved posts/reels, TikTok favorites/shares, YouTube Watch Later/playlists, Qiita/Zenn, GitHub, 食べログ/maps, recipe sites, shopping wishlists, browser bookmarks, blogs and articles.

Users often remember the meaning, not the source:

- この前のスペアリブのレシピ
- 新宿あたりの焼肉屋
- おすすめされてたミステリー漫画
- あとで見ようと思ってた映画
- WordPressのページャー404の記事
- GitHubで見たあのライブラリ

Found should optimize for the remembered meaning while preserving the original source.

## Target flow

~~~txt
Share / paste / import
        ↓
durable Evidence Packet
        ↓
source-aware extraction
        ↓
content classification
        ↓
entity resolution
        ↓
facets / genres / location / topic
        ↓
optional recent intent/context relation
        ↓
search / browse / reopen / act
~~~

## Automatic organization model

Do not use one mutually-exclusive folder field. A saved item may receive independent dimensions:

~~~txt
source       = TikTok
domain       = food
object_type  = restaurant
genre        = yakiniku
place        = Shinjuku / Tokyo
entity       = resolved restaurant
state        = saved_for_later
intent       = optional inferred context
~~~

Another TikTok can be entertainment.anime or tech.article. Source is provenance, not meaning.

## Source is also a first-class browse/filter axis

Content meaning is the primary organization axis, but the source platform must remain visible, searchable, and browsable.

Users must be able to open source views such as:

~~~txt
TikTok
YouTube
Instagram
X
Qiita
Zenn
GitHub
食べログ
Recipe sites
Blogs
~~~

These are not exclusive folders. They are source facets over the same saved corpus.

Examples:

- TikTok + Food + Restaurant + Ramen
- YouTube + Entertainment + Anime
- Qiita + Tech + WordPress
- Instagram + Food + Recipe + Spare ribs

A user should be able to browse either direction:

~~~txt
Food → Restaurant → Ramen
or
TikTok → Food → Restaurant → Ramen
~~~

Search must also accept source constraints such as 「TikTokで見たラーメン」 or 「YouTubeでおすすめされてた映画」.

## Multi-source presentation

When multiple media point to the same underlying entity or topic, Found should preserve each source as a separate evidence item while presenting a grouped entity/context when useful.

Example:

~~~txt
焼肉店 A

Sources
├ TikTok video
├ Instagram reel
├ 食べログ page
└ official site
~~~

The grouped view must not erase the individual media items. Users may want to reopen the exact TikTok or YouTube item later.

## Saved-item card

The default card should make heterogeneous media visually scannable.

Required card fields when available:

- thumbnail / preview image;
- title;
- short note / 備考;
- source badge/icon;
- content type;
- category / genre chips;
- location for place content;
- saved date;
- original-source link/action.

Example:

~~~txt
[thumbnail]

炭火焼肉 ○○
TikTok · 焼肉 · 新宿

備考: 厚切りタンが気になった
2026/10/08
~~~

For recipe content:

~~~txt
[thumbnail]

やわらかスペアリブ
DELISH KITCHEN · レシピ · 豚肉

備考: 今度すき焼き以外で肉料理したい
2026/10/08
~~~

For tech content:

~~~txt
[thumbnail or site icon]

WordPress pagination 404 fix
Qiita · Tech · WordPress · pagination

備考: 英語カテゴリのpage/2問題で確認
2026/10/08
~~~

Thumbnail handling is source-dependent. If a reliable thumbnail cannot be obtained, show a stable source/site icon or generated placeholder rather than blocking the save.

## Current top-level domains

These are UI/product hypotheses. Storage must remain extensible.

### Food

Object types:
- restaurant / cafe / bar / bakery / food shop
- recipe
- food product
- cooking technique
- food recommendation/list

Useful facets:
- cuisine/dish genre: ramen, yakiniku, sushi, curry, izakaya, cafe, sweets, etc.
- country/prefecture/city/neighborhood/station
- purpose/context when reliable: lunch, dinner, date, family, solo
- recipe dish, primary ingredient, cooking method, cuisine, duration

Examples:

~~~txt
食 > 店 > ラーメン > 神奈川 > 川崎
食 > 店 > 焼肉 > 東京 > 新宿
食 > レシピ > スペアリブ
食 > レシピ > 鶏肉 > 20分
~~~

### Entertainment

Object types:
- movie
- book
- manga
- anime
- TV/series
- video
- podcast/radio
- game where useful

Useful facets:
- genre
- title/entity
- author/director/creator
- series/franchise
- recommendation source
- want-to-watch / want-to-read / later / in-progress / completed where applicable

### Tech / IT

Object types:
- article
- documentation
- repository
- issue / PR
- library/package/tool
- snippet/tutorial
- product/service

Useful facets:
- topic/language/framework: WordPress, PHP, JavaScript, TypeScript, React, CSS, Node, Docker, Git, etc.
- problem/error concept
- official vs community source
- repository/package identity
- version when extractable

### Places / Travel

Object types:
- restaurant (cross-labeled with Food)
- attraction
- hotel/ryokan
- onsen/spa
- event/venue
- shop
- park/nature
- transport-related place

Useful facets:
- coordinates/place entity
- country/prefecture/city/neighborhood/station
- place genre
- planned-trip/context relation when reliable

### Shopping / Products / Wishlist

Shopping is a first-class domain because "欲しいもの" often becomes especially fragmented across EC sites, social media, review articles and videos.

Object types:
- product
- service/subscription
- wishlist item
- candidate/comparison source
- review

Useful facets:
- product category
- brand
- model
- merchant/source
- candidate group / decision context
- considering / bought / rejected only when explicitly observed or strongly confirmed

## Lifecycle is separate from category

Do not create an "あとで見る" domain. Use states such as:

~~~txt
saved_for_later
want_to_watch
want_to_read
want_to_visit
want_to_try
considering
completed
visited
cooked
bought
~~~

A saved item remains both a real domain object and a later-use item.

## Source handling

Preserve:
- original URL
- canonical URL when resolvable
- source platform/app
- source title/caption
- creator/author where permitted
- capture timestamp
- user note
- extraction provenance
- every source reference after deduplication

Example same restaurant:

~~~txt
Restaurant entity
sources:
- TikTok reel
- Instagram reel
- 食べログ page
- official site
~~~

## Confidence and correction

- high confidence: organize automatically
- medium confidence: organize automatically but make correction easy
- low confidence: keep searchable/visible without forcing Inbox cleanup

No inferred genre/status becomes an irreversible fact.

## Product boundary with Memories

Shared candidates:
- evidence/capture envelope
- source adapters
- canonical URL/entity identity
- provenance
- embeddings/search primitives
- encryption
- export/deletion

Found-specific:
- later-use states
- content/domain taxonomy
- intent/context clustering
- decision/resume state
- source-to-entity relationships

Memories-specific:
- life episodes
- people relationships
- autobiographical timeline
- narrative/reflection

Do not combine the product UI solely because infrastructure is shared.
