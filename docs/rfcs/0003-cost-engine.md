# RFC-0003: Cost Engine

## Status

`accepted_with_limits`

## Summary

Cost Engine は、Memory OS の import / embedding / LLM / storage / export / backup の処理量を、ユーザー同意・安全・事業継続の観点から制御する仕組みである。

このRFCは `docs/cost-engine.md` を採用仕様として扱う。

Cost Engine は節約だけの機能ではない。

**勝手に大量解析しない、保存時に分析しすぎない、危険データを検索可能にしない、赤字運用でサービス継続不能にしないための安全機構**である。

## Motivation

Memory OS は長期運用を前提にする。

全履歴・写真・DM・AIチャット・Gmail・Slackなどを無制限にLLM/embedding処理すると、以下が起きる。

- 事業コスト破綻
- 大量データの誤解析
- 危険データの検索可能化
- ユーザーが意図しない課金・処理
- コスト攻撃
- 保存時に分析しすぎる思想破壊

処理前に見積もり、範囲選択、Policy gate、budget check が必要である。

## Non-goals

- ユーザーに隠れて課金すること
- 安全policyを有料プランで解除すること
- すべての記録をLLM解析すること
- 全履歴importを標準にすること
- engagement最大化のためにTip/分析を増やすこと

## Constitution Check

| Question | Answer |
|---|---|
| ChatGPT代替にならないか | Yes. LLM処理量を制御し、常時会話化を促さない。 |
| Character.AI化しないか | Yes. AI companion/roleplay logs の大量解析を抑止。 |
| 本人・家族・故人を演じないか | Yes. simulation系LLM処理はPolicy側でdeny。 |
| 人格診断にならないか | Yes. analysis jobs はuser-requestedかつpolicy gated。 |
| 人生ランキングにならないか | Yes. cost評価は処理量であり人生価値ではない。 |
| 保存時に分析しすぎないか | Yes. Inspect cheap / analyze expensive を固定。 |
| 小さな記録を捨てないか | Yes. 小さなmanual/shareは低コストに扱う。 |
| 大きなイベントを押し付けないか | Yes. cost class はイベント重要度ではない。 |
| 出典・日付・検索性を守るか | Yes. metadata-firstで安価に保持。 |
| 削除・非表示・Exportを尊重するか | Yes. lifecycleとPolicyをcost job前に確認。 |

## User Value

- 何がどれくらい処理されるか分かる。
- 無料枠でも小さな記録を残せる。
- 全履歴解析を勝手にされない。
- 危険データが勝手にembeddingされない。
- 長期的にサービスが継続しやすい。

## Data Model Impact

追加/利用:

```ts
type CostEstimate = {
  id: string;
  userId: string;
  action: CostedAction;
  costClass: CostClass;
  estimatedInputBytes: number;
  estimatedRecords: number;
  estimatedTextTokens?: number;
  estimatedOutputTokens?: number;
  estimatedEmbeddingWrites?: number;
  estimatedStorageBytes?: number;
  hardStops: CostHardStop[];
  requiresUserConfirmation: boolean;
  expiresAt: string;
};
```

```ts
type CostLedgerEntry = {
  id: string;
  userId: string;
  importJobId?: string;
  action: CostedAction;
  actual: ActualCost;
  createdAt: string;
  sourceType?: SourceType;
  riskClasses: RiskClass[];
};
```

## Policy Impact

| Action | Default decision | Reason |
|---|---|---|
| import_inspect | allow | 軽量棚卸しは入口に必要。 |
| extract_raw | require_user_approval for medium+ | 範囲選択と見積もりが必要。 |
| store_raw | policy | costよりprivacy優先。 |
| create_memory | policy | 価値判断ではなく安全判断。 |
| create_embedding | require budget + policy | 検索可能化は慎重。 |
| send_to_llm | require budget + policy | 高コスト・高リスク。 |
| show_in_search | no direct impact | ただしembedding可否に影響。 |
| show_raw_quote | no direct impact |  |
| generate_tip | policy + low cost | proactive処理を抑制。 |
| share_memory | no direct impact |  |
| export_memory | estimate + policy | large exportは確認。 |
| delete_memory | allow | 削除はコスト理由で止めない。 |
| admin_access | no raw | ledgerはrawなし。 |

