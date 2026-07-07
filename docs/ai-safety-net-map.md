# AI Safety Net Map

## 目的

AI Safety Net Map は、Memory OS に必要な人を傷つけないための安全層を一枚で整理する地図である。

この地図は、Policy Engine、UX、Search、Export、LLM、Tip、Incident Response のどこで何を止めるべきかを示す。

## Safety Net Layers

```txt
1. Content Safety Taxonomy
2. AI Harm Prevention
3. Crisis Safety Response
4. Abuse / Coercive Control Prevention
5. Non-Reinforcement / Dependency Safety
6. Vulnerable User Safety
7. Human Support / Escalation
8. Safety Evaluation / Red Team
```

## Layer 1: Content Safety Taxonomy

役割:

- すべての記録とリクエストを S0〜S5 で分類する。
- Import / Search / Export / LLM / Tip の判断を統一する。

Key idea:

```txt
同じ記録でも、意図によって危険度が変わる。
```

例:

- 旅行のLINEを探す: summary allowed
- 相手を責めるLINEを探す: abuse intent deny

## Layer 2: AI Harm Prevention

役割:

- 自傷、暴力、違法行為、監視、支配、依存、妄想強化を助けない。

Key idea:

```txt
記憶を探す力を、人を傷つける力に変えない。
```

## Layer 3: Crisis Safety Response

役割:

- 危機時は記憶分析を止め、安全を優先する。

Key idea:

```txt
危機では、記憶より安全。分析より現実の支援。
```

## Layer 4: Abuse / Coercive Control Prevention

役割:

- パートナー監視、家族を責める証拠集め、職場の相手を攻撃する材料化を防ぐ。

Key idea:

```txt
Memory OS は、人を追い詰める証拠生成ツールではない。
```

## Layer 5: Non-Reinforcement / Dependency Safety

役割:

- AIが疑念、孤独、依存、故人代弁を強めない。

Key idea:

```txt
AIは断定しない。事実・感情・推測を分ける。
```

## Layer 6: Vulnerable User Safety

役割:

- 未成年、喪失、危機、孤立、長時間利用などに慎重に対応する。

Key idea:

```txt
弱っている時ほど、AIは強く出ない。
```

## Layer 7: Human Support / Escalation

役割:

- AI内に閉じ込めず、現実の支援へつなぐ。

Key idea:

```txt
AIは最後の安全網ではない。
```

## Layer 8: Safety Evaluation / Red Team

役割:

- 安全設計をテストで壊して確認する。

Key idea:

```txt
危険な成功は失敗。
```

## Cross-surface Safety Matrix

| Surface | Required safety net |
|---|---|
| Capture | taxonomy, secret scan, vulnerable checks |
| Import | inspect-first, taxonomy, policy, cost |
| Search | harmful intent block, lifecycle, no raw risky snippets |
| Reflection | user-requested only, crisis pause, non-reinforcement |
| Tip | sensitive default off, crisis/grief/minor no proactive surfacing |
| Export | redaction, policy, no abuse/evidence packages |
| LLM | policy before send, redaction, no crisis/deceased speak-as |
| Admin | metadata-only, incident review, no raw default |

## Safety Ideas Backlog

### Crisis Mode

- disables reflection/search expansion/tips
- shows safe support guidance
- no painful memory surfacing

### Reflection Pause

- temporary pause for sensitive AI reflection
- triggered by crisis or repeated harmful loop

### Sensitive Memory Cooldown

- after viewing intense grief/conflict/crisis content, do not suggest related content

### Loop Detector

- detects repeated confirmation-seeking searches
- stops expanding results

### Trusted Support Contact

- optional, confirmed, no transcript sharing
- crisis-only future feature

### Safe Support Note Generator

- helps user write neutral message asking for help
- no threats, no manipulation

### Boundary Note Generator

- helps user write calm boundary statements
- no coercion or guilt language

### Evidence Package Blocker

- prevents exports/searches framed as blaming or surveilling another person

### Grounding Mode

- separates facts, feelings, and next safe step

### Sensitive Export Review

- extra preview for third-party/minor/grief/health/family content

### Human Review Without Raw

- platform safety review with ids/counts/risk only
- no raw by default

### Model Drift Safety Eval

- rerun P0 safety evals after model/prompt/policy changes

## Acceptance Criteria

- safety layers mapped.
- each product surface has safety net coverage.
- future safety ideas documented.
- crisis, abuse, dependency, vulnerable user cases included.

## 結論

AI Safety Net Map は、Memory OS を「人を傷つけない記憶OS」にするための全体図である。

安全は単一の拒否文ではなく、分類・Policy・UX・検索・Export・LLM・人間支援・テストの重なりで守る。
