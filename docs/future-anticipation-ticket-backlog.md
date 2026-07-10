# Future Anticipation Ticket Backlog

## 目的

`docs/future-anticipation-and-following-spec.md` を実装可能なticketへ分解する。

最初は漫画だけ。

## P1-A Domain

### FUT-A-001 Follow State

Add:

- follow_state
- continuation_state
- muted_at
- notification_mode

Acceptance:

- series単位でfollow/unfollowできる。
- creator followはP2までUI非表示。
- default notification modeはin_app_only。

### FUT-A-002 Series / Volume Identity

Add:

- series identity
- volume identity
- edition
- release region
- paper/digital distinction

Acceptance:

- 再版を新刊と誤判定しない。
- 同名作品を別seriesとして扱える。
- 巻番号不明を許容する。

### FUT-A-003 Release Event

Add:

- release_event
- source name/url
- checked_at
- scheduled/released/delayed/cancelled/unknown

Acceptance:

- sourceなしeventを公開しない。
- checked_atをUIに出せる。
- 延期・中止更新を保持する。

## P1-B UI

### FUT-B-001 Follow Toggle on Manga Shelf

Screen:

- Manga/Anime shelf detail

UI:

```txt
この作品を追う
続刊待ち
通知方法
```

Acceptance:

- 1tapでfollow/unfollow。
- destructive confirmation不要。
- muteとunfollowを区別する。

### FUT-B-002 Continuation Status Chip

Chips:

- 進行中
- 続刊待ち
- 完了
- 保留

Acceptance:

- user can override.
- system does not auto-complete.

### FUT-B-003 Next Release Card

Example:

```txt
次巻
2026年9月4日予定
情報源を見る
```

Acceptance:

- “予定”を必ず明示。
- source visible。
- unknown dateを表現できる。

### FUT-B-004 Future Enjoyment Box

Screen:

- 振り返り or future tab section

MVP content:

- next month manga releases
- followed manga only
- want-to items count

Acceptance:

- AI recommendationなし。
- empty stateは通知を促さない。

### FUT-B-005 Release Calendar

Views:

- 今月
- 来月
- 未定

Acceptance:

- delayed/cancelled visible。
- region/edition filter possible。

## P1-C Actions

### FUT-C-001 One-tap Shelf Update

Actions from released event:

- 見たいに追加
- 読了に更新
- 今回は追わない

Acceptance:

- action history recorded。
- no auto purchase link in MVP。

### FUT-C-002 Weekly Follow Digest

Content:

- 1〜5 release events
- followed series only

Acceptance:

- duplicate suppression。
- app card first。
- notification opt-in only。

### FUT-C-003 Event Cooldown / Dedupe

Acceptance:

- same source event not repeated。
- changed date creates update, not duplicate。
- postponed event supersedes prior schedule。

## P1-D Data Provider Spike

### FUT-D-001 Manga Release Provider Review

Research:

- official publisher feeds/pages
- ISBN/book catalog APIs
- retailer data terms
- Japanese release coverage
- rate limits
- commercial use

Deliverable:

- provider comparison
- terms/cost/risk
- source reliability grading

No-Go:

- unauthorized scraping
- hidden login scraping
- one retailer as unverified source of truth

### FUT-D-002 Synthetic Fixture Set

Fixtures:

- scheduled next volume
- delayed volume
- cancelled edition
- paper/digital different dates
- same-title different series
- unknown date
- duplicate source reports

Acceptance:

- all P1 tests run without external API。

## P2

- anime next season
- podcast new episode
- movie streaming availability
- creator follow
- explainable discovery
- game release / major update

## Explicitly Not Included

- generic recommendation feed
- sponsored recommendation
- all-title auto-follow
- default push notifications
- personality-based recommendation
- purchase affiliate links in MVP

## Suggested Order

```txt
FUT-A-001
→ FUT-A-002
→ FUT-A-003
→ FUT-D-002
→ FUT-B-001
→ FUT-B-002
→ FUT-B-003
→ FUT-C-001
→ FUT-B-004
→ FUT-B-005
→ FUT-C-003
→ FUT-C-002
→ FUT-D-001 before production data
```

## Definition of Done

The P1 slice is complete when:

```txt
追跡中の漫画
→ 次巻予定がsource付きで見える
→ 延期更新を扱える
→ 発売後に見たい/読了へ更新できる
→ 来月の楽しみ箱へ出る
→ 通知なしでもアプリ内で確認できる
```
