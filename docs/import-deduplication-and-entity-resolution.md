# Import Deduplication and Entity Resolution Design

## 目的

この文書は、Memory OS が何十年もImportを続けても、同じ情報を無限に増やさず、かつ危険な自動統合で人生文脈を壊さないためのDedup / Entity Resolution設計である。

対象:

- 同じファイルを2回Import
- 同じ履歴を再ExportしてImport
- SpotifyとLast.fmの同じ再生
- Netflix CSVとFilmarksの同じ映画
- Filmarksと手入力の同じ映画
- 食べログURLと手入力の同じ店
- 漫画アプリと購入メールの同じ巻
- 削除したものを再Importした時の復活防止

## 最重要原則

### 1. Dedup is not deletion

重複検出は、データ削除ではない。

安全に同一と分かるものは同じactivityへlinkする。

曖昧なものはmatch candidateとして残す。

### 2. Never merge by AI feeling

AIが「似ている気がする」だけで統合しない。

統合には、外部ID、安定key、タイトル/作者/日付/URLなどの根拠が必要。

### 3. Source item remains durable

同じactivityに紐づいても、source_itemは残す。

なぜなら出典が違うから。

### 4. User-confirmed merge is a first-class record

ユーザーが「同じ」と判断したmergeは、merge_decisionとして保存する。

後で解除できるようにする。

### 5. Deleted means do not resurrect

削除済みのkeyに一致したものは、再Import時に既定除外する。

## Dedupe Layers

```ts
type DedupeLayer =
  | 'import_job'
  | 'raw_file'
  | 'source_native_item'
  | 'canonical_activity'
  | 'canonical_item'
  | 'semantic_memory';
```

## Layer 1: Import Job Dedupe

Goal:

- same operation retry does not duplicate work.

Key input:

- user_id
- input_kind
- input_payload_hash
- parser_id
- parser_version
- selected_scope_hash

Example:

```txt
同じNetflix CSVを同じscopeで2回Import
→ 既存Import Preview/Resultを再利用
```

Action:

- exact duplicate: return existing import job result.
- same file different selected scope: allow new import job.

## Layer 2: Raw File Dedupe

Goal:

- same uploaded object is not stored multiple times.

Key:

```txt
user_id + sha256(file bytes)
```

Action:

- reuse raw_object_ref if retention policy allows.
- do not assume same file means same consent.
- new ImportJob can point to existing raw object.

## Layer 3: Source Native Item Dedupe

Goal:

- source-provided stable IDs prevent duplicates.

Examples:

### Spotify

```txt
user_id + spotify_account_hash + track_id + played_at
```

### Last.fm

```txt
user_id + lastfm_username_hash + artist + track + uts_timestamp
```

### X

```txt
user_id + x_account_hash + tweet_id + relation_type
```

### YouTube

```txt
user_id + youtube_account_hash + video_id + watched_at
```

### Netflix

Netflix CSV may not include stable external IDs.

Use:

```txt
user_id + netflix_profile_hash + normalized_title + watched_date
```

### LINE

Use conservative key:

```txt
user_id + source_ref_id + timestamp + speaker_direction + content_hash
```

Never dedupe LINE across unrelated chats by text alone.

## Layer 4: Canonical Activity Dedupe

Goal:

- same user activity imported from different places.

Examples:

- Netflix watched movie + Filmarks watched movie
- Filmarks watched movie + manual movie memory
- Spotify track + Last.fm scrobble
- 食べログ restaurant URL + manual visited restaurant

Canonical Activity Key:

```ts
interface CanonicalActivityKey {
  userId: string;
  domain: string;
  activityType: string;
  canonicalItemId?: string;
  normalizedTitle?: string;
  normalizedCreator?: string;
  occurredDateBucket?: string;
  progressBucket?: string;
  sourceReliabilityHint?: string;
}
```

Confidence rules:

### High confidence

Auto-link to same user_activity when:

- same external ID and same activity timestamp/date, or
- same canonical_item_id + same activity_type + same exact date, or
- same URL normalized + same user activity type.

### Medium confidence

Create match candidate when:

- same title + same year + date close, but no external ID.
- same restaurant name + area, but no URL.
- same song title + artist + time within window from two services.

### Low confidence

Keep separate when:

- title only.
- no date.
- common title.
- different creators.
- same restaurant chain but different branch.
- same anime/manga title but different season/version.

## Layer 5: Canonical Item Entity Resolution

Goal:

- identify same work/place/show/book/track across services.

Order of trust:

1. same authoritative external ID
2. same provider canonical URL
3. same normalized title + creator + release year
4. same normalized title + strong metadata match
5. trigram candidate + user confirmation

Examples:

### Movies

Prefer:

- TMDb ID
- IMDb ID if available
- title + year + director/cast optional

### Anime / Manga

Prefer:

