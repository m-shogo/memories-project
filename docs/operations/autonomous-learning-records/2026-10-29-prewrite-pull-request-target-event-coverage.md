# Supplemental OPS learning — pull_request_target prewrite event coverage (2026-10-29)

Append-only supplemental learning only; canonical learning authority `docs/operations/AUTONOMOUS-OPS-LEARNING.md`, mandatory policy `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure / previously unreviewed event class

- **Symptom:** The read-only prewrite direct-event fanout audit recognized `push` and `pull_request` but did not recognize `pull_request_target`. A future workflow using this privileged PR event could therefore be omitted from the conservative path-match inventory.
- **Observed evidence:** The reviewed parser's quoted-event normalization, inline-event recognition, duplicate-event check, fallback and event-loop all enumerated only `push` and `pull_request`. This is a static coverage gap, not an observed unauthorized GitHub Actions execution.
- **Verified root cause:** The event inventory was a hard-coded two-element tuple, excluding another supported direct PR event. An omitted event cannot be covered by downstream path-pattern checks.
- **Failed approach:** Treating `pull_request` as the only relevant PR-trigger spelling when estimating source-change blast radius.
- **Correction / executable recurrence guard:** [`316ca527`](https://github.com/m-shogo/memories-project/commit/316ca527069d679eb0561f1cafc5da2a017ec135) adds `pull_request_target` to quoted, scalar, inline, duplicate and filtered event handling. Five synthetic cases cover filtered, unrelated, unfiltered, quoted and duplicated target events. Three actual CLI fixture cases prove matching and non-matching target-event behavior.
- **Retry condition:** Revisit only after a reviewed event grammar change or concrete false-negative fixture; do not infer indirect `workflow_run`/reusable-workflow closure from this direct-event guard. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical large-learning append transport or human-promotion blockers.

## Material success

- **Observed outcome / evidence:** [Autonomous Learning Guard #40897594198](https://github.com/m-shogo/memories-project/actions/runs/40897594198) completed SUCCESS on exact source `316ca527069d679eb0561f1cafc5da2a017ec135`. Logs confirm **161** fail-closed negative cases, **32** prewrite fanout synthetic cases, entrypoint document validation PASS, clean-source and append-only checks PASS. Conservative possible-match counts remained **88** operability and **3** rate-limit; no external workflow was executed by the audit.
- **Why safe:** Only the read-only prewrite fanout auditor and CI-bound negative validator changed. No workflow YAML, credential, traffic, recovery evidence, production authority or promotion was modified.
- **Reusable mechanism:** Treat security-relevant PR event variants as distinct explicit trigger forms; prove both match and non-match using the actual CLI, while retaining conservative handling for unsupported YAML/minimatch grammar.
- **Protected-authority check:** Production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `NO_GO`; canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` are unchanged. Registered/semantically eligible generations, human-approved recovery objective, executable reviewed request, generation-bound evidence, complete typed eight-domain record, final candidate and human promotion remain absent/separate.

## Next safe target

Audit indirect `workflow_run` and reusable `workflow_call` dependencies separately, using bounded read-only graph fixtures. Do not treat direct path matching as proof of transitive CI reachability or use it to narrow production workflow triggers.
