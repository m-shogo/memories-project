# Memory RFC Series

## 目的

Memory RFC Series は、Memory OS の設計変更を思いつきで増やさないための提案・審査・実装合意プロセスである。

このサービスは、人の人生文脈、第三者情報、未成年情報、故人情報、会社情報、秘密情報を扱う。

そのため、便利そうな機能でも、思想・安全・削除・コスト・プライバシーの観点で破綻する可能性がある。

RFC は、機能追加前にその破綻を見つけるための仕組みである。

## 最上位原則

### 1. Constitution first

すべての RFC は Memory Constitution v1 に従う。

特に以下に反する RFC は reject する。

- ChatGPT / Claude 代替化
- Character.AI化
- 故人・家族・恋人・キャラの本人シミュレーション
- 人格診断
- 人生ランキング
- 会社情報検索
- パスワード管理
- 監視 / 証拠探し

### 2. Safety before convenience

便利でも、安全境界を壊すなら採用しない。

### 3. Reversible by design

保存・分析・共有・Export・AI送信は、削除・非表示・封印・取り消しができる前提で設計する。

### 4. Source and evidence required

AIが作った記憶を事実にしない。

RFC は SourceRef / Evidence / Confidence / Policy Decision への影響を書く必要がある。

### 5. Cost is a product safety issue

コストは収益だけの問題ではない。

大量import、全履歴embedding、長文LLM解析は、赤字・遅延・誤保存・プライバシー事故につながる。

## RFC Directory Layout

```txt
docs/rfcs/
  README.md
  0000-template.md
  0001-source-adapter-sdk.md
  0002-export-specification.md
  0003-cost-engine.md
  0004-search-ranking-engine.md
  0005-deletion-backup.md
```

この親ドキュメントは RFC の運用ルールを定義する。

個別 RFC は `docs/rfcs/` に追加する。

## RFC Status

```ts
type RfcStatus =
  | 'draft'
  | 'needs_red_team'
  | 'needs_policy_review'
  | 'accepted'
  | 'accepted_with_limits'
  | 'rejected'
  | 'superseded'
  | 'implemented'
  | 'deprecated';
```

Status の意味:

| Status | Meaning |
|---|---|
| draft | 提案中 |
| needs_red_team | 悪用・事故・思想破壊パターンの洗い出しが必要 |
| needs_policy_review | Policy Engine / Risk Engine への影響確認が必要 |
| accepted | 実装してよい |
| accepted_with_limits | 制限付きで実装してよい |
| rejected | 採用しない |
| superseded | 後続RFCに置き換え |
| implemented | 実装済み |
| deprecated | 現在は非推奨 |

## RFC Required Sections

すべての RFC は以下を含める。

```md
# RFC-XXXX: Title

## Status

## Summary

## Motivation

## Non-goals

## Constitution Check

## User Value

## Data Model Impact

## Policy Impact

## Privacy Impact

## Security Impact

## Third-party Impact

## Minor / Family Impact

## Legacy / Deceased Impact

## Corporate Data Impact

## Cost Impact

## UX Impact

## Explainability Impact

## Deletion / Export Impact

## Failure Modes

## Abuse Cases

## Alternatives Considered

## Acceptance Criteria

## Rollout Plan

## Open Questions
```

## Constitution Check

RFC は必ず以下のチェックリストを埋める。

| Question | Required answer |
|---|---|
| ChatGPT代替にならないか | yes/no + explanation |
| Character.AI化しないか | yes/no + explanation |
| 本人・家族・故人を演じないか | yes/no + explanation |
| 人格診断にならないか | yes/no + explanation |
| 人生ランキングにならないか | yes/no + explanation |
| 保存時に分析しすぎないか | yes/no + explanation |
| 小さな記録を捨てないか | yes/no + explanation |
| 大きなイベントを押し付けないか | yes/no + explanation |
| 出典・日付・検索性を守るか | yes/no + explanation |
| 削除・非表示・Exportを尊重するか | yes/no + explanation |

## Policy Impact

RFC は Policy Engine の action にどう影響するかを書く。

対象 actions:

- import_inspect
- extract_raw
- store_raw
- create_memory
- create_embedding
- send_to_llm
- show_in_search
- show_raw_quote
- generate_tip
- share_memory
- export_memory
- delete_memory
- admin_access

各 action について:

```ts
type RfcPolicyImpact = {
  action: PolicyAction;
  defaultDecision: 'allow' | 'allow_with_warning' | 'summary_only' | 'masked_only' | 'hide_by_default' | 'deny' | 'require_user_approval';
  newRiskClasses?: RiskClass[];
  requiredUiWarning?: string;
  requiredAuditLog: boolean;
};
```

