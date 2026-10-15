# Found — platform access and competitor delta (2026-10-15)

Status: research-only. Does not authorize implementation or override repository production/security gates.

## Verified platform access constraints

- X provides an official authenticated-user Bookmarks API; commercial eligibility, cost and quotas require separate validation. https://docs.x.com/x-api/posts/bookmarks/introduction
- YouTube Data API explicitly rejects listing the Watch Later playlist (`watchLaterNotAccessible`). Do not promise OAuth-based Watch Later sync. https://developers.google.com/youtube/v3/docs/playlistItems/list
- TikTok's Data Portability API supports EEA/UK users, not Japanese users at present. Its full export schema includes favorite-video references. This is distinct from the Display API for users' own public posts and the restricted Research API. https://developers.tiktok.com/products/data-portability-api/ and https://developers.tiktok.com/docs/en/data-portability-data-types
- Stashr's desktop imports depend on supported platform browser sessions. Its documentation notes a Reddit saved-list cap of approximately 1,000 items. https://stashr.me/docs/importing-your-saves

## Competitor price correction

Karakeep's official pricing page currently lists **50 free bookmarks**, not 10 as previously reported. Pro remains $4/month or $40/year. The date of this change has not been established. https://karakeep.app/pricing/

Raindrop Free still provides unlimited bookmarks and import/export. https://raindrop.io/pro/buy

## Design implications

1. Maintain a per-source Connector Capability Registry: platform, capture method, permissions, geographic availability, completeness, freshness, sync health, last verification date.
2. Keep saved-on-source, imported-to-Found, user-confirmed intent, observed outcome, and inferred preference separate.
3. Prioritize Share Extension, durable capture, visual cards, category/source browsing, and reliable search. Automatic native-save sync is conditional, not a universal P0 promise.
4. Treat Karakeep as a disposable comparison baseline, not an automatic replacement for Memory OS architecture.
5. Validate Saved→Did→Liked with minimal manual effort and measured improvement to retrieval and decisions. Do not assume it is a competitive moat.
6. Require import/export field fidelity and data minimization; avoid collecting unrelated private archive fields.

## Next tests

- 40–60 mixed-source capture and retrieval tasks across iPhone and desktop, with source-app recovery and Search Success@3.
- Platform-by-platform API/permission/cost matrix, prioritizing Japan eligibility.
- Existing product baseline vs Memories-linked prototype on choice quality and user effort.
- Paid switching experiment against Raindrop Free and Karakeep Cloud.

Decision: **no standalone Found build yet**; pursue evidence and connector feasibility first.
