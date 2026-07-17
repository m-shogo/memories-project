# Concrete MVP Product Scope

最終更新: 2026-07-17

This document defines the user-facing MVP scope. It does not authorize implementation ahead of the security and backend gates in:

1. `docs/memory-os-current-authority-order-round-9-security.md`
2. `docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md`
3. `docs/current-product-direction.md`

---

# MVP product promise

```txt
タイトル、URL、進行、短いメモを軽く入れる
→ 保存前にPreviewできる
→ 自分の棚・地図・進行として見える
→ 後から検索、修正、更新、Exportできる
→ optionalに記憶の町へ反映される
```

The MVP is successful only when Capture / Preview / Apply / retrieval / correction / export are trustworthy. Town polish cannot substitute for those capabilities.

---

# MVP platform scope

```txt
canonical client:
iOS native app

primary intake:
Share Extension URL / text
Files / fileImporter
manual Quick Add

bulk migration support:
limited Desktop Import Portal

canonical processing:
Go backend

Town:
static/limited SpriteKit view only after backend P0 gates
```

The initial MVP does not require a public web application, Android client, social account graph or cross-device Town editor.

---

# Navigation

The navigation labels are candidates until the native prototype is tested.

Preferred information architecture:

```txt
ホーム / 棚
振り返り
追加
町
```

Search must be available from Home/Shelf without entering Town.

“Discovery” is not a mandatory standalone tab. Confirmed relations and recent additions may appear within shelves, reflection and search. A separate Discovery tab is added only if testing shows a clear user need.

---

# 1. Add and intake

## 1.1 Quick Add

One lightweight input surface accepts:

```txt
SPY×FAMILY 12巻まで
葬送のフリーレン 8話まで
https://tabelog.com/...
PERFECT DAYS 見た
鎌倉のカレー屋 行きたい
```

Primary actions:

```txt
貼り付け
ファイルを選ぶ
Previewを見る
```

No silent final save. All import paths enter Preview before Apply.

## 1.2 Share Extension

P0 accepted share inputs:

- one URL;
- selected text;
- optional user-entered short title/note;
- minimal source application metadata that is safe and available.

The extension stores only the minimal App Group intake envelope required to resume in the main app. Secrets remain in Keychain. Large parsing, network retries and final Apply do not run inside the extension.

## 1.3 Files intake

P0 file intake supports bounded staged input such as Generic CSV. The app sends declared metadata and obtains server authorization; the server remains authority for owner, epoch, object key and storage version.

ZIP/archive import is not required for the first public vertical slice even if safety contracts already exist.

---

# 2. Import Preview

Preview shows exactly what will be applied and what was rejected.

Header:

```txt
検出形式
source
accepted count
rejected count
warnings
保存先候補
expiry
```

Candidate rows may show:

```txt
title
medium/type
source label/date
status/progress
warnings
duplicate candidate indication
```

User actions:

```txt
保存対象から外す
タイトル修正
棚を変更
進行値を修正
重複候補を見る
```

Safe rejected-row report shows only row number and stable issue codes/messages. It never displays raw rejected cells recovered from a server report.

Final Apply requires exact Preview ID and hash and occurs only with iOS user authority.

## Save result

Show factual accounting:

```txt
追加 N件
更新 N件
スキップ N件
拒否 N件
```

Created + updated + skipped must account for every accepted Preview candidate. A partial result is not displayed as success.

Actions:

```txt
棚を見る
続けて追加
閉じる
```

Optional Town reaction comes after the save result and never replaces it.

---

# 3. Home and shelves

Home is a practical shelf entry, not a life dashboard.

P0 shelves:

1. 漫画・アニメ
2. 映画・視聴
3. 食 / 行きたい場所
4. あとで見る
5. 未整理Inbox

Do not fill Home with unreleased placeholders.

A shelf card may show:

```txt
title
item count
recent change
pending count
one practical action
```

