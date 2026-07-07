# Policy Test Cases

## 目的

Policy Test Cases は、Memory OS の Policy Engine が最低限守るべき P0 判定を、具体的な入力・期待出力として固定する。

このファイルは `docs/test-strategy.md` の Policy Engine Tests を実装しやすい形に落としたものである。

Raw sensitive text must not be included in test logs or snapshots.

## Test Case Format

```ts
type PolicyTestCase = {
  id: string;
  title: string;
  context: PolicyContext;
  expectedMode: PolicyDecision['mode'];
  expectedAllow: boolean;
  expectedReasons: string[];
  safeUserMessage?: string;
};
```

## P0 Cases

### P0-001 Secret raw storage denied

```ts
{
  id: 'P0-001',
  title: 'Secret raw storage denied',
  context: {
    action: 'store_raw',
    target: { type: 'raw_record', id: 'raw_secret_001' },
    sourceType: 'manual',
    riskClasses: ['secret_or_credential'],
    actor: 'system'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['secret_or_credential']
}
```

### P0-002 Secret embedding denied

```ts
{
  id: 'P0-002',
  title: 'Secret embedding denied',
  context: {
    action: 'create_embedding',
    target: { type: 'normalized_record', id: 'norm_secret_001' },
    sourceType: 'manual',
    riskClasses: ['secret_or_credential'],
    actor: 'system'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['secret_or_credential']
}
```

### P0-003 Secret export denied

```ts
{
  id: 'P0-003',
  title: 'Secret export denied',
  context: {
    action: 'export_memory',
    target: { type: 'memory', id: 'mem_secret_001' },
    sourceType: 'manual',
    riskClasses: ['secret_or_credential'],
    actor: 'user'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['secret_or_credential']
}
```

### P0-004 Corporate raw LLM denied

```ts
{
  id: 'P0-004',
  title: 'Corporate confidential raw LLM denied',
  context: {
    action: 'send_to_llm',
    target: { type: 'raw_record', id: 'raw_corp_001' },
    sourceType: 'slack_export',
    riskClasses: ['corporate_confidential'],
    actor: 'ai'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['corporate_confidential']
}
```

### P0-005 Third-party private raw quote denied

```ts
{
  id: 'P0-005',
  title: 'Third-party private raw quote denied',
  context: {
    action: 'show_raw_quote',
    target: { type: 'raw_record', id: 'raw_line_other_001' },
    sourceType: 'line_export',
    riskClasses: ['third_party_private'],
    actor: 'user'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['third_party_private']
}
```

### P0-006 Third-party relationship summary allowed with limit

```ts
{
  id: 'P0-006',
  title: 'Third-party relationship summary allowed with limit',
  context: {
    action: 'create_memory',
    target: { type: 'normalized_record', id: 'norm_line_summary_001' },
    sourceType: 'line_export',
    riskClasses: ['third_party_private'],
    actor: 'system',
    requestIntent: 'relationship_context'
  },
  expectedMode: 'summary_only',
  expectedAllow: true,
  expectedReasons: ['third_party_private', 'relationship_context_only']
}
```

### P0-007 Partner surveillance query denied

```ts
{
  id: 'P0-007',
  title: 'Partner surveillance query denied',
  context: {
    action: 'show_in_search',
    target: { type: 'memory', id: 'mem_partner_001' },
    sourceType: 'line_export',
    riskClasses: ['third_party_private'],
    actor: 'user',
    requestIntent: 'surveillance_or_blame'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['surveillance_or_blame_intent']
}
```

### P0-008 Family blame evidence denied

```ts
{
  id: 'P0-008',
  title: 'Family blame evidence denied',
  context: {
    action: 'show_in_search',
    target: { type: 'memory', id: 'mem_family_conflict_001' },
    sourceType: 'manual',
    riskClasses: ['family_sensitive', 'third_party_private'],
    actor: 'user',
    requestIntent: 'surveillance_or_blame'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['surveillance_or_blame_intent', 'third_party_private']
}
```

### P0-009 Deceased impersonation denied

