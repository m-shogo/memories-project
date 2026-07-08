# Next Chat Fable DB Review Handoff

## 目的

この文書は、次チャットまたはFableレビューに入る時の短い引き継ぎである。

実装はまだしない。

今回の焦点は、AI記憶体サービス / Memory OS の **DB・Import・削除・RLS・dedupe・tombstone・raw storage・export/re-import・token/OAuth・audit/log・search/embedding** を、実装前に壊れにくくすること。

## Current Work Added

追加済み:

```txt
docs/fable-review-prompt.md
docs/fable-review-and-db-hardening-addendum.md
```

READMEからも辿れるようにした。

## Current Verdict

```txt
ready_for_fable_review_with_db_contract_corrections
```

意味:

- 方向性は強い。
- 実装に入る前のレビュー対象としては十分。
- ただし、FableレビューでP0指摘が出る前提で見る。
- 今すぐDB migration実装に入る状態ではない。

## Main Finding

破綻しそうな場所は、思想ではなく **概念モデルと物理DB設計のズレ**。

特に:

```txt
privacy enum混在
MemoryCandidate importanceの誤用
source_account_ref未固定
HMAC/key_versionなしdedupe/tombstone
key_referenceなし暗号化
oauth_connection未固定
nullable idempotency key
private canonical itemのglobal化
時刻精度なしdedupe
parser/schema version不足
JSONB audit/outbox leakage
削除後re-import復活
hidden/sealed/deletedの派生index残留
```

## Fableに必ず読ませる順番

```txt
1. README.md
2. docs/next-chat-handoff.md
3. docs/fable-review-prompt.md
4. docs/fable-review-and-db-hardening-addendum.md
5. docs/db-long-term-architecture.md
6. docs/db-table-design-v1.md
7. docs/db-edge-cases-and-hardening.md
8. docs/db-implementation-preflight-checklist.md
9. docs/first-migration-slice-plan.md
10. docs/rls-policy-and-negative-tests.md
```

## Fableへの要求

Fableには「良いですね」ではなく、以下を出させる。

```txt
1. Overall verdict
2. P0 blockers before implementation
3. P1 fixes before production
4. P2 future improvements
5. DB schema contradictions
6. RLS bypass possibilities
7. Delete/re-import resurrection paths
8. Dedupe false positive/negative risks
9. Raw/log/JSONB/queue leakage risks
10. Export/re-import safety risks
11. Concrete doc/spec changes
12. Concrete first implementation order
```

## Implementation Still Forbidden

まだやらない:

```txt
migration files
Prisma schema
Drizzle schema
API routes
UI implementation
Parser implementation
OAuth connector
Embedding
Export package
search index
memory_record save
persona_agent
relationship_state
```

## First Migration Contract To Preserve

First migration can create only:

```txt
app_user
source_account_ref
source_ref
import_job
import_input_file
import_detection_result
import_preview
import_preview_candidate
raw_object_ref
dedupe_key
deletion_tombstone
policy_decision
lifecycle_event
audit_event
outbox_event
key_reference
oauth_connection
```

Do not create in first migration:

```txt
source_item
source_item_key
canonical_item
canonical_item_external_id
canonical_item_alias
user_activity
user_activity_source_link
memory_record
memory_source_link
evidence_record
search_document
embedding_record
export_package
persona_agent
relationship_state
```

## Next Recommended Work

実装しないまま進めるなら:

```txt
1. Fableレビュー結果を受ける。
2. P0だけを docs/db-table-design-v1.md / docs/first-migration-slice-plan.md に反映する。
3. migration-001-foundation-contract.md を作る。
4. RLS policy matrix for first-slice tables を作る。
5. SafeMetadataGuard spec を作る。
6. account deletion mode decision memo を作る。
```

実装に進むのはその後。

## Final Note

このMemory OSは、いい思想だから壊れるのではなく、いい思想をDB・権限・削除・Import・Exportの端まで通さないと壊れる。

Fableレビューでは、思想への共感より、実装者がショートカットしそうな場所を潰す。
