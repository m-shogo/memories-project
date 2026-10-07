# Found — MVP Scope

最終更新: 2026-10-08

> Product experiment only. This scope does not authorize feature implementation ahead of repository-wide production/security gates.

## MVP question

Can a user share useful things from different media without organizing them manually, then later retrieve them by remembered meaning?

The MVP is successful if the user experiences:

~~~txt
different sources
→ one reliable save flow
→ automatic useful classification
→ original source preserved
→ easy rediscovery
~~~

## P0 capture

Primary:
- iOS Share Extension: URL + text + safe source metadata
- manual URL/text paste
- Safari/browser share

Architecture should remain compatible with later Android sharesheet, browser extension, import/export files, API-supported sync, screenshots/images.

A share must be durably acknowledged before expensive enrichment.

## P0 source families

Priority examples:
- X
- Instagram
- TikTok
- YouTube
- Qiita
- Zenn
- GitHub
- 食べログ
- recipe sites
- maps/place pages
- shopping/product pages
- blogs/news/articles
- generic web URL

Unsupported rich extraction must still save the original URL/text.

## P0 classification

Infer asynchronously where necessary:
- source
- domain
- object type
- title/entity
- basic genre/topic
- place/location where applicable
- later-use state where justified

Initial presentation:

~~~txt
Food
  ├ Restaurant / Place
  │  ├ Ramen
  │  ├ Yakiniku
  │  ├ Sushi
  │  ├ Cafe
  │  └ ...
  └ Recipe
     ├ dish
     ├ main ingredient
     └ cooking/cuisine facets

Entertainment
  ├ Movie
  ├ Book
  ├ Manga
  └ Anime

Tech
  ├ Article
  ├ Docs
  ├ GitHub/Repository
  └ Tool/Library

Places / Travel
Shopping / Product
Other / Unclassified
~~~

This is a presentation aid, not the canonical storage schema. Canonical records should use extensible facets.

## No filing at capture

Do not ask the user to choose a folder, recipe vs restaurant, movie vs anime, ramen vs yakiniku, or project before saving.

Normal flow:

~~~txt
Share → Found → Saved
~~~

Optional correction happens later.

## P0 retrieval acceptance

Search from Home must handle:
- この前のスペアリブレシピ
- 新宿の焼肉
- TikTokで見たラーメン
- あとで見たかった映画
- おすすめされてた漫画
- ミステリーの本
- WordPressのページャー404
- GitHubで見たやつ
- Reactの記事
- exact restaurant/product/title/repository names

Results should show:
- normalized title/entity
- content type
- useful facets
- original source
- original URL
- saved date
- related sources when the same entity was saved more than once

## P0 browsing

Do not require a deep folder tree. Useful filters may include Food, Places, Recipes, Movies, Books, Manga, Anime, Tech, Products, source, genre/topic, location, and saved date.

Source browsing is required, not optional. The user must be able to filter or browse TikTok, YouTube, Instagram, X, Qiita, Zenn, GitHub, 食べログ and other supported sources while keeping the same content taxonomy.

Examples:

~~~txt
TikTok
→ Food
→ Restaurant
→ Ramen

YouTube
→ Entertainment
→ Movie

Qiita
→ Tech
→ WordPress
~~~

あとで見る is a cross-domain state/filter rather than a shelf that erases the real content type.

## P0 saved-card presentation

Mixed media must remain easy to scan in one list/grid.

Each card should show, when available:

- thumbnail / preview image;
- title;
- user note / 備考;
- source badge/icon;
- category and genre chips;
- place/location for place content;
- saved date;
- action to reopen the original source.

Compact example:

~~~txt
[thumbnail]  炭火焼肉 ○○
             TikTok · 焼肉 · 新宿
             備考: 厚切りタンが気になった
~~~

Another:

~~~txt
[thumbnail]  やわらかスペアリブ
             Recipe site · レシピ · 豚肉
             備考: 今度作る
~~~

For text-heavy IT content where no meaningful image exists, use source/site icon or a stable fallback preview instead of delaying capture.

The same entity may contain multiple source cards. Do not replace a TikTok/YouTube/source-specific card with only a normalized entity card, because the user may remember and want the original media itself.

## P0 corrections

Allow quick correction of:
- domain/object type
- genre/topic
- place
- title/entity
- duplicate/incorrect merge

Corrections should improve personal ranking/classification signals when practical.

## Non-goals for first experiment

Do not require:
- user-created folder hierarchy
- Inbox-zero workflow
- AI chat
- daily digest
- social feed
- capture of all browsing history
- full video/audio archival
- perfect parsing for every site
- deep recommendation engine
- outcome prediction
- agent execution

## Data that must survive

For every save preserve at minimum:

~~~txt
capture id
captured_at
source app/site
original URL when present
canonical URL when resolved
title
shared text/caption when permitted
user note
classification result + confidence
entity links
provenance
~~~

Derived classifications may be recomputed. Original source evidence remains recoverable subject to retention/privacy policy.

## MVP success signals

Qualitative:
- users naturally share from more than one source
- users do not feel a need to manually file most items
- automatic categories are understandable without learning a new system
- remembered-fragment search finds the expected item
- users trust that saves are not lost

Quantitative candidates:
- multi-source capture within first week
- classification correction rate
- Search Success@3
- time-to-find for known saved items
- repeat Share Extension use
- capture integrity
- percentage left unclassified
- false merge rate

Do not optimize total save count as the primary metric. The product succeeds when saved information becomes easier to recover and use.
