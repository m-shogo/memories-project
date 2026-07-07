# Pre-implementation Go / No-Go Review

## 目的

この文書は、Memory OS が設計フェーズから実装フェーズへ移る前に、何がGoで何がNo-Goかを判定する最終レビューである。

実装開始の勢いで、安全・DB・Import・Export・OAuth・RLS・fixtureを飛ばさないために使う。

## Current Verdict

```txt
ready_with_known_risks
```

意味:

- 設計の骨格は強い。
- 実装に入る順番も決まっている。
- ただし、最初に作る対象を間違えると壊れる。
- いきなりAPI connectorやmemory_record保存やembeddingに入ってはいけない。

## Go / No-Go Summary

### Go: 設計上進めてよい

- synthetic fixture計画
- first migration slice設計
- RLS negative tests設計
- Import Preview-only prototype設計
- Universal Paste Import設計
- Parser Registry設計
- Source Adapter interface設計
- Dedupe/Tombstone設計
- Token/OAuth encryption設計
- Policy P0-001〜P0-040

### No-Go: まだ実装してはいけない

- full API connector
- LINE bulk raw import
- Importから直接memory_record保存
- Import時の全件embedding
- Export package実装
- raw永久保存
- service scraping
- vector DB source of truth
- Graph DB source of truth
- all-in-one memories JSON table

## First Implementation Path

実装開始時の正しい順番:

```txt
1. Create synthetic fixtures
2. Implement first migration slice
3. Implement RLS policies + negative tests
4. Implement SecurityGate
5. Implement Universal Paste Parser
6. Implement Import Preview-only prototype
7. Implement Dedupe/Tombstone checks in preview
8. Implement Safe Commit for low-risk manual/paste only
9. Implement Browser Bookmark parser
10. Implement Netflix CSV parser
11. Implement LINE text parser summary-only
12. Only then consider API connectors
```

## Step 1: Synthetic Fixtures

Must create before parser code:

- browser bookmarks normal/private/malicious
- Netflix CSV standard/duplicate/shared profile
- LINE export/copy/deleted reimport
- X archive minimal/likes sensitive
- Filmarks paste/url
- 食べログ url/list/reservation
- Podcast OPML/RSS
- GERA list/url
- manga/anime progress
- Spotify paste/API sample
- Apple Music paste/export sample
- YouTube Takeout sample
- security fixtures
- dedupe fixtures
- tombstone fixtures

Go if:

- fixture contains synthetic data only.
- expected detection/preview/policy snapshots exist.

No-Go if:

- real personal data is used.
- raw private titles appear in snapshots.

## Step 2: First Migration Slice

Create only foundation tables:

```txt
app_user
source_ref
source_account_ref
import_job
import_input_file
import_detection_result
import_preview
import_preview_candidate
raw_object_ref
dedupe_key
deletion_tombstone
policy_decision
lifecycle_event
audit_event
outbox_event
key_reference
oauth_connection
```

Go if:

- RLS policies are planned.
- key_version/key_algorithm columns exist for dedupe/tombstone.
- raw object retention/expiry columns exist.

No-Go if:

- memory_record is the first central table.
- dedupe_key/tombstone are skipped.
- token encryption is postponed but OAuth table is created insecurely.

## Step 3: RLS Negative Tests

Go if:

- cross-user read denied.
- missing app.current_user_id fails closed.
- support role cannot read raw/private titles.
- app runtime role is not table owner.

No-Go if:

- tests only cover happy path.
- support/admin can see raw by default.

## Step 4: SecurityGate

Must block:

- active content rendering
- unsafe URL schemes
- archive traversal
- oversized paste/file
- XML external entity
- CSV formula execution/re-export risk

Go if:

- malicious fixtures pass safely.

No-Go if:

- raw HTML can be rendered in Preview.
- unsafe URL is stored as normal.

## Step 5: Import Preview-only Prototype

Go if:

- user can paste list/text/url.
- source can be selected.
- parser creates candidates.
- privacy defaults visible.
- no final records saved.

No-Go if:

- preview commits records.
- AI analysis runs on import.
- private titles appear in logs.

## Step 6: Dedupe/Tombstone in Preview

Go if:

- exact duplicates marked.
- deleted tombstone candidates selected=false.
- low-confidence merge becomes candidate only.

No-Go if:

- deleted records are auto-restored.
- low-confidence items are auto-merged.

## Step 7: Safe Commit for Low-risk Manual/Paste

Only after Preview + Policy + Dedupe + Tombstone.

Allowed first save:

- low-risk generic title list
- low-risk manga/anime progress
- low-risk restaurant URL without companion/date precision sensitive fields

Still not allowed first:

- LINE raw
- X likes/bookmarks raw
- private bookmarks raw
- large Takeout
- full streaming history without preview confirmation

## API Connector Gate

API connector may start only after:

- token encryption exists.
- OAuth revocation exists.
- provider scope review exists.
- source_account_ref exists.
- Import Preview exists.
- Policy Evaluation exists.
- API response fixture exists.

Provider order:

1. Spotify
2. AniList
3. Last.fm
4. TMDb catalog enrichment
5. Google Books/Open Library/NDL/Calil catalog enrichment
6. Apple Music research spike
7. X API only if terms/cost review passes

## Export Gate

Export implementation may start only after:

- Export safety ceremony implemented.
- re-auth path exists.
- export staging TTL exists.
- deletion lifecycle/search/export filtering works.
- private/sealed/raw/third-party default exclusions work.

## Embedding Gate

Embedding may start only after:

- search works without embedding.
- policy eligibility exists.
- lifecycle invalidation works.
- input_hash/model_version stored.
- monthly/user budget exists.

No-Go if:

- embedding all source_items on import.
- embedding private raw.
- embedding LINE/DM raw.

## Final No-Go Conditions

Do not start implementation if any are true:

- no fixtures
- no Import Preview
- no dedupe_key
- no deletion_tombstone
- no raw TTL
- no key_reference
- no token encryption plan
- no RLS negative tests
- no Policy P0 tests
- no migration safety checklist
- no rollback plan

## Final Go Conditions

Implementation may begin with Preview-only slice when:

- fixtures exist or are created as first coding step.
- first migration slice is followed.
- RLS negative tests are planned.
- SecurityGate is implemented before parser output reaches UI.
- Import Preview does not save final records.

## Verdict

```txt
Go for implementation preparation and Preview-only prototype.
No-Go for full production Import, API connectors, Export, and Embedding.
```

## 結論

Memory OSは実装に近い。

ただし、最初に作るのはMemory保存機能ではない。

最初に作るのは、fixture、DB foundation、RLS negative tests、SecurityGate、Universal Paste、Import Preview-only prototypeである。

この順番を守れば、長期で壊れにくいMemory OSに進める。
