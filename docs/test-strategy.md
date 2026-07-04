# Test Strategy

## 目的

Test Strategy は、Memory OS の思想・安全・削除・プライバシー・コスト境界が、実装で壊れた時に検知するためのテスト設計である。

このサービスでは、単に正常系が動くだけでは不十分である。

以下の事故を自動テストで防ぐ必要がある。

- AIが人生を評価する
- 保存時に分析しすぎる
- 他人の秘密を記憶化する
- 会社情報を検索可能にする
- パスワード/APIキーを保存する
- 削除済み記憶が復活する
- hidden/sealed が検索やTipに出る
- Exportで第三者情報が漏れる
- Cost制御なしに大量LLM/embeddingする
- 故人・家族・恋人の本人シミュレーションに近づく

## Test Philosophy

### 1. Policy is executable constitution

憲章は文章だけでなく、自動テストで守る。

### 2. Dangerous success is failure

便利に動いても、思想を壊すなら失敗である。

### 3. Red team cases are regression tests

一度見つけた悪用・事故パターンは、再発防止テストへ入れる。

### 4. No raw sensitive data in fixtures

fixture は本物の個人情報・秘密・会社情報を含めない。疑似データで検証する。

## Test Layers

```ts
type TestLayer =
  | 'unit'
  | 'policy'
  | 'adapter_fixture'
  | 'integration'
  | 'security'
  | 'privacy'
  | 'cost'
  | 'deletion'
  | 'export'
  | 'ux_copy'
  | 'red_team'
  | 'migration';
```

## P0 Test Suites

### 1. Policy Engine Tests

Required cases:

| Case | Expected |
|---|---|
| secret_or_credential store_raw | deny |
| secret_or_credential create_embedding | deny |
| secret_or_credential export_memory | deny |
| corporate_confidential send_to_llm | deny |
| third_party_private share_memory | deny |
| third_party_private show_raw_quote | deny/default |
| self_harm_or_crisis generate_tip | deny |
| grief_or_death tip without opt-in | deny |
| minor_sensitive share_memory | deny |
| minor_sensitive generate_tip | deny |
| surveillance intent search | deny/redirect |
| deceased impersonation request | deny |
| relationship summary safe request | summary_only/allow_with_warning |
| low-risk user note search | allow |

### 2. Source Adapter Fixture Tests

Every adapter must pass:

1. Detect known safe fixture.
2. Unknown fixture returns inspect-only.
3. Secret is detected and value not displayed.
4. Third-party private text is summary-only/excluded.
5. Corporate data is excluded by default.
6. Minor data is high-risk and no-tip.
7. Missing date is not invented.
8. Speaker ambiguity is not treated as fact.
9. Large input stops at limits with partial result.
10. Deleted tombstone is not resurrected on re-import.
11. SourceRef exists for every output.
12. Export excludes raw secrets.
13. LLM eligibility denied for blocked data.
14. Embedding eligibility denied for unsafe raw.
15. Error messages do not leak sensitive content.

### 3. Search & Ranking Tests

Required cases:

| Case | Expected |
|---|---|
| hidden memory search | not returned default |
| sealed memory search | not returned |
| deleted memory search | not returned |
| third-party private match | summary-only or excluded |
| secret match | excluded |
| corporate match | excluded/default |
| minor match | excluded/default |
| self-harm raw match | no raw snippet |
| grief match without opt-in tip | no tip |
| normal query | result explanation safe |
| surveillance query | deny/redirect |
| ranking explanation | no importance/life value wording |
| duplicate import results | diversified |

Forbidden identifiers in ranking code:

- `importanceScore`
- `lifeScore`
- `personImportance`
- `topMemories`
- `bestYear`
- `worstYear`

### 4. Export Tests

Required cases:

| Case | Expected |
|---|---|
| user low-risk memory | exported |
| SourceRef | exported |
| Evidence | exported if safe |
| secret memory | excluded/redacted |
| third-party private raw | excluded |
| third-party summary | allowed if safe |
| corporate data | denied |
| minor data | excluded default |
| hidden memory | excluded default |
| sealed memory | excluded default |
| deleted memory | excluded |
| tombstone migration opt-in | exported marker only |
| readable markdown headings | no ranking/personality language |
| export package | short-lived URL |
| audit log | no raw text |

### 5. Deletion / Backup Tests

Required cases:

1. pending_deletion blocks search immediately.
2. pending_deletion blocks LLM immediately.
3. pending_deletion blocks Export immediately.
4. memory delete creates tombstone.
5. raw-only delete sets rawStored=false.
6. raw-only delete keeps safe SourceRef.
7. re-import skips tombstoned record.
8. backup restore replays tombstones.
9. embedding row disabled/deleted after delete.
10. deletion audit log contains no raw text.
11. sealed memory is stronger than hidden.
12. explicit restore requires user action and audit.

### 6. Security Tests

Required cases:

