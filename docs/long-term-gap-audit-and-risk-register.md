# Long-term Gap Audit and Risk Register

## 目的

この文書は、Memory OS を数年ではなく、10年・20年・30年続ける前提で、まだ不足しがちな設計領域を洗い出し、実装前に塞ぐためのrisk registerである。

DB、Import、Policy、Exportだけでは足りない。

長期運用では、以下で壊れる。

- 料金設計が甘くて赤字になる
- 法務/地域/未成年/第三者データが曖昧
- support/admin権限が強すぎる
- 退会/事業撤退/買収時にExportできない
- schema/API変更で古いExportが読めない
- abuse対応がなく、監視/証拠探し/なりすましに使われる
- AI model/provider変更で過去の解釈が変わる
- backup/restoreで削除済みが復活する
- user trustが崩れるcopy/notification/暗黙分析が入る

## Current Verdict

```txt
ready_with_known_risks
```

実装に近いが、長期運用では以下の領域をP0/P1で補強する。

## Risk Severity

```ts
type LongTermRiskSeverity = 'P0_existential' | 'P1_major' | 'P2_medium' | 'P3_low';
```

- P0_existential: 事業/信頼/安全が終わる
- P1_major: 大規模修正が必要になる
- P2_medium: 運用負荷が大きい
- P3_low: 後からでも直せる

## P0 Existential Risks

### RISK-LT-001 Cost runaway

Problem:

- raw media, embeddings, LLM summaries, exports, backups, API syncが無制限に増える。

Impact:

- 赤字化。
- 無料ユーザーが増えるほど破産。
- 途中で機能停止すると信頼を失う。

Required controls:

- plan-based quotas.
- cost ledger per user/source/action.
- lazy embeddings.
- raw TTL.
- export package TTL.
- per-source sync limits.
- abuse rate limits.

Docs:

- `docs/business-cost-and-plan-sustainability.md`
- `docs/cost-engine.md`
- `docs/db-operational-guardrails.md`

### RISK-LT-002 Admin/support raw access

Problem:

- support/adminがraw LINE、画像、private bookmark、OAuth token、Export packageを見られると信頼が終わる。

Required controls:

- support sees counts/status/reason codes only.
- break-glass flow only for narrow metadata.
- no raw by default.
- admin access audit.
- role separation.
- RLS negative tests.

Docs:

- `docs/support-admin-and-abuse-operations.md`
- `docs/rls-policy-and-negative-tests.md`

### RISK-LT-003 Legal/data rights ambiguity

Problem:

- ユーザー本人データ、第三者データ、未成年、故人、家族、地域別規制、削除権、Export権の境界が曖昧。

Required controls:

- data subject rights model.
- account deletion modes.
- minor/third-party restrictions.
- data residency strategy.
- legal hold restricted mode.
- terms/privacy review before production.

Docs:

- `docs/legal-compliance-and-data-rights.md`
- `docs/minor-and-family-policy.md`
- `docs/legacy-and-deceased-policy.md`

### RISK-LT-004 Exit/sunset failure

Problem:

- 事業撤退・買収・料金変更・サービス終了時に、ユーザーが人生文脈を持ち出せない。

Required controls:

- portability-first export.
- sunset plan.
- read-only grace period.
- bulk export safety.
- documented export format.
- migration guide.

Docs:

- `docs/platform-continuity-sunset-and-portability.md`
- `docs/export-specification.md`
- `docs/export-safety-and-reauthentication.md`

### RISK-LT-005 Persona/impersonation drift

Problem:

- 長期で機能追加されるうちに、AI恋人・故人再現・他人代弁へずれる。

Required controls:

- persona activation never introduced.
- persona-like import simulationAllowed=false.
- product review gate for any conversational feature.
- policy tests blocking speak-as.

Docs:

- `docs/persona-import-export-safety.md`
- `docs/identity-and-impersonation-safety.md`
- `docs/policy-test-cases-media-persona.md`

### RISK-LT-006 Schema/API/export incompatibility

Problem:

- 5年後、昔のExport/Import/schemaが読めない。

Required controls:

- versioned export manifest.
- backward-compatible readers.
- migration policy.
- deprecation windows.
- compatibility test corpus.

Docs:

- `docs/schema-api-and-export-version-governance.md`
- `docs/compatibility-policy.md`

## P1 Major Risks

### RISK-LT-007 Support burden explosion

Controls:

- self-serve export/delete.
- clear import status.
- non-raw diagnostics.
- user-visible policy reasons.
- safe error messages.

### RISK-LT-008 Notification creep

Controls:

- no guilt/streak copy.
- no sensitive proactive tips.
- notification category allowlist.
- quiet defaults.

### RISK-LT-009 Backup restore mismatch

Controls:

- tombstone replay.
- derived search/embedding invalidation.
- restore drills.
- account deletion mode handling.

### RISK-LT-010 Third-party API lock-in

Controls:

- every S-rank service has non-API path.
- paste/manual/export first.
- provider-specific review.
- adapter isolation.

### RISK-LT-011 AI provider/model change

Controls:

- model version stored.
- AI interpretation separated from fact.
- no automatic reinterpretation.
- reprocessing requires policy/user-aware flow.

### RISK-LT-012 Data quality decay

Controls:

- source provenance.
- confidence levels.
- user corrections.
- reversible merges.
- no AI overwrite of facts.

## Missing Design Areas Now Added

This gap audit adds/points to new long-term docs:

- `docs/business-cost-and-plan-sustainability.md`
- `docs/legal-compliance-and-data-rights.md`
- `docs/support-admin-and-abuse-operations.md`
- `docs/platform-continuity-sunset-and-portability.md`
- `docs/schema-api-and-export-version-governance.md`

## Long-term Go/No-Go

### Go

Proceed to implementation only if:

- cost ledger and quotas are part of foundation.
- raw/admin access is denied by design.
- Export format is versioned.
- support diagnostics are raw-free.
- account deletion/export/sunset assumptions are documented.
- non-API import route exists for user-priority services.

### No-Go

Do not proceed if:

- free unlimited raw/media/embedding is planned.
- support/admin can read raw content by default.
- Export format is not versioned.
- account deletion mode is undefined.
- API connector is the only path for S-rank services.
- persona activation is introduced.

## 結論

Memory OS は、技術的に保存できるだけでは長く続かない。

長期で必要なのは、赤字防止、法務/地域/権利、support/admin最小権限、事業撤退時のportability、version governance、abuse対応である。

このrisk registerをP0 gateとして扱い、実装前・リリース前・大きな機能追加前に見直す。
