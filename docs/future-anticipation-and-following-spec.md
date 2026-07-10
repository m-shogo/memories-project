# Future Anticipation and Following Spec

## 目的

Memory OS に「過去を振り返る」だけでなく、「今追っているものの続き」と「これからの楽しみ」を持たせる。

ただし、一般的なおすすめアプリにはしない。

```txt
過去: 振り返り
現在: 棚と進行
未来: 続き・発売予定・行きたい場所
```

この3層をつなぐ。

## 採用判断

### 採用

- ユーザーが明示的に追っている作品の新刊・新話・新シーズン
- 見たい映画の配信開始
- 追っている作者・監督・番組の新作
- 続刊待ち / 新シーズン待ち / 配信待ち状態
- 発売日カレンダー
- 未来の楽しみ箱
- 週1の新着まとめ
- 発売情報からワンタップで棚更新

### 後回し

- 一般的な「あなたにおすすめ」
- AIが曖昧な好み分析から選ぶ作品
- 広告・スポンサー混在推薦
- 全ジャンル同時対応

## Core Principle

```txt
おすすめするのではなく、ユーザーが既に選んだ興味の続きを支える。
```

## P1 First Vertical Slice

最初は漫画だけ対応する。

```txt
漫画棚
→ この作品を追う
→ 次巻情報を取得
→ 週1新着まとめ
→ 発売日カレンダー
→ 見たい / 読了 / 今回は追わない
```

漫画を最初にする理由:

- 巻単位で構造化しやすい
- 続き待ちが明確
- 進行棚と自然につながる
- 発売通知の価値が分かりやすい
- ユーザー操作も軽い

## User-facing States

```ts
type FollowState =
  | 'not_following'
  | 'following_series'
  | 'following_creator'
  | 'paused'
  | 'muted';

type ContinuationState =
  | 'in_progress'
  | 'waiting_next_volume'
  | 'waiting_next_season'
  | 'waiting_streaming'
  | 'completed'
  | 'on_hold';
```

## Manga Shelf UI

棚詳細に追加:

```txt
この作品を追う
続刊待ち
次巻予定
通知方法
```

Example:

```txt
SPY×FAMILY
12巻まで読了
続刊待ち
次巻: 2026年9月4日予定
```

Actions:

```txt
見たいに追加
読了に更新
今回は追わない
通知をオフ
```

## Future Enjoyment Box

月単位で未来の予定をまとめる。

Example:

```txt
8月の楽しみ

新刊 2冊
新シーズン 1作品
配信開始 1作品
行きたい店 3件
```

表示対象:

- 明示的に追跡中の作品
- user-created want-to list
- 行きたい店
- 旅行・イベント箱

表示しない:

- AIが勝手に推測した興味
- sponsored content
- sensitive/private relationship events

## Release Calendar

Calendar views:

- 今月
- 来月
- 未定

Event fields:

```ts
interface ReleaseEvent {
  id: string;
  itemId: string;
  seriesId?: string;
  creatorId?: string;
  eventType:
    | 'volume_release'
    | 'episode_release'
    | 'season_start'
    | 'streaming_start'
    | 'book_release'
    | 'game_release'
    | 'major_update';
  scheduledAt?: string;
  status: 'scheduled' | 'released' | 'delayed' | 'cancelled' | 'unknown';
  sourceUrl: string;
  sourceName: string;
  checkedAt: string;
  region?: string;
  edition?: string;
}
```

## Notification Policy

Default:

```txt
アプリ内のみ
```

Options:

```txt
アプリ内のみ
週1でまとめる
重要な作品だけ即時
すべて通知しない
```

初期値は `アプリ内のみ`。

即時通知は作品ごとのopt-in。

## Weekly Follow Digest

Example:

```txt
棚の新着

漫画の新刊 2件
新しいPodcast 3件
見たい映画の配信開始 1件
```

Rules:

- 1〜5件だけ
- 同じ作品を繰り返さない
- 延期・中止は事実として表示
- ネタバレ禁止
- promotional copy禁止

## Explainable Discovery

P2では発見画面に任意機能として追加できる。

Allowed reasons:

```txt
同じ作者
同じシリーズ
続編
同じ監督
同じ原作
```

Not allowed as first implementation:

```txt
あなたはこういう性格だから好きそう
最近落ち込んでいるからおすすめ
```

## Data Reliability Requirements

発売情報は変わるため、必ず持つ。

- source URL
- source name
- checked_at
- scheduled / delayed / cancelled
- region
- paper / digital / edition
- official / secondary source distinction

UI copy:

```txt
2026年9月4日予定
```

確定できない場合:

```txt
発売時期未定
```

## Anti-patterns

- 全作品を自動追跡
- 全通知ON
- 一般推薦をHome上部に出す
- sponsored contentを混ぜる
- 発売日を断定し、sourceを出さない
- 再版を新刊扱いする
- 地域差を無視する
- 電子版・紙版を同一扱いする
- AI好み診断を使う

## Success Metrics

Primary:

- follow opt-in率
- release event open率
- release eventから棚更新した率
- future enjoyment box閲覧率
- mute率
- notification opt-out率

Do not optimize for:

- notification count
- daily open streak
- total time spent

## P1 Acceptance Tests

1. 漫画棚から作品を追跡できる。
2. 追跡は作品単位で解除できる。
3. 次巻情報にsourceとchecked_atがある。
4. 発売延期・中止を表示できる。
5. 紙・電子・地域差を区別できる。
6. 初期通知はアプリ内のみ。
7. 新着から見たい/読了へ更新できる。
8. 同じeventを重複通知しない。
9. ネタバレを含まない。
10. AI推薦なしでも成立する。

## 結論

Memory OS は一般的なおすすめアプリにはしない。

ユーザーが自分で選んだ棚の続きを支え、未来の楽しみを静かにまとめる。

```txt
自分の記憶
→ 今の興味
→ 次の楽しみ
```

これをP1の正式機能として採用する。
