# Found — Source and Card Presentation

最終更新: 2026-10-08

## Principle

Found must unify content across media without erasing the media it came from.

The same item participates in several parallel views:

~~~txt
CONTENT
Food > Restaurant > Ramen

SOURCE
TikTok

PLACE
Kanagawa > Kawasaki

STATE
Want to visit
~~~

These are facets over one corpus, not competing folder hierarchies.

## Source browse

Source is a first-class facet and search dimension.

Initial source views may include:

- TikTok
- YouTube
- Instagram
- X
- Qiita
- Zenn
- GitHub
- 食べログ
- Recipe sites
- Maps
- Shopping sites
- Blogs / generic web

Examples:

~~~txt
TikTok
├ Food
│  ├ Restaurant
│  │  ├ Ramen
│  │  └ Yakiniku
│  └ Recipe
├ Entertainment
│  ├ Movie
│  └ Anime
└ Tech

YouTube
├ Recipe
├ Movie
├ Anime
└ Tech
~~~

The user can start from either content or source. Neither hierarchy owns the item.

## Search examples

Required source-aware queries include:

- TikTokで見たラーメン
- YouTubeで見たスペアリブ
- Instagramで保存した焼肉屋
- Xでおすすめされてた漫画
- QiitaのWordPress 404の記事
- GitHubで見たライブラリ

Source is a ranking/filter signal, not the only retrieval key.

## Default card anatomy

Recommended mixed-media card:

~~~txt
┌──────────────────────────────┐
│ [ thumbnail / preview ]      │
│                              │
│ Title                        │
│ TikTok · 焼肉 · 新宿         │
│                              │
│ 備考: 厚切りタンが気になった │
│                              │
│ saved 10/08          Open ↗  │
└──────────────────────────────┘
~~~

Card information priority:

1. thumbnail/visual identity;
2. title;
3. source badge;
4. category / genre / place chips;
5. user note / 備考;
6. saved date;
7. reopen-original action.

Do not overload every card with all extracted metadata. Rich metadata belongs in detail views and filters.

## Thumbnail rules

Prefer, when lawful and technically available:

1. source-provided thumbnail/Open Graph image;
2. video/post thumbnail provided by the source;
3. website article image;
4. source/site icon;
5. stable generated placeholder by content type.

Thumbnail failure must never block capture.

For text-heavy Tech/IT content, a clean site/source icon may be more useful than a low-quality decorative image.

## Title rules

Keep both:

- original/source title;
- normalized display/entity title when resolved.

The normalized title may improve browsing, but the original title must remain available in detail/provenance.

Examples:

~~~txt
normalized: 炭火焼肉 ○○ 新宿店
original:   新宿で絶対食べてほしい厚切りタン3選 #焼肉
~~~

## Notes / 備考

User-authored notes and machine-generated descriptions are different data.

Keep separate fields/concepts:

~~~txt
user_note
machine_summary
source_caption
~~`

The card label 備考 should primarily display user-authored text when present.

If an AI-generated cue is shown, it must not masquerade as the user's own note. Use separate visual treatment or wording such as:

~~~txt
備考: 今度しーちゃんと行く        ← user
内容: 厚切りタンを紹介する動画      ← derived
~~~

Do not silently overwrite user notes during re-enrichment.

## Same entity, multiple media

If the same restaurant/movie/product/etc. appears from several sources, support both entity-level and source-level viewing.

Example:

~~~txt
炭火焼肉 ○○

Saved from 3 sources
├ [TikTok thumb] 厚切りタン紹介
├ [Instagram thumb] 新宿焼肉まとめ
└ [食べログ icon] 店舗ページ
~~~

Entity grouping improves organization; source cards preserve why/how the user discovered it.

## List / grid modes

Product hypothesis:

- visual domains (food, places, movies, products): thumbnail-forward grid/card view;
- text-heavy domains (Tech, articles, docs): compact list with icon, title, note, source, topic chips;
- source views such as TikTok/YouTube: thumbnail-forward by default;
- global search: mixed adaptive cards.

Do not force one identical card density across every medium.

## P0 acceptance criteria

A P0 UI prototype should demonstrate at least:

1. mixed list containing TikTok, YouTube, recipe-site, Qiita and 食べログ items;
2. visible source badge on every item;
3. thumbnail or safe fallback;
4. title;
5. optional user note/備考;
6. category/genre facets;
7. filter by source;
8. filter by content category;
9. search combining source + meaning;
10. reopening the original source URL.