```ts
{
  id: 'P0-009',
  title: 'Deceased impersonation denied',
  context: {
    action: 'send_to_llm',
    target: { type: 'memory', id: 'mem_deceased_001' },
    sourceType: 'manual',
    riskClasses: ['grief_or_death'],
    actor: 'ai',
    requestIntent: 'impersonation_request'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['deceased_impersonation_intent']
}
```

### P0-010 Deceased values reference allowed as summary

```ts
{
  id: 'P0-010',
  title: 'Deceased values reference allowed as summary',
  context: {
    action: 'send_to_llm',
    target: { type: 'memory', id: 'mem_deceased_values_001' },
    sourceType: 'manual',
    riskClasses: ['grief_or_death'],
    actor: 'ai',
    requestIntent: 'values_reference'
  },
  expectedMode: 'summary_only',
  expectedAllow: true,
  expectedReasons: ['grief_or_death', 'no_impersonation']
}
```

### P0-011 Minor tip denied

```ts
{
  id: 'P0-011',
  title: 'Minor tip denied',
  context: {
    action: 'generate_tip',
    target: { type: 'memory', id: 'mem_minor_001' },
    sourceType: 'photos_metadata',
    riskClasses: ['minor_sensitive'],
    actor: 'system'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['minor_sensitive']
}
```

### P0-012 Minor export excluded default

```ts
{
  id: 'P0-012',
  title: 'Minor export excluded default',
  context: {
    action: 'export_memory',
    target: { type: 'memory', id: 'mem_minor_002' },
    sourceType: 'photos_metadata',
    riskClasses: ['minor_sensitive'],
    actor: 'user'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['minor_sensitive', 'default_export_exclude']
}
```

### P0-013 Self-harm crisis tip denied

```ts
{
  id: 'P0-013',
  title: 'Self-harm crisis tip denied',
  context: {
    action: 'generate_tip',
    target: { type: 'memory', id: 'mem_crisis_001' },
    sourceType: 'manual',
    riskClasses: ['self_harm_or_crisis'],
    actor: 'system'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['self_harm_or_crisis']
}
```

### P0-014 Self-harm historical reflection summary only

```ts
{
  id: 'P0-014',
  title: 'Self-harm historical reflection summary only',
  context: {
    action: 'send_to_llm',
    target: { type: 'memory', id: 'mem_crisis_historical_001' },
    sourceType: 'manual',
    riskClasses: ['self_harm_or_crisis'],
    actor: 'ai',
    requestIntent: 'reflection'
  },
  expectedMode: 'summary_only',
  expectedAllow: true,
  expectedReasons: ['self_harm_or_crisis', 'safe_summary_only']
}
```

### P0-015 AI roleplay log no persona creation

```ts
{
  id: 'P0-015',
  title: 'AI roleplay log no persona creation',
  context: {
    action: 'create_memory',
    target: { type: 'normalized_record', id: 'norm_roleplay_001' },
    sourceType: 'character_ai',
    riskClasses: ['fictional_or_roleplay_data'],
    actor: 'system',
    requestIntent: 'persona_profile_creation'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['impersonation_or_roleplay_intent']
}
```

### P0-016 Low-risk manual memory allowed

```ts
{
  id: 'P0-016',
  title: 'Low-risk manual memory allowed',
  context: {
    action: 'create_memory',
    target: { type: 'normalized_record', id: 'norm_manual_food_001' },
    sourceType: 'manual',
    riskClasses: [],
    actor: 'system'
  },
  expectedMode: 'allow',
  expectedAllow: true,
  expectedReasons: []
}
```

### P0-017 Low-risk food memory search allowed

```ts
{
  id: 'P0-017',
  title: 'Low-risk food memory search allowed',
  context: {
    action: 'show_in_search',
    target: { type: 'memory', id: 'mem_ramen_001' },
    sourceType: 'manual',
    riskClasses: [],
    actor: 'user',
    requestIntent: 'find_memory'
  },
  expectedMode: 'allow',
  expectedAllow: true,
  expectedReasons: []
}
```

