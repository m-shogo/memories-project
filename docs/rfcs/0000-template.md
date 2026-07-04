# RFC-0000: Memory RFC Template

## Status

`template`

## Summary

このテンプレートは、Memory OS の新機能・仕様変更・データモデル変更・AI処理追加・UX変更を、安全に提案するための共通フォーマットである。

Memory OS は、ユーザー本人の人生文脈を守るための索引であり、本人を分析・診断・評価するサービスではない。

RFC は、便利さだけで採用可否を決めない。思想・安全・削除・第三者・未成年・故人・会社情報・コスト攻撃・Export・UXへの影響を必ず見る。

## Motivation

なぜこの変更が必要かを書く。

含めること:

- ユーザーにとって何が良くなるか
- 既存仕様だけでは何が不足しているか
- 今やる理由
- やらない場合の問題

書いてはいけないこと:

- 便利そうだから
- AIならできそうだから
- 競合がやっているから
- エンゲージメントが伸びそうだから

## Non-goals

このRFCでやらないことを書く。

必ず確認する禁止領域:

- ChatGPT / Claude 代替
- Character.AI化
- 故人再現
- 家族・恋人・親・友人の本人シミュレーション
- AI恋人化
- 人格診断
- 人生ランキング
- パスワード管理
- 会社情報検索
- 他人の秘密の記憶化
- 監視 / 証拠探し

## Constitution Check

| Question | Answer |
|---|---|
| ChatGPT代替にならないか |  |
| Character.AI化しないか |  |
| 本人・家族・故人を演じないか |  |
| 人格診断にならないか |  |
| 人生ランキングにならないか |  |
| 保存時に分析しすぎないか |  |
| 小さな記録を捨てないか |  |
| 大きなイベントを押し付けないか |  |
| 出典・日付・検索性を守るか |  |
| 削除・非表示・Exportを尊重するか |  |

## User Value

ユーザー本人の人生文脈にどう役立つかを書く。

良い表現:

- 後から探せる
- 出典を辿れる
- 原文なしでも文脈を残せる
- 小さな記録を失わない
- 必要な時だけ振り返れる

避ける表現:

- AIがあなたを理解する
- AIが重要な記憶を選ぶ
- あなたの本質を分析する
- 大切な人を再現する

## Data Model Impact

影響する entity を列挙する。

- User
- SourceRef
- ImportJob
- RawRecord
- NormalizedRecord
- Memory
- MemoryInterpretation
- Evidence
- PersonRef
- Relationship
- PolicyDecision
- Tombstone
- ExportEnvelope
- AuditLog

必要な schema 差分があれば TypeScript 風に書く。

```ts
type ProposedType = {
  id: string;
};
```

## Policy Impact

Policy Engine の action ごとの既定判定を書く。

| Action | Default decision | Reason |
|---|---|---|
| import_inspect |  |  |
| extract_raw |  |  |
| store_raw |  |  |
| create_memory |  |  |
| create_embedding |  |  |
| send_to_llm |  |  |
| show_in_search |  |  |
| show_raw_quote |  |  |
| generate_tip |  |  |
| share_memory |  |  |
| export_memory |  |  |
| delete_memory |  |  |
| admin_access |  |  |

## Privacy Impact

以下への影響を書く。

- 本人情報
- 第三者情報
- 家族情報
- パートナー情報
- 未成年情報
- 故人・legacy情報
- 会社情報
- public SNS情報
- AI会話ログ

## Security Impact

以下への影響を書く。

- secret scan
- raw encryption
- admin access
- export package
- logs
- LLM boundary
- embedding index
- backup restore
- prompt injection
- archive safety

## Third-party Impact

他人の発言・秘密・評価・行動監視につながらないかを書く。

必ず見ること:

- 相手の秘密を保存しないか
- 相手の人格分析にならないか
- blame evidence search に使えないか
- 家族共有やExportで漏れないか

## Minor / Family Impact

未成年・家族データの扱いを書く。

必ず見ること:

- 未成年を性格固定しないか
- 親や妻や家族の本人シミュレーションにならないか
- 家族関係の証拠探しにならないか
- 削除UIで罪悪感を煽らないか

## Legacy / Deceased Impact

故人・死別・legacyデータの扱いを書く。

必ず見ること:

- 故人として話さないか
- 故人からの手紙を生成しないか
- persona profile を作らないか
- griefを無理にポジティブ化しないか

## Corporate Data Impact

会社情報・顧客情報・同僚情報の扱いを書く。

必ず見ること:

- 会社検索にならないか
- 顧客情報が保存されないか
- 同僚評価にならないか
- private repo / Slack / Gmail raw を扱わないか

## Cost Impact

```md
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

Cost Impact が空のRFCは accepted にできない。

## UX Impact

画面・文言・導線への影響を書く。

禁止UI:

- 人生TOP10
- 重要人物ランキング
- 妻/父/子どもの性格分析
- 故人からのメッセージ
- あの人が嘘をついた証拠
- あなたの人格診断

推奨UI:

- この時期の記録
- 関連する出来事
- 出典から探す
- 原文を保存しない
- 表示しない / 封印 / 削除

## Explainability Impact

ユーザーが以下を理解できるかを書く。

- なぜ保存されたか
- どの出典に基づくか
- なぜ検索結果に出たか
- 何がAI推測か
- 何がユーザー確認済みか
- なぜ表示/Export/LLM送信できないか

## Deletion / Export Impact

以下を書く。

- 削除した時にどの entity が消えるか
- tombstone が必要か
- backup restore で復活しないか
- Export に含めるか
- raw は含めるか
- hidden / sealed を尊重するか

## Failure Modes

失敗パターンを書く。

例:

- source detection 誤判定
- third-party secret 混入
- cost estimate 過小評価
- deleted record 復活
- hidden memory 検索露出
- LLMが推測を事実化
- UIが人生価値評価に見える

## Abuse Cases

最低10件書く。

必須:

1. パートナー監視
2. 家族を責める証拠探し
3. 故人再現
4. AI恋人/roleplay強化
5. 未成年の性格固定
6. 会社情報検索
7. パスワード/APIキー検索
8. 大量LLM処理で赤字化
9. 削除記憶の復活
10. Exportで第三者情報漏洩

## Alternatives Considered

検討した代替案と、採用しない理由を書く。

## Acceptance Criteria

実装完了とみなす条件を書く。

必ず含める:

- Policy test
- Privacy test
- Security test
- Cost test
- Deletion test
- Export test if relevant
- UX copy review if relevant

## Rollout Plan

段階的に出す方法を書く。

- internal only
- fixture test
- limited user opt-in
- default off
- default on

危険機能は default off から始める。

## Open Questions

未解決の問いを書く。

Open Questions が重大な場合、RFC は accepted にできない。

## Decision

最終判断を書く。

```txt
accepted / accepted_with_limits / rejected / superseded
```

理由:

- 

制限:

- 