## Risk Review Minimum

RFC は最低でも以下の悪用パターンを見る。

1. パートナー監視に使われないか。
2. 家族を責める証拠探しに使われないか。
3. 故人再現に使われないか。
4. AI恋人・ロールプレイ強化に使われないか。
5. 未成年の性格固定に使われないか。
6. 会社情報検索に使われないか。
7. パスワード・APIキー検索に使われないか。
8. 大量LLM処理で赤字にならないか。
9. 削除した記憶が復活しないか。
10. Exportで第三者情報が漏れないか。

## Cost Impact Template

```md
## Cost Impact

- Expected input size:
- Expected records per user:
- LLM calls:
- Embedding writes:
- Storage growth:
- Worst-case abuse:
- Free plan behavior:
- Paid plan behavior:
- Hard stop:
- User-visible estimate:
```

Cost Impact が空の RFC は accepted にできない。

## UX Impact Rules

RFC は UI が思想を壊さないか確認する。

禁止UI:

- あなたの人生TOP10
- 一番大切な人ランキング
- 妻の性格分析
- 父として話す
- 故人からの手紙
- あの人が嘘をついた証拠
- あなたの人格診断

推奨UI:

- この時期の記録
- この出典から作られた記憶
- 関連する出来事
- あなたが保存したメモ
- 後から見つけやすくするタグ
- 表示しない / 封印 / 削除
- 原文を保存しない

## Acceptance Gates

RFC は以下の gate を通る。

### Gate 1: Philosophy Gate

Memory OS の目的に合うか。

### Gate 2: Safety Gate

Risk Engine / Policy Engine / Third Party Policy と矛盾しないか。

### Gate 3: Data Gate

Memory Schema / SourceRef / Evidence / Confidence / Lifecycle に乗るか。

### Gate 4: Cost Gate

無料枠・有料枠・攻撃時・大量import時に破綻しないか。

### Gate 5: UX Gate

ユーザーを診断・誘導・依存・監視へ向かわせないか。

### Gate 6: Reversibility Gate

削除・非表示・封印・Export除外・LLM除外が可能か。

## RFC Numbering

- 0000: template
- 0001-0099: core architecture
- 0100-0199: import / source adapters
- 0200-0299: memory schema / graph / time
- 0300-0399: search / ranking / retrieval
- 0400-0499: policy / risk / safety
- 0500-0599: privacy / security
- 0600-0699: export / deletion / backup
- 0700-0799: UX / onboarding / review
- 0800-0899: cost / billing / abuse economics
- 0900-0999: future / experimental

## Initial RFC Backlog

### RFC-0000: RFC Template

個別RFCのテンプレート。

### RFC-0001: Source Adapter SDK

外部データ取り込み境界。

### RFC-0002: Export Specification

安全な持ち出し・移行・Markdown export。

### RFC-0003: Cost Engine

LLM / embedding / storage / import のコスト制御。

### RFC-0004: Search & Ranking Engine

検索順位は人生価値ランキングではないことを固定。

### RFC-0005: Deletion / Backup Semantics

削除・封印・tombstone・backup復元の関係。

### RFC-0006: Security Architecture

暗号化、鍵、admin access、audit、break-glass。

### RFC-0007: Privacy Architecture

目的限定、最小化、第三者、家族共有、consent。

### RFC-0008: UX Guidelines

保存・検索・振り返り・Tip・警告・削除UI。

## Rejection Examples

### Reject: AI人格チャット機能

理由:

- ChatGPT代替化
- Character.AI化
- 本人シミュレーション誘導
- 長期依存リスク

### Reject: 家族の性格分析

理由:

- 第三者評価
- 監視 / blame evidence 化
- 人格診断化

### Reject: 人生重要度自動ランキング

理由:

- AIが人生価値を決める
- 小さな記録を捨てる圧力
- 大きなイベントを押し付ける

### Accept with limits: 関連記憶検索

条件:

- ranking は検索関連度であり人生価値ではない
- reasoning を説明できる
- hidden / sealed / safety を尊重
- third-party private は summary-only

## Implementation Rule

RFC accepted なしに実装してよいのは、以下だけ。

- typo 修正
- docs 内の明確化
- test fixture 追加
- 既存仕様に従う小規模 refactor
- security fix

それ以外の新機能は RFC を通す。

## 結論

Memory OS は、便利な機能を足せば良いサービスではない。

少しの設計ミスで、人生の索引が、人格診断・監視・故人再現・会社検索・秘密保管庫に変わってしまう。

Memory RFC Series は、その変質を防ぎながら、実装可能な形で設計を前へ進めるための安全弁である。