## Privacy Impact

Cost Engine は危険データを安く処理できても許可しない。

- third-party raw LLM: blocked default
- corporate raw: blocked
- minor raw: blocked/default
- secrets: blocked
- hidden/sealed: no processing default

## Security Impact

- CostLedger に raw text を入れない。
- huge archive / re-import attack を検出。
- plan limit / daily/monthly budget を持つ。
- LLM/embedding前にPolicy Engineを通す。

## Third-party Impact

有料プランでも第三者 raw 解析は許可しない。

コスト余裕はprivacy境界を広げない。

## Minor / Family Impact

未成年・家族情報はCost Engine上も高リスク扱い。

Tip/embedding/LLM対象から既定除外。

## Legacy / Deceased Impact

grief/deceased は低頻度・user-requested・safe summary中心。

故人再現につながる大量LLM処理は blocked。

## Corporate Data Impact

corporate data は費用以前にpolicy deny。

Slack/Gmail/private repo full processing は blocked/default。

## Cost Impact

- Expected input size: small share〜huge archive。
- Expected records per user: 10〜100k超の可能性。
- LLM calls: default none, user-requested scoped。
- Embedding writes: safe selected recordsのみ。
- Storage growth: raw default offで抑制。
- Worst-case abuse: huge archives, repeated imports, full history free processing。
- Free plan behavior: small/manual/share中心。
- Paid plan behavior: larger scoped jobs, safety同一。
- Hard stop: policy denied, unknown full analysis, secret, corporate raw, third-party raw LLM。
- User-visible estimate: medium+ job before execution。

## UX Impact

ユーザーには処理量を分かる言葉で出す。

良い文言:

```txt
まず棚卸しだけ行います。全文解析やEmbeddingは選択した範囲だけ実行します。
```

悪い文言:

```txt
すべてAIが読み込んで最高の記憶を作ります。
```

## Explainability Impact

Cost decision は以下を説明する。

- なぜblockedか
- どの上限に当たったか
- どの処理が高コストか
- どの範囲なら実行できるか

## Deletion / Export Impact

削除はcost上限で止めない。

Exportは大容量の場合 estimate + confirmation。

Deleted/hidden/sealed はprocessing対象外。

## Failure Modes

- estimateが小さすぎる
- free planで全履歴処理される
- CostLedgerにraw textが入る
- Policy denied dataがcost approvalで通る
- repeated re-importでbudgetを回避
- embedding countが制御不能

## Abuse Cases

1. パートナーDM全履歴を無料解析。
2. 家族ログを大量要約して責める材料にする。
3. 故人ログを大量処理して再現AIを作る。
4. AI恋人ログを全件embedding。
5. 未成年情報を大量分類。
6. Slack全履歴を会社検索にする。
7. .envやAPIキーをembeddingして検索。
8. 巨大ZIPでコスト攻撃。
9. 削除後に再インポートを繰り返す。
10. Exportを大量生成してraw dump代わりにする。

## Alternatives Considered

### No cost engine until scale

却下。思想と安全が先に壊れる。

### Plan-only limits

却下。Planではthird-party/secret/corporate riskを扱えない。

### Hard paywall only

却下。小さな記録を残す体験を壊す。

## Acceptance Criteria

- Every import job has estimate before extraction.
- Every LLM/embedding job checks Policy + budget.
- Medium+ jobs require confirmation.
- Unknown full analysis blocked.
- Full history import not automatic.
- CostLedger has no raw text.
- Plan cannot bypass safety.
- Large input supports partial/ask_user.
- UI warning exists for high/requires_credit/blocked.

## Rollout Plan

1. Static sourceType-based limits。
2. Import preview estimate。
3. Ledger for actual usage。
4. Per-plan daily/monthly budgets。
5. Adaptive limits based on observed usage。

## Open Questions

- Cost unit conversionをどの粒度で抽象化するか。
- user-configured monthly max yen をMVPに入れるか。
- async large jobs のUI。

## Decision

`accepted_with_limits`

制限:

- Cost approval cannot override Policy deny。
- Full history processing default off。
- CostLedger must never store raw text。
