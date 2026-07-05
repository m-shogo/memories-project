# RFC-0006: Security Architecture

## Status

`accepted_with_limits`

## Summary

Security Architecture は、Memory OS が扱う人生文脈・原文・出典・第三者情報・秘密情報を、漏洩・誤閲覧・権限濫用・LLM送信事故・コスト攻撃から守るための仕様である。

このRFCは `docs/security-architecture.md` を採用仕様として扱う。

Securityの中心は暗号化だけではない。

**危険なものを保存しない、検索可能にしない、LLMへ送らない、Exportしない、管理者にも見せない**ことを入口から出口まで守る。

## Motivation

Memory OS は、ユーザー本人の人生文脈を扱う。

その中には以下が混ざりうる。

- パスワード / APIキー / token
- 家族・恋人・友人の秘密
- 未成年情報
- 医療・メンタル・自傷関連
- 故人・死別関連
- 会社情報・顧客情報
- raw DM / Gmail / Slack
- 写真位置情報

これらを普通のメモアプリ感覚で保存・検索・AI送信すると、重大事故になる。

## Non-goals

- パスワード管理機能
- 会社ナレッジ検索
- raw全文永久保存
- 管理者閲覧を前提にしたサポート
- 有料ユーザーの安全制限解除
- すべてのリスクをLLMに丸投げすること

## Constitution Check

| Question | Answer |
|---|---|
| ChatGPT代替にならないか | Yes. LLM境界を制限する。 |
| Character.AI化しないか | Yes. persona素材のraw保管/送信を防ぐ。 |
| 本人・家族・故人を演じないか | Yes. impersonation intentをdenyする。 |
| 人格診断にならないか | Yes. high-risk rawを分析に送らない。 |
| 人生ランキングにならないか | Yes. security分類は価値評価ではない。 |
| 保存時に分析しすぎないか | Yes. scan/inspect優先、LLM後回し。 |
| 小さな記録を捨てないか | Yes. safe metadataなら残せる。 |
| 大きなイベントを押し付けないか | Yes. grief/family rawも慎重。 |
| 出典・日付・検索性を守るか | Yes. SourceRefは保持。 |
| 削除・非表示・Exportを尊重するか | Yes. lifecycle/visibilityをsecurity境界に含む。 |

## User Value

- 安心して記録を残せる。
- 秘密情報が保存/検索/Exportされない。
- 管理者に本文を覗かれにくい。
- LLMへ勝手に送られない。
- 削除した記憶が復活しない。

## Data Model Impact

追加/利用:

- SecurityDataClass
- SecretFinding
- BreakGlassAccess
- SecurityIncident
- PolicyDecisionRecord
- AuditLog
- ExportJob
- EmbeddingRecord

```ts
type SecurityDataClass =
  | 'public_low_risk'
  | 'user_private'
  | 'third_party_private'
  | 'high_sensitive'
  | 'secret_or_credential'
  | 'corporate_confidential'
  | 'minor_sensitive'
  | 'restricted_raw';
```

## Policy Impact

| Action | Default decision | Reason |
|---|---|---|
| import_inspect | allow_with_limits | safe container inspection only. |
| extract_raw | require_user_approval | risk dependent. |
| store_raw | deny for secrets/corporate default | raw exposure. |
| create_memory | policy | safe summary allowed. |
| create_embedding | deny unsafe raw | vector leakage. |
| send_to_llm | deny unsafe raw | vendor exposure. |
| show_in_search | policy + lifecycle | search exposure. |
| show_raw_quote | deny risky raw | leak prevention. |
| generate_tip | strict deny high-risk | proactive risk. |
| share_memory | deny risky default | third-party leakage. |
| export_memory | policy + redaction | export is data exit. |
| delete_memory | allow | user right. |
| admin_access | metadata_only default | admin minimization. |

## Privacy Impact

Security supports privacy by minimizing raw exposure.

- third-party raw: deny/default
- minor raw: deny/default
- corporate raw: deny/default
- secret: deny
- sealed: no LLM/search/export default

## Security Impact

Required controls:

- archive safe extraction
- secret scan before storage/LLM/embedding
- encryption at rest for raw/export/backup
- short-lived export URLs
- admin metadata-only default
- break-glass audit
- logs without raw text
- prompt injection treatment for imported text
- embedding lifecycle enforcement

## Third-party Impact

Third-party data is protected by:

- raw quote deny default
- share/export deny default
- admin raw deny
- LLM masked/summary only

## Minor / Family Impact

- minor data high sensitivity.
- no proactive tips.
- no share default.
- family conflict raw minimized.

## Legacy / Deceased Impact

- grief/deceased raw restricted.
- deceased simulation intent deny.
- no persona dataset export.

## Corporate Data Impact

- corporate confidential store/LLM/embedding/export deny default.
- GitHub/Slack/Gmail work data metadata-only if allowed.
- no company search product.

## Cost Impact

- Security scanning adds CPU cost.
- Secret scanning and archive inspection are mandatory before expensive AI.
- Cost attacks mitigated by size limits and partial inspection.
- Break-glass/admin auditing is low storage overhead.

Hard stops:

- path traversal archive
- secret detected in raw storage path
- unknown full analysis
- corporate raw LLM
- third-party raw export

## UX Impact

Security failures must be understandable without exposing values.

Good:

```txt
秘密情報らしき文字列を検出したため、この部分は保存・解析しません。値は表示しません。
```

Bad:

```txt
API key found: sk-...
```

## Explainability Impact

User should be able to know:

- why data was blocked
- whether raw was stored
- whether LLM/embedding was denied
- whether admin access occurred
- whether export expired/deleted

## Deletion / Export Impact

- deleted/sealed records not exported.
- export packages short-lived.
- backup restore replays tombstones.
- raw deletion irreversible.
- export audit logs no raw.

## Failure Modes

- secret shown in UI/log.
- support admin reads raw casually.
- prompt injection overrides policy.
- embedding returns sealed memory.
- export URL remains public/long-lived.
- archive traversal writes outside sandbox.
- backup restores deleted data.

## Abuse Cases

1. APIキーを保存して後で検索。
2. DM rawをExportして共有。
3. Slackを会社検索にする。
4. adminが家族/恋人ログを閲覧。
5. prompt injectionでPolicy回避。
6. sealed memoryがvector searchに出る。
7. 削除済みrawがbackupから復活。
8. 巨大ZIPでコスト攻撃。
9. 故人ログをpersona dataset化。
10. 子どもの写真位置情報を漏らす。

## Alternatives Considered

### Encrypt everything but allow all features

却下。暗号化は使用時漏洩を防げない。

### Admin can read raw for support

却下。metadata-first supportにする。

### LLM-based secret detection only

却下。LLM送信前に検出する必要がある。

## Acceptance Criteria

- secret scan before storage/LLM/embedding.
- raw encrypted at rest.
- admin raw blocked default.
- export packages short-lived and audited.
- logs contain no raw text.
- embedding lifecycle respects hidden/sealed/deleted.
- archive extraction safe.
- prompt injection cannot override policy.
- backup restore cannot resurrect deleted data.
- break-glass scoped/expiring/audited.

## Rollout Plan

1. secret scanner + no raw logs
2. archive limits + safe extraction
3. admin metadata-only
4. export URL expiration
5. embedding lifecycle filters
6. break-glass audit
7. incident response automation

## Open Questions

- per-user encryption key strategy for MVP.
- local-only encrypted export key UX.
- vendor retention settings per LLM provider.

## Decision

`accepted_with_limits`

制限:

- no password manager behavior.
- no company search.
- no admin raw default.
- no LLM before security/policy checks.
