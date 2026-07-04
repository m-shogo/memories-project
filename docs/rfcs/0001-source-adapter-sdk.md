# RFC-0001: Source Adapter SDK

## Status

`accepted_with_limits`

## Summary

Source Adapter SDK は、外部サービス・ファイル・共有入力を Memory OS に取り込むための実装境界である。

Adapter は分析器ではなく変換器である。入力を安全に受け取り、出典・日付・検索性・削除可能性を守り、Policy Engine / Cost Engine / Memory Schema に渡せる形へ整える。

このRFCは `docs/source-adapter-sdk.md` を採用仕様として扱う。

## Motivation

Memory OS は、AIチャット履歴、LINE、写真メタデータ、カレンダー、GitHub、手動メモなど、多様な source を扱う。

しかし入口が曖昧だと、以下が起きる。

- 全文を保存前にLLMへ送る
- 他人の秘密を記憶化する
- 会社情報を個人記憶として取り込む
- パスワード/APIキーを検索可能にする
- source/date/evidence を失う
- 削除しても再インポートで復活する
- コスト見積もりなしに大量embeddingする

Source Adapter SDK は、これらを入口で防ぐために必要である。

## Non-goals

- universal scraper を作ること
- 全サービスの全形式を完全parseすること
- すべてのログを自動Memory化すること
- import時に人格分析すること
- ChatGPT / Claude 代替を作ること
- Character.AIやAI恋人を強化すること
- 故人・家族・恋人の本人シミュレーション素材を作ること
- 会社検索・パスワード検索を便利にすること

## Constitution Check

| Question | Answer |
|---|---|
| ChatGPT代替にならないか | Yes. Adapter は会話応答を作らず、取り込み境界だけを定義する。 |
| Character.AI化しないか | Yes. roleplay/AI companion logs は自動Memory化しない。 |
| 本人・家族・故人を演じないか | Yes. persona profile や speak-as 用データを作らない。 |
| 人格診断にならないか | Yes. normalization は検索性の整形だけ。 |
| 人生ランキングにならないか | Yes. importance 判断をAdapter責務から除外。 |
| 保存時に分析しすぎないか | Yes. Inspect Before Analyze を強制。 |
| 小さな記録を捨てないか | Yes. safe metadata/source/date/search text は残せる。 |
| 大きなイベントを押し付けないか | Yes. Adapter はイベント価値を決めない。 |
| 出典・日付・検索性を守るか | Yes. SourceRef / occurredAt / searchableText を中心にする。 |
| 削除・非表示・Exportを尊重するか | Yes. tombstone / raw policy / export safety hints を持つ。 |

## User Value

- ユーザーが明示的に渡した記録を、安全に取り込める。
- 出典・日付・検索性が揃う。
- 原文を保存しない選択ができる。
- 危険なデータは取り込み前に分かる。
- 全履歴解析ではなく、範囲選択できる。

## Data Model Impact

影響:

- SourceRef
- ImportJob
- RawRecord
- NormalizedRecord
- Evidence
- PolicyDecision
- DeletionTombstone
- CostEstimate

追加推奨:

```ts
type AdapterId = string;

type AdapterRuntime = 'server' | 'client' | 'local_cli' | 'worker';

type AdapterRunMode = 'inspect_only' | 'metadata_only' | 'scoped_extract' | 'blocked';
```

## Policy Impact

| Action | Default decision | Reason |
|---|---|---|
| import_inspect | allow | 棚卸しは低コスト・低リスクで必要。 |
| extract_raw | require_user_approval | scope選択後のみ。 |
| store_raw | masked_only / summary_only / deny | source risk に依存。 |
| create_memory | require_user_approval for high risk | 家族/医療/他人秘密など。 |
| create_embedding | deny for unsafe raw | safe normalized text のみ。 |
| send_to_llm | summary_only / masked_only | Inspect後・Policy後のみ。 |
| show_in_search | policy | visibility/lifecycle依存。 |
| show_raw_quote | deny default for third-party | 原文漏洩防止。 |
| generate_tip | deny for high risk | proactive resurfacing は厳格。 |
| share_memory | deny default for third-party | 相手の秘密保護。 |
| export_memory | policy | Export Specification に従う。 |
| delete_memory | allow | ユーザー権利。 |
| admin_access | metadata_only | raw閲覧禁止default。 |

## Privacy Impact

Source Adapter は privacy boundary の入口である。

