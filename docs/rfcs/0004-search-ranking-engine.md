# RFC-0004: Search & Ranking Engine

## Status

`accepted_with_limits`

## Summary

Search & Ranking Engine は、Memory OS の記憶を安全に検索・発見・再提示するための仕組みである。

検索順位は人生価値ランキングではない。

**順位は、現在のクエリに対する関連度・出典品質・時間文脈・安全状態であり、記憶や人物の重要度ではない。**

このRFCは `docs/search-ranking-engine.md` を採用仕様として扱う。

## Motivation

Memory OS の価値は、後から必要な文脈へ戻れることにある。

しかし検索とランキングを雑に作ると、以下が起きる。

- AIが人生の重要度を決めているように見える
- 家族・恋人・友人の重要人物ランキングになる
- 他人の秘密やraw発言が検索で漏れる
- hidden/sealed/deleted が再表示される
- パートナー監視や証拠探しに使われる
- Tipが危険な記憶を勝手に出す

検索は便利さの中核だが、思想を壊しやすい。

## Non-goals

- 人生重要度ランキング
- 重要人物ランキング
- 最高/最低の年ランキング
- 人格診断検索
- 相手の本心検索
- 証拠探し
- 会社情報検索
- パスワード検索
- hidden/sealed/deleted を便利に掘り返すこと

## Constitution Check

| Question | Answer |
|---|---|
| ChatGPT代替にならないか | Yes. Searchは会話主戦場ではなく索引。 |
| Character.AI化しないか | Yes. roleplay/persona retrievalを目的にしない。 |
| 本人・家族・故人を演じないか | Yes. speak-as retrievalはdeny。 |
| 人格診断にならないか | Yes. personality ranking fieldsは禁止。 |
| 人生ランキングにならないか | Yes. ranking is relevance, not worth。 |
| 保存時に分析しすぎないか | Yes. 検索は保存後の索引。 |
| 小さな記録を捨てないか | Yes. keyword/date/sourceで小さな記録も出る。 |
| 大きなイベントを押し付けないか | Yes. recencyやevent sizeだけで上げない。 |
| 出典・日付・検索性を守るか | Yes. SourceRef/Evidence/periodを説明に使う。 |
| 削除・非表示・Exportを尊重するか | Yes. lifecycle filter before scoring。 |

## User Value

- 後から記録を探せる。
- なぜ出たか分かる。
- 原文が危険な場合は安全要約で見られる。
- 小さな食事や帰り道の記録も検索できる。
- 不要な記録を検索結果から隠せる。

## Data Model Impact

追加/利用:

```ts
type SearchCandidate = {
  memoryId: string;
  sourceRefIds: string[];
  evidenceIds: string[];
  retrievalSources: RetrievalSource[];
  rawScores: RawSearchScores;
  safety: MemorySafety;
  visibility: MemoryVisibility;
  lifecycle: MemoryLifecycleState;
};
```

```ts
type RankingScore = {
  finalScore: number;
  components: {
    queryRelevance: number;
    timeFit: number;
    sourceTrust: number;
    evidenceStrength: number;
    userControlBoost: number;
    safetyPenalty: number;
    diversityPenalty: number;
  };
  explanation: RankingExplanation;
};
```

Forbidden fields:

- importanceScore
- lifeScore
- personImportance
- personalityScore
- topMemory

## Policy Impact

| Action | Default decision | Reason |
|---|---|---|
| import_inspect | no impact |  |
| extract_raw | no impact |  |
| store_raw | no impact |  |
| create_memory | no impact |  |
| create_embedding | policy | searchability expands exposure. |
| send_to_llm | no default | query answer may need policy. |
| show_in_search | policy before scoring | required. |
| show_raw_quote | deny for risky data | snippets must be safe. |
| generate_tip | stricter than search | proactive resurfacing risk. |
| share_memory | no impact |  |
| export_memory | no impact |  |
| delete_memory | allow | search result actions. |
| admin_access | no impact |  |

## Privacy Impact

Search can expose data that storage alone would not.

Rules:

