# Media and Image Import / Export Safety

## 目的

この文書は、Memory OS に画像・スクリーンショット・写真・サムネイル・表紙画像・添付ファイルが入る場合に、Importしてよいか、Exportしてよいか、どの条件なら安全かを定義する。

画像は単なる添付ではない。

画像には以下が含まれうる。

- 顔
- 未成年
- 位置情報
- 撮影日時
- 端末情報
- 家族/恋人/友人/同僚
- チャット本文のスクリーンショット
- 医療/健康/学校/仕事/金融情報
- privateな趣味
- 著作物/表紙/漫画ページ/動画サムネイル
- EXIF/GPS
- OCR可能な文字

そのため、画像は text import より安全とは限らない。

## 最上位原則

### 1. Images are not harmless metadata

画像は、顔・場所・関係・時間・生活圏を一気に漏らす。

### 2. Default to metadata-first

画像そのものを保存する前に、以下だけで足りるか確認する。

- title
- date
- source
- user memo
- safe thumbnail
- object reference
- redacted summary

### 3. Strip high-risk metadata by default

EXIF GPS、端末ID、詳細位置、カメラ情報は既定で保存しない。

### 4. Faces and minors are restricted by default

顔が写る写真、未成年が写る写真は、owner_sensitiveまたはrestricted。

### 5. Screenshots are often third-party data

LINE、DM、メール、SNS、仕事画面、予約画面のスクリーンショットは、他人の発言や個人情報を含む。

raw画像保存・Exportは慎重にする。

### 6. Import OK does not mean Export OK

Importできることと、Exportできることは別。

Importはowner_sensitiveで保管できても、Exportでは除外・redact・再認証が必要な場合がある。

## Media Types

```ts
type MediaImportKind =
  | 'personal_photo'
  | 'screenshot'
  | 'chat_screenshot'
  | 'document_photo'
  | 'receipt_photo'
  | 'food_photo'
  | 'place_photo'
  | 'book_cover_or_catalog_image'
  | 'movie_or_music_cover_art'
  | 'manga_or_comic_page'
  | 'video_thumbnail'
  | 'profile_image_or_avatar'
  | 'generated_image'
  | 'unknown_image';
```

## Import / Export Eligibility Matrix

| Image kind | Import default | Export default | Notes |
|---|---|---|---|
| personal photo with only user | allowed owner_sensitive | excluded unless selected | EXIF stripped by default |
| family/friend photo | allowed restricted | excluded by default | faces/third-party context |
| minor/child photo | restricted | denied/default excluded | guardian/legal policy needed |
| food photo | allowed owner_only | included if no people/location sensitive | EXIF stripped |
| restaurant/place photo | owner_sensitive if location/date precise | excluded unless selected | location pattern risk |
| chat screenshot | summary/metadata only default | raw export denied/default excluded | third-party raw risk |
| LINE/DM screenshot | restricted summary-only | denied/default excluded | no evidence package |
| receipt/reservation photo | owner_sensitive | excluded unless selected | financial/location/time info |
| medical/health document photo | restricted/sealed suggestion | denied/default excluded | no proactive tips |
| work/internal screenshot | restricted or denied | denied/default excluded | corporate data |
| book/movie/music cover | catalog reference preferred | reference/URL preferred | avoid storing copyrighted image raw |
| manga/comic page | metadata only | denied | do not store page content |
| video thumbnail | catalog reference preferred | reference/URL preferred | copyright/terms |
| profile/avatar image of other person | restricted | denied/default excluded | identity/impersonation risk |
| generated image | owner_only if user-created | included only if user selects | provenance required |
| unknown image | preview only | excluded | classify before commit |

## Import Processing Rules

### Security Gate

Before image processing:

- validate file size.
- validate actual content type, not extension only.
- reject unsupported formats.
- reject SVG as active content unless sanitized/rasterized safely.
- strip metadata before preview where possible.
- do not expose image at public URL.
- store object outside webroot/public storage.
- scan for malicious payload where infrastructure supports it.

### Metadata Extraction

Allowed by default:

