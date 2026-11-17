# Cross-project learning protocol (v1)
Date: 2026-11-18
Status: policy recorded; cross-repository enforcement NOT implemented
Owner intent: improve from mistakes across all projects. Same failure class may occur up to three times, but every recurrence must produce a stronger, verified intervention. No claim of guaranteed autonomous recall.

## Distinguish what changed
- NEW: genuinely new user objective, preference or decision.
- CORRECTION: assistant misunderstood a pre-existing objective.
- CHANGE: user explicitly replaced a previous decision.
- HYPOTHESIS: assistant idea, not a user preference.
- VERIFIED: supported by named source, timestamp and scope.
- UNKNOWN: insufficient evidence.
Never infer CHANGE from CORRECTION.

## Failure lifecycle
Identity: project + failure_class + violated_contract (not arbitrary wording).
For each occurrence record: date, project, concrete evidence/link, user impact, root cause, recurrence count, fix, verification method, verification result, next check owner.
1st occurrence: fix immediate output, log cause, add a check.
2nd occurrence: change workflow or add executable validation; test against prior example.
3rd occurrence: redesign the weak boundary; add regression coverage and require evidence before marking resolved.
4th occurrence: classify the prevention system as failed; stop claiming it works, escalate to architectural review. Never hide or reset the count.
A successful result may close an incident, but must not erase the historical count.

## Before each relevant project task
1. Locate actual repository and active branch. Read its README/current authority and applicable project decisions; if unavailable, say so.
2. Check applicable open incidents and regression rules before suggesting a plan.
3. Classify request (NEW/CORRECTION/CHANGE/HYPOTHESIS) and separate user's objective from assistant recommendations.
4. Do work; cite exact files and verified external sources, state unverified scope.
5. Validate results. Write back only significant decisions, incident learning, and verified outcomes to the project's existing appropriate files.
6. When learning crosses projects, update this central protocol or central incident index, and link relevant projects. Do not blindly modify unrelated repos.
7. Report evidence of action, not intentions. Never call a written rule an automated safeguard.

## Cross-project architecture proposal (not yet implemented)
- A single central index of incident IDs and shared invariants in memories-project.
- Project-local concise authority for goals, decisions, and operational constraints; central index links, does not duplicate personal details.
- CI checks for schema validity, broken links, contradictions and missing verification metadata where feasible.
- Regression cases from real failures; pass/fail history per repository.
- Scheduled review of recurrence counts and unverified fixes; respect existing automations and avoid duplicate alerts.
- Do not put passwords, tokens, private account identifiers, or sensitive personal data in logs.
- Do not claim all ChatGPT conversations automatically load this file. Retrieval and enforcement require explicit integration in each project or automation.

## Seed incidents (2026-11-18)
- CP-001 | category: context-not-read | observed in alpha-pon | 1 documented incident cluster | source: alpha-pon/docs/investment/decision-learning.md | fix: README links to preferences and incident log | verification: links read back; recurrence prevention NOT verified.
- CP-002 | category: preference-vs-recommendation | observed in alpha-pon | 1 documented incident cluster | source: same | fix: separate user desires, suggestions, holdings | verification: documented only.
- CP-003 | category: correction-vs-change | observed in alpha-pon | 1 documented incident cluster | source: same | fix: classification contract | verification: documented only.
- CP-004 | category: unverified-claims | observed in alpha-pon | 1 documented incident cluster | source: same | fix: evidence/time/scope requirement | verification: documented only.
Counts above are initial recorded incident clusters, NOT claims about total historical occurrences. Audit history before changing counts.

## Next concrete implementation steps
1. Inspect existing incident/learning machinery across each target repository and avoid duplication.
2. Create machine-readable incident registry with immutable IDs, recurrence and verification states.
3. Add a validator with regression fixtures to one pilot repository.
4. Integrate only after tests pass; measure repeated errors, false alarms and missed detections.