Home does not show:

- life score;
- happiness or personality assessment;
- daily completion rate;
- streak;
- missed-day guilt copy;
- large statistical dashboards.

## 3.1 Manga / anime progress

Supported units:

```txt
volume
episode
chapter
```

Status:

```txt
planned
in_progress
completed
paused
```

Actions:

```txt
+1
直接変更
完了
保留
sourceを見る
```

No cross-category “completion percentage” or daily target.

## 3.2 Movie / viewing shelf

Status:

```txt
watched
want_to_watch
favorite
```

Optional user rating/note may be stored, but public reviews, social feed and personality analysis are not MVP features.

## 3.3 Food / place list

A map SDK is not required for the first slice. Start with region-grouped lists.

Store:

```txt
name
region
want_to_go / visited
favorite
source URL
optional user note
```

Companion, exact visit timestamp and precise GPS are not mandatory.

## 3.4 Inbox

Inbox holds items the user or deterministic parser has not assigned.

Actions:

```txt
棚へ移す
タイトル修正
source確認
削除
保留
```

The product does not demand bulk cleanup.

---

# 4. Search and correction

P0 search covers title, safe normalized text, shelf/type and user-confirmed metadata.

Users can:

- find saved items;
- open source evidence;
- edit title/status/progress/note;
- move an item between compatible shelves;
- delete records;
- inspect revision history where required by contract;
- export selected or complete data.

Search results do not expose hidden/sealed/restricted records outside their authorization context.

---

# 5. Reflection

P0 reflection is factual and optional.

Month view may show:

```txt
漫画・アニメ 3件更新
映画 2件追加
食 4件追加
未整理Inbox 1件
```

It does not infer “best month”, happiness, relationship quality or life importance.

Weekly Box/Month Capsule can be empty without guilt copy or a forced action.

---

# 6. Confirmed connections

Only explainable, evidence-backed relationships are shown, such as:

- same stable external ID;
- same normalized title plus year/creator;
- same restaurant name plus region;
- same source-native item;
- explicit user confirmation.

Candidate links are not silently promoted to facts. Users can reject or unlink them.

A graph/constellation visualization is post-MVP unless simple list/card relations prove insufficient.

---

# 7. Export and deletion

MVP includes:

- standard structured export;
- source/provenance fields where safe;
- user-readable archive/index;
- account deletion request and status;
- deletion fencing of new writes;
- no hidden dependency on Town state.

Export and deletion do not require visiting Town.

---

# 8. Memory Town MVP

Town is optional and follows the practical save experience.

Minimum Town slice after backend P0:

- fixed-view static scene;
- small set of feature-bound buildings;
- morning/day/night/midnight presentation;
- optional ambient motion;
- building tap opens corresponding practical shelf;
- Town OFF/static/list accessibility equivalents;
- no editor, economy, rewards or progression pressure.

Town growth uses neutral confirmed aggregates and excludes duplicates, filler and generated fake records.

---

# 9. Explicit MVP exclusions

- Chat assistant/LLM replacement
- AI partner/family/deceased simulation
- automatic personality/happiness/importance scoring
- public profiles, followers, comments or public Town feed
- recommendations optimized around advertising
- login rewards, streaks, daily quests
- currency, crafting, loot/gacha
- Town decay or care obligations
- ranking or competitive placement scores
- mandatory precise GPS/companions/relationship fields
- full archive migration as first-run requirement
- browser final Apply authority
- Android and multi-user Town
- Town editor and real-time collaborative layout

---

# 10. MVP implementation gate

The feature scope above is not the current coding order.

Before iOS product implementation expands, backend P0 must prove:

```txt
private version-bound upload
isolated bounded parse
verified Preview spool
short atomic Preview commit
exact-hash idempotent Apply
cross-user and stale-epoch denial
deletion fencing and cleanup
current local/remote validation evidence
```

Current production verdict remains `NO-GO`.
