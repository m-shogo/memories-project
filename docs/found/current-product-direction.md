# Found — Current Product Direction

最終更新: 2026-10-08

> Working direction, not an immutable requirement. Validate with real usage and revise when evidence contradicts it.

## Problem

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

### Shopping / Products

Object types:
- product
- service/subscription
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
