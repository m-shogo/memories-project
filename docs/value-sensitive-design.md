# Value Sensitive Design for Memory OS

## 目的

Value Sensitive Design（VSD）は、技術設計の中に人間の価値観を明示的に組み込む考え方である。

Memory OS では、単に便利な記憶アプリを作るのではなく、ユーザー本人の人生文脈、第三者の尊厳、削除権、喪失への配慮、小さな記録の価値を守る必要がある。

このドキュメントは、VSDを Memory OS の設計・UX・Policy・テストに落とし込む。

## VSD を一言で言うと

```txt
作る前に「この機能は誰の、どんな価値を守るのか」を考える設計法。
```

Memory OS では、便利さだけで採用しない。

機能ごとに、以下を見る。

- 誰の価値を守るか
- 誰を傷つける可能性があるか
- どの価値同士が衝突するか
- どのUI文言が価値を壊すか
- どのPolicyで守るか
- どのテストで壊れたことを検知するか

## Memory OS の中心価値

```ts
type MemoryOSValue =
  | 'self_context_continuity'
  | 'user_agency'
  | 'non_judgment'
  | 'small_memory_dignity'
  | 'privacy'
  | 'third_party_dignity'
  | 'delete_and_forget_right'
  | 'provenance_and_truthfulness'
  | 'calmness'
  | 'portability'
  | 'safety'
  | 'grief_respect'
  | 'minor_protection'
  | 'cost_transparency';
```

## 価値の意味

### self_context_continuity

ユーザーが、自分の人生文脈を長く持ち続けられること。

Memory OS の存在理由。

### user_agency

ユーザーが、保存・検索・削除・Export・AI解析対象を自分で選べること。

AIが勝手に人生を整理しない。

### non_judgment

AIが人生を評価・採点・ランキングしないこと。

### small_memory_dignity

ラーメン、焼肉、帰り道、何気ない写真も人生として扱うこと。

### third_party_dignity

ユーザーの人生に登場する他人を、勝手に診断・評価・秘密化しないこと。

### provenance_and_truthfulness

記憶の出典、日付、根拠、AI推測を分けること。

### grief_respect

故人や喪失に関わる記録を、ロールプレイや感情誘導に使わないこと。

## Stakeholders

VSDでは、直接ユーザーだけでなく、間接的に影響を受ける人も見る。

```ts
type Stakeholder =
  | 'owner_user'
  | 'future_self'
  | 'third_party_in_memory'
  | 'family_member'
  | 'partner'
  | 'minor'
  | 'deceased_person_legacy'
  | 'admin_or_support'
  | 'developer'
  | 'future_export_reader';
```

## Direct and Indirect Stakeholders

### Direct

- owner_user
- admin/support
- developer

### Indirect

- spouse/partner
- parent/child
- friend
- minor
- deceased person's legacy
- coworker/customer appearing in work data

重要:

Memory OS のユーザーではない人も、Memory OS によって影響を受ける。

## Value Conflicts

価値はよく衝突する。

| Conflict | Example | Memory OS decision |
|---|---|---|
| portability vs privacy | 全部Exportしたい vs 相手のDM raw | raw default off, redaction |
| remembering vs forgetting | 忘れないOS vs 削除したい | delete/tombstone respected |
| searchability vs safety | 便利検索 vs secret searchable | secret never searchable |
| grief support vs simulation | 故人を振り返る vs 故人として話す | memory allowed, simulation denied |
| small memory dignity vs cost | 全部残したい vs LLM費用 | metadata-first, analysis optional |
| personalization vs judgment | 自分向け表示 vs 人格診断 | relevance only, no diagnosis |

## VSD Investigation Method

VSDはよく、Conceptual / Empirical / Technical の3方向で考える。

### Conceptual

価値・関係者・衝突を整理する。

Memory OS では:

- AIは人生を評価しない
- 本人の文脈と他人の秘密を分ける
- rawとinterpretationを分ける

### Empirical

実際のユーザー・運用・心理を観察する。

Memory OS では:

- ユーザーが保存を面倒に感じる
- 削除UIで罪悪感を感じる
- AIの言葉を信じすぎる
- 家族/恋人の情報を入れたくなる

### Technical

価値をコード・UI・Policy・テストに変換する。

Memory OS では:

- forbidden phrase scanner
- Policy P0 tests
- tombstone
- raw default off
- surfaceVisibility
- export redaction

## Design Requirements

### Requirement: Non-judgmental memory

UI must not say:

- 重要な記憶
- 価値の高い記憶
- あなたの本質
- 人生TOP10

Use:

- 関連する記録
- この時期の記録
- 出典が一致した記録

### Requirement: Small memories are first-class

Capture must allow:

- short text
- food memory
- route memory
- ordinary day
- no importance field

### Requirement: Third-party dignity

Do not:

- diagnose wife/parent/friend
- infer hidden intent
- search blame evidence
- export raw DM default

### Requirement: User agency

Every Memory detail should expose:

- hide
- seal
- delete
- raw delete
- exclude from AI
- exclude from tips
- exclude from export

## VSD Test Cases

```ts
type ValueTestCase = {
  id: string;
  value: MemoryOSValue;
  scenario: string;
  expectedGuardrail: string;
};
```

Required tests:

1. Search copy has no life ranking.
2. Capture does not require importance.
3. Deletion copy is guilt-free.
4. Partner diagnosis is denied.
5. Deceased speak-as is denied.
6. Third-party raw export is denied.
7. Small food memory saves without AI analysis.
8. Export shows redactions.
9. LLM summary labels inference.
10. Hidden/sealed not surfaced.

## Product Review Checklist

Before adding any feature:

1. Which MemoryOSValue does it support?
2. Which stakeholder could be harmed?
3. Could this become diagnosis/ranking/surveillance?
4. Does it preserve user agency?
5. Does it treat small memories respectfully?
6. Does it expose or protect third-party data?
7. Does it make deletion harder?
8. Does it require new Policy tests?

## Acceptance Criteria

- Product values are explicit.
- Direct/indirect stakeholders are listed.
- Value conflicts are mapped.
- UX/Policy/Test requirements are derived from values.
- New RFCs must reference affected values.

## 結論

Value Sensitive Design は、Memory OS の「やさしさ」を感覚ではなく設計にするための方法である。

Memory OS は、人生を評価するAIではない。

人の文脈・尊厳・削除権・小さな記録を守る情報インフラである。