- AniList ID
- MAL ID
- title aliases + start year + format

### Music

Prefer:

- ISRC if available
- Spotify track ID
- MusicBrainz recording ID
- title + artist + album duration

### Restaurant

Prefer:

- 食べログ URL
- Google Maps/place ID if user adds later
- normalized name + area + branch

### Book

Prefer:

- ISBN
- NDL/Open Library/Google Books IDs
- title + author + publisher/year

## Layer 6: Semantic Memory Near-Duplicate

Goal:

- avoid duplicate user-facing memory records.

Do not auto-merge.

Examples:

- “Netflixで作品Aを見た”
- “Filmarksに作品Aを記録した”
- “作品Aを見て感想を書いた”

These may be related but not identical.

Action:

- suggest related records.
- allow user to merge/keep separate.
- preserve all source links.

## Normalization Rules

### Text normalization

- trim whitespace
- Unicode normalize NFKC for keys
- lowercase where language-safe
- remove common decorative punctuation
- collapse spaces
- keep original title separately

### URL normalization

- lowercase host
- remove fragment
- remove safe tracking params
- normalize trailing slash
- do not remove query params blindly for services where query identifies content

### Time normalization

Keep original time fields.

Derive buckets:

- exact timestamp
- date bucket
- month bucket
- unknown

Never overwrite original occurred_at.

### Title aliasing

Use alias table rather than overwriting.

```txt
canonical_item_title_alias
```

## Tables

### dedupe_key

Global active key registry.

Used for exact/high confidence uniqueness.

### entity_match_candidate

Stores potential matches for user/system review.

```sql
create table entity_match_candidate (
  id uuid primary key,
  user_id uuid not null,
  candidate_type text not null,
  left_table text not null,
  left_id uuid not null,
  right_table text not null,
  right_id uuid not null,
  score numeric not null,
  reasons jsonb not null default '[]'::jsonb,
  status text not null default 'pending',
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);
```

### merge_decision

Stores user/system-confirmed merge decisions.

```sql
create table merge_decision (
  id uuid primary key,
  user_id uuid not null,
  merge_type text not null,
  survivor_table text not null,
  survivor_id uuid not null,
  merged_table text not null,
  merged_id uuid not null,
  decided_by text not null,
  decision_reason text,
  reversible boolean not null default true,
  created_at timestamptz not null default now(),
  undone_at timestamptz
);
```

### canonical_item_alias

```sql
create table canonical_item_alias (
  id uuid primary key,
  canonical_item_id uuid not null,
  alias_type text not null,
  alias_value text not null,
  normalized_alias_key text not null,
  source_ref_id uuid,
  confidence import_confidence not null default 'medium',
  created_at timestamptz not null default now()
);
```

## Re-import Resurrection Guard

When source_item candidate is parsed:

1. generate dedupe keys.
2. check deletion_tombstone.
3. if tombstone match:
   - mark candidate as previously_deleted.
   - selected=false by default.
   - require explicit user action to restore.

UX copy:

```txt
この候補は以前削除した記録と一致する可能性があります。
既定では保存しません。
```

Do not say:

```txt
削除した大切な記憶を復元しますか？
```

## Exact vs Candidate Decision Matrix

| Case | Action |
|---|---|
| same import job key | return existing job |
| same file hash | reuse object, new scope allowed |
| same source native key | link or skip duplicate source_item |
| same canonical item + exact date/activity | link to same user_activity |
| same title/date but no external ID | candidate |
| same title only | separate |
| same semantic summary | related, no merge |
| deleted tombstone match | exclude by default |

## Cost Protection

Dedup reduces:

- source_item count
- search_document count
- embedding count
- export size
- timeline clutter

But over-aggressive merge causes data loss.

Memory OS chooses:

```txt
safe exact dedupe automatically
ambiguous dedupe as suggestion
semantic merge only with user confirmation
```

## Tests

P0 tests:

1. same Netflix CSV imported twice does not duplicate activities.
2. same file with different scope creates new job but reuses raw object.
3. Spotify and Last.fm same track/time create one activity with two source links when high confidence.
4. same movie title without year/date remains separate or candidate.
5. same restaurant chain different branch remains separate.
6. deleted source item is excluded on re-import.
7. hidden/sealed records are not used to auto-create public search docs.
8. semantic near-duplicates are not auto-merged.
9. user-confirmed merge can be undone.
10. dedupe logs contain no raw private content.

## 結論

Memory OSの重複排除は、単純なunique制約ではなく、source-aware / activity-aware / entity-aware / user-confirmed の多層設計にする。

安全に同一と分かるものだけ自動linkする。

曖昧なものはcandidateにする。

削除済みのものは再Importで復活させない。

これにより、何十年分のImportが増えても、同じ情報でDB・検索・embedding・Exportが膨らむことを防げる。
