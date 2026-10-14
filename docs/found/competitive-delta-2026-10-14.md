# Found competitor delta — 2026-10-14

Status: exploratory research, not product authority or implementation authorization. This note does not override repository-wide production/security NO_GO gates.

## Release delta

- Stashr announced desktop Firefox support on 2026-10-11 (Firefox 140+); still no iOS Share Extension or native mobile app. https://stashr.me/blog/stashr-firefox-extension
- Karakeep's latest official GitHub release remains v0.33.2 (2026-08-11). Semantic/hybrid search remains experimental. https://github.com/karakeep-app/karakeep/releases
- No new dated major release was confirmed today for mymind or Raindrop. Do not infer absence of all product changes from release announcements alone.

## Newly verified evidence and implications

1. **Interoperability is more mature than assumed.** Karakeep v0.29.0 already added an importer for mymind exports. v0.31.0 expanded backups/exports to include lists. This is not proof of lossless migration: a mymind import issue reported 997/1066 progress and 47 failed entries in v0.29.0. Measure field-level round trips and partial failures, not merely presence of an Import/Export button.
   - https://github.com/karakeep-app/karakeep/releases
   - https://github.com/karakeep-app/karakeep/issues/2208
2. **iOS capture quality is a real test target, not a unique feature.** Karakeep issue #3018 (2026-08-13) reports successful Share Sheet saves followed by a frozen source app; #3030 (2026-08-20) reports phone captures not appearing in an already-open desktop web view until manual refresh. These are individual reports, not prevalence or current universal behavior.
   - https://github.com/karakeep-app/karakeep/issues/3018
   - https://github.com/karakeep-app/karakeep/issues/3030
3. **Native-save sync is not a unique moat.** In addition to Stashr's desktop capture, the community-maintained karakeep-sync project supports Hacker News upvotes, Reddit saves, GitHub stars and Pinboard. Check maintenance and permissions before considering adoption.
   - https://github.com/sidoshi/karakeep-sync
4. **API integration is gated by pricing and contracts.** Stashr API/CLI/MCP require Pro, while Karakeep offers REST API and self-hosting. mymind's entity API explicitly warns that its schema/endpoints are work in progress.
   - https://stashr.me/docs/api
   - https://access.mymind.com/api/entities

## Product decision update

Do not reimplement generic bookmarking, tagging, visual cards, semantic search, MCP, or basic import/export solely to match competitors.

Preserve the existing Found P0 promise: effortless capture and retrieval of scattered saves, with source platform and content category as independent facets, and thumbnail/title/user note/source provenance preserved.

Elevate **capture trust** and **migration integrity** as measurable acceptance gates rather than unproven differentiators:

- Share Sheet: source app returns to an interactive state; local durable acknowledgement is explicit; server-side enrichment may continue asynchronously.
- Offline/timeouts: no false "saved" state; idempotent retries; source URL and user note never disappear.
- Cross-device: new captures become visible after foreground revalidation without requiring manual reload.
- Import/export: round-trip checks for URL, source, title, user note, timestamps, source caption, entity links, media asset references, and per-item failures.
- Dedupe: preserve individual source evidence even when multiple saves resolve to the same entity; allow correction of false merges.
- Evidence/provenance: Saved != Wanted != Did != Liked; machine-inferred claims must not become user-confirmed facts.

## Test plan (proposed, not executed)

Use a consented corpus of 40-60 URLs across TikTok, YouTube, Instagram, X, shopping, food/places, recipe, Qiita, Zenn and GitHub. Compare mymind, Stashr, Raindrop, Karakeep, and relevant iOS alternatives. Measure:

- source-app return success; capture receipt and eventual enrichment completion; duplicate/idempotency outcomes;
- thumbnail/title/source/notes correctness; false entity merge rate;
- Search Success@3 and time-to-reopen using remembered fragments;
- import/export round-trip fidelity and failure visibility;
- 2-3 week continued usage, manual classification burden, and willingness to switch/pay against the free Raindrop baseline.

Thresholds should be predeclared before testing; do not fabricate current performance or WTP numbers.

## Architecture boundary

Karakeep can be a disposable **external PoC baseline** or integration adapter, not an automatic replacement for the repository's canonical Go/PostgreSQL security and import architecture. Do not introduce AGPL-derived code or bypass production/security gates without separate review. Maintain source-vs-capture-method separation and an independent evidence envelope.

## Decision

**No standalone Found build yet.** First run reliability and migration tests against existing products, then a small Saved→Did→Liked evaluation with explicit user evidence. Shared evidence/entity infrastructure with Memories remains a candidate; unified UI and monetization remain hypotheses.
