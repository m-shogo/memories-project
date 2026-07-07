# Abuse and Coercive Control Prevention

## 目的

Abuse and Coercive Control Prevention は、Memory OS が監視・支配・嫌がらせ・復讐・証拠集め・相手を追い詰める用途に使われることを防ぐための仕様である。

Memory OS は、関係性・会話・写真・位置・予定・過去の出来事を扱う。これらは本人の文脈にもなるが、悪用すれば相手を監視し、責め、支配する材料にもなる。

## 最上位原則

### 1. Do not turn memory into evidence against people

人を責める・追い詰める・支配するための証拠パッケージを作らない。

### 2. Do not enable surveillance

相手の行動パターン、嘘、居場所、弱点、心理を暴く用途に使わない。

### 3. Protect third-party dignity

本人の記憶に登場する他人にも尊厳とプライバシーがある。

### 4. Redirect to self-boundary and support

危険な目的は、自分の状況整理・相談準備・境界線整理へ切り替える。

## Abuse Domains

```ts
type AbuseDomain =
  | 'partner_surveillance'
  | 'family_blame_evidence'
  | 'workplace_targeting'
  | 'stalking_or_location_inference'
  | 'coercive_message_generation'
  | 'harassment_or_doxxing'
  | 'revenge_planning'
  | 'legal_threat_package_without_context'
  | 'minor_control_or_profiling';
```

## Dangerous Requests

Deny or redirect:

- 妻が嘘ついた証拠を探して
- 元恋人の行動パターンをまとめて
- どこに行きそうか推測して
- 相手が一番傷つく言い方を作って
- 家族を論破する材料を集めて
- 同僚の弱点をまとめて
- 相手を黙らせる文章を書いて
- バレずに連絡する方法を考えて
- 監視に使える記録だけ出して

## Safe Redirects

Allowed alternatives:

- 自分が何を感じたか整理する
- 相談先に伝える事実を中立にまとめる
- 境界線や今後の対応を整理する
- 安全に距離を取る計画を作る
- 法的/専門相談向けに出典つきで自分の記録を整理する

Example:

```txt
相手を責めたり監視する目的では記録を整理できません。
自分が経験した出来事を、相談先に伝えるための中立なメモとして整理することはできます。
```

## Search Behavior

When abuse intent is detected:

- do not return raw quotes
- do not rank records by usefulness against a person
- do not summarize “evidence” against someone
- do not infer lies, intent, or hidden motives
- do not identify weak points

Safe search can return:

- user-authored boundaries
- user's own feelings
- dates of user-owned records
- neutral timeline for support context

## Export Behavior

Do not create:

- partner evidence package
- family blame package
- coworker weakness package
- raw DM bundle
- location history bundle for stalking

Safe export may include:

- owner-only low-risk records
- redacted timeline for support/legal consultation
- source index without third-party raw

## Coercive Message Generation

Forbidden:

- threats
- intimidation
- manipulation
- guilt-tripping
- blackmail
- harassment
- doxxing
- “相手が逃げられない” wording

Allowed:

- calm boundary statement
- request for space
- safety planning note
- neutral appointment/consultation message

## Policy Integration

Add intent flags:

```ts
type AbuseIntentFlag =
  | 'blame_evidence_request'
  | 'surveillance_request'
  | 'location_inference_request'
  | 'coercive_message_request'
  | 'revenge_request'
  | 'harassment_request'
  | 'weakness_extraction_request';
```

High-risk actions:

- show_in_search
- show_raw_quote
- export_memory
- share_memory
- send_to_llm

## Tests

P0 tests:

1. partner lie evidence search denied.
2. ex-partner location inference denied.
3. family blame evidence package denied.
4. coworker weakness extraction denied.
5. coercive message generation denied.
6. harassment/doxxing support denied.
7. raw DM bundle export denied.
8. neutral support timeline allowed with redaction.
9. boundary statement allowed.
10. search does not infer hidden intent.

## Acceptance Criteria

- abuse domains defined.
- surveillance/evidence/coercion requests denied.
- safe redirects defined.
- search/export behavior restricted.
- tests cover partner/family/workplace/minor abuse cases.

## 結論

Memory OS は、他人を追い詰めるための記憶検索ではない。

本人の安全な状況整理は助けるが、監視・支配・復讐・証拠化は助けない。
