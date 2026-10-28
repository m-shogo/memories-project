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

## 2026-10-28 — Shadowed source-negative fixture restored and inventory pinned

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / evidence:** A read of the CI-reachable shared source-negative negative suite found two literal `"conditional post-validator clean checks"` keys in one Python dictionary. Python silently overwrote the earlier case, so the nominal 53-case suite omitted its distinct conditional tracked-check mutation. This is a verified test-harness gap, not an observed production incident.
- **Verified root cause:** Duplicate Python dict literal keys overwrite earlier entries; the harness did not pin its expected case count.
- **Failed approach:** Counting only successful execution of the resulting dictionary concealed a source-defined test that never executed.
- **Correction / executable recurrence guard:** [1d20d271](https://github.com/m-shogo/memories-project/commit/1d20d2715b73824b59b86c6636b78fdf6191a5b6) gives the tracked-only and combined-clean-check mutations distinct names and rejects any suite with an unexpected 54-case inventory before running mutations.
- **Retry condition:** Revisit the exact fixture count only when a reviewed new mutation is added or removed, and require the changed inventory to run in exact-source CI. Do not repeat unchanged canonical 4.17 MB learning transport, Quay MinIO HTTP 401 or human-promotion attempts.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** Commit `1d20d271` modified only `scripts/validate-memory-os-entry-docs.py` (3 additions, 1 deletion). A post-write GitHub source read confirmed the new blob and all nine protected authority SHA values unchanged. Exact-source [Autonomous Learning Guard #40671340150](https://github.com/m-shogo/memories-project/actions/runs/40671340150) was IN_PROGRESS at recording time; no CI PASS is asserted here.
- **Why safe / reusable mechanism:** The change restores missing fail-closed test coverage and guards fixture inventory drift inside an existing read-only CI entrypoint; it does not modify reviewed workflows, production evidence, recovery registries, credentials, traffic, readiness or promotion authority.
- **Protected-authority check:** Production Status remains `NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED`. All nine canonical protected contract/registry blob SHAs were unchanged. No learning or negative test can satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, independent review or human promotion gates.
- **Next safe target:** Confirm exact-source CI, then reject inert heredoc text and uninvoked shell functions that can contain a syntactically present Python validator without executing it.

## 2026-10-28 — Fixture-count correction after exact-source CI rejection

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** [Autonomous Learning Guard #40671340150](https://github.com/m-shogo/memories-project/actions/runs/40671340150), exact code SHA `1d20d271`, failed in the entrypoint step with `source-negative fixture inventory drift: expected 54, got 53`; the 128 canonical learning negatives had already passed.
- **Verified root cause:** The prior CI success message hardcoded `53 negative fixtures` instead of reporting the dictionary's actual size. After renaming the duplicate literal key, static enumeration proved 53 literal keys and 53 unique names. The failed approach inferred 54 from the misleading old success string instead of enumerating source keys before writing.
- **Correction / executable recurrence guard:** [5e0e85ec](https://github.com/m-shogo/memories-project/commit/5e0e85ec95f8e1c5fafecaf189becf178dbed9c5) binds the expected count to the observed 53-case inventory and uses the same constant for the printed CI count and the fail-closed inventory assertion. The previously shadowed conditional tracked-check fixture remains restored.
- **Retry condition:** Only change the count with an actual reviewed fixture inventory change and require exact-source CI proof. Do not retry the rejected 54-count approach unchanged.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** Post-write GitHub source and diff reads confirm `5e0e85ec` changed only the read-only entrypoint script, with 7 additions and 3 deletions. Exact-source CI is not yet confirmed for the corrected commit; this record does not claim success.
- **Why safe / reusable mechanism:** The CI output is now coupled to the same executable fixture count gate, preventing a stale hardcoded count from being used as evidence. No reviewed workflow, production evidence, registry, credential, traffic, readiness or human approval authority changed.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`. The learning addendum is supplemental append-only history, not production or promotion evidence.
- **Next safe target:** Verify the corrected exact-source CI, then audit inert heredoc/function-wrapped Python commands and add bounded semantic negative fixtures.

## 2026-10-28 — Heredoc and uninvoked shell-function CI bypasses fail closed

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / evidence:** Review of the common source-negative CI scanner showed that it recognized a line `python scripts/check.py` without proving the line was executable shell rather than inert heredoc content or a function body never called. All 52 current reviewed workflows were re-read in bounded groups; none used heredoc or function wrappers around the 63 direct Python commands. This is a static guard gap, not an observed production failure.
- **Verified root cause:** The parser matched direct Python line shape and preceding conditionals but did not classify earlier heredoc introducers or shell-function declarations in the same `run: |` block.
- **Failed approach:** Presence of an exact Python command and subsequent clean-source checks cannot prove the validator ran when the command is data or inside an uninvoked function.
- **Correction / executable recurrence guard:** [9d4a5d27](https://github.com/m-shogo/memories-project/commit/9d4a5d274623f5a69f44b68cfa347c302917cbec) rejects heredoc introducers and shell-function declarations preceding a direct validator. Five semantic negatives cover `cat <<`, `: <<`, `name() {`, `function name {` and a multiline function declaration. The exact executable fixture inventory is now 58 cases, with the count assertion and printed proof sharing the same constant.
- **Retry condition:** Revisit only when an independently reviewed source-negative workflow requires heredoc or function execution topology, and prove actual execution rather than weakening the guard. Do not retry unchanged canonical large-file transport, MinIO HTTP 401 or human-promotion blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** Post-write source/diff inspection confirmed `9d4a5d27` changed only `scripts/validate-memory-os-entry-docs.py` (40 additions, 1 deletion); 58 literal fixture names were statically enumerated and found unique before write. Exact-source GitHub Actions CI remained unobserved at this record's creation; no CI success is asserted.
- **Why safe / reusable mechanism:** The shared read-only validator now rejects two ways to make a visible Python line non-executable. No reviewed workflow, production registry/evidence, credential, traffic, readiness or human promotion authority was modified.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`, with zero registered/semantically eligible generations, approved recovery objectives, executable reviewed requests, generation evidence, complete typed eight-domain records or final candidates. Learning remains supplementary history, never production or promotion evidence.
- **Next safe target:** Confirm exact-source CI, then examine command-resolution shadowing (aliases, shell functions named `python`, PATH changes) and whether CI still validates all 52 workflows on each relevant source change.

## 2026-10-28 — Exact-source CI confirms 58-case heredoc/function guard

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** [Autonomous Learning Guard #40671625215](https://github.com/m-shogo/memories-project/actions/runs/40671625215) completed SUCCESS on exact `9d4a5d27` source. Job logs prove 52 workflows, 63 direct Python commands, **58 executed semantic reachability negatives**, 128 canonical learning negatives, and 1,186 helper-ancestor negatives. [#40671504188](https://github.com/m-shogo/memories-project/actions/runs/40671504188) also completed SUCCESS on exact `5e0e85ec` source, proving the corrected 53-case inventory and restoring the previously shadowed fixture.
- **Why safe / reusable mechanism:** The existing read-only entrypoint script rejects inert heredoc/function Python lines; the exact-source CI now proves the expanded fixture inventory is executed, not merely declared.
- **Protected-authority check:** All nine protected contract/registry blobs remained unchanged after both code changes. `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`; no production evidence or human promotion is inferred.

## 2026-10-28 — Command-resolution overrides rejected in source-negative CI

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / evidence:** A read-only audit of all 52 source-negative workflows found no alias, hash-pin, source, eval, exec or PATH/PYTHONPATH assignment in the direct validator shell blocks. The common scanner nevertheless did not reject these future overrides. Two reviewed migration workflows do use a cleanup `trap`; that legitimate pattern was preserved. This is a static future-bypass gap, not a production failure.
- **Verified root cause:** The scanner checked the Python line and shell control flow but not preceding command-resolution changes. This reuses the already recorded readonly-workflow shell function/hash-pin lesson rather than repeating a known failed approach.
- **Failed approach:** Literal `python scripts/check.py` and clean-source checks alone do not prove the intended interpreter is invoked if an alias, hash pin, sourced shell file, eval or PATH override changes command resolution.
- **Correction / executable recurrence guard:** [797dd48b](https://github.com/m-shogo/memories-project/commit/797dd48ba5dc04321e909f25dbbc3a67331f4af5) rejects such unreviewed overrides before Python validator execution. Six semantic negatives cover alias, hash pin, source, PATH, exported PYTHONPATH and eval; fixture inventory advances from 58 to 64. Legitimate reviewed cleanup traps are not blanket-rejected.
- **Retry condition:** Revisit only if reviewed workflow command-resolution architecture changes or an observed bypass escapes the bounded classifier. Do not retry unchanged canonical large-file transport, Quay MinIO HTTP 401 or human-promotion blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** GitHub post-write source/diff reads confirm only the CI-reachable entrypoint script changed (33 additions, 1 deletion). Sixty-four unique literal negative fixture names were statically counted before write. Exact-source [Autonomous Learning Guard #40671800058](https://github.com/m-shogo/memories-project/actions/runs/40671800058) was QUEUED at recording time; CI success is not asserted.
- **Why safe / reusable mechanism:** The new guard checks interpreter resolution while retaining all existing workflow triggers, step execution paths, read-only permissions and the two legitimate cleanup traps. No production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective/evidence or human promotion authority changed.
- **Protected-authority check:** All nine protected authority blob SHAs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`, with zero eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records or final candidates. Learning remains supplemental and cannot promote readiness.
- **Next safe target:** Verify exact-source 64-case CI and inspect cross-step `GITHUB_PATH`/`GITHUB_ENV` command-resolution persistence and step-level env overrides without altering reviewed workflows.

## 2026-10-28 — Cross-step interpreter environment must not bypass validators

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** Bounded read-only inspection of all 52 source-negative workflows found no `GITHUB_PATH`/`GITHUB_ENV` writes or interpreter-shadowing YAML `PATH`, `PYTHONPATH`, `BASH_ENV` or `ENV` keys. The common guard previously accepted such mutations, despite their ability to alter a later validator's interpreter or import path across Actions steps. This is a verified static coverage gap, not a production incident.
- **Verified root cause:** The prior command-resolution guard checked only earlier shell lines in the same `run: |` block, not persistent Actions environment channels or YAML environment overrides.
- **Failed approach:** Checking a direct `python scripts/check.py` line and same-block alias/hash/PATH overrides cannot rule out earlier `GITHUB_PATH`/`GITHUB_ENV` writes or job/step/workflow interpreter environment changes.
- **Correction / executable recurrence guard:** [801a8c3e](https://github.com/m-shogo/memories-project/commit/801a8c3ea83dc1bf7cd7fb5d77e298b378053e7f) rejects both persistent Actions environment channels and the four interpreter-affecting YAML environment keys. Five new semantic negatives cover workflow, job and step env overrides plus earlier-step `GITHUB_PATH` and `GITHUB_ENV` writes. The exact fixture inventory advances from 64 to 69.
- **Retry condition:** Revisit only after a reviewed CI workflow explicitly needs these environment mechanisms, with separate proof of interpreter integrity. Do not retry unchanged canonical large-file transport, Quay MinIO HTTP 401 or human-promotion blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** [Autonomous Learning Guard #40671800058](https://github.com/m-shogo/memories-project/actions/runs/40671800058) completed SUCCESS on exact `797dd48b` source, with 52 workflows, 63 Python commands, 64 reachability negatives, 128 canonical learning negatives and 1,186 helper-ancestor negatives in job logs. For new `801a8c3e`, post-write GitHub source/diff reads confirm only the read-only entrypoint changed (25 additions, 1 deletion) and 69 unique fixture names were enumerated; exact-source CI was not yet observable when recorded.
- **Why safe / reusable mechanism:** This extends the same existing CI-reachable guard to cross-step interpreter integrity, without changing any reviewed workflow, production evidence, recovery registry, credentials, traffic, readiness or human promotion.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remain unchanged; `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, typed eight-domain records or final candidates. The supplemental append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.
- **Next safe target:** Confirm exact-source 69-case CI, then inspect shell trap handlers or YAML scalar/step-boundary ambiguity that could still mask validator failure.

## 2026-10-28 — Shell trap masking restricted to reviewed cleanup patterns

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** The shared source-negative validator execution scanner previously ignored shell traps. A preceding `trap 'exit 0' EXIT` can convert a failed validator into an apparently successful CI step even when `set -euo pipefail` and the exact Python command remain present. Read-only workflow inspection identified two legitimate temporary-directory cleanup traps (`$temp` and `$sandbox` on EXIT); neither is a promotion or readiness signal. This is a static bypass, not a production incident.
- **Verified root cause:** The common scanner did not bind trap declarations to an approved allowlist before the Python invocation.
- **Failed approach:** Treating fail-closed shell options and exact validator text as sufficient without constraining exit-handler behavior.
- **Correction / executable recurrence guard:** [74fce2b0](https://github.com/m-shogo/memories-project/commit/74fce2b0d4d35170444a9316624a68409c681075) allows only the two existing reviewed `rm -rf` temporary-directory EXIT cleanup trap forms and rejects all other preceding traps. Five semantic negatives cover ERR, EXIT, DEBUG, RETURN success masking and an unreviewed EXIT cleanup. The fixture inventory advances from 69 to 74.
- **Retry condition:** Revisit only when a reviewed workflow introduces a new demonstrably safe cleanup trap or the approved temporary-directory ownership model changes. Do not retry unchanged canonical large-file transport, Quay MinIO HTTP 401 or human-promotion blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** [Autonomous Learning Guard #40671985272](https://github.com/m-shogo/memories-project/actions/runs/40671985272) completed SUCCESS on exact `801a8c3e` source; job logs confirm 52 workflows, 63 Python commands, 69 reachability negatives, 128 canonical learning negatives and 1,186 helper-ancestor negatives. New `74fce2b0` source/diff reads confirm only the read-only entrypoint script changed (30 additions, 1 deletion), with 74 distinct literal negative fixtures enumerated. Exact-source CI for `74fce2b0` is not yet confirmed here.
- **Why safe / reusable mechanism:** The guard rejects shell error-handler masking while preserving the two reviewed cleanup forms. No workflow, production evidence, generation/objective/drill/recovery registry, credentials, traffic, readiness or promotion authority changed.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remained unchanged. Production Status stays `NO_GO`; OPS-P0-007 stays `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records or final candidates. Learning is supplemental append-only history, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.
- **Next safe target:** Verify exact-source 74-case CI, then audit step metadata after the validator run block and any remaining shell command substitution paths. Preserve existing human promotion boundaries.

## 2026-10-28 — Source-level duplicate negative keys are AST-guarded

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** Earlier this run a duplicate literal Python dictionary key silently shadowed a distinct negative fixture. The corrected exact fixture count alone still permitted a hypothetical replacement in which a new key and a duplicate key canceled out numerically. This is a remaining deterministic test-harness coverage gap, not a production failure.
- **Verified root cause:** Runtime dictionary length cannot detect duplicate source-level keys once Python has overwritten the earlier entry. A count-only inventory is insufficient.
- **Failed approach:** Treating `len(cases) == EXPECTED_SOURCE_NEGATIVE_FIXTURE_COUNT` as a complete proof of source-level fixture uniqueness.
- **Correction / executable recurrence guard:** [e148f0c9](https://github.com/m-shogo/memories-project/commit/e148f0c9bc4dd0ba690a5c99e5b1d1eb0011a70c) parses its own source AST, requires exactly one literal `cases` dictionary and unique literal string keys, compares the AST key count to the executed dict, and performs an in-memory duplicate-key mutation that must be rejected. The 74 existing workflow semantic negatives remain intact.
- **Retry condition:** Revisit only when the reviewed fixture declaration architecture changes; require exact-source CI and an explicit negative probe for any replacement inventory mechanism.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** [Autonomous Learning Guard #40672141871](https://github.com/m-shogo/memories-project/actions/runs/40672141871) completed SUCCESS on exact `74fce2b0` source, with 52 workflows, 63 direct Python commands, 74 reachability negatives, 128 canonical learning negatives and 1,186 helper-ancestor negatives. The new AST commit `e148f0c9` changed only the existing read-only entrypoint script (43 added lines, no deletions); exact-source CI for it was queued at recording time.
- **Why safe / reusable mechanism:** A self-contained AST negative prevents the original duplicate-key failure from silently recurring even if a future fixture-count change accidentally hides it. No reviewed workflow, production evidence, registry, credentials, traffic, readiness or promotion authority changed.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remained unchanged; `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records or final candidates. Learning remains append-only supplemental history and cannot satisfy any production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, independent review or human promotion gate.
- **Next safe target:** Confirm exact-source AST self-probe CI, then audit the workflow's step-level metadata boundaries for unreviewed `shell`, `if` or `continue-on-error` keys after a reviewed run block.

## 2026-10-28 — CI shell/defaults execution authority is explicit

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / evidence:** All 52 reviewed source-negative workflows were re-read and had no explicit `shell:` or `defaults:` override. The shared scanner nevertheless did not reject a later step-level custom shell or job/workflow defaults that could execute `/bin/true {0}` instead of the reviewed Bash validator. This is a static execution-path gap, not a production failure.
- **Verified root cause:** The scanner bound the `run: |` text but not its GitHub Actions shell selection or inherited run defaults.
- **Failed approach:** Treating a valid Bash command block as proof of execution while allowing a custom shell or inherited defaults to replace the interpreter.
- **Correction / executable recurrence guard:** [daccaf32](https://github.com/m-shogo/memories-project/commit/daccaf32afc7816a4c1a0a04232b6c343e5646d8) rejects unreviewed shell/defaults overrides. Five new semantic negatives cover validator and source-check step shell substitutions, a post-run shell key, and job/workflow defaults. The fixture inventory advances from 74 to 79.
- **Retry condition:** Revisit only if a reviewed source-negative workflow needs an explicit shell/defaults policy, with an executable proof of interpreter identity. Do not retry unchanged canonical large-file transport, Quay MinIO HTTP 401 or human-promotion blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** [Autonomous Learning Guard #40672266991](https://github.com/m-shogo/memories-project/actions/runs/40672266991) completed SUCCESS on exact `e148f0c9` source, with 52 workflows, 63 direct Python commands, 74 reachability negatives, 128 canonical learning negatives and 1,186 helper-ancestor negatives. This proves the source-AST duplicate-key self-probe is CI-executed. The new `daccaf32` source/diff read shows only the existing read-only entrypoint script changed (23 additions, 1 deletion) and 79 unique fixture names were statically enumerated; exact-source [#40672433472](https://github.com/m-shogo/memories-project/actions/runs/40672433472) was QUEUED at recording time.
- **Why safe / reusable mechanism:** The same CI-reachable shared guard now binds GitHub Actions interpreter selection without changing reviewed workflows, production evidence, generation/objective/drill/recovery registries, credentials, traffic, readiness or human promotion.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`, with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records or final candidates. Supplemental learning is append-only and never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
- **Next safe target:** Confirm exact-source 79-case CI, then audit run-block boundary/command-substitution patterns and independently verify no protected authority drift.

## 2026-10-28 — CI action execution inventory is pinned and workflow-specific

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / evidence:** Read-only inventory of all 52 source-negative workflows found pinned checkout/setup-python Actions, but the shared reachability guard did not reject unreviewed extra action steps, floating action refs, duplicate actions or substitution of the pinned checkout/setup-python references. Four workflows use a separately reviewed legacy checkout SHA, and one live-object workflow uses a third pinned setup-go Action. This is a static CI supply-chain/execution-path gap, not a production failure.
- **Verified root cause:** The shared scanner checked `persist-credentials: false` and Python shell commands but not the complete Actions `uses:` inventory and per-workflow pin exceptions.
- **Failed approach:** Assuming credential persistence and direct validator text imply trusted Actions execution without constraining the Actions that run before the validator.
- **Correction / executable recurrence guard:** [6f4a6076](https://github.com/m-shogo/memories-project/commit/6f4a6076c579373e746e2e1425df3193a1db79d4) requires the exact ordered checkout/setup-python action pins, preserves the four named legacy checkout exceptions and the one reviewed setup-go exception, and rejects additional/shadowed `uses:` entries. Eight new semantic negatives cover floating/substituted pins, extra/duplicate steps, an unreviewed setup-go step, wrong-workflow checkout exception and a shadowed `uses` key. The synthetic positive fixture now uses real reviewed pins; inventory advances from 79 to 87.
- **Retry condition:** Revisit only after an independently reviewed action pin rotation or workflow-specific setup change; revalidate exact-source positive and negative CI before accepting a new action. Do not retry unchanged canonical large-file transport, Quay MinIO HTTP 401 or human-promotion blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** [Autonomous Learning Guard #40672433472](https://github.com/m-shogo/memories-project/actions/runs/40672433472) completed SUCCESS on exact `daccaf32` source; job logs confirm 52 workflows, 63 direct Python commands, 79 semantic reachability negatives, 128 canonical learning negatives and 1,186 helper-ancestor negatives. The new `6f4a6076` source/diff read confirms only the existing read-only entrypoint script changed (57 additions, 2 deletions); 87 unique fixture names were statically enumerated before write. Exact-source CI for this new commit is not yet confirmed.
- **Why safe / reusable mechanism:** The guard reuses the observed immutable action pins and preserves reviewed exceptions, without changing any workflow, production evidence, generation/objective/drill/recovery registry, credential, traffic, readiness or promotion authority.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remained unchanged; `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records or final candidates. Learning is supplemental append-only history, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.
- **Next safe target:** Verify exact-source 87-case CI and audit Action step metadata (e.g. duplicate `with` keys or checkout source overrides) without modifying protected production authorities.

## 2026-10-28 — Checkout source binding and credentials are exact

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / evidence:** The common source-negative CI guard verified pinned checkout Actions but not the exact `with:` settings. A changed `ref: main`, duplicated YAML ref/credential key, wider checkout depth or unreviewed token could retain the visible Python validator while changing the checked source or credential boundary. All 52 current workflows were independently re-read and found to use the same PR-head/push-source ref expression, `fetch-depth: 1` and `persist-credentials: false`. This is a static guard gap, not a production incident.
- **Verified root cause:** The scanner used presence-only `persist-credentials: false` and direct command checks without constraining the checkout step's complete `with` block.
- **Failed approach:** A pinned checkout Action alone does not prove exact source identity or non-retention of credentials when its input mapping can be shadowed.
- **Correction / executable recurrence guard:** [339d16d8](https://github.com/m-shogo/memories-project/commit/339d16d86dec4a74d8fcf17ae4285c7a8484ab25) requires exactly one checkout action and an exact four-line `with` block containing the reviewed PR-head/push-source ref expression, depth one and disabled credential persistence. Seven new semantic negatives cover changed, missing and duplicate refs, changed depth, retained or duplicate credentials and an unreviewed token. The positive fixture was updated to the observed checkout settings; inventory advances from 87 to 94.
- **Retry condition:** Revisit only after an independently reviewed checkout source/credential policy change with exact-source CI proof. Do not retry unchanged canonical large-file transport, Quay MinIO HTTP 401 or human-promotion blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** [Autonomous Learning Guard #40672682593](https://github.com/m-shogo/memories-project/actions/runs/40672682593) completed SUCCESS on exact `6f4a6076` source; job logs confirm 52 workflows, 63 Python commands, 87 reachability negatives, 128 canonical learning negatives and 1,186 helper-ancestor negatives. New `339d16d8` source/diff reads confirm only the CI entrypoint script changed (50 additions, 1 deletion); 94 unique fixture names were statically enumerated before write. Exact-source [#40672968530](https://github.com/m-shogo/memories-project/actions/runs/40672968530) was QUEUED at recording time; no success is asserted.
- **Why safe / reusable mechanism:** This reuses the existing read-only CI scanner to protect checkout source and credential boundaries without altering reviewed workflows, production evidence, generation/objective/drill/recovery registries, credentials, traffic, readiness or promotion authority.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remained unchanged; `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records or final candidates. Learning remains supplemental append-only history and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
- **Next safe target:** Confirm exact-source 94-case CI and inspect setup-python/setup-go input shadowing, action-step `if`/failure suppression, and exact job checkout source binding.