- dimensions
- file size
- safe mime type
- created/imported time
- image hash/HMAC hash

Disabled by default:

- precise GPS
- device identifiers
- camera serial numbers
- full EXIF dump
- hidden embedded metadata

### OCR

OCR can turn images into raw text.

Rules:

- OCR is off by default.
- OCR output is raw sensitive text.
- OCR is policy-gated.
- OCR for chat/document screenshots is summary-only or denied by default.
- OCR output must not enter logs.

### Face Recognition

Do not implement face recognition by default.

Rules:

- no face identity inference.
- no automatic relationship inference.
- no “who appears most” ranking.
- face presence may trigger privacy warning, but identity is user-labeled only.

## Storage Defaults

```ts
type MediaStorageDefault = {
  rawStored: boolean;
  thumbnailStored: boolean;
  exifStored: boolean;
  ocrStored: boolean;
  privacyLevel: 'owner_only' | 'owner_sensitive' | 'restricted';
  exportDefault: 'included' | 'excluded';
  aiAnalysisDefault: 'off' | 'allowed_after_user_request';
};
```

Defaults:

- rawStored=false for screenshots/chat/documents unless user explicitly opts in and policy allows.
- thumbnailStored=true only if safe and redaction not needed.
- exifStored=false for GPS/device-sensitive fields.
- ocrStored=false.
- AI analysis off.

## Export Rules

### Standard Export

Include by default:

- safe metadata
- user memo
- sourceRef
- redacted thumbnail if safe

Exclude by default:

- raw images with faces
- minor images
- chat screenshots
- document screenshots
- medical/financial/work images
- EXIF GPS
- OCR raw
- sealed media

### Full Archive Export

Requires:

- Export Safety ceremony
- step-up re-auth
- explicit media scope selection
- warning for third-party/minor/sealed/raw images
- delay/cancellation window for high-risk export

### Third-party / minor media

Export default:

- excluded.

Allowed only if:

- user explicitly selects.
- policy allows.
- legal/guardian/consent constraints are satisfied where required.
- raw is not third-party private content that policy denies.

## Image Search and Tips

Do not generate proactive tips from sensitive images.

Examples denied:

- “最近この人とよく会っています”
- “この場所によく行っています”
- “この写真の子どもは…”
- “このスクショから相手の本心は…”

Allowed:

- “この時期に保存された写真です”
- “この記録には画像があります”
- “安全のため画像の詳細は表示していません”

## Copyright / Content Rights

Memory OS should not store raw copyrighted pages or media content as user memory.

Examples:

- manga pages: metadata only.
- recipe full page screenshot: URL + user memo preferred.
- movie/music cover art: catalog URL/reference preferred.
- book cover: catalog reference preferred.

Do not use imported copyrighted images to train/generate style/personality.

## Policy Reasons

```ts
type MediaPolicyReason =
  | 'image_contains_faces_possible'
  | 'minor_media_restricted'
  | 'exif_location_stripped'
  | 'ocr_disabled_by_default'
  | 'chat_screenshot_summary_only'
  | 'third_party_media_export_excluded'
  | 'copyrighted_page_content_denied'
  | 'work_internal_screenshot_denied'
  | 'medical_or_financial_image_restricted'
  | 'raw_media_export_requires_reauth'
  | 'media_metadata_only_default';
```

## P0 Tests

1. EXIF GPS is stripped by default.
2. raw chat screenshot is not OCRed by default.
3. LINE screenshot raw export is denied/default excluded.
4. minor photo export is denied/default excluded.
5. manga page raw import is denied/metadata-only.
6. SVG active content is not executed.
7. image private title/path is not logged.
8. full archive media export requires re-auth and explicit scope.
9. sealed image has no active search thumbnail.
10. face presence does not create identity/person ranking.

## 結論

画像はMemory OSに入れられるが、画像そのものを常に保存・検索・Exportするわけではない。

画像Importはmetadata-first、EXIF stripped、OCR off、AI analysis off、Export excluded by defaultが基本である。

特に顔、未成年、LINE/DM/仕事/医療/金融/漫画ページは、ImportできてもExportできるとは限らない。
