# Supplemental OPS learning — generation binding and strict preflight negative diagnostic order (2026-10-29)

Append-only supplemental record; **not** canonical `AUTONOMOUS-OPS-LEARNING.md` and never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation recovery, typed eight-domain non-resurrection or human promotion evidence.

## Material failure — strict preflight PR-SHA negative rejected by a different canonical guard

- **Symptom:** First strict-preflight source-negative exact-diagnostic CI failed after the semantic/trigger/runtime negatives passed.
- **Observed evidence:** [Preflight Eligibility Consistency #40795818356](https://github.com/m-shogo/memories-project/actions/runs/40795818356) FAILED on [a9f9f3e7](https://github.com/m-shogo/memories-project/commit/a9f9f3e7460ffb7763377275ebb3e4b679f0e50c). Log: `preflight eligibility consistency wrong source negative diagnostic: PR SHA: preflight eligibility consistency CI source drift: writer SHA`.
- **Verified root cause:** The PR-SHA fixture substitutes the exact token already used for writer SHA, increasing its cardinality. The earlier REQUIRED writer-SHA inventory guard correctly rejects before the later PR-SHA absence check.
- **Failed approach:** Deriving expected rejection from the mutated fixture's name rather than the actual first failing reviewed authority invariant.
- **Correction:** [303033b4](https://github.com/m-shogo/memories-project/commit/303033b4c862c15d15ddcf67a372228abab4ca59) explicitly classifies this PR-SHA collision as the canonical `writer SHA` diagnostic; no validation rule, admission condition or source authority was weakened.
- **Executable recurrence guard:** The source-negative suite now requires case-specific exact diagnostics for all 20 existing cases and separately removes the push-only self-trigger. [Corrected exact-source CI #40795876461](https://github.com/m-shogo/memories-project/actions/runs/40795876461) completed **SUCCESS**: 18 semantic source cases, one additional push-only trigger negative, two blob-only cases, 15 YAML exact-diagnostic negatives and six runtime branch cases.
- **Retry condition:** Reassess only if reviewed REQUIRED ordering, SHA tokens or event trigger inventory changes, or a new demonstrated bypass appears. Do not rerun the unchanged failed `a9f9f3e7` source.

## Material successes and reusable guard

- **Generation binding:** [c9a727ff](https://github.com/m-shogo/memories-project/commit/c9a727ffc8ff44678876f5f44191f8954c3a3bc7) converts all 112 event-specific trigger removals, 16 additions and two shortened-inventory negatives from generic `SystemExit` acceptance to exact expected publisher/independent event diagnostics. [Source Negative #40795772064](https://github.com/m-shogo/memories-project/actions/runs/40795772064) completed **SUCCESS** with 48 existing YAML exact-diagnostic negatives preserved. [Generation Binding Publisher #40795772033](https://github.com/m-shogo/memories-project/actions/runs/40795772033) also completed **SUCCESS**; branch HEAD was unchanged after completion.
- **Strict preflight eligibility:** [a9f9f3e7](https://github.com/m-shogo/memories-project/commit/a9f9f3e7460ffb7763377275ebb3e4b679f0e50c) introduced case-specific source diagnostics and actual push-only self-trigger removal; the observed diagnostic-order failure was corrected in [303033b4](https://github.com/m-shogo/memories-project/commit/303033b4c862c15d15ddcf67a372228abab4ca59) and verified by [CI #40795876461](https://github.com/m-shogo/memories-project/actions/runs/40795876461).

**Why safe:** Both changes modify existing CI-reachable read-only Python source-negative validators. All trigger/source mutations are synthetic; reviewed workflows, registry writers, recovery evidence, credentials, traffic, readiness and human promotion were untouched.

**Reusable mechanism:** Bind each synthetic negative to the *first actual canonical invariant* that fails. A mutation can simultaneously violate two token counts; the earlier guard determines its diagnostic. Independently exercise PR and push copies of a trigger path, and reject unrelated exceptions instead of accepting any `SystemExit`.

**Protected-authority check:** Before this append, production status blob `3ab8092c7e3fec2b48d62fb2728f024151f610c5` still held `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remained `PREREQUISITES_BLOCKED`. Registered and semantically eligible generations, explicitly approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final candidates all remained zero. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` was unchanged. Reviewed drill requests are planning authority only; final candidates still require all gates and independent review, and human promotion remains separate/non-automatic.

**Scoped blockers:** Canonical learning transport remains unreadable through the existing large-file path; no unchanged retry or substitution. Existing MinIO/Quay 401 and external human approval constraints remain unchanged. No production-equivalent evidence or readiness was fabricated.

**Next safe target:** Audit strict drill-preflight and generation-binding source-negative suites for fixture-label collisions, event-specific push aliases and exact diagnostic classifier gaps, while avoiding any protected authority changes.
