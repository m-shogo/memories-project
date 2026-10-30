# Supplemental OPS learning — Unicode YAML line separators and bounded CAS recovery (2026-10-30)

Append-only supplemental history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure — prospective event undercount

- **Symptom:** Non-ASCII YAML line separators could conceal a push/PR event from the newline-oriented prewrite workflow trigger parser. This is a prospective parsing gap, not an observed GitHub Actions or production incident.
- **Observed evidence:** The prior parser modeled `\n`-oriented root and event rows, with no explicit check for U+0085 NEL, U+2028 LS, or U+2029 PS. The new synthetic fixtures exercise each separator; a Japanese-text dispatch-only positive control prevents blanket non-ASCII rejection. GitHub acceptance of every Unicode separator as a YAML line break is **not** asserted.
- **Verified root cause:** The reviewed regular expressions do not establish equivalent semantics for Unicode YAML line-separator variants.
- **Failed approach:** Treating no literal newline-based `on:/push:` match as proof that no direct trigger can exist.
- **Correction / executable recurrence guard:** [`bff97b03`](https://github.com/m-shogo/memories-project/commit/bff97b03fbf8ef701d73ba6bf0f7e2946ee2e967) conservatively marks these three Unicode separator forms as possible matches, with three negatives and one Japanese-text positive in both the auditor self-test and real CLI. Existing ordered fixture inventories and exact workflow count/identity checks remain.
- **Retry condition:** Narrow only after a reviewed YAML parser compatibility proof, exact positive/negative CLI tests, source CI and protected-authority verification.

## Material failure — scoped GitHub write-orchestration interruption

- **Symptom:** The first bounded attempt to prepare this code change ended without a commit and returned a GitHub GraphQL `UNKNOWN` error.
- **Observed evidence:** Error timestamp `2026-10-30T01:55:53Z`, reference `E996:1406B:703A12:173111C:6AE3F928`. Fresh reads showed both target validator blobs unchanged and branch `so` advanced from `f42b577a` to `01625b00` by a separate incident-control fixture commit.
- **Verified root cause or explicit unknown:** The exact GraphQL failure cause is unknown. Concurrent branch movement is verified, but its causal relationship to the connector error is not established.
- **Failed approach:** Assuming the interrupted orchestration completed or blindly retrying against the old parent SHA.
- **Correction / recurrence guard:** Re-read latest branch, compare the one unrelated incident fixture commit, re-read both target files and mandatory contract, and create the code commit against the new parent with an explicit expected-SHA ref lease. No force push or overwrite was used.
- **Retry condition:** Retry only after fresh head/source reconciliation and a responsive connector, with a bounded single attempt; stop on another unchanged transport failure rather than repeatedly resubmitting writes.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40988765707](https://github.com/m-shogo/memories-project/actions/runs/40988765707) completed **SUCCESS** on exact code source `bff97b03fbf8ef701d73ba6bf0f7e2946ee2e967`. Logs confirm append-only PASS, learning contract PASS, **408 fail-closed negatives**, **100 prewrite fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and read-only completion.
- **Why safe:** Only two read-only Python validators changed in the code commit. The independent incident fixture commit was preserved; no workflow YAML, production service, credentials, traffic, readiness, generation/objective, drill, recovery evidence, typed eight-domain record, independent review or human promotion was fabricated or modified by this work.
- **Reusable mechanism:** Treat unmodeled YAML separators as ambiguity and use fresh-head compare-plus-CAS recovery after an interrupted write; do not infer a successful write from an error.
- **Protected-authority check:** Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and generation/objective/drill/evidence/non-resurrection/promotion registries remain unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0; no approved recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate or human promotion.

## Limits and next safe target

Direct trigger matching is not transitive CI reachability. The Go-only Upload Route focused-test path remains MinIO-coupled and workflow permissions are unchanged. Next: fail closed on symlinked prewrite target paths, while allowing missing prospective paths; continue independent Go/Python closure work without retrying unchanged blockers.
