# Autonomous OPS Learning Addendum — 2026-10-28 — CI CLI suffix bypass

**Scope:** Append-only supplementary learning/history; **not** the canonical authority at `docs/operations/AUTONOMOUS-OPS-LEARNING.md`. Do not treat this file as production evidence, readiness, a recovery objective, a drill result, typed non-resurrection evidence, independent review or promotion. Reconcile into the canonical learning authority only when its large-file transport retry condition changes, without replacing or deleting prior history.

## Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** The common source-negative CI reachability parser previously accepted a direct Python command with arbitrary trailing arguments, including `python scripts/check.py --help`. Such a command can exit successfully without running validation. This was a static guard gap; no actual production failure or bypass was observed.
- **Verified root cause:** The prior `re.fullmatch` pattern ended in `(.*)` and rejected only four shell operator tokens in that suffix. Benign-looking CLI flags were not checked.
- **Failed approach:** Checking the executable prefix and a small denylist of shell operators cannot prove the validator ran its intended CLI.
- **Correction / executable recurrence guard:** [d9b724d8](https://github.com/m-shogo/memories-project/commit/d9b724d800d48afc6fa6b8cfbb2b3660ba0f0231) requires a complete command match (allowing the existing reviewed `python -B` form and whitespace only). Four semantic negatives cover `--help`, `-h`, an unreviewed `--repo-root` override and output redirection. The fixture count advances from 47 to 51.
- **Retry condition:** Revisit the exact-command allowlist only if an independently reviewed workflow genuinely needs CLI arguments; do not relax the guard for hypothetical convenience. Do not retry unchanged Quay MinIO HTTP 401 or human-promotion blockers.

## Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / observed evidence:** A read-only GitHub inventory of all 52 reviewed source-negative workflows found 63 direct Python validator commands, each with no trailing CLI arguments. The source update was committed as `d9b724d800d48afc6fa6b8cfbb2b3660ba0f0231`; the four new fixture definitions were statically counted, bringing the total to 51. **Exact-source GitHub Actions CI was not yet observable** via the available commit-run/status queries; do not report CI success until an actual run/job log is checked.
- **Why safe / reusable mechanism:** Only the shared read-only entrypoint guard changed. The exact command requirement rejects help-only, alternate-root and shell-redirection invocations rather than allowing them to masquerade as executed validators. Reviewed workflows, production evidence, credentials, traffic, readiness and promotion authority were not changed.
- **Protected-authority check:** All nine protected contract/registry Git blob SHAs were re-read after the code commit and were unchanged. Production status and OPS-P0-007 snapshot both state `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records and final candidates. Human promotion is separate and non-automatic.

## Learning transport / bounded tooling

- **Known blocker (unchanged):** The canonical learning file is approximately 4.17 MB and prior full-file Contents API and later Git blob/tree attempts encountered HTTP/2 transport failures. Root cause remains explicitly unknown. The same unchanged large-payload write was not retried. This small addendum is supplementary and must never substitute for the canonical learning authority.
- **New bounded-call lesson:** A single request batching 52 GitHub file reads exceeded the connector's maximum tool-call count. The failed approach was the oversized batch; the correction was five bounded read batches (12/12/12/12/4) which successfully verified all 52 workflows. Keep future connector batches bounded and retry a larger batch only if the call limit changes.
- **Next safe target:** Obtain exact-source CI evidence for the CLI suffix guard, then inspect whether source-negative workflow shell step metadata can shadow or skip the validator despite the exact command check. Preserve protected authority and append-only history.

## 2026-10-28 — Shell AND/OR short-circuit cannot bypass CI validators

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** The prior common reachability scanner could see a syntactically valid `python scripts/check.py` line while a preceding `true ||` or `false &&` shell list skipped its execution. This is a static bypass discovered by review, not an observed production incident.
- **Verified root cause:** The scanner checked shell control keywords, unconditional exit and disabled errexit but not the immediately preceding shell AND/OR list operator.
- **Failed approach:** A literal command line plus `set -euo pipefail` does not prove execution when the command is the short-circuited operand of an AND/OR list.
- **Correction / executable recurrence guard:** [d5c28d23](https://github.com/m-shogo/memories-project/commit/d5c28d23d233ee44c5f94ac29dcd7b456e9d3002) rejects a direct validator preceded by a non-comment shell line ending `&&` or `||`. Two semantic negative fixtures model `true ||` and `false &&`; total shared reachability negatives advance from 51 to 53.
- **Retry condition:** Revisit when the reviewed shell execution topology changes, especially if multiline shell list syntax is introduced. Do not retry unchanged external MinIO or human-approval blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** The code commit `d5c28d23` was accepted. A separate local Python classifier smoke test passed 3 positive and 3 negative inputs, including a trailing-backslash shell-list variant. The actual GitHub Actions exact-source run remains unconfirmed; a local classifier is not a CI success or production proof.
- **Why safe / reusable mechanism:** Only the shared read-only CI entrypoint was changed; no reviewed workflow, generation/objective/drill/evidence registry, credential, traffic or human promotion authority was modified.
- **Protected-authority check:** All nine protected authority blob SHAs were re-read after the code change and remained identical to their pre-write values. `productionDecision=NO_GO` and OPS-P0-007 `PREREQUISITES_BLOCKED` remain authoritative. Learning and fixture outcomes cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, independent review or promotion gates.
- **Next safe target:** Obtain exact-source CI run/job evidence for both guards. Then inspect heredoc or shell function wrappers that could make a visible Python line non-executable, without broadening reviewed workflow permissions or mutating production authority.
