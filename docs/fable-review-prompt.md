# Fable Review Prompt

以下をそのままFableに渡す。

```txt
Repository:
https://github.com/m-shogo/memories-project.git

Branch:
so

Task:
実装はしないでください。
このrepoの AI Memory OS / Memory OS 設計をレビューしてください。
特にDB、Import、削除、RLS、dedupe、tombstone、raw storage、export/re-import、OAuth/token、audit/log、search/embedding、privacy/safety 境界を重点的に見てください。

Product goal:
ChatGPT / Claude / Gemini / Character.AI の代替ではなく、AI時代に「自分の人生の文脈」を持ち続けるMemory OSを作る。

Core philosophy:
- AIは人生を評価しない
- AIは人生を忘れないための索引
- ラーメン、焼肉、帰り道、卒業式後の写真も全部人生
- 重要度をAIが決めない
- 保存時に分析しすぎない
- 保存時は安全チェック、ソース、日付、検索性が中心
- 分析はユーザーが求めた時だけ
- 小さな記録を捨てない
- 大きなイベントも押し付けない

Absolute non-goals:
- ChatGPT代替
- Character.AI化
- 故人再現
- 親/妻/恋人の本人シミュレーション
- AI恋人化
- AI伴侶化
- AI家族化
- 人格診断
- 人生ランキング
- パスワード管理
- 会社情報検索
- 他人の秘密の記憶化
- 監視/証拠探し
- 本人なりすまし
- AI本人代弁
- persona_agent table
- relationship_state table

Must-read docs:
- README.md
- docs/next-chat-handoff.md
- docs/fable-review-and-db-hardening-addendum.md
- docs/memory-data-model.md
- docs/product-boundaries.md
- docs/privacy-and-ethics.md
- docs/import-export-strategy.md
- docs/import-security-checklist.md
- docs/db-long-term-architecture.md
- docs/db-table-design-v1.md
- docs/db-edge-cases-and-hardening.md
- docs/db-implementation-preflight-checklist.md
- docs/first-migration-slice-plan.md
- docs/rls-policy-and-negative-tests.md
- docs/token-encryption-and-oauth-security.md
- docs/import-deduplication-and-entity-resolution.md
- docs/schema-api-and-export-version-governance.md
- docs/support-admin-and-abuse-operations.md
- docs/platform-continuity-sunset-and-portability.md
- docs/policy-test-cases.md
- docs/policy-test-cases-media-persona.md
- docs/healthy-attachment-and-dependency-design.md
- docs/empathetic-boundary-response-policy.md

Review output format:

1. Overall verdict
   - ready
   - ready_with_known_risks
   - blocked

2. P0 blockers before implementation
   - implementation must not start until these are fixed

3. P1 fixes before production
   - implementation can start, but production cannot ship until fixed

4. P2 future improvements
   - useful later, not blocking

5. DB schema contradictions
   - especially mismatches between memory-data-model and db-table-design-v1
   - privacy enum drift
   - first migration slice missing tables/columns

6. RLS / AuthZ failure modes
   - cross-user reads
   - missing current_user_id behavior
   - app runtime role owner bypass
   - support/admin raw access
   - FK/unique constraint existence leaks

7. Import pipeline failure modes
   - preview skip
   - direct import-to-memory save
   - parser/schema drift
   - huge import blast radius
   - shared profile contamination
   - raw/log/JSONB leakage

8. Dedupe / Tombstone failure modes
   - deleted data resurrection
   - HMAC/key_version missing
   - low-confidence auto merge
   - dictionary attack risk
   - key rotation risk

9. Delete / Backup / Restore failure modes
   - account deletion mode ambiguity
   - tombstone minimization
   - backup restore resurrecting deleted data
   - search/embedding/tip/export cache invalidation

10. Export / Re-import failure modes
    - raw/media/persona export defaults
    - export package TTL
    - schema version migration
    - tombstone/policy replay on re-import

11. Search / Embedding failure modes
    - vector DB as source of truth
    - embedding all import rows
    - hidden/sealed/deleted search leakage
    - stale embeddings after deletion/privacy change

12. Product safety failure modes
    - AI importance becoming life score
    - persona/relationship drift
    - roleplay/person simulation
    - guilt/streak/loneliness notification copy
    - sensitive surprise reveal in weekly/monthly rituals

13. Concrete recommended doc changes
    - exact file names
    - exact sections to change
    - proposed wording or schema patches

14. Concrete first implementation order
    - only after review
    - no implementation in this task

Important DB contract to verify:

First migration may create only foundation tables:
- app_user
- source_account_ref
- source_ref
- import_job
- import_input_file
- import_detection_result
- import_preview
- import_preview_candidate
- raw_object_ref
- dedupe_key
- deletion_tombstone
- policy_decision
- lifecycle_event
- audit_event
- outbox_event
- key_reference
- oauth_connection

First migration must not create:
- source_item
- source_item_key
- canonical_item
- canonical_item_external_id
- canonical_item_alias
- user_activity
- user_activity_source_link
- memory_record
- memory_source_link
- evidence_record
- search_document
- embedding_record
- export_package
- persona_agent
- relationship_state

Important review focus:
The current design is strong, but do not praise it generically.
Act as a skeptical architecture / privacy / DB / safety reviewer.
Find contradictions, missing constraints, migration risks, and places where an implementation agent would likely take a shortcut.

Do not implement code.
Do not create migration files.
Do not add product features.
Only review and propose precise doc/spec corrections.
```
