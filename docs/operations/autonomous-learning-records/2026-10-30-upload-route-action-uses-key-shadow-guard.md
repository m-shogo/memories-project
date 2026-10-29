# Supplemental OPS learning — Upload Route YAML uses-key shadow guard (2026-10-30)

Append-only supplemental history only; canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under `contracts/operations/autonomous-learning-system.json`. This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure / static parser gap

- **Symptom:** The new ordered Upload Route action identity guard matched only canonical `- uses:` rows. An extra YAML action written as `uses :`, quoted `"uses":` / `'uses':`, or a flow mapping `{uses: ...}` could leave the three reviewed canonical matches unchanged.
- **Observed evidence:** A bounded regex/YAML-source reproduction confirmed that these four alternate key shapes are not returned by the canonical line parser. The two actual workflows use only three canonical action steps each; this is a prospective shadow escape, not observed workflow drift.
- **Verified root cause:** Counting canonical parsed action rows without separately detecting all alternate `uses` key occurrences can silently omit a new action identity.
- **Failed approach:** Treating an exact three-action canonical match as proof that no other semantically valid YAML action key exists.
- **Correction / executable recurrence guard:** [`423c89eb`](https://github.com/m-shogo/memories-project/commit/423c89eb9e6e06408e1cdcc11eecfd45d42e9752) additionally counts conservative quoted/spaced/flow `uses` mentions and requires equality with canonical parsed action rows. Four new CI-bound negatives reject the shadow forms. This is conservative lexical YAML checking, not a complete YAML semantics parser.
- **Retry condition:** Rebaseline only after reviewing a legitimate alternate YAML action syntax and all workflow execution/trigger implications with exact-source CI and protected-authority check. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical large-learning append transport or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40940947231](https://github.com/m-shogo/memories-project/actions/runs/40940947231) **SUCCESS** on exact source `423c89eb9e6e06408e1cdcc11eecfd45d42e9752`. Logs show contract PASS, 201 printed fail-closed cases, 74 fanout synthetic, 1186 helper-ancestor negatives, append-only, entry-document and read-only PASS. Four nested negatives are not separately counted in the printed 201.
- **Why safe:** Only the read-only negative validator changed (+7 lines). No workflow YAML, production source, credentials, traffic, generation/objective, reviewed requests, recovery evidence, typed eight-domain records, independent review or promotion was changed.
- **Reusable mechanism:** Pair exact canonical YAML key parsing with conservative shadow-key occurrence detection; preserve existing reviewed action identities while rejecting unrecognized syntax.
- **Protected-authority check:** Post-code-commit canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and protected registries unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations, approved current objectives, executable reviewed requests, generation evidence, complete typed eight-domain records, final candidates and human promotion remain zero. Preflight requires distinct unsuperseded semantically eligible environments and explicit human-approved current objective; reviewed requests remain planning-only, evidence request-bound, independent review and promotion separate.

## Next safe target

Pin the exact Python/Go runtime command surface in both Upload Route workflows and preserve the known CI trigger coverage gap. Do not narrow workflow triggers or change mutable action refs without independent review and authorization.
