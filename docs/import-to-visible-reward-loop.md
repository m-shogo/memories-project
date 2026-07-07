# Import to Visible Reward Loop

## 目的

この文書は、Import機能を「データを入れる処理」ではなく、「入れた瞬間にワクワクが見える体験」として設計する。

Memory OSは、Importできるだけでは弱い。

Importしたくなる理由、Import後に見える報酬、週1で戻る理由までつながって初めて、良い依存性になる。

## Core Loop

```txt
Empty Shelf
→ Import Prompt
→ Preview
→ Visible Reward
→ Weekly Hook
→ Next Import Suggestion
```

このloopをすべての媒体に持たせる。

## Loop Contract

```ts
interface ImportVisibleRewardLoop {
  medium: ImportMedium;
  emptyState: string;
  importPrompt: string;
  previewPromise: string[];
  postImportReward: VisibleRewardType[];
  weeklyHook: string;
  dailyMicroAction?: string;
  nextImportSuggestion?: string;
}
```

## Universal Title List

Empty state:

```txt
まだ棚がありません。
タイトルを貼るだけで、最初の棚を作れます。
```

Preview promise:

- タイトル候補
- source未確定
- media type選択

Visible reward:

- new_shelf_created
- collection_stack

Weekly hook:

```txt
今週は1つだけ棚に追加できます。
```

## URL Clip

Empty state:

```txt
URLを貼るだけで、映画・店・音楽・記事の候補に分けられます。
```

Preview promise:

- URL host
- service candidate
- unsafe URL blocked

Visible reward:

- cross_source_link_found
- new_shelf_created
- map_region_added if restaurant

Weekly hook:

```txt
行きたい店や見たい作品を1つだけ足せます。
```

## Streaming Watch Activity

Empty state:

```txt
視聴棚はまだ空です。
NetflixやPrime Videoの履歴を入れると、見た作品の年表ができます。
```

Preview promise:

- watched count
- date range
- duplicate candidates
- shared profile warning

Visible reward:

- new_shelf_created
- timeline_unlocked
- duplicate_cleaned

Post-import copy:

```txt
視聴棚ができました。
4年分の作品を時期ごとに見返せます。
```

Weekly hook:

```txt
去年の今ごろ見ていた作品を1つ開けます。
```

Next suggestion:

```txt
Filmarksを足すと、見たい作品や評価も同じ棚に並べられます。
```

## Movie Activity

Empty state:

```txt
映画棚はまだ空です。
Filmarksや映画メモを入れると、自分の映画史が見えます。
```

Visible reward:

- shelf_filled
- timeline_unlocked
- cross_source_link_found

Weekly hook:

```txt
見たい映画を1つだけ追加できます。
```

## Manga / Anime Progress

Empty state:

```txt
漫画/アニメ棚はまだ空です。
「12巻まで」「7話まで」のように貼るだけで進行表ができます。
```

Preview promise:

- title
- media type
- volume/episode/chapter progress
- status

Visible reward:

- progress_track_created
- shelf_filled

Post-import copy:

```txt
進行棚ができました。
途中の作品と完了した作品を分けて見られます。
```

Weekly hook:

```txt
1作品だけ進行を更新できます。
```

Daily micro-action:

```txt
巻数を1つ更新する
```

This is likely one of the strongest early loops because it is useful immediately.

## Music Listening Activity

Empty state:

```txt
音楽棚はまだ空です。
Apple Music / Spotify / Last.fm / プレイリストから、この時期の音楽を残せます。
```

Preview promise:

- tracks/artists/playlists
- recent/private flags
- AI analysis off

Visible reward:

- timeline_unlocked
- collection_stack
- cross_source_link_found

Weekly hook:

```txt
最近よく聴いた曲を1つ棚に残せます。
```

Safe discovery:

```txt
この時期によく記録されていた曲です。
```

## Audio / Radio Activity

Empty state:

```txt
ラジオ/Podcast棚はまだ空です。
番組名やURLを貼ると、聴いた回・聴きたい回を並べられます。
```

Visible reward:

- new_shelf_created
- collection_stack

Weekly hook:

```txt
今週聴きたい回を1つ入れられます。
```

## Restaurant / Food Activity

Empty state:

```txt
食の地図はまだ空です。
食べログURLや店名を貼ると、行きたい店の地図ができます。
```

Preview promise:

- restaurant candidates
- area/genre
- location sensitivity
- companion inference denied

Visible reward:

- map_region_added
- new_shelf_created

Post-import copy:

```txt
食の地図に3件追加されました。
地域別に見返せます。
```

Weekly hook:

```txt
行きたい店を1つだけ追加できます。
```

## Message / Conversation Context

Empty state:

```txt
会話メモ箱はまだ空です。
原文を残さず、安全な要約だけ置けます。
```

Preview promise:

- message count
- date range
- raw hidden
- export excluded

Visible reward:

- weekly_box_closed
- safe_memory_box_created

Weekly hook:

- no proactive sensitive hook.

Allowed user action:

```txt
必要な時だけ、会話メモ箱を開けます。
```

## Image / Media Context

Empty state:

```txt
写真箱はまだ空です。
まずはEXIFを消した安全なメタデータから箱を作れます。
```

Visible reward:

- collection_stack
- year_capsule

Weekly hook:

```txt
この月の写真箱を1つ見られます。
```

No face identity inference.

## Persona-like Context

Empty state:

```txt
創作メモ箱はまだ空です。
キャラ設定やエチュードの記録を、fictionとして保存できます。
```

Visible reward:

- creative_notes_box_created

No weekly dependency hook.

No activation.

## Export Archive Context

Empty state:

```txt
Export確認箱はまだ空です。
Exportファイルを入れると、何が含まれるかを保存前に確認できます。
```

Visible reward:

- export_readiness_improved

Weekly hook:

```txt
Export readinessを1つ確認できます。
```

## Reward Mapping Table

| Parser/Adapter | Visible reward | Weekly hook |
|---|---|---|
| title-list-parser | first shelf created | 1つ追加 |
| url-list-parser | service candidates / map/list | 1 URL追加 |
| netflix-csv-parser | viewing timeline | 去年の今ごろ |
| manga-progress-parser | progress tracker | 1作品更新 |
| tabelog-url-parser | food map | 行きたい店追加 |
| gera-episode-parser | audio shelf | 聴きたい回追加 |
| line-snippet-parser | safe memo box | user-requested only |
| image-metadata-parser | photo box | month box view |
| persona-detector | creative notes box | no dependency hook |
| export-manifest-parser | export readiness | backup readiness |

## Implementation Rule

Every Import MVP ticket must output:

```txt
Preview Promise
Visible Reward
Weekly Hook
Next Import Suggestion
```

If a medium cannot safely have a weekly hook, it must explicitly say:

```txt
No proactive weekly hook because sensitive.
```

## P0 Tests

1. Empty state tells what appears after import.
2. Preview tells what shelf will be created.
3. Post-import reward is domain-specific, not generic count only.
4. Sensitive imports do not create proactive hooks.
5. Every MVP parser has a visible reward mapping.
6. Weekly hook never uses guilt/streak/loneliness copy.
7. Next import suggestion is optional and non-coercive.
8. Import-to-visible-reward demo works with synthetic fixture.
9. UI can show before/after for at least 3 media categories.
10. Developer ticket cannot close without visible reward note.

## 結論

Importは裏側の処理ではない。

Memory OSの楽しさは、Importによって棚・地図・年表・進行表が見える瞬間にある。

この見える報酬を作ることで、ユーザーも作成者も先を見られる。
