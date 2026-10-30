# Supplemental OPS learning — root-level YAML event alias ambiguity (2026-10-30)

Append-only supplemental learning; canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md`, mandatory contract `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, or human promotion evidence.

## Material failure — prospective root-key undercount

- **Symptom:** A root-level YAML merge or a tagged/anchored/complex `on` mapping key could introduce an event without the literal `^on:` spelling. The prewrite direct-fanout audit could therefore return zero matches. This is a prospective parser gap, **not** an observed GitHub Actions event or production incident.
- **Observed evidence:** Source review of the prior parser showed root detection for literal/quoted `on:` and selected escapes but no root merge, tagged-key, anchored-key, or complex-key branch. Concrete fixtures include `events: &e {on: [push]}\n<<: *e`, `!!str on:`, `!<tag:yaml.org,2002:str> on:`, `&key on:`, and `? on`. These are conservative ambiguity fixtures; GitHub acceptance of every YAML form is **not** asserted.
- **Verified root cause:** The fallback checked a literal two-space `push:` event row; a root-level transformed `on` key with noncanonical nested indentation could escape that check.
- **Failed approach:** Treating missing literal `on:` plus missing literal two-space push/PR as proof of dispatch-only semantics.
- **Correction / executable recurrence guard:** [`6bb15f1b`](https://github.com/m-shogo/memories-project/commit/6bb15f1bb8cc4bc00086e4c2b4ca0eb286532480) conservatively rejects root merge/tagged/anchored/complex event-key ambiguity. Six negatives and one unrelated-anchor positive are executed both in the auditor self-test and real subprocess CLI, with ordered fixture-label identity checks and exact workflow count/identity assertions.
- **Retry condition:** Legitimate root YAML alias/tag/merge behavior requires explicit semantic review, bounded positives/negatives, exact-source CI and protected-authority verification. Do not retry unchanged MinIO 401, workflow-write permissions, canonical large-learning transport, or human-promotion blockers.

## Material success

- **Observed outcome/evidence:** Exact-source [Autonomous Learning Guard #40987934900](https://github.com/m-shogo/memories-project/actions/runs/40987934900) completed **SUCCESS** for `6bb15f1bb8cc4bc00086e4c2b4ca0eb286532480`. Logs confirm append-only PASS, learning contract PASS, **396 fail-closed negatives**, **87 fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and read-only execution success.
- **Why safe:** Only the two read-only Python validators changed; no actual workflow trigger, Go source, credentials, production traffic, readiness, evidence registry, recovery authority, or promotion gate changed.
- **Reusable mechanism:** Over-approximate unreviewed root YAML mapping semantics and prove both in-process classification and actual CLI count/identity behavior; never infer non-reachability from an unsupported YAML key form.
- **Protected-authority check:** Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and generation/objective/drill/evidence/non-resurrection/promotion registries remained unchanged. `productionDecision=NO_GO`; registered/eligible generations 0/0, approved recovery objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records, final candidates and human promotion all remain zero.

## Limits and next safe target

Direct workflow matches are not full transitive CI reachability. The Upload Route Go-only focused-test path remains blocked by existing workflow permission and MinIO startup ordering. Next: conservatively audit GitHub minimatch bracket negation/POSIX classes versus Python `fnmatch`, with actual CLI negatives, then revisit Go/Python trigger closure without modifying workflow YAML.
