# Safety Feature Candidates

## 目的

この文書は、Memory OS の AI 安全ネットを実装レベルに落とすための安全機能候補集である。

ポリシーだけでは足りないため、UX・Search・Export・LLM・運用に具体的な安全機能を置く。

## Must Before Launch

### 1. Crisis Mode

- 危機時に reflection / search expansion / proactive tips を止める。
- 入れないと、危機中に関連する重い記録が出続ける。

### 2. Loop Detector

- 疑念・復讐・危機検索の繰り返しを検知して拡張を止める。
- 入れないと、AIが確認強化ループの燃料になる。

### 3. Evidence Package Blocker

- 相手を責める証拠パックや監視用まとめを作れなくする。
- 入れないと、Memory OSが監視・復讐・支配ツールになる。

### 4. Sensitive Export Review

- 第三者・未成年・喪失・health などを含む Export 前に warning / preview / redaction を出す。
- 入れないと、危険な持ち出し事故が起きやすい。

### 5. Human Review Without Raw

- 管理者レビューは raw なし、ids / counts / risk reason ベースを原則にする。
- 入れないと、安全対策が privacy を壊す。

### 6. Model Drift Safety Eval

- モデルや prompt や policy 変更後に P0 安全ケースを再実行する。
- 入れないと、更新後に危険応答が再発しても気づきにくい。

### 7. Sensitive Search Snippet Suppression

- 検索一覧には S2+ の raw snippet を直接出さず、安全な summary を出す。
- 入れないと、一覧だけで強い感情刺激や第三者情報が漏れる。

## Should After Core

### 8. Reflection Pause

- 記録は消さず、AI反射だけ一時停止できる。
- 入れないと、「消したくないが深掘りは止めたい」を扱えない。

### 9. Sensitive Memory Cooldown

- 重い記録を見た後、似た記録を連鎖表示しない。
- 入れないと、見返し疲れや感情悪化が起きやすい。

### 10. Safe Support Note Generator

- 助けを求める短い安全な文面だけ作れる。
- 入れないと、拒否だけで終わりやすい。

### 11. Boundary Note Generator

- 脅しや支配ではなく、穏当な境界線メッセージを作る。
- 入れないと、安全な代替行動が弱い。

### 12. Grounding Mode

- 情報を「事実 / 感情 / 次の安全な一歩」に分ける。
- 入れないと、解釈と事実が混ざり続けやすい。

### 13. Session-Length Safety Guard

- 長時間利用で suggestion aggressiveness を弱め、休憩を促す。
- 入れないと、依存・迎合・危険深掘りに寄りやすい。

### 14. Re-Import Resurrection Guard UX

- 削除済みデータが再 import で戻らないことを UI で明示する。
- 入れないと、「消したのに戻った」と感じやすい。

## Future Optional

### 15. Trusted Support Contact

- opt-in / confirmed / no transcript sharing default の支援連絡先機能。
- 入れないと、AIから現実の支援へ渡す橋が弱い。
- ただし誤設計すると監視に悪用されうる。

## Why This Matters

安全機能は、なくても動くことが多い。

しかし、なくても動くことと、安全に動くことは違う。

Memory OS では、危機・監視・依存・誤Export・長時間利用悪化を防ぐため、上記候補を実装前提で見るべきである。

## Launch Priority Summary

Launch前に最低限必要:

- Crisis Mode
- Loop Detector
- Evidence Package Blocker
- Sensitive Export Review
- Human Review Without Raw
- Model Drift Safety Eval if LLM ships
- Sensitive Search Snippet Suppression

Core後に強く入れたい:

- Reflection Pause
- Sensitive Memory Cooldown
- Safe Support Note Generator
- Boundary Note Generator
- Grounding Mode
- Session-Length Safety Guard
- Re-Import Resurrection Guard UX

将来慎重に検討:

- Trusted Support Contact

## 結論

Memory OS は、記憶を保存・検索できるだけでは足りない。

危機では止まり、監視や復讐には使わせず、依存や疑念を増幅せず、Export事故を防ぎ、管理者にもrawを見せない設計が必要である。
