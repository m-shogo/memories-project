# Policy Test Cases: Media and Persona Import / Export

## 目的

この文書は、`docs/policy-test-cases.md` のP0-001〜P0-040に続く、画像・メディア・他人格・persona-like data・Export/Re-importに関する追加P0 policy testsである。

既存policy testsに加えて、以下を防ぐ。

- 画像EXIF/GPSの漏えい
- LINE/DMスクショのraw OCR/Export
- 未成年/第三者画像の標準Export混入
- 漫画ページ/著作物raw保存
- 他人/故人/家族/恋人の人格化
- AI companion / character card のagent化
- persona bundle Export
- Memory OS Exportの再Importでpolicy bypass

## P0 Media / Persona Cases

### P0-041 Image EXIF GPS stripped by default

```ts
{
  id: 'P0-041',
  title: 'Image EXIF GPS stripped by default',
  context: {
    action: 'import_media_metadata',
    target: { type: 'media_object', id: 'photo_with_exif_001' },
    sourceType: 'image_upload',
    riskClasses: ['exif_location_present'],
    actor: 'system',
    exifGpsIncluded: true
  },
  expectedMode: 'allow_with_restrictions',
  expectedAllow: true,
  expectedReasons: ['exif_location_stripped', 'media_metadata_only_default']
}
```

### P0-042 Chat screenshot OCR denied by default

```ts
{
  id: 'P0-042',
  title: 'Chat screenshot OCR denied by default',
  context: {
    action: 'create_ocr_text',
    target: { type: 'media_object', id: 'line_screenshot_001' },
    sourceType: 'chat_screenshot',
    riskClasses: ['third_party_private', 'chat_screenshot'],
    actor: 'system',
    userExplicitlyRequestedOcr: false
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['ocr_disabled_by_default', 'chat_screenshot_summary_only', 'third_party_private']
}
```

### P0-043 LINE screenshot raw export denied

```ts
{
  id: 'P0-043',
  title: 'LINE screenshot raw export denied',
  context: {
    action: 'export_memory',
    target: { type: 'media_object', id: 'line_screenshot_raw_001' },
    sourceType: 'chat_screenshot',
    riskClasses: ['third_party_private', 'raw_media', 'chat_screenshot'],
    actor: 'user'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['third_party_media_export_excluded', 'chat_screenshot_summary_only']
}
```

### P0-044 Minor photo standard export denied

```ts
{
  id: 'P0-044',
  title: 'Minor photo standard export denied',
  context: {
    action: 'export_memory',
    target: { type: 'media_object', id: 'minor_photo_001' },
    sourceType: 'image_upload',
    riskClasses: ['minor_sensitive', 'image_contains_faces_possible'],
    actor: 'user',
    exportPackageClass: 'standard_memory_export'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['minor_media_restricted', 'default_export_exclude']
}
```

### P0-045 Manga page raw import denied

```ts
{
  id: 'P0-045',
  title: 'Manga page raw import denied',
  context: {
    action: 'store_raw',
    target: { type: 'media_object', id: 'manga_page_001' },
    sourceType: 'manga_page_image',
    riskClasses: ['copyrighted_page_content'],
    actor: 'system'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['copyrighted_page_content_denied', 'media_metadata_only_default']
}
```

### P0-046 Image SVG active content rendering denied

```ts
{
  id: 'P0-046',
  title: 'SVG active content rendering denied',
  context: {
    action: 'render_import_preview',
    target: { type: 'media_object', id: 'active_svg_001' },
    sourceType: 'svg_upload',
    riskClasses: ['active_content_detected'],
    actor: 'system',
    renderMode: 'raw_svg'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['active_content_removed', 'raw_html_preview_rendering_denied']
}
```

### P0-047 Real person style export as persona denied

```ts
{
  id: 'P0-047',
  title: 'Real person style export as persona denied',
  context: {
    action: 'export_persona_bundle',
    target: { type: 'persona_data', id: 'other_person_style_001' },
    sourceType: 'writing_style_sample_other_person',
    riskClasses: ['real_person_style', 'impersonation_risk'],
    actor: 'user',
    requestIntent: 'persona_clone_export'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['real_person_style_restricted', 'impersonation_bundle_denied']
}
```

### P0-048 Deceased persona activation denied

```ts
{
  id: 'P0-048',
  title: 'Deceased persona activation denied',
  context: {
    action: 'activate_persona_agent',
    target: { type: 'persona_data', id: 'deceased_person_records_001' },
    sourceType: 'deceased_person_records',
    riskClasses: ['grief_or_death', 'deceased_person_persona'],
    actor: 'system',
    requestIntent: 'deceased_speak_as'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['deceased_person_simulation_denied', 'simulation_not_allowed']
}
```

