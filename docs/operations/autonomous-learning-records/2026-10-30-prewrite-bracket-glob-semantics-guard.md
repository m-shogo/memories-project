# Supplemental OPS learning — workflow bracket glob semantic ambiguity (2026-10-30)

Append-only supplemental history only; canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed executable request, request-bound recovery, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure — prospective direct trigger undercount

- **Symptom:** Python `fnmatch` can return false for a workflow path pattern whose GitHub minimatch bracket grammar is not equivalently modeled, potentially undercounting direct CI trigger fanout. This is a prospective prewrite parser gap, not an observed production or GitHub Actions failure.
- **Observed evidence:** Local Python 3.13 `fnmatch.fnmatchcase("scripts/a.py", "scripts/[^b].py")` and `fnmatch.fnmatchcase("scripts/a.py", "scripts/[[:alpha:]].py")` both returned false. The previous audit delegated these patterns to `fnmatch` without a conservative ambiguity branch. GitHub acceptance/precise matching of every POSIX class is not asserted.
- **Verified root cause:** GitHub minimatch and Python `fnmatch` do not have a proven identical bracket-negation/POSIX-class grammar; a false non-match cannot safely establish no CI trigger.
- **Failed approach:** Treating the Python glob result as a complete GitHub path-filter decision for `[^...]`, `[!...]`, and `[[:...:]]`.
- **Correction / executable recurrence guard:** [`6814fda7`](https://github.com/m-shogo/memories-project/commit/6814fda7782c0e0b131ba9aeac6f883a566f71f0) conservatively classifies those bracket forms as possible matches, adds three ambiguity negatives plus ordinary bracket-match and bracket-miss positive controls to both self-test and real CLI, pins ordered fixture identities and reconciles exact count/identity. Original 64/47 reviewed fixture inventories remain intact.
- **Retry condition:** Narrowing this conservative classification requires a verified GitHub-compatible minimatch grammar, cross-engine positive/negative evidence, exact-source CI, workflow identity reconciliation and protected-authority verification. Do not retry unchanged external MinIO 401, workflow-write permission, canonical large-learning transfer or human promotion blockers.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40988219380](https://github.com/m-shogo/memories-project/actions/runs/40988219380) completed **SUCCESS** for exact source `6814fda7782c0e0b131ba9aeac6f883a566f71f0`. Job logs confirm append-only PASS, learning contract PASS, **401 fail-closed negatives**, **92 prewrite fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and read-only completion.
- **Why safe:** Only CI-reachable read-only Python validators changed; no workflow YAML, Go production code, external services, credentials, production traffic, readiness, recovery evidence or promotion authority changed.
- **Reusable mechanism:** Fail closed on cross-engine glob constructs unless their semantics are proved equivalent, while preserving ordinary bracket match/miss behavior through explicit positive controls.
- **Protected-authority check:** Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, and generation/objective/drill/evidence/non-resurrection/promotion registries remain unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no approved recovery objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain record, final candidate, or human promotion.

## Limits and next safe target

A bounded direct path audit is not transitive CI closure. The Go-only focused Upload Route test still lacks a verified MinIO-independent workflow trigger, and workflow writes remain permission-scoped. Next: reject Unicode invisible/control path identities at the prewrite CLI boundary with positive Japanese filename controls; keep production and learning authorities separate.
