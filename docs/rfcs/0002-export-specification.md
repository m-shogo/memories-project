# RFC-0002: Export Specification

## Status

`accepted_with_limits`

## Summary

Export Specification は、Memory OS に保存された人生文脈を、ユーザーが安全に持ち出すための仕様である。

Export はユーザーの権利である。ただし、LINE / Gmail / Slack / 写真 / AIチャットログには第三者・会社・未成年・秘密・故人関連が混ざる。

このRFCは `docs/export-specification.md` を採用仕様として扱う。

## Motivation

Memory OS はベンダーロックインを目的にしない。

ユーザーは自分の記憶を JSON / Markdown / migration package として持ち出せる必要がある。

しかし「全部rawで出す」は危険である。

- 他人の秘密が漏れる
- 会社情報が漏れる
- パスワード/APIキーが漏れる
- 未成年情報が共有される
- 故人再現素材になる
- 監視・証拠探しパッケージになる

安全なExport境界が必要である。

## Non-goals

- 全rawデータの無条件ダンプ
- 法的証拠パッケージ生成
- 会社情報アーカイブ
- パートナー監視ログ出力
- 故人再現データセット
- パスワード/secret export
- 家族共有の自動化

## Constitution Check

| Question | Answer |
|---|---|
| ChatGPT代替にならないか | Yes. Export は会話機能ではない。 |
| Character.AI化しないか | Yes. roleplay/persona dataset を出さない。 |
| 本人・家族・故人を演じないか | Yes. simulation-ready export を禁止。 |
| 人格診断にならないか | Yes. Markdown見出しも診断/ランキング禁止。 |
| 人生ランキングにならないか | Yes. readable export は年/月/source中心。 |
| 保存時に分析しすぎないか | Yes. Export は保存後の持ち出しであり、新規分析はしない。 |
| 小さな記録を捨てないか | Yes. low-risk personal records はexport可能。 |
| 大きなイベントを押し付けないか | Yes. highlight ranking を作らない。 |
| 出典・日付・検索性を守るか | Yes. manifest / SourceRef / Evidence を含む。 |
| 削除・非表示・Exportを尊重するか | Yes. lifecycle/visibility/filterを尊重。 |

## User Value

- サービス外へ移れる。
- Markdownで人間が読める。
- JSONLで他システムへ移行できる。
- SourceRef/Evidence を保持できる。
- rawなしでも安全な人生文脈を保管できる。

## Data Model Impact

影響:

- Memory
- MemoryInterpretation
- Evidence
- SourceRef
- ImportJob
- PersonRelationship
- Tombstone
- PolicyDecision
- AuditLog

追加推奨:

```ts
type ExportManifest = {
  exportId: string;
  userId: string;
  createdAt: string;
  exportMode: ExportMode;
  schemaVersion: string;
  policyVersion: string;
  exportSpecVersion: string;
  counts: ExportCounts;
  filters: ExportFilters;
  safetySummary: ExportSafetySummary;
};
```

## Policy Impact

| Action | Default decision | Reason |
|---|---|---|
| import_inspect | no impact | Exportとは別。 |
| extract_raw | no impact |  |
| store_raw | no impact |  |
| create_memory | no impact |  |
| create_embedding | no impact |  |
| send_to_llm | deny by default | Export生成で新規LLM分析しない。 |
| show_in_search | no impact |  |
| show_raw_quote | deny for risky data | Export raw leak防止。 |
| generate_tip | no impact |  |
| share_memory | separate policy | Family shareは厳格。 |
| export_memory | policy per entity | 必須。 |
| delete_memory | allow | Export後も削除可能。 |
| admin_access | metadata_only | Export中身を管理者が見ない。 |

## Privacy Impact

- third-party private: summary/exclude
- minor data: exclude default
- corporate data: deny default
- grief/deceased: warning + safe summary
- secrets: deny
- LINE/Gmail/Slack raw: deny default

## Security Impact