### P0-049 Character card import does not create agent

```ts
{
  id: 'P0-049',
  title: 'Character card import does not create agent',
  context: {
    action: 'activate_persona_agent',
    target: { type: 'persona_data', id: 'character_card_001' },
    sourceType: 'character_card',
    riskClasses: ['persona_like_data_detected', 'fictional_or_roleplay_data'],
    actor: 'system',
    userExplicitlyRequestedAgent: false
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['simulation_not_allowed', 'character_card_export_excluded']
}
```

### P0-050 AI companion logs excluded from export by default

```ts
{
  id: 'P0-050',
  title: 'AI companion logs excluded from export by default',
  context: {
    action: 'export_memory',
    target: { type: 'persona_data', id: 'ai_companion_log_001' },
    sourceType: 'ai_companion_chat_log',
    riskClasses: ['ai_companion_dependency_risk', 'fictional_or_roleplay_data'],
    actor: 'user',
    exportPackageClass: 'standard_memory_export'
  },
  expectedMode: 'deny_by_default',
  expectedAllow: false,
  expectedReasons: ['ai_companion_dependency_risk', 'default_export_exclude']
}
```

### P0-051 Persona bundle re-import no activation

```ts
{
  id: 'P0-051',
  title: 'Persona bundle re-import no activation',
  context: {
    action: 'reimport_export_package',
    target: { type: 'export_package', id: 'persona_bundle_import_001' },
    sourceType: 'persona_like_export',
    riskClasses: ['persona_like_data_detected'],
    actor: 'system',
    packageContainsPersonaLikeData: true
  },
  expectedMode: 'allow_with_restrictions',
  expectedAllow: true,
  expectedReasons: ['simulation_not_allowed', 'allow_restricted_no_activation']
}
```

### P0-052 Memory OS export re-import must check tombstones

```ts
{
  id: 'P0-052',
  title: 'Memory OS export re-import must check tombstones',
  context: {
    action: 'reimport_export_package',
    target: { type: 'export_package', id: 'memoryos_export_001' },
    sourceType: 'memory_os_export',
    riskClasses: ['deleted_records_may_resurface'],
    actor: 'system',
    tombstoneReplayPlanned: false
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['deletion_tombstone_replay_required', 'reimport_does_not_bypass_policy']
}
```

### P0-053 Export manifest raw private title denied

```ts
{
  id: 'P0-053',
  title: 'Export manifest raw private title denied',
  context: {
    action: 'create_export_manifest',
    target: { type: 'export_manifest', id: 'manifest_private_title_001' },
    sourceType: 'export',
    riskClasses: ['private_hobby_content'],
    actor: 'system',
    manifestContainsRawPrivateTitles: true
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['private_title_logging_denied', 'export_manifest_no_raw_private_titles']
}
```

### P0-054 Persona data not merged into self identity

```ts
{
  id: 'P0-054',
  title: 'Persona data not merged into self identity',
  context: {
    action: 'merge_records',
    target: { type: 'persona_data', id: 'roleplay_persona_001' },
    sourceType: 'roleplay_chat_log',
    riskClasses: ['fictional_or_roleplay_data', 'persona_like_data_detected'],
    actor: 'system',
    mergeTarget: 'self_profile'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['persona_like_data_detected', 'do_not_merge_into_self_identity']
}
```

### P0-055 Full media archive export requires reauth and scope review

```ts
{
  id: 'P0-055',
  title: 'Full media archive export requires reauth and scope review',
  context: {
    action: 'create_export_package',
    target: { type: 'export_package', id: 'media_archive_001' },
    sourceType: 'media_archive_export',
    riskClasses: ['raw_media', 'image_contains_faces_possible'],
    actor: 'user',
    reauthCompleted: false,
    explicitMediaScopeSelected: false
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['raw_media_export_requires_reauth', 'explicit_media_scope_required']
}
```

## Acceptance Criteria

- P0-041〜P0-055 are included with P0 policy suite.
- No image EXIF/GPS leaks by default.
- No raw chat screenshot OCR/export by default.
- No minor/third-party media in standard export by default.
- No persona-like import activates agent behavior.
- No real person/deceased/partner/family persona export.
- No re-import bypasses tombstone/policy.
- Export manifests contain risk flags, not raw private titles.

## 結論

画像と他人格データは、Import/Export/Re-importの境界を分けないと危険である。

この追加P0 suiteにより、Memory OSは画像・スクショ・未成年・第三者・著作物・AIキャラ・他人の文体・故人/家族/恋人人格データを、記録として扱えても人格化・Export漏えい・再Import bypassには使えない設計になる。
