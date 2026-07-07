# First Import Fixture Examples

## 目的

この文書は、実装開始時に最初に作るsynthetic fixtureの具体的な中身と、expected detection / preview / policy snapshotの形を定義する。

ここではまだ実fixtureファイルは作らない。

ただし、実装に入ったらこの文書をそのまま `fixtures/import/**` に展開できる状態にする。

## Rules

- 実ユーザーの個人データを使わない。
- 実在の私的URLを使わない。
- token / email address / phone number / real LINE textを使わない。
- adult/private/sensitiveのfixtureも、露骨な本文ではなく synthetic marker で表現する。
- expected snapshotにraw private textを入れない。

## Fixture 1: unsafe-url-schemes.txt

Path:

```txt
fixtures/import/security/unsafe-url-schemes.txt
```

Content:

```txt
https://example.test/safe-memory-link
http://example.test/plain-http-ok
javascript:alert('memory-os-test')
data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==
file:///Users/example/private.txt
chrome://settings/passwords
extension://abc123/options.html
blob:https://example.test/abc
```

Expected detection:

```json
{
  "fixtureId": "security-unsafe-url-schemes",
  "detectedMedium": "url_clip",
  "confidence": "medium",
  "securityFlags": [
    "unsafe_url_scheme_detected"
  ],
  "safeUrlCount": 2,
  "blockedUrlCount": 6
}
```

Expected preview:

```json
{
  "candidateCount": 2,
  "blockedCount": 6,
  "candidates": [
    {
      "title": "https://example.test/safe-memory-link",
      "urlSafety": "safe_http",
      "selected": true,
      "privacyLevel": "owner_only"
    }
  ]
}
```

Expected policy:

```json
{
  "expectedAllow": true,
  "expectedReasons": [
    "unsafe_url_scheme_rejected",
    "safe_candidates_preview_only"
  ]
}
```

## Fixture 2: title-list-basic.txt

Path:

```txt
fixtures/import/universal/title-list-basic.txt
```

Content:

```txt
架空映画A
架空アニメB
架空漫画C
架空ラジオ番組D
```

Expected detection:

```json
{
  "fixtureId": "universal-title-list-basic",
  "detectedMedium": "title_list",
  "confidence": "low",
  "requiresUserSelection": true,
  "reasons": [
    "plain_line_list",
    "no_strong_source_signal"
  ]
}
```

Expected preview:

```json
{
  "candidateCount": 4,
  "selectedByDefault": 4,
  "aiAnalysisDefault": "off",
  "exportDefault": "included",
  "candidates": [
    {
      "title": "架空映画A",
      "medium": "title_list",
      "privacyLevel": "owner_only",
      "confidence": "low"
    }
  ]
}
```

Expected policy:

```json
{
  "expectedAllow": true,
  "expectedMode": "preview_only",
  "expectedReasons": [
    "import_preview_required",
    "low_confidence_requires_user_selection"
  ]
}
```

## Fixture 3: url-list-basic.txt

Path:

```txt
fixtures/import/universal/url-list-basic.txt
```

Content:

```txt
https://filmarks.example.test/movies/fictional-001
https://tabelog.example.test/kanagawa/A0000/A000000/fictional-restaurant/
https://open.spotify.example.test/track/fictional-track-001
https://example.test/unknown-page
```

Expected detection:

```json
{
  "fixtureId": "universal-url-list-basic",
  "detectedMedium": "url_clip",
  "confidence": "medium",
  "sourceCandidates": [
    "filmarks",
    "tabelog",
    "spotify",
    "unknown_url"
  ]
}
```

Expected preview:

```json
{
  "candidateCount": 4,
  "unknownCount": 1,
  "candidates": [
    {
      "urlHost": "filmarks.example.test",
      "serviceCandidate": "filmarks",
      "privacyLevel": "owner_only"
    },
    {
      "urlHost": "tabelog.example.test",
      "serviceCandidate": "tabelog",
      "privacyLevel": "owner_sensitive"
    }
  ]
}
```

## Fixture 4: netflix-viewing-activity-standard.csv

Path:

```txt
fixtures/import/streaming/netflix-viewing-activity-standard.csv
```

Content:

```csv
Title,Date
Fictional Series: Season 1: Episode 1,2026-07-01
Fictional Movie A,2026-07-02
Fictional Movie A,2026-07-02
Fictional Documentary B,2026-07-04
```

Expected detection:

```json
{
  "fixtureId": "streaming-netflix-viewing-activity-standard",
  "detectedSource": "netflix",
  "detectedMedium": "streaming_watch_activity",
  "parserId": "netflix-viewing-activity-csv-parser",
  "confidence": "high",
  "reasons": [
    "known_csv_headers",
    "date_title_rows"
  ]
}
```

Expected preview:

```json
{
  "candidateCount": 4,
  "duplicateCandidates": 1,
  "privacyDefault": "owner_sensitive",
  "aiAnalysisDefault": "off",
  "exportDefault": "excluded",
  "candidates": [
    {
      "title": "Fictional Series: Season 1: Episode 1",
      "activityType": "watched",
      "occurredAtText": "2026-07-01",
      "occurredAtPrecision": "date",
      "privacyLevel": "owner_sensitive"
    }
  ]
}
```

Expected policy:

```json
{
  "expectedMode": "allow_with_restrictions",
  "expectedReasons": [
    "streaming_history_owner_sensitive_default",
    "ai_analysis_off_default",
    "export_default_excluded"
  ]
}
```

## Fixture 5: manga-progress-list.txt

Path:

```txt
fixtures/import/anime-manga/manga-progress-list.txt
```

Content:

```txt
架空漫画A 12巻まで
架空漫画B 45話まで
架空漫画C 読書中 3巻
架空漫画D 完了
```

