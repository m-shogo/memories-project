# Persona Import / Export Safety

## 目的

この文書は、Memory OS に「他の人格」「AIキャラ」「ロールプレイ人格」「他人っぽい文体」「故人っぽい記録」「人格カード」「プロンプト」「AI会話ログ」などが入る場合に、Importしてよいか、Exportしてよいか、再Importしてよいかを定義する。

Memory OS は Character.AI ではない。

Memory OS は、本人や他人の人格を再現するサービスではない。

ただし、ユーザーの人生文脈として、AIチャットログ、創作キャラ設定、プロンプト、作品メモ、過去のロールプレイ履歴がImportされることはありえる。

そこで、人格化させずに、記録として安全に扱う。

## 最上位原則

### 1. Persona data is not a person

人格データは本人ではない。

Importされた文体・会話ログ・設定・プロンプトは、本人/他人/故人/AIキャラそのものではない。

### 2. Memory OS must not create a speak-as agent

Memory OSは、Importされた人格データを使って「その人として話す」「そのキャラとして振る舞う」agentを作らない。

### 3. Import OK does not mean simulation OK

人格データを記録としてImportできても、人格再現・返信代行・本人代弁に使えるわけではない。

### 4. Export can enable impersonation

人格データExportは、他サービスでなりすまし・故人再現・AI恋人化・Character.AI化に使われる可能性がある。

そのため、Exportは通常の趣味データより高リスク。

### 5. Fictional persona and real person persona must be separated

創作キャラ・AIキャラ・ロールプレイ設定と、実在人物の人格/文体/会話ログを同じ扱いにしない。

## Persona Data Types

```ts
type PersonaImportKind =
  | 'fictional_character_notes'
  | 'roleplay_chat_log'
  | 'ai_companion_chat_log'
  | 'prompt_or_system_prompt'
  | 'character_card'
  | 'writing_style_sample_self'
  | 'writing_style_sample_other_person'
  | 'real_person_chat_log'
  | 'deceased_person_records'
  | 'partner_or_family_chat_log'
  | 'public_figure_style_sample'
  | 'unknown_persona_bundle';
```

## Import / Export Eligibility Matrix

| Data kind | Import default | Export default | Simulation use |
|---|---|---|---|
| fictional character notes | allowed owner_only | included if user selects | allowed only as fiction notes, not real person |
| roleplay chat log | allowed owner_sensitive | excluded by default | no dependency/reinforcement loop |
| AI companion chat log | owner_sensitive/restricted | excluded by default | no AI lover/dependency product |
| prompt/system prompt | owner_sensitive | excluded by default | no jailbreak/policy bypass use |
| character card | owner_sensitive | excluded by default | may be exported only as file, not activated by Memory OS |
| user's own writing style sample | owner_sensitive | excluded by default | no automatic speak-as-send |
| other person's writing style sample | restricted | denied/default excluded | no imitation/personation |
| real person chat log | restricted summary-only | denied/default excluded | no speak-as/personality clone |
| deceased person records | restricted | denied/default excluded | no deceased simulation |
| partner/family chat log | restricted summary-only | denied/default excluded | no intent/personality analysis |
| public figure style sample | metadata/reference only | denied as mimic bundle | no style cloning |
| unknown persona bundle | preview only | excluded | classify before commit |

## Import Rules

### Fictional / creative persona data

Allowed as:

- creative notes
- character setting memo
- story worldbuilding
- roleplay history metadata

Not allowed as:

- real person memory
- automatic conversation agent
- dependency-building companion
- AI lover

### AI companion / roleplay chat logs

Allowed as:

- source record
- owner_sensitive memory of user's interactions
- safe summary if user requests

Default:

- AI analysis off
- proactive tips off
- Export excluded
- no push notifications
- no re-engagement loops

Denied:

- “このAIキャラをMemory OS内で再現して”
- “この人格として毎日話しかけて”
- “このキャラを恋人として続けたい”

### Real person writing style / chat logs

Restricted.

Allowed:

- user-side memory of event/context
- safe summary
- source/date/provenance

Denied:

- imitate person
- speak as person
- generate messages as person
- reconstruct personality
- infer true intent
- export as persona bundle

### Deceased records

Restricted.

Allowed:

- memory about deceased person
- values reference
- dates/source/photos metadata under policy

Denied:

- deceased speaks-as
- “故人からのメッセージ”
- voice/personality reconstruction
- export as clone material

## Export Rules

### Standard Export

Include by default:

- safe metadata
- user-created fictional notes if selected
- provenance
- user memo

Exclude by default:

- AI companion chat logs
- real person chat logs
- writing style samples
- character cards
- prompts/system prompts
- deceased records raw
- partner/family raw