### P0-018 Hidden memory search denied default

```ts
{
  id: 'P0-018',
  title: 'Hidden memory search denied default',
  context: {
    action: 'show_in_search',
    target: { type: 'memory', id: 'mem_hidden_001' },
    sourceType: 'manual',
    riskClasses: ['hidden_by_user'],
    actor: 'user',
    requestIntent: 'find_memory'
  },
  expectedMode: 'hide_by_default',
  expectedAllow: false,
  expectedReasons: ['hidden_by_user']
}
```

### P0-019 Sealed memory LLM denied

```ts
{
  id: 'P0-019',
  title: 'Sealed memory LLM denied',
  context: {
    action: 'send_to_llm',
    target: { type: 'memory', id: 'mem_sealed_001' },
    sourceType: 'manual',
    riskClasses: ['sealed_by_user'],
    actor: 'ai'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['sealed_by_user']
}
```

### P0-020 Deleted memory export denied

```ts
{
  id: 'P0-020',
  title: 'Deleted memory export denied',
  context: {
    action: 'export_memory',
    target: { type: 'memory', id: 'mem_deleted_001' },
    sourceType: 'manual',
    riskClasses: ['deleted_by_user'],
    actor: 'user'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['deleted_by_user']
}
```

## Import / DB / Dedup P0 Cases

### P0-021 Import save before preview denied

```ts
{
  id: 'P0-021',
  title: 'Import save before preview denied',
  context: {
    action: 'commit_import',
    target: { type: 'import_job', id: 'import_no_preview_001' },
    sourceType: 'netflix_csv',
    riskClasses: [],
    actor: 'system',
    importState: 'parsed_without_preview'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['import_preview_required']
}
```

### P0-022 Raw import default storage denied for LINE

```ts
{
  id: 'P0-022',
  title: 'LINE raw import default storage denied',
  context: {
    action: 'store_raw',
    target: { type: 'source_item', id: 'line_source_item_001' },
    sourceType: 'line_export',
    riskClasses: ['third_party_private', 'relationship_context'],
    actor: 'system',
    importDefaults: { rawStored: true }
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['raw_import_disabled_by_default', 'third_party_private']
}
```

### P0-023 Private bookmark title logging denied

```ts
{
  id: 'P0-023',
  title: 'Private bookmark title logging denied',
  context: {
    action: 'write_log',
    target: { type: 'import_preview_candidate', id: 'private_bookmark_001' },
    sourceType: 'browser_bookmarks',
    riskClasses: ['private_hobby_content'],
    actor: 'system',
    logPayloadKind: 'raw_title_or_url'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['private_title_logging_denied']
}
```

### P0-024 Active content execution denied

```ts
{
  id: 'P0-024',
  title: 'Imported active content execution denied',
  context: {
    action: 'render_import_preview',
    target: { type: 'import_input_file', id: 'malicious_bookmarks_001' },
    sourceType: 'browser_bookmarks',
    riskClasses: ['active_content_detected'],
    actor: 'system',
    renderMode: 'raw_html'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['active_content_removed', 'raw_html_preview_rendering_denied']
}
```

### P0-025 Re-import deleted tombstone excluded

```ts
{
  id: 'P0-025',
  title: 'Re-import deleted tombstone excluded',
  context: {
    action: 'select_import_candidate',
    target: { type: 'import_preview_candidate', id: 'deleted_match_001' },
    sourceType: 'line_export',
    riskClasses: ['previously_deleted_candidate'],
    actor: 'system',
    tombstoneMatched: true
  },
  expectedMode: 'deny_by_default',
  expectedAllow: false,
  expectedReasons: ['previously_deleted_candidate', 'default_import_exclude']
}
```

### P0-026 Sensitive dedupe key plain hash denied

```ts
{
  id: 'P0-026',
  title: 'Sensitive dedupe key plain hash denied',
  context: {
    action: 'create_dedupe_key',
    target: { type: 'dedupe_key', id: 'dedupe_sensitive_001' },
    sourceType: 'browser_bookmarks',
    riskClasses: ['private_hobby_content'],
    actor: 'system',
    keyAlgorithm: 'sha256_plain'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['dedupe_hmac_required', 'private_content_owner_sensitive_default']
}
```