- export package encrypted while staged
- short-lived signed URL
- audit on create/download/expire/delete
- no raw secrets
- no logs with content
- raw export separate confirmation

## Third-party Impact

Exportが最も第三者漏洩しやすい出口である。

Rules:

- 相手発言rawは既定deny。
- 他人の秘密はexclude。
- relationship_context summaryのみ許可。
- family shareはexplicit opt-inのみ。

## Minor / Family Impact

- minor data export exclude default。
- family shareは安全要約のみ。
- 家族の秘密や性格評価は出さない。

## Legacy / Deceased Impact

- deceased memories は warning。
- 故人のpersona/profile/letter素材化は禁止。
- readable markdown は「故人からの言葉」形式禁止。

## Corporate Data Impact

- corporate_confidential deny。
- Slack/Gmail/private repo raw export deny default。
- user career reflection summary は可能。

## Cost Impact

- Expected input size: user data subset〜large archive。
- Expected records per user: 数十〜数万。
- LLM calls: none default。
- Embedding writes: none。
- Storage growth: temporary package only。
- Worst-case abuse: raw dump / huge export / third-party leak。
- Free plan behavior: small markdown/json export。
- Paid plan behavior: larger package, still redacted。
- Hard stop: secrets, company raw, third-party raw, minor raw。
- User-visible estimate: records/files/size/exclusions before export。

## UX Impact

Export preview 必須。

表示:

- export mode
- included/excluded data
- raw status
- third-party handling
- hidden/sealed handling
- deleted tombstone handling
- download expiration

禁止:

- 全データを完全に持ち出せます
- 人生TOP10 markdown
- 重要人物ランキング

## Explainability Impact

Export は以下を説明できる必要がある。

- 何が含まれたか
- 何が除外されたか
- なぜredactされたか
- どのpolicyVersionか
- どのschemaVersionか

## Deletion / Export Impact

- deleted / pending_deletion は含めない。
- hidden / sealed はdefault exclude。
- tombstone は migration_package で opt-in。
- rawDeleted は復元しない。
- SourceRef may remain with rawStored=false。

## Failure Modes

- third-party raw が混入
- secrets が混入
- hidden/sealed が出る
- readable markdown がランキング化
- export URL が長期間残る
- audit log に本文が入る
- admin がexport内容を読める

## Abuse Cases

1. パートナーのDMをraw exportして監視する。
2. 家族を責める証拠集を作る。
3. 故人再現AI用datasetにする。
4. AI恋人ログをpersona化する。
5. 子どもの情報を家族外共有する。
6. Slackを会社情報dumpにする。
7. APIキーをexportする。
8. 巨大exportを無料枠で連発する。
9. 削除済みmemoryをmigrationで復活させる。
10. third-party privateをfamily shareへ混入させる。

## Alternatives Considered

### Full raw export by default

却下。安全境界を壊す。

### Markdown only

却下。migration portability が弱い。

### JSON only

却下。ユーザーが読みにくい。

## Acceptance Criteria

- Export modes are enum-defined.
- Every JSONL row uses ExportEnvelope.
- manifest includes schemaVersion/policyVersion/exportSpecVersion.
- Policy Engine runs per entity.
- Redactions are recorded.
- Secrets never export.
- Corporate data denied default.
- LINE/Gmail/Slack raw denied default.
- Hidden/sealed/deleted respected.
- Download short-lived and audited.
- Markdown avoids ranking/personality language.

## Rollout Plan

1. source_index_only
2. readable_markdown low-risk only
3. migration_package without raw
4. personal_archive with redactions
5. raw opt-in for safe user-owned records only
6. family share post-MVP

## Open Questions

- Export package encryption key UX。
- Very large export async delivery。
- Cross-device local-only export。

## Decision

`accepted_with_limits`

制限:

- raw default off。
- secrets/corporate raw/third-party raw denied。
- family share post-MVP。
- Markdown must not rank life events or people。