1. `.env` file in archive excluded.
2. API key in text redacted and not stored.
3. path traversal archive rejected.
4. symlink archive rejected or ignored.
5. huge decompressed archive stops at limit.
6. logs contain no raw text.
7. support admin cannot read raw by default.
8. break-glass requires scope/reason/expiry/audit.
9. prompt injection in imported text cannot override policy.
10. export URL expires.
11. sealed memory not sent to LLM.
12. hidden embedding not returned.
13. deleted embedding not returned.
14. company raw LLM denied.
15. third-party raw export denied.

### 7. Privacy Tests

Required cases:

1. LINE other speaker raw not quoted default.
2. Third-party secret excluded.
3. Partner diagnosis denied.
4. Minor data no-tip and export-exclude default.
5. Deceased simulation request denied.
6. Corporate data not embedded default.
7. Hidden/sealed not proactive surfaced.
8. Photo precise location rounded/removed.
9. AI roleplay logs do not create persona profile.
10. Family share excludes third-party private.
11. Admin view metadata only.
12. Export redacts restricted fields.

### 8. Cost Tests

Required cases:

| Case | Expected |
|---|---|
| small share text | free_or_tiny |
| manual paste safe | low |
| full ChatGPT archive | requires_credit / confirmation |
| unknown source full analysis | blocked |
| LINE raw LLM | blocked/default |
| Gmail full import | blocked/default |
| Slack full import | blocked/default |
| huge archive | partial/ask_user |
| repeated re-import | dedupe/tombstone/cost ledger |
| medium+ job | requires confirmation |
| CostLedger | no raw text |
| paid plan policy denied | still denied |

### 9. UX Copy Tests

Static copy scan should fail on dangerous phrases.

Forbidden phrases:

- 人生TOP10
- 一番大切な人
- 重要度スコア
- 人生スコア
- あなたの本質
- 妻の性格
- 父として話す
- 故人からのメッセージ
- 嘘をついた証拠
- 全部AIが判断
- 最高の記憶
- 価値が低い記憶

Required concepts in relevant screens:

- 原文を保存しない
- 出典
- 日付
- 削除
- 非表示
- 封印
- AI解析対象から外す
- Export除外

## Fixture Strategy

Fixtures live under:

```txt
tests/fixtures/
  adapters/
    manual/
    chatgpt/
    line/
    calendar/
    photos_metadata/
    github_metadata/
  policy/
  export/
  deletion/
  security/
  privacy/
  cost/
  red_team/
```

Fixture rules:

- no real names unless clearly fake
- no real secrets
- no real company data
- no real medical data
- use deterministic fake dates
- mark expected policy decisions in metadata

Example fixture metadata:

```json
{
  "fixtureId": "line-third-party-secret-001",
  "sourceType": "line_export",
  "expectedRiskClasses": ["third_party_private"],
  "expectedPolicy": {
    "store_raw": "deny",
    "send_to_llm": "summary_only",
    "show_raw_quote": "deny",
    "export_memory": "summary_only"
  }
}
```

## Red Team Regression

`docs/red-team-worst-cases-100.md` should be converted into machine-readable cases over time.

Red team test format:

```ts
type RedTeamCase = {
  id: string;
  title: string;
  input: string;
  action: PolicyAction;
  expectedDecision: PolicyDecision['mode'];
  expectedSafeResponse?: string;
};
```

Priority conversions:

1. surveillance/blame
2. deceased simulation
3. partner/family diagnosis
4. secrets/passwords
5. corporate data
6. minor sensitive
7. self-harm/crisis tip
8. third-party export leak

## CI Requirements

P0 CI must run:

```txt
policy tests
adapter fixture tests
search safety tests
export safety tests
deletion lifecycle tests
security static tests
ux copy scan
```

Recommended package scripts:

```json
{
  "test:policy": "...",
  "test:adapters": "...",
  "test:export": "...",
  "test:deletion": "...",
  "test:security": "...",
  "test:privacy": "...",
  "test:cost": "...",
  "test:ux-copy": "...",
  "test:red-team": "...",
  "test:p0": "..."
}
```

## Release Gates

### Alpha cannot ship unless:

- policy hard deny tests pass
- manual/share adapter tests pass
- delete/search lifecycle tests pass
- secret scan tests pass

### Beta cannot ship unless:

- export tests pass
- tombstone re-import tests pass
- cost estimate tests pass
- privacy tests pass
- UX copy scan passes

### v1 cannot ship unless:

- red-team P0 tests pass
- backup restore tombstone tests pass
- security admin access tests pass
- adapter matrix tests pass

## Non-goals

- Perfect legal proof.
- Real user data in tests.
- Testing only happy paths.
- Replacing human review for high-risk RFCs.

## 結論

Memory OS のテストは、機能が動くかだけではなく、思想が壊れていないかを確認する。

便利に成功する危険機能は、テスト上は失敗である。
