# Collection Drive and Segmented Motivation

## 目的

この文書は、Memory OSのワクワクを「コレクション魂」から設計する。

老若男女で刺さる入口は違ってよい。

ただし、共通する芯はある。

```txt
集めたい
埋めたい
整えたい
見返したい
増えたことを感じたい
なくしたくない
```

Memory OSは、この人間の自然なコレクション欲を、AI人格ではなく自分の棚・地図・箱・年表へ向ける。

## Core Collection Drives

```ts
type CollectionDrive =
  | 'completion'
  | 'curation'
  | 'progress'
  | 'nostalgia'
  | 'identity_display'
  | 'future_preparation'
  | 'family_legacy'
  | 'travel_map'
  | 'taste_archive'
  | 'life_admin';
```

### completion

埋めたい。

Examples:

- 映画棚の空き
- 食の地図の未登録地域
- 漫画進行の未更新作品
- 年ごとの箱

### curation

自分で選びたい。

Examples:

- 見たい映画リスト
- 行きたい店リスト
- 好きなラジオ回
- 自分だけの棚

### progress

進んでいるのを見たい。

Examples:

- 12巻まで
- 7話まで
- 完了
- あとで見る

### nostalgia

過去を掘りたい。

Examples:

- 去年の今ごろ
- 2020年の棚
- 旅行前後
- 結婚式前後

### identity_display

人に見せたいわけではなく、自分で「自分っぽい」と感じたい。

Examples:

- 自分の映画史
- 自分のラジオ棚
- 自分の食の地図

### future_preparation

未来の自分のために整える。

Examples:

- AIに渡すcontext pack
- 旅行前の店リスト
- 次に読む/見る/聴く

### family_legacy

家族・夫婦・子ども・親との文脈。

Careful:

- third-party rawや未成年はrestricted。
- 家族人格化しない。

### travel_map

場所で埋まる楽しさ。

### taste_archive

趣味棚としての楽しさ。

### life_admin

実用の整理。

- Export readiness
- backup
- 重複整理
- source接続状態

## Segment Design

### Young / Student / Hobby-heavy

刺さるもの:

- 漫画/アニメ進行
- 音楽棚
- 推し/作品棚
- 見たい/読みたいlist
- Year Capsule
- share-safe card

Import hooks:

```txt
今読んでる作品を貼るだけで進行棚ができます。
```

```txt
プレイリストURLから、この時期の音楽棚を作れます。
```

Weekly hook:

```txt
今週、1作品だけ進行を更新できます。
```

Daily micro:

```txt
1話/1巻だけ進める
```

### Busy Working Adult

刺さるもの:

- 食の地図
- 見たい映画/読書/Podcast整理
- 週1の軽い棚更新
- Export/backup安心
- AI context pack

Import hooks:

```txt
食べログURLを貼るだけで、行きたい店の地図ができます。
```

```txt
Podcastやラジオを入れて、移動時間の棚を作れます。
```

Weekly hook:

```txt
週末に行きたい店を1つ追加できます。
```

Daily micro:

```txt
URLを1つ保存する
```

### Couple / Family / Wedding / Life Event

刺さるもの:

- 旅行箱
- 食の地図
- 写真箱
- Life Event Pack
- 結婚式前後の箱
- 夫婦の予定/思い出の安全なmetadata

Careful:

- partner analysis禁止。
- relationship truth inference禁止。
- 写真/会話rawは慎重。

Import hooks:

```txt
旅行前後の店・写真メタデータ・予定を、1つの箱にできます。
```

```txt
結婚式前後の記録を、あとから見返せる箱にできます。
```

Weekly hook:

```txt
旅行箱に、行きたい店を1つ追加できます。
```

### Parent / Household

刺さるもの:

- 家族行事箱
- 写真箱
- 食の記録
- 旅行箱
- 子どもの記録はrestrictedで安全に

Careful:

- minor data restricted。
- proactive tips禁止。
- face/location safety。

Import hooks:

```txt
写真そのものではなく、まず安全なメタデータから月ごとの箱を作れます。
```

### Older Adult / Senior

刺さるもの:

- 写真箱
- 旅行箱
- 家族行事
- 読書/映画/音楽
- Export/backup安心
- 大きな字/簡単操作

Careful:

- 故人再現しない。
- support/admin raw accessなし。

Import hooks:

```txt
昔の旅行や写真を、日付ごとの箱として残せます。
```

```txt
家族に見せる用と、自分だけ用を分けられます。
```

Weekly hook:

```txt
昔の写真箱を1つ開けます。
```

### Power User / Engineer / AI-heavy

刺さるもの:

- Export/Re-import
- API/provider registry
- AI context pack
- schema/version transparency
- source provenance
- local backup

Import hooks:

```txt
AIを乗り換えても使える、自分のcontext packを作れます。
```

Weekly hook:

```txt
Export readinessを1つ確認できます。
```

## Universal Motivators

全層に共通しやすい:

1. 空の棚が埋まる
2. 進行が見える
3. 去年の今ごろが見える
4. 地図が埋まる
5. 1つだけ追加できる
6. Exportできる安心
7. 自分っぽい棚になる
8. 失いたくない蓄積になる

## Segment-specific Entry Points

| Segment | First shelf | First import | First weekly hook |
|---|---|---|---|
| Hobby-heavy | Manga/Anime Progress | progress paste | 1作品更新 |
| Movie fan | Movie Shelf | Filmarks/Netflix | 去年の映画 |
| Food/travel | Food Map | 食べログURL | 行きたい店1つ |
| Music/radio | Music/Audio Shelf | playlist/GERA | 聴きたい回1つ |
| Couple/family | Travel/Life Event Box | restaurant/photo metadata | 旅行箱更新 |
| Senior | Photo/Travel Box | photo metadata/manual | 昔の箱1つ |
| AI-heavy | Context Pack | selected shelves | Export readiness |

## Reward Timing

### Immediate

- shelf created
- count visible
- map/list appears
- progress row appears

### Weekly

- weekly box
- one action
- last year this week
- one correction

### Monthly

- month room snapshot
- new year/month capsule
- shelf growth summary
- export readiness check

### Seasonal / Event

- travel pack
- summer/winter box
- wedding/life event pack
- year capsule

## P0 Tests

1. every segment has at least one safe entry shelf.
2. segment copy does not shame or pressure.
3. family/couple flows do not infer relationship truth.
4. parent/minor flows default restricted.
5. senior/photo flows do not imply deceased simulation.
6. every segment has weekly hook and no streak.
7. every first import shows immediate visible reward.
8. AI-heavy flow exports context without raw unsafe data.
9. share-safe card excludes private/sensitive by default.
10. collection drive never becomes life ranking.

## 結論

Memory OSのワクワクは、全員に同じ顔で出さなくていい。

老若男女で入口は変える。

ただし、共通するのは「自分の棚・地図・箱・年表が埋まる快感」である。

このコレクション魂を、Importしたくなる体験と週1/月1の戻る理由にする。