- LINE/DM: third_party_limited default
- Photos: metadata-first, location rounding, no face recognition default
- Gmail: very high risk, post-MVP
- Slack/work: corporate_data default
- AI chat exports: user discussion evidence, not fact evidence

## Security Impact

必須:

- archive safety
- secret scan
- path traversal rejection
- huge input limit
- no raw secret logging
- LLM boundary before send
- embedding deny for unsafe raw

## Third-party Impact

Adapter は speaker separation を可能な限り行う。

第三者 raw は原則 summary-only / masked / excluded。

相手の秘密、性格診断、本心推測、監視意図の抽出は禁止。

## Minor / Family Impact

- minor data は high risk。
- family data は relationship_context のみ。
- 家族の性格評価や blame evidence 化は禁止。

## Legacy / Deceased Impact

- deceased/legacy data は memory summary / values reference のみ。
- persona profile / simulation seed / speak-as は作らない。

## Corporate Data Impact

- Slack/Gmail/private repo/code は default deny or metadata-only。
- user work context は扱えるが、会社情報検索は作らない。

## Cost Impact

- Expected input size: share/manual は小、archive は大。
- Expected records per user: 数十〜数万。
- LLM calls: default none. scope後のみ。
- Embedding writes: safe normalized selected subsetのみ。
- Storage growth: raw保存を抑制。
- Worst-case abuse: huge ZIP, re-import, free full history。
- Free plan behavior: inspect + small selected extract。
- Paid plan behavior: larger scoped extract, safety policyは同じ。
- Hard stop: unknown full analysis, secrets, corporate raw, third-party raw LLM。
- User-visible estimate: import preview に表示。

## UX Impact

Import Preview が必須。

表示:

- source type
- counts
- date range
- sensitive finding count
- excluded by default
- cost estimate
- raw/LLM/embedding settings

禁止:

- 全部読み込んでAIが大切な記憶を選ぶ
- 相手の秘密や会社情報を便利に検索できる表現

## Explainability Impact

Adapter output は以下を説明できる必要がある。

- どのsourceから来たか
- いつimportされたか
- raw保存したか
- なぜ除外/要約/マスクされたか
- LLM/embedding対象か

## Deletion / Export Impact

- RawRecord は contentHash を持つ。
- importJobId で一括削除可能。
- tombstone で再インポート復活を防ぐ。
- Export は SourceRef / rawStored / redaction を尊重。

## Failure Modes

- source detection 誤判定
- unknown source を深掘りしてしまう
- secret をログに出す
- LINE相手発言を本人発言として扱う
- missing date をAIが作る
- full history を勝手にembedding
- deleted record を再インポートで復活

## Abuse Cases

1. パートナーLINEを取り込み監視に使う。
2. 家族の悪い証拠を探す。
3. 故人の発言を集めて再現チャットを作る。
4. AI恋人ログから人格を作る。
5. 子どもの発言を性格診断する。
6. Slackを会社検索にする。
7. .env を取り込み後で検索する。
8. 巨大ZIPで無料枠を燃やす。
9. 削除済みログを再インポートする。
10. Exportで相手のDM rawを漏らす。

## Alternatives Considered

### Direct import without SDK

却下。sourceごとの安全境界が散らばり、Policy/Cost/Deletionが抜ける。

### LLM-first import

却下。保存前に分析しすぎる。秘密・第三者・会社情報の漏洩リスクが高い。

### Raw-first archive

却下。パスワード管理・会社検索・監視用途に近づく。

## Acceptance Criteria

- Adapter interface compiles as TS types.
- detect/inspect/estimateCost/plan/extract/normalize の順を守る。
- unknown source は inspect only。
- one safe fixture produces SourceRef + RawRecord + NormalizedRecord。
- one risky fixture is blocked before LLM/embedding。
- secret value is not displayed/logged。
- deletion tombstone prevents resurrection。
- no adapter bypasses permissions。
- 15 required test categories are implemented.

## Rollout Plan

1. manual_paste
2. share_text
3. ChatGPT selected subset
4. LINE text summary-only
5. Google Calendar
6. Photos metadata only
7. GitHub metadata only

Gmail / Slack / Discord full import は post-MVP。

## Open Questions

- Adapter runtime を client/server/local でどう分けるか。
- sourceごとの parser version migration。
- very large import の非同期UX。

## Decision

`accepted_with_limits`

制限:

- full history import はdefault off。
- raw保存はsourceごとに厳格。
- unknown source full analysis はblocked。
- Gmail/Slack/DiscordはMVP対象外。