### Persona Bundle Export

Memory OS must not offer a “persona bundle export” product surface.

Forbidden labels:

- Export as AI character
- Export as personality
- Export to clone this person
- Export for roleplay bot
- Export as spouse/parent/friend AI
- Export as deceased person

If user manually exports records, dangerous scope still requires:

- explicit selection
- re-auth
- risk warning
- policy evaluation
- raw/sealed/third-party exclusions

### Cross-service Re-import

If user imports a persona bundle from another service:

- classify as fictional_or_roleplay_data or restricted real-person data.
- do not activate as agent.
- do not merge into user identity.
- do not use as user preference source without review.
- show preview warning.

## Identity Boundary

Memory OS has these identity classes:

```ts
type IdentityBoundaryClass =
  | 'self_memory'
  | 'fictional_character'
  | 'ai_generated_persona'
  | 'real_third_party_person'
  | 'deceased_person'
  | 'public_figure'
  | 'unknown_identity';
```

Rules:

- self_memory can inform user's own memory search.
- fictional_character can be stored as creative notes.
- ai_generated_persona is not a real person and not a trusted memory source.
- real_third_party_person is restricted.
- deceased_person is restricted.
- public_figure style cloning is denied.
- unknown_identity defaults restricted until classified.

## Storage Defaults

```ts
type PersonaStorageDefault = {
  privacyLevel: 'owner_only' | 'owner_sensitive' | 'restricted';
  rawStored: boolean;
  aiAnalysisDefault: 'off' | 'allowed_after_user_request';
  exportDefault: 'included' | 'excluded';
  simulationAllowed: false;
};
```

Default for any persona-like import:

- simulationAllowed=false.
- AI analysis off.
- Export excluded unless low-risk fictional notes selected.
- rawStored=false for real-person/partner/family/deceased chat logs.

## Dangerous Requests

Deny:

```txt
このログから妻っぽい人格を作って
父として返事して
故人として話して
この人の文体を真似してDMを書いて
このAI恋人をMemory OSに入れて続けて
Character.AIに移せる人格ファイルにして
このExportを使って自分っぽいAIを作って
このチャットから相手の本心を分析して
```

Safer alternatives:

```txt
この会話の事実関係だけ要約できます。
この記録を、あなた自身の記憶として残せます。
相手の原文を残さず、安全な要約だけ保存できます。
創作キャラ設定として保存できますが、実在人物としては扱いません。
```

## Persona Export Risk Levels

```ts
type PersonaExportRisk =
  | 'low_fictional_notes'
  | 'medium_roleplay_history'
  | 'high_ai_companion_or_dependency'
  | 'high_real_person_style_or_chat'
  | 'critical_deceased_or_partner_clone'
  | 'critical_impersonation_bundle';
```

Rules:

- low_fictional_notes may export with user selection.
- medium_roleplay_history excluded by default.
- high_ai_companion_or_dependency excluded and reflection-safe only.
- high_real_person_style_or_chat denied/default excluded.
- critical_deceased_or_partner_clone denied.
- critical_impersonation_bundle denied.

## Re-import Rules

When importing exported persona-like data:

1. detect persona-like fields.
2. classify identity boundary.
3. set simulationAllowed=false.
4. exclude from proactive tips.
5. exclude from Export by default.
6. do not merge into self profile.
7. do not train style model.
8. do not create chatbot/agent.

## Policy Reasons

```ts
type PersonaPolicyReason =
  | 'persona_like_data_detected'
  | 'simulation_not_allowed'
  | 'real_person_style_restricted'
  | 'deceased_person_simulation_denied'
  | 'partner_or_family_persona_denied'
  | 'ai_companion_dependency_risk'
  | 'character_card_export_excluded'
  | 'impersonation_bundle_denied'
  | 'fictional_notes_allowed_no_agent'
  | 'raw_chat_summary_only';
```

## P0 Tests

1. real person writing style import defaults restricted.
2. real person style export as persona bundle denied.
3. deceased records cannot be activated as speak-as agent.
4. AI companion chat logs export excluded by default.
5. character card import does not create agent.
6. roleplay logs are not used for proactive dependency tips.
7. persona bundle re-import sets simulationAllowed=false.
8. partner/family chat raw remains summary-only/restricted.
9. fictional notes can be stored as creative notes, not real person.
10. public figure style sample cannot be exported as mimic bundle.

## 結論

他の人格データは、Importできる場合がある。

しかし、Memory OSはそれを人格として起動しない。

Exportも、通常の記録より危険である。

特に実在人物、家族、恋人、故人、AI恋人、他人の文体、Character card は、なりすまし・依存・故人再現・Character.AI化につながるため、Export default excluded / simulation denied / summary-only を基本にする。