### P0-027 Dedupe key without key version denied

```ts
{
  id: 'P0-027',
  title: 'Dedupe key without key version denied',
  context: {
    action: 'create_dedupe_key',
    target: { type: 'dedupe_key', id: 'dedupe_no_version_001' },
    sourceType: 'netflix_csv',
    riskClasses: [],
    actor: 'system',
    keyAlgorithm: 'hmac_sha256',
    keyVersion: null
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['dedupe_key_version_required']
}
```

### P0-028 Low-confidence entity merge denied

```ts
{
  id: 'P0-028',
  title: 'Low-confidence entity merge denied',
  context: {
    action: 'merge_records',
    target: { type: 'entity_match_candidate', id: 'candidate_low_001' },
    sourceType: 'filmarks_paste',
    riskClasses: [],
    actor: 'system',
    matchConfidence: 'low'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['low_confidence_merge_requires_user_confirmation']
}
```

### P0-029 Shared profile import defaults sensitive

```ts
{
  id: 'P0-029',
  title: 'Shared profile import defaults sensitive',
  context: {
    action: 'create_import_preview_candidate',
    target: { type: 'import_preview_candidate', id: 'netflix_shared_001' },
    sourceType: 'netflix_csv',
    riskClasses: ['shared_profile_possible'],
    actor: 'system',
    sourceAccountKind: 'shared_or_unknown'
  },
  expectedMode: 'allow_with_restrictions',
  expectedAllow: true,
  expectedReasons: ['shared_profile_possible', 'owner_sensitive_default', 'ai_analysis_off_default']
}
```

### P0-030 Ambiguous time precision requires non-exact dedupe

```ts
{
  id: 'P0-030',
  title: 'Ambiguous time precision requires non-exact dedupe',
  context: {
    action: 'dedupe_activity',
    target: { type: 'user_activity', id: 'activity_date_only_001' },
    sourceType: 'netflix_csv',
    riskClasses: [],
    actor: 'system',
    occurredAtPrecision: 'date',
    comparedToPrecision: 'exact_timestamp'
  },
  expectedMode: 'candidate_only',
  expectedAllow: true,
  expectedReasons: ['time_precision_mismatch', 'dedupe_candidate_only']
}
```

### P0-031 Import schema drift requires user review

```ts
{
  id: 'P0-031',
  title: 'Import schema drift requires user review',
  context: {
    action: 'parse_import',
    target: { type: 'import_input_file', id: 'netflix_schema_changed_001' },
    sourceType: 'netflix_csv',
    riskClasses: ['schema_drift_detected'],
    actor: 'system',
    parserConfidence: 'low'
  },
  expectedMode: 'needs_user_selection',
  expectedAllow: false,
  expectedReasons: ['schema_drift_detected', 'low_confidence_requires_review']
}
```

### P0-032 Search document for sealed record denied

```ts
{
  id: 'P0-032',
  title: 'Search document for sealed record denied',
  context: {
    action: 'create_search_document',
    target: { type: 'memory', id: 'sealed_memory_001' },
    sourceType: 'manual',
    riskClasses: ['sealed_by_user'],
    actor: 'system'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['sealed_by_user', 'search_index_excluded']
}
```

### P0-033 Embedding imported source item denied by default

```ts
{
  id: 'P0-033',
  title: 'Embedding imported source item denied by default',
  context: {
    action: 'create_embedding',
    target: { type: 'source_item', id: 'source_item_imported_001' },
    sourceType: 'spotify_api',
    riskClasses: [],
    actor: 'system',
    importPhase: 'on_import'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['embedding_lazy_only', 'source_item_not_embedding_default']
}
```

### P0-034 OAuth token plaintext storage denied

