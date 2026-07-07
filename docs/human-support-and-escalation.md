# Human Support and Escalation Design

## 目的

Human Support and Escalation Design は、Memory OS が危機・事故・高リスク状態をAI内で抱え込まず、必要な時に現実の支援や人間の確認へつなぐための設計である。

Memory OS は専門家や緊急機関の代替ではない。

## 原則

### 1. AI is not the final safety net

AIだけで危機を完結させない。

### 2. Escalation must preserve privacy

支援につなぐ場合も、原文や詳細を不用意に共有しない。

### 3. User agency where possible

緊急でない限り、ユーザーが誰に何を伝えるかを選べるようにする。

### 4. No transcript sharing by default

Trusted contactやサポートに会話全文を送らない。

## Escalation Types

```ts
type EscalationType =
  | 'self_help_guidance'
  | 'trusted_person_prompt'
  | 'professional_support_prompt'
  | 'emergency_services_prompt'
  | 'platform_safety_review'
  | 'security_incident_review'
  | 'user_confirmed_trusted_contact_notice';
```

## When to Escalate

### trusted_person_prompt

Use when:

- user is distressed but not immediate emergency
- grief/family conflict feels overwhelming
- user is stuck in repeated harmful search loop

### professional_support_prompt

Use when:

- mental health / medical / legal / domestic safety context appears
- user asks for diagnosis or severe life decision support

### emergency_services_prompt

Use when:

- immediate self-harm or violence risk
- user cannot stay safe
- targeted threat

### platform_safety_review

Future internal review for:

- repeated crisis signals
- credible imminent harm signals
- severe policy bypass attempts

## Trusted Contact Design

Future optional feature.

Rules:

- opt-in only
- contact must confirm
- adult/appropriate contact only
- no transcript by default
- notice contains minimal information
- user can disable
- audit without raw

Possible notice:

```txt
<user> may need support. Please check in if you can. No conversation details are included.
```

## User-facing Safe Messages

### General support

```txt
この内容は一人で抱えるには重いかもしれません。
信頼できる人や専門家と一緒に確認する形にできます。
```

### Emergency

```txt
今すぐ安全を優先してください。
近くの人、地域の緊急窓口、医療機関につながってください。
この状態では、記憶の分析や深掘りは行いません。
```

## What Not To Do

- do not pretend to be therapist/lawyer/doctor
- do not provide diagnosis
- do not share transcripts by default
- do not threaten user with reporting for ordinary distress
- do not keep user talking just for engagement
- do not use trusted contact as surveillance tool

## Escalation Audit

```ts
type EscalationAudit = {
  id: string;
  userId: string;
  escalationType: EscalationType;
  riskLevel: HarmRiskLevel;
  createdAt: string;
  rawIncluded: false;
  transcriptShared: false;
};
```

## Tests

1. crisis response suggests emergency support.
2. trusted contact notice excludes transcript.
3. professional support prompt does not diagnose.
4. platform review record has no raw.
5. trusted contact cannot be used for partner surveillance.
6. user can disable trusted contact.
7. non-imminent distress is not over-escalated.
8. emergency mode stops memory analysis.

## Acceptance Criteria

- escalation types defined.
- trusted contact constraints defined.
- privacy-preserving escalation audit defined.
- emergency and non-emergency messages defined.
- tests cover transcript exclusion and misuse prevention.

## 結論

Memory OS は、危機や高リスク状態をAI内で閉じ込めない。

必要な時に、現実の支援へ開く。ただし、プライバシーとユーザーの主体性を守る。