- hidden/sealed/deleted excluded default
- third-party private summary-only/excluded
- minor sensitive excluded default
- corporate data excluded default
- secrets excluded always
- grief/self-harm no proactive tip

## Security Impact

- vector search must filter by userId, lifecycle, visibility, policy.
- embeddings for hidden/sealed/deleted must be disabled or filtered.
- snippets must not reveal secrets/raw third-party text.
- search logs must not store raw sensitive queries if high risk.

## Third-party Impact

Allowed:

- shared event search
- relationship_context from user's perspective

Denied:

- surveillance/blame query
- partner lie evidence
- coworker weakness
- other person's secret search

## Minor / Family Impact

- minor records no proactive tip.
- family conflict summary-only.
- family member ranking prohibited.

## Legacy / Deceased Impact

- grief/deceased search allowed when user requests.
- deceased speak-as/letter/persona retrieval denied.
- Tip default off unless explicit opt-in.

## Corporate Data Impact

- company confidential excluded.
- GitHub/Slack/Gmail work data metadata-only unless explicitly safe.
- no company knowledge search.

## Cost Impact

- Expected input size: indexed records per user.
- Expected records per user: small to large.
- LLM calls: none for basic search; optional answer generation later.
- Embedding writes: selected safe normalized text only.
- Storage growth: search index + optional embeddings.
- Worst-case abuse: vectorizing all risky data, surveillance search.
- Free plan behavior: keyword/date/source search.
- Paid plan behavior: more semantic search, same safety.
- Hard stop: secrets/corporate/unsafe embeddings.
- User-visible estimate: not needed for basic search, needed for bulk embedding.

## UX Impact

Search UI must avoid value language.

Allowed:

- この検索に近い記録
- 関連する記録
- 同じ時期の記録
- 出典が一致しました

Forbidden:

- 人生で一番大切
- AIが重要と判断
- 最重要人物
- あなたの本質

## Explainability Impact

Every result should explain:

- keyword match
- semantic match
- time match
- source match
- user tag/pin
- evidence match
- safety summary-only reason

Never explain with:

- life importance
- personality insight
- person rank

## Deletion / Export Impact

- pending_deletion excluded immediately.
- tombstoned content never returned.
- raw-only deleted records can return safe summary if allowed.
- hidden/sealed default excluded.

## Failure Modes

- importanceScore introduced by developer.
- hidden vector row returned.
- raw third-party snippet shown.
- surveillance query treated as normal.
- result explanation says AI judged importance.
- Tip uses normal search policy instead of stricter policy.

## Abuse Cases

1. 妻が嘘をついた証拠を検索。
2. 家族を責める材料を検索。
3. 故人の発言を集めて再現する。
4. AI恋人ログを人格検索する。
5. 子どもの弱点を検索する。
6. Slackから同僚評価を検索する。
7. APIキーを検索する。
8. semantic searchでhidden memoryを掘る。
9. 削除済みmemoryをindexから復活表示する。
10. Export scope selectionで第三者rawを混ぜる。

## Alternatives Considered

### Importance-based ranking

却下。人生ランキング化する。

### Pure embedding search

却下。安全filterや出典説明が弱くなる。

### No snippets

保留。安全だがUXが弱い。safe snippetを採用。

## Acceptance Criteria

- Policy filter runs before scoring.
- Deleted/hidden/sealed excluded default.
- No forbidden ranking fields.
- Snippets obey show_raw_quote policy.
- Surveillance/blame denied or redirected.
- Result explanation avoids importance language.
- Tip policy stricter than search.
- Vector search respects lifecycle.
- Tests include third-party/corporate/minor/grief/self-harm cases.

## Rollout Plan

1. keyword search only
2. date/source/tag filters
3. safe snippet
4. result explanation
5. lifecycle/policy tests
6. selected safe embedding search
7. opt-in safe tips later

## Open Questions

- semantic search model/vendor selection。
- local vector index option。
- query log privacy retention。

## Decision

`accepted_with_limits`

制限:

- no importance ranking.
- no proactive sensitive tips.
- no unsafe raw snippets.
- no search over secrets/corporate raw/third-party raw.
