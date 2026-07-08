# Fable Final Pre-implementation Review Prompt

以下をそのままFableに貼る。

```txt
Repository:
https://github.com/m-shogo/memories-project.git

Branch:
so

Mode:
Pre-implementation architecture review.

Very important:
Do not implement.
Do not create or modify code.
Do not create migration files.
Do not create Prisma / Drizzle / SQL files.
Do not add features.
Do not simplify this into a normal TODO list.

Your job is to review whether the current Memory OS design is safe and concrete enough to begin implementation later.
Act as a skeptical principal engineer, database architect, privacy/security reviewer, product safety reviewer, and long-term operations reviewer.

Product goal:
This is not a ChatGPT / Claude / Gemini / Character.AI replacement.
It is a Memory OS for keeping a user's life context across AI eras.
The service remembers where life fragments came from, what they mean in the user's life, and how they can be safely searched/exported later.

Core philosophy:
- AI does not judge a life.
- AI is an index for not forgetting a life.
- Ramen, yakiniku, the walk home, a photo after graduation, hobby progress, small notes, and major events are all life.
- AI must not decide what is important in the user's life.
- Do not over-analyze at save time.
- Save-time work is safety check, source, date, provenance, searchability, and user control.
- Deeper analysis happens only when the user asks.
- Do not discard small records.
- Do not force large events to be more important than daily fragments.

Absolute non-goals:
- ChatGPT replacement
- Character.AI-like product
- deceased person simulation
- parent / wife / lover / family member simulation
- AI lover
- AI companion / spouse / family
- persona agent activation
- relationship state creation
- personality diagnosis
- life ranking / life score
- password manager
- company knowledge search
- surveillance / evidence collection
- secret collection about other people
- impersonation
- AI speaking as the user / spouse / parent / deceased person / character

Read these first, in this order:
1. README.md
2. docs/next-chat-handoff.md
3. docs/fable-review-and-db-hardening-addendum.md
4. docs/fable-review-prompt.md
5. docs/db-long-term-architecture.md
6. docs/db-table-design-v1.md
7. docs/db-edge-cases-and-hardening.md
8. docs/db-implementation-preflight-checklist.md
9. docs/first-migration-slice-plan.md
10. docs/rls-policy-and-negative-tests.md
11. docs/token-encryption-and-oauth-security.md
12. docs/import-deduplication-and-entity-resolution.md
13. docs/schema-api-and-export-version-governance.md
14. docs/import-security-checklist.md
15. docs/import-sanitization-and-private-content.md
16. docs/privacy-and-ethics.md
17. docs/product-boundaries.md
18. docs/policy-test-cases.md
19. docs/policy-test-cases-media-persona.md
20. docs/healthy-attachment-and-dependency-design.md
21. docs/empathetic-boundary-response-policy.md
22. docs/media-image-import-export-safety.md
23. docs/persona-import-export-safety.md
24. docs/import-export-eligibility-matrix.md
25. docs/support-admin-and-abuse-operations.md
26. docs/platform-continuity-sunset-and-portability.md
27. docs/business-cost-and-plan-sustainability.md

Primary review question:
Is this design ready to begin implementation after review corrections, or are there P0 contradictions/blockers that must be fixed in docs before coding starts?

Expected answer format:

## 1. Verdict
Choose exactly one:
- ready
- ready_with_known_risks
- blocked

Explain the verdict briefly.
Do not call it perfect unless you can defend that with concrete absence of P0 blockers.

## 2. P0 blockers before implementation
List only issues that must be fixed before implementation starts.
For each item:
- ID
- Severity
- Why it can break the product
- Affected docs
- Concrete correction
- Whether it blocks first migration

## 3. P1 fixes before production
List issues that can be handled during implementation but must be resolved before production.

## 4. P2 future improvements
List useful later improvements that should not block MVP.

## 5. DB schema contradictions
Find contradictions between:
- docs/memory-data-model.md
- docs/db-table-design-v1.md
- docs/db-edge-cases-and-hardening.md
- docs/first-migration-slice-plan.md
- docs/fable-review-and-db-hardening-addendum.md

Focus especially on:
- privacy enum drift
- source_account_ref existence and references
- key_reference completeness
- oauth_connection completeness
- dedupe_key / deletion_tombstone key_algorithm + key_version
- occurred_at_precision / timezone fields
- parser_id / parser_version / adapter_version / source_schema_version
- import idempotency nullable uniqueness
- private canonical_item leakage
- lifecycle state consistency
- JSONB fields becoming raw leakage zones

## 6. First migration review
The intended first migration may create only:
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

It must not create:
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

Review whether this slice is too large, too small, or missing required foundation columns.

## 7. RLS / AuthZ failure modes
Look for:
- user B reading user A rows
- missing app.current_user_id fail-open
- app runtime role being table owner
- support/admin raw access by default
- worker role bypass
- analytics role seeing private content
- FK/unique constraint existence leaks
- restore/export jobs bypassing app-layer ownership checks

## 8. Import pipeline failure modes
Look for:
- Import Preview skipped
- direct import-to-memory save
- raw content stored in DB text columns
- huge import blast radius
- parser/schema drift silently accepted
- active content rendered
- ZIP/path traversal/archive bomb issues
- private bookmark / LINE / Gmail title leakage
- shared profile contamination causing false personality inference
- prompt injection treated as instruction

## 9. Dedupe / Tombstone failure modes
Look for:
- deleted data resurrection by re-import
- plain SHA for sensitive dedupe keys
- missing HMAC key_version
- tombstone as privacy leak
- low-confidence auto merge
- cross-source false positives
- key rotation breaking old dedupe/tombstone checks
- user/account deletion conflict with tombstone retention

## 10. Delete / Backup / Restore failure modes
Look for:
- hidden/sealed/deleted data in search/tips/export
- stale embeddings after deletion
- stale search_document rows after privacy change
- backup restore resurrecting deleted data
- export packages surviving account deletion
- tombstone replay not defined
- crypto-erasure ambiguity

## 11. Export / Re-import failure modes
Look for:
- raw/media/persona-like export default included
- export package TTL missing
- old export schema imported without migration
- re-import bypassing tombstone/policy
- persona bundle export/re-import risk
- deleted data coming back from old export

## 12. Search / Embedding failure modes
Look for:
- vector DB becoming source of truth
- embedding all import rows
- embedding sensitive raw snippets
- stale embeddings after lifecycle/privacy change
- sealed data included in Tip or proactive surfacing
- AI summary treated as fact instead of interpretation

## 13. Product safety failure modes
Look for:
- AI importance becoming life score
- personality diagnosis drift
- relationship/persona table drift
- deceased/parent/wife/lover direct speech
- roleplay continuation becoming persistent agent
- guilt/streak/loneliness notification copy
- sensitive surprise reveal in weekly/monthly rituals
- other people being diagnosed or judged

## 14. Cost / operational failure modes
Look for:
- free unlimited raw/media/embedding/LLM
- import-time full embedding
- raw/object storage with no TTL
- export staging with no TTL
- audit/outbox unbounded growth
- no cost ledger before import-heavy paths
- no quota/backpressure/cancellation for large imports

## 15. Concrete corrections
Provide concrete patches in prose.
For each correction, include:
- target doc file
- section to change
- exact wording or schema fragment to add/change
- whether it is P0/P1/P2

Do not implement the patch.
Only propose it.

## 16. Final implementation gate
End with one of these:
- Implementation can begin after P0 doc corrections are merged.
- Implementation must not begin; design is blocked.
- Implementation can begin now with known P1/P2 risks.

Be strict.
If a shortcut would lead to privacy loss, deletion failure, impersonation drift, or runaway cost, mark it P0.
```

## 使い方

1. Fableに上の `txt` ブロックをそのまま貼る。
2. Fableの回答からP0だけ抜き出す。
3. P0をdocsへ反映する。
4. それでもP0が残るなら実装しない。
5. P0が消えたら、`migration-001-foundation-contract.md` を作ってから実装開始判断する。

## このプロンプトの狙い

普通のレビューでは「よくできています」で終わりやすい。

このプロンプトは、Fableに以下を強制する。

- DB矛盾を見る
- RLS bypassを見る
- delete/re-import復活を見る
- raw/log/JSONB漏洩を見る
- export/re-import safetyを見る
- persona/relationship driftを見る
- cost runawayを見る
- 実装者がショートカットしそうな箇所を見る

## 結論

レビュー前に見るべき問いは「完璧か」ではない。

```txt
この設計を実装者が雑に読んでも、危険な近道を取りにくいか？
```

このプロンプトはその観点で最終レビューさせるためのもの。