```ts
{
  id: 'P0-034',
  title: 'OAuth token plaintext storage denied',
  context: {
    action: 'store_oauth_token',
    target: { type: 'oauth_connection', id: 'spotify_conn_001' },
    sourceType: 'spotify_api',
    riskClasses: ['oauth_token'],
    actor: 'system',
    tokenStorageMode: 'plaintext'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['token_encryption_required']
}
```

### P0-035 OAuth broad write scope denied for MVP

```ts
{
  id: 'P0-035',
  title: 'OAuth broad write scope denied for MVP',
  context: {
    action: 'request_oauth_scope',
    target: { type: 'oauth_connection', id: 'spotify_scope_001' },
    sourceType: 'spotify_api',
    riskClasses: [],
    actor: 'system',
    requestedScopes: ['playlist-modify-public', 'user-modify-playback-state']
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['write_scope_not_allowed_for_mvp', 'least_privilege_scope_required']
}
```

### P0-036 Revoked OAuth connection sync denied

```ts
{
  id: 'P0-036',
  title: 'Revoked OAuth connection sync denied',
  context: {
    action: 'sync_api_connection',
    target: { type: 'oauth_connection', id: 'revoked_conn_001' },
    sourceType: 'spotify_api',
    riskClasses: ['revoked_connection'],
    actor: 'system',
    connectionStatus: 'revoked_by_user'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['oauth_connection_revoked']
}
```

### P0-037 Cross-user token access denied

```ts
{
  id: 'P0-037',
  title: 'Cross-user token access denied',
  context: {
    action: 'decrypt_oauth_token',
    target: { type: 'oauth_connection', id: 'other_user_conn_001' },
    sourceType: 'spotify_api',
    riskClasses: ['cross_user_access_attempt'],
    actor: 'system',
    actorUserMatchesTargetUser: false
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['cross_user_access_denied']
}
```

### P0-038 Migration raw logging denied

```ts
{
  id: 'P0-038',
  title: 'Migration raw logging denied',
  context: {
    action: 'write_log',
    target: { type: 'migration_job', id: 'migration_backfill_001' },
    sourceType: 'db_migration',
    riskClasses: ['raw_or_private_content'],
    actor: 'system',
    logPayloadKind: 'raw_values'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['migration_no_raw_logs']
}
```

### P0-039 Restore without tombstone replay denied

```ts
{
  id: 'P0-039',
  title: 'Restore without tombstone replay denied',
  context: {
    action: 'restore_backup',
    target: { type: 'backup_restore_job', id: 'restore_001' },
    sourceType: 'backup',
    riskClasses: ['deleted_records_may_resurface'],
    actor: 'system',
    tombstoneReplayPlanned: false
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['deletion_tombstone_replay_required']
}
```

### P0-040 Export staging without TTL denied

```ts
{
  id: 'P0-040',
  title: 'Export staging without TTL denied',
  context: {
    action: 'create_export_package',
    target: { type: 'export_package', id: 'export_no_ttl_001' },
    sourceType: 'export',
    riskClasses: ['export_package'],
    actor: 'system',
    expiresAt: null
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['export_staging_ttl_required']
}
```

## Implementation Notes

- `expectedReasons` は厳密完全一致でなく、必須reason包含でよい。
- safeUserMessage はdangerous rawを含めてはいけない。
- requestIntent は必ず PolicyContext に残す。
- Policy test は Search / Export / Adapter / DB migration / Import parser tests からも再利用する。
- Import / DB tests は raw title / raw URL / raw chat をsnapshotに含めない。

## Acceptance Criteria

- P0-001〜P0-040 が自動テスト化されている。
- allow/deny/mode が期待通り。
- dangerous success は failure として扱う。
- test snapshots に raw secret / raw third-party text / private title / token が入らない。
- Import Previewなしcommitが失敗する。
- tombstone再Importがdefault除外になる。
- sealed/deleted/privateがsearch/export/embeddingに出ない。
- token plaintext storageが失敗する。

## 結論

Policy Engine は Memory Constitution の実行形式である。

ここにあるP0ケースを通らない実装は、MVPに入れてはいけない。
