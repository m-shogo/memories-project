# Found — Classification and Retrieval Model

最終更新: 2026-10-08

## Goal

A saved item must remain discoverable by what the user remembers later, not only by its original title, URL, or platform.

Canonical acceptance example:

> A recipe-site URL saved today must later be retrievable by "この前のスペアリブレシピ" even when the user does not remember the page title, site, or URL.

The same rule applies to restaurants, media recommendations, shopping candidates, and IT articles.

## Separate source from content

Source answers where it came from:

~~~txt
x / instagram / tiktok / youtube / qiita / zenn / github / tabelog /
recipe_site / shopping_site / blog / map / browser / other
~~~

Content answers what it is:

~~~txt
food.recipe
food.restaurant
place.hotel
place.attraction
entertainment.movie
entertainment.book
entertainment.manga
entertainment.anime
tech.article
tech.documentation
tech.repository
shopping.product
...
~~~

Never infer content type from source alone.

| Source | Possible content |
|---|---|
| TikTok | ramen restaurant |
| TikTok | spare-ribs recipe |
| TikTok | movie recommendation |
| TikTok | JavaScript tip |
| YouTube | cooking recipe |
| YouTube | anime recommendation |
| YouTube | Git tutorial |
| X | restaurant recommendation |
| X | product review |
| X | GitHub library recommendation |

## Faceted examples

Restaurant:

~~~json
{
  "domain": "food",
  "objectType": "restaurant",
  "genres": ["yakiniku"],
  "place": {"country": "JP", "prefecture": "Tokyo", "city": "Shinjuku"},
  "state": "want_to_visit"
}
~~~

Recipe:

~~~json
{
  "domain": "food",
  "objectType": "recipe",
  "dish": ["スペアリブ"],
  "ingredients": ["豚スペアリブ"],
  "methods": ["焼く"],
  "state": "saved_for_later"
}
~~~

Media recommendation:

~~~json
{
  "domain": "entertainment",
  "objectType": "movie",
  "genres": ["mystery"],
  "state": "want_to_watch",
  "recommendation": true
}
~~~

IT article:

~~~json
{
  "domain": "tech",
  "objectType": "article",
  "topics": ["WordPress", "pagination", "rewrite", "404"],
  "source": "qiita",
  "state": "saved_for_later"
}
~~~

## Retrieval pipeline

Use hybrid retrieval rather than one embedding:

~~~txt
query
→ lexical retrieval for exact terms
→ semantic retrieval for vague meaning
→ metadata/facet filtering and boosts
→ recency/context boost when time is implied
→ source/provenance boost when source is named
→ fused ranking
~~~

Exact matching matters for model numbers, repositories, error codes, package names, restaurant names, ISBN/title fragments. Semantic retrieval matters for remembered phrases such as:

- この前のスペアリブレシピ
- 新宿の焼肉屋
- おすすめされてたミステリー漫画
- WordPressのページャーが404になるやつ
- 買おうとしてた革靴

## Query hints

A query can contain several remembered dimensions:

~~~txt
time       この前 / 去年 / 最近
source     TikTokで見た / Qiitaの記事
domain     レシピ / 映画 / 漫画 / IT記事
topic      スペアリブ / pagination / 焼肉
place      新宿 / 横浜 / 川崎
state      あとで見ようと思った / 行きたかった
entity     title / brand / repository / restaurant
~~~

Keep the raw query while also extracting hints.

## Acceptance examples

### この前のスペアリブレシピ

- infer food + recipe
- normalize/expand スペアリブ into dish/ingredient concepts
- soft recency boost for この前
- search title + extracted page text + recipe fields + notes
- return the original recipe URL/site prominently

### 新宿の焼肉

- boost restaurant/place records
- area = Shinjuku
- genre/cuisine = yakiniku
- group TikTok/Instagram/食べログ references under the same restaurant entity when confident

### おすすめ映画

- search movie items from every source
- boost recommendation-like surrounding content
- preserve the original recommendation source/recommender when available

### 前に見たWordPressの404の記事

- domain = tech
- topic = WordPress
- lexical/semantic boost for 404
- include Qiita, Zenn, GitHub, official docs, blogs without source bias

## Preserve two truths

A result should answer:

1. What is this? — normalized entity/content.
2. Where did I save it from? — original source/provenance.

Do not trade away the original URL in exchange for normalization.

## Entity resolution and deduplication

Do not deduplicate only by URL. Potential same-entity signals include:

- canonical URL
- schema.org identifiers
- ISBN
- model/SKU
- GitHub owner/repo
- normalized place name + coordinates/address
- title + creator
- structured recipe identity
- high-confidence semantic/entity match

When uncertain, keep separate records and soft-link them instead of destructive merge.

## Implementation order

P0:
- source
- domain
- object type
- original URL/title
- core entity
- basic genre/topic
- place where applicable
- later-use state

P1:
- richer recipe metadata
- entertainment genres/creator graph
- tech problem/error concepts
- product comparison groups
- recommendation relationships

P2:
- intent/resume-state inference
- outcome/repeat learning
- personalized ranking

## Evaluation

Measure at minimum:

- domain classification accuracy
- object-type accuracy
- entity-resolution precision
- genre/topic precision
- Search Success@3 for remembered-fragment queries
- false destructive-merge rate
- correction rate

Precision is more important than aggressive filing. Unclassified but searchable is safer than confidently wrong structure.
