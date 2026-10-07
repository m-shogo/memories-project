# Found — cross-source memory track

最終更新: 2026-10-08

> Status: product/design exploration. This document does not override the Memory OS production authority, security gates, or current implementation priorities in the repository root.

## Position in memories-project

Found is developed inside the same repository as Memories, but as a distinct product surface.

~~~txt
Memory OS / shared evidence kernel
├─ Memories
│  └─ experienced / retrospective memory
└─ Found
   └─ selected / prospective / later-use memory
~~~

- Memories: what happened, people, episodes, life narrative, reflection.
- Found: what the user found, wants to revisit, is comparing, intends to try, or wants to resume.

Found is not "Memories 2" and should not force one combined UI. It is the prospective/later-use side of the same broader Memory OS idea.

## Current product promise

Found accepts a share from many different apps and sites, remembers the original source, understands the content, and automatically organizes it by what it is, not by where it came from.

Examples:

~~~txt
TikTok ramen video
Instagram yakiniku reel
Tabelog restaurant URL
→ Food > Place > Restaurant
→ ramen / yakiniku + area facets

recipe-site URL
YouTube cooking video
TikTok recipe
→ Food > Recipe
→ dish / ingredient / cuisine facets
→ searchable later as "この前のスペアリブレシピ"

YouTube movie recommendation
X post recommending a novel
blog post about manga
TikTok anime recommendation
→ Entertainment
→ Movie / Book / Manga / Anime
→ genre + creator/title + later state

Qiita / Zenn / GitHub / official docs / blog
→ Tech
→ article / docs / repository / issue / tool
→ WordPress / PHP / JS / TS / CSS / React / Docker / Git etc.
~~~

The source platform is preserved as provenance, but source platform is not the primary category.

## Core product principles

1. Share first, organize automatically. Saving must not require choosing a folder, category, genre, or project.
2. Source and meaning are separate dimensions. TikTok can contain a restaurant, recipe, movie recommendation, IT tip, product, or travel place.
3. Original URL is durable memory. The exact page/video/post originally saved must remain reopenable.
4. "Later" is a state, not a category. A recipe, movie, restaurant, or IT article may all be saved for later while remaining in their real domain.
5. Multi-label beats one-folder classification. A restaurant may be Food + Place + Tokyo + Shinjuku + Yakiniku at the same time.
6. Corrections are optional and low friction; users should not need to maintain folders.
7. Raw saves remain accessible. Automatic structure must never hide or destroy the captured item.
8. Provenance is preserved. Same-entity sources may be grouped, but source references are not discarded.
9. Search must work from remembered fragments, not only exact title/source.
10. Taxonomy and UX remain hypotheses and should evolve with evidence.

## Proposed user-facing shape

~~~txt
Search
Recent / grouped context
Saved
~~~

Domain-specific rendering can appear after classification, but the user should not need to navigate a complex folder tree.

## Documents

- [Current product direction](current-product-direction.md)
- [Classification and retrieval model](classification-and-retrieval-model.md)
- [MVP scope](mvp-scope.md)