Expected preview:

```json
{
  "candidateCount": 4,
  "medium": "anime_manga_progress",
  "privacyDefault": "owner_only",
  "candidates": [
    {
      "title": "架空漫画A",
      "mediaType": "manga",
      "activityType": "reading",
      "volumeProgress": 12
    },
    {
      "title": "架空漫画B",
      "mediaType": "manga",
      "activityType": "reading",
      "chapterProgress": 45
    }
  ]
}
```

## Fixture 6: tabelog-url-list.txt

Path:

```txt
fixtures/import/restaurant/tabelog-url-list.txt
```

Content:

```txt
https://tabelog.example.test/tokyo/A0000/A000000/fictional-yakiniku/
https://tabelog.example.test/kanagawa/A0001/A000100/fictional-italian/
架空カフェC 横浜 行きたい
```

Expected preview:

```json
{
  "candidateCount": 3,
  "medium": "restaurant_food_activity",
  "candidates": [
    {
      "serviceCandidate": "tabelog",
      "activityType": "saved",
      "privacyLevel": "owner_sensitive",
      "warnings": [
        "location_context_possible"
      ]
    }
  ]
}
```

Expected policy:

```json
{
  "expectedReasons": [
    "restaurant_location_context_owner_sensitive",
    "no_relationship_inference"
  ]
}
```

## Fixture 7: gera-episode-list.txt

Path:

```txt
fixtures/import/audio/gera-episode-list.txt
```

Content:

```txt
架空GERA番組A #101 架空タイトル
架空GERA番組A #102 次の架空タイトル
架空ラジオB 2026-07-03 深夜の架空回
```

Expected preview:

```json
{
  "candidateCount": 3,
  "medium": "audio_episode_activity",
  "privacyDefault": "owner_only",
  "candidates": [
    {
      "showTitle": "架空GERA番組A",
      "episodeNumber": "101",
      "episodeTitle": "架空タイトル",
      "activityType": "want_to_listen"
    }
  ]
}
```

## Fixture 8: line-copy-selected.txt

Path:

```txt
fixtures/import/message/line-copy-selected.txt
```

Content:

```txt
2026/07/01 21:05 自分: 架空の予定について話した
2026/07/01 21:06 相手: 架空の返事をした
2026/07/01 21:10 自分: また確認すると言った
```

Expected preview:

```json
{
  "candidateCount": 1,
  "medium": "message_conversation_context",
  "privacyDefault": "restricted",
  "rawStored": false,
  "aiAnalysisDefault": "off",
  "exportDefault": "excluded",
  "candidates": [
    {
      "messageCount": 3,
      "relationshipContextPossible": true,
      "safeSummary": "2026-07-01ごろの選択された会話メモです。",
      "warnings": [
        "third_party_private",
        "raw_chat_summary_only"
      ]
    }
  ]
}
```

Expected policy:

```json
{
  "expectedMode": "summary_only",
  "expectedReasons": [
    "third_party_private",
    "raw_chat_summary_only",
    "export_default_excluded"
  ]
}
```

## Fixture 9: photo-with-exif.meta.json

Path:

```txt
fixtures/import/media/photo-with-exif.meta.json
```

Content:

```json
{
  "syntheticFileName": "synthetic-photo-with-exif.jpg",
  "safeMimeType": "image/jpeg",
  "width": 1200,
  "height": 900,
  "exifGpsPresent": true,
  "deviceMetadataPresent": true,
  "facePresencePossible": false,
  "minorPossible": false
}
```

Expected preview:

```json
{
  "candidateCount": 1,
  "medium": "image_media_context",
  "privacyDefault": "owner_sensitive",
  "candidates": [
    {
      "mediaKind": "personal_photo",
      "exifGpsPresent": true,
      "exifGpsStripped": true,
      "ocrPerformed": false,
      "exportDefault": "excluded",
      "warnings": [
        "exif_location_stripped",
        "ocr_disabled_by_default"
      ]
    }
  ]
}
```

## Fixture 10: character-card.json

Path:

```txt
fixtures/import/persona/character-card.json
```

Content:

```json
{
  "name": "Fictional Test Character",
  "description": "Synthetic fictional character description for parser testing.",
  "scenario": "Synthetic roleplay scenario.",
  "first_mes": "Synthetic greeting.",
  "metadata": {
    "source": "fixture"
  }
}
```

Expected preview:

```json
{
  "candidateCount": 1,
  "medium": "persona_like_context",
  "privacyDefault": "owner_sensitive",
  "candidates": [
    {
      "personaKind": "character_card",
      "identityBoundaryClass": "fictional_character",
      "simulationAllowed": false,
      "aiAnalysisDefault": "off",
      "exportDefault": "excluded",
      "warnings": [
        "persona_like_data_detected",
        "simulation_not_allowed"
      ]
    }
  ]
}
```

Expected policy:

```json
{
  "expectedMode": "allow_with_restrictions",
  "expectedReasons": [
    "fictional_notes_allowed_no_agent",
    "simulation_not_allowed",
    "character_card_export_excluded"
  ]
}
```

## CI Fixture Validation

Before parser tests run, fixture lint must check:

- no real token-looking strings.
- no real email addresses.
- no private domains except `.example.test`.
- no phone number patterns.
- no raw adult/private explicit text in snapshots.
- expected snapshots do not contain raw chat text.
- persona fixture never sets `simulationAllowed=true`.

## 結論

最初のfixtureは、Security / Universal / S-rank / Sensitive / Media / Persona を最小セットで横断する。

この10個を先に作れば、ParserRegistry、Detector、Preview、Policyの骨格をかなり安全に検証できる。
