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

## 2026-10-28 — setup-python interpreter inputs are exact and unshadowed

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** A read-only inventory of all 52 source-negative workflows confirmed `actions/setup-python` uses the reviewed pinned Action and `python-version: "3.12"`. The shared guard did not reject changed/duplicate Python version inputs, injected cache/version-file inputs or missing `with` authority. This is a static CI execution-path gap, not a production failure.
- **Verified root cause:** The existing Action inventory guard constrained `uses:` refs but did not inspect the setup-python `with` mapping.
- **Failed approach:** A pinned setup-python Action does not prove the reviewed interpreter version when its inputs can be changed or shadowed.
- **Correction / executable recurrence guard:** [b0fe55af](https://github.com/m-shogo/memories-project/commit/b0fe55afcf244f46bdc9f0b4d642df2a1efae6d6) requires exactly one setup-python step and its exact two-line `with` mapping. Six semantic negatives cover changed, missing or duplicated Python versions, cache and version-file overrides, and a missing `with` block. The negative inventory advances from 94 to 100.
- **Retry condition:** Revisit only if an independently reviewed interpreter version/input policy changes; require exact-source CI and negative proof. Do not retry unchanged canonical large-file transport, Quay MinIO HTTP 401 or human-promotion blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** [Autonomous Learning Guard #40672968530](https://github.com/m-shogo/memories-project/actions/runs/40672968530) completed SUCCESS on exact `339d16d8` source; job logs prove 52 workflows, 63 Python commands, 94 semantic reachability negatives, 128 canonical learning negatives and 1,186 helper-ancestor negatives. The new `b0fe55af` commit changed only the read-only entrypoint script (42 additions, 1 deletion); 100 unique fixture names were statically enumerated before write. Exact-source CI for this commit is not yet confirmed here.
- **Why safe / reusable mechanism:** Interpreter input authority is now checked within the same existing read-only CI guard. No workflow, production evidence, generation/objective/drill/recovery registry, credential, traffic, readiness or human promotion authority changed.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remain unchanged; `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records or final candidates. Supplemental append-only learning is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.
- **Next safe target:** Verify exact-source 100-case CI and harden the single reviewed setup-go Action input mapping without weakening any production gate.

## 2026-10-28 — Reviewed setup-go exception has exact inputs and executable negatives

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** The single reviewed live-object-stage source-negative workflow uses pinned `actions/setup-go` with `go-version: "1.23.x"` and `cache: false`. The common guard previously pinned the action SHA but did not reject altered/duplicated Go version, enabled cache or extra setup-go inputs. This is a static execution-authority gap, not a production incident.
- **Verified root cause:** The existing per-workflow Action inventory covered the setup-go `uses` ref but not its `with` mapping.
- **Failed approach:** An immutable Action SHA alone cannot prove the reviewed Go toolchain/cache behavior when input keys can be shadowed.
- **Correction / executable recurrence guard:** [73ed1282](https://github.com/m-shogo/memories-project/commit/73ed12826ec87ea46b86f9559d5430e365d7181b) binds the sole setup-go step to the exact reviewed Go version/cache inputs. A separate positive synthetic live-object fixture and six negative mutations cover changed, duplicate or missing Go version, enabled or missing cache and an extra input. The common fixture inventory advances from 100 to 106, with per-fixture relative workflow binding.
- **Retry condition:** Revisit only after an independently reviewed setup-go version/cache policy change and exact-source CI validation. Do not retry unchanged canonical large-file transport, Quay MinIO HTTP 401 or human-promotion blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** [Autonomous Learning Guard #40673180471](https://github.com/m-shogo/memories-project/actions/runs/40673180471) completed SUCCESS on exact `b0fe55af` source, with 52 workflows, 63 Python commands, 100 semantic reachability negatives, 128 canonical learning negatives and 1,186 helper-ancestor negatives. The new `73ed1282` commit changed only the CI-reachable read-only entrypoint script (55 additions, 2 deletions); 106 unique literal fixture names were statically enumerated before write. Exact-source [#40673336622](https://github.com/m-shogo/memories-project/actions/runs/40673336622) was QUEUED at recording time, so no CI success is claimed yet.
- **Why safe / reusable mechanism:** The one existing setup-go exception is made explicit without broadening the set of accepted actions or changing reviewed workflows, production evidence, generation/objective/drill/recovery registries, credentials, traffic, readiness or human promotion.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remained unchanged; `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records or final candidates. Supplemental append-only learning never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
- **Next safe target:** Verify exact-source 106-case CI, then audit step-level Action execution metadata and production-authority drift independently.

## 2026-10-28 — Final exact-source 106-case CI evidence

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / observed evidence:** [Autonomous Learning Guard #40673336622](https://github.com/m-shogo/memories-project/actions/runs/40673336622) completed SUCCESS on exact code SHA `73ed12826ec87ea46b86f9559d5430e365d7181b`. The completed job log proves the canonical learning contract validator, 128 canonical learning negative cases, 52 source-negative workflows, 63 direct Python validator commands, 106 executed reachability negative fixtures (including the setup-go positive/negative exception), 1,186 helper-ancestor negatives, append-only canonical learning verification and final read-only clean-worktree checks.
- **Why safe / reusable mechanism:** The reviewed source-negative CI workflows were not changed. The shared read-only validator now proves both direct command reachability and the approved Actions/checkout/interpreter/toolchain execution boundary; all new fixture mutations are synthetic.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remained unchanged relative to the run baseline. Production Status stays `NO_GO`; OPS-P0-007 stays `PREREQUISITES_BLOCKED`. No registered or semantically eligible production-equivalent generation, approved current recovery objective, executable reviewed drill request, request-bound generation recovery evidence, complete typed eight-domain non-resurrection record, final candidate or human production-promotion authority was created. Learning is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.
- **Next safe target:** Audit the remaining GitHub Actions step metadata and shell source-boundary edge cases with the existing common guard; do not retry unchanged external MinIO, human approval or canonical learning transport blockers.

## 2026-10-28 — Source-negative workflow metadata authority and CI fixture corrections

### Material failure 1: source-negative positive control rejected

- **Symptom:** [Autonomous Learning Guard #40678512591](https://github.com/m-shogo/memories-project/actions/runs/40678512591) on exact `9b01b08d` FAILED with `source-negative reachability positive control failed`. Canonical learning contract and 128 canonical negatives passed.
- **Observed evidence:** The newly added environment inventory used the raw Python regex `r"^\\\\s*env:"`, which matches a literal backslash-s rather than whitespace. The synthetic positive fixture correctly had one reviewed `env:` block, but the regex counted zero.
- **Verified root cause:** Double escaping while generating Python source through a JavaScript patch; the positive control failed closed.
- **Failed approach:** Trusting source-string construction without running the CI positive control.
- **Correction:** [`5231664b`](https://github.com/m-shogo/memories-project/commit/5231664bc09ff7532ba32193cafc44d05a389f74) replaced the literal-backslash pattern with `r"^\\s*env:"`.
- **Executable recurrence guard:** The synthetic positive fixture now includes the reviewed exact PR-head environment block, and the existing entrypoint guard runs it before 121 negative fixtures.
- **Retry condition:** Re-evaluate the environment regex only after the exact-source positive and negative CI results are checked; never relax it to permit unreviewed environment overrides.

### Material failure 2: two semantic negatives escaped

- **Symptom:** [Autonomous Learning Guard #40678614650](https://github.com/m-shogo/memories-project/actions/runs/40678614650) on exact `5231664b` FAILED because `job runner override` and `job timeout override` negatives escaped.
- **Observed evidence:** The common validator compared the ordered job metadata key names but not their scalar values. A changed runner or timeout preserved the expected keys.
- **Verified root cause:** Structural-key equivalence was incorrectly treated as value authority.
- **Failed approach:** Key-only job metadata validation.
- **Correction / executable recurrence guard:** [`71979b00`](https://github.com/m-shogo/memories-project/commit/71979b00bb25501b914d1a2f9fc4552023ef9041) additionally requires exact `runs-on: ubuntu-latest` and `timeout-minutes: 5`. The two previously escaped mutations remain mandatory negatives; 121 cases are bound to the shared CI entrypoint.
- **Retry condition:** Only change the exact runner/timeout values after independent review of the execution environment and exact-source positive/negative CI evidence.

### Material transient tool failure: GitHub Git-object write preparation

- **Symptom / evidence:** A GitHub GraphQL request failed transiently at 2026-10-28 11:15:43 UTC with request reference `B71E:1146FE:26F13B:81549D:6AE1D95E`; a subsequent read confirmed the intended regex correction had not reached the branch.
- **Root cause:** Unknown external GraphQL execution failure, not evidence of an application defect.
- **Failed approach:** The first Git-object preparation attempt returned no confirmed commit.
- **Correction / recurrence guard:** Re-read `so`, the target file and learning contract; rebuild the commit on the advanced branch and publish with an expected-HEAD lease. No force push.
- **Retry condition:** Retry only after a fresh successful read confirms source state; stop on a mismatched lease rather than overwriting concurrent work.

### Scoped success and authority boundary

- **Outcome / observed evidence:** A read-only inventory of the 52 source-negative workflows found the reviewed job timeout and sole `PR_HEAD_SHA` environment mapping consistently present. The code commits `9b01b08d`, `5231664b` and `71979b00` changed only the common read-only entrypoint validator; the latest exact-source CI for `71979b00` remains **unconfirmed at this learning append**.
- **Why safe / reusable mechanism:** Fifteen new synthetic metadata mutations cover workflow concurrency/defaults/environment, job runner/timeout/container/strategy/environment, and step working directory/ID/environment/PR-head/continue-on-error/timeout. Production workflows and authorities were not edited.
- **Protected-authority check:** The nine protected production status, OPS-P0-007 snapshot, generation/objective/drill/evidence/typed-non-resurrection/promotion registries and canonical learning contract remained byte-identical by blob SHA on the checked branch. `productionDecision=NO_GO`, OPS-P0-007 has zero eligible generations, objectives, executable requests, recovery evidence, typed eight-domain records and final candidates. No production or human-promotion authority was created.
- **Learning boundary:** This is append-only supplemental history, not the canonical 4.17 MB learning authority and never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence. Canonical transport blocker remains unchanged; do not retry it blindly.

## 2026-10-28 — Exact-source metadata and shell-boundary CI closures

### Material success: exact workflow/job/step metadata authority

- **Outcome / observed evidence:** [Autonomous Learning Guard #40678750672](https://github.com/m-shogo/memories-project/actions/runs/40678750672) completed SUCCESS on exact code `71979b00bb25501b914d1a2f9fc4552023ef9041`. The job log proves 52 source-negative workflows, 63 direct Python validator commands, 121 executed reachability negative fixtures, 128 canonical learning negatives and 1,186 helper ancestor negatives. The prior two failures are closed by executable checks, not by ignoring the fixtures.
- **Why safe:** Reviewed workflows were read only; the common CI entrypoint was the sole code target. The positive fixture contains the reviewed PR-head environment and job runner/timeout; unknown workflow/job/step metadata and environment shadows fail closed.
- **Reusable mechanism:** Require exact approved metadata keys, runner and timeout scalar values, sole `PR_HEAD_SHA` environment mapping and pinned checkout/toolchain settings, plus negative mutation proof.
- **Protected-authority check:** All nine protected authority blob SHAs were unchanged. `productionDecision=NO_GO`, OPS-P0-007 remains prerequisite-blocked with zero registered/eligible generations, approved objectives, executable reviewed requests, recovery evidence, complete typed non-resurrection records or final candidates.

### Material failure prevented: inert or weakened exact-source shell

- **Symptom / observed evidence:** A read-only audit of all 52 source-negative workflows found 50 with the same reviewed PR-head/push verification shell template and two explicit operability-inventory variants (atomic-write uses `PR_HEAD_SHA:-`; both omit the diagnostic echo). The previous common guard merely searched for `git rev-parse HEAD` and `git status --porcelain` substrings, which comments, echoes or short-circuited commands could satisfy. No observed production failure.
- **Verified root cause:** Source substring presence is not equivalent to an executable exact-source comparison in the correct shell step.
- **Failed approach:** Relying on the checkout Action ref and textual HEAD-command fragments without verifying the reviewed source-verification shell block.
- **Correction / executable recurrence guard:** [`e16a50ea`](https://github.com/m-shogo/memories-project/commit/e16a50ea5d3f5414a1d9badb62a3fefb21ae0197) requires the complete reviewed fail-closed PR/push source-verification shell, with only the two observed explicit variants. Fourteen synthetic negatives reject commented, echoed, inverted, short-circuited, conditional, duplicated, or omitted HEAD/clean checks; early exits, disabled errexit, wrong expected SHA assignments, disabled event rejection and extra shell execution. Total shared reachability negatives: 135.
- **Retry condition:** Revisit the exact template only after a separately reviewed source-verification workflow change and exact-source positive/negative CI evidence; never weaken it for a hypothetical workflow variant.

### Material success: exact-source shell proof

- **Outcome / observed evidence:** [Autonomous Learning Guard #40679211756](https://github.com/m-shogo/memories-project/actions/runs/40679211756) completed SUCCESS on exact `e16a50ea5d3f5414a1d9badb62a3fefb21ae0197`. Job logs show 52 workflows, 63 Python commands, 135 reachability negative fixtures, 128 canonical learning negatives, 1,186 helper ancestor negatives and append-only canonical learning PASS.
- **Why safe / reusable mechanism:** This is a read-only static guard with synthetic mutations. The 52 reviewed workflow files, protected contracts/registries, production credentials, traffic, readiness and human promotion were not modified.
- **Protected-authority check:** The nine protected contract/registry blob SHAs remained identical; `productionDecision=NO_GO` and all OPS-P0-007 real-evidence gates remain unsatisfied. Supplemental learning cannot satisfy any production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gate.
- **Next safe target:** Audit whether post-validator clean-source checks can be bypassed by shell short-circuit lists, heredocs, traps or function wrappers while preserving the exact-source and authority guards. Canonical large-file transport, MinIO Quay HTTP 401 and human approval blockers are unchanged; do not retry them.

## 2026-10-28 — Post-validator clean-source check execution guard

### Material failure: five negative fixtures escaped the first regex patch

- **Symptom / observed evidence:** [Autonomous Learning Guard #40679533083](https://github.com/m-shogo/memories-project/actions/runs/40679533083) on exact `acaf2ed0` FAILED: tracked/untracked clean checks in heredocs, tracked/untracked checks in uninvoked functions, and a post-validator `eval` override escaped. Canonical learning and 128 canonical negatives passed.
- **Verified root cause:** JavaScript-to-Python patch double-escaped regex metacharacters in raw Python patterns, making the heredoc/function/command-resolution detectors inert.
- **Failed approach:** Assuming a source-level regex patch worked without running the negative fixtures.
- **Correction / executable recurrence guard:** [`dd4208ee`](https://github.com/m-shogo/memories-project/commit/dd4208ee856369c5f5d53a286cc8c7c6814aee61) replaced them with correct literal regexes and simplified the shell-list predecessor check. Ten mandatory negative mutations now cover clean-check short-circuit lists, heredocs, uninvoked functions, failure-masking traps and command overrides.
- **Retry condition:** Only revisit after a reviewed shell-syntax change, preserving all ten negative cases and exact-source CI proof.

### Material success: clean-source checks are executable

- **Outcome / observed evidence:** [Autonomous Learning Guard #40679623157](https://github.com/m-shogo/memories-project/actions/runs/40679623157) completed SUCCESS on exact `dd4208ee856369c5f5d53a286cc8c7c6814aee61`: 52 source-negative workflows, 63 Python commands, 145 reachability negative fixtures, 128 canonical learning negatives, 1,186 helper ancestor negatives and append-only canonical learning PASS.
- **Why safe / reusable mechanism:** The shared read-only entrypoint guard changed; reviewed workflows and production source/evidence were untouched. Post-validator tracked/untracked clean-source checks now reject inert shell wrappers rather than trusting visible command strings.
- **Protected-authority check:** All nine protected contract/registry blob SHAs remained unchanged. `productionDecision=NO_GO`, OPS-P0-007 prerequisite-blocked; zero registered/eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records or final candidates. No human promotion.
- **Learning boundary:** Supplemental append-only history is not canonical authority and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
- **Next safe target:** Check extra/folded YAML run steps that could execute outside the reviewed verification/validator steps. Do not retry unchanged canonical learning transport, Quay MinIO HTTP 401 or human approval blockers.

### Material concurrency guard success

- **Outcome / evidence:** An initial append attempt was prepared on `dd4208ee`, but a concurrent metrics commit advanced `so` to `0b992c7e` before publication. The expected-HEAD check rejected the stale write; no force update or loss of concurrent work occurred.
- **Why safe / reusable mechanism:** Re-read branch, target append-only file and canonical contract; rebuild on the new head only when the target blob remains unchanged.
- **Protected-authority check:** No production authority or registry write was attempted; `NO_GO` remains unchanged.

## 2026-10-28 — Closed source-negative run-step topology

### Material failure prevented: unreviewed YAML run-step execution

- **Symptom / observed evidence:** A read-only inventory of 52 reviewed source-negative workflows found 49 with two literal `run: |` steps and three with an explicitly reviewed third Go/migration step: live-object-stage, local-migration-recovery, and migration-evidence-registry. The previous common guard allowed additional `run` steps and folded `run: >` scalars because it checked individual Python invocations but not the complete step count and scalar style. No actual production incident was observed.
- **Verified root cause:** The step metadata allowlist accepted `run` keys without bounding their count, YAML scalar form or reviewed exceptions.
- **Failed approach:** Relying on the existence of verified Python commands while ignoring extra executable steps before or after the validator.
- **Correction / executable recurrence guard:** [`e8e161a9`](https://github.com/m-shogo/memories-project/commit/e8e161a909785e2914e0e0b75ac60f397c04ea92) binds every reviewed workflow to exactly two literal run steps, except the three observed reviewed three-step workflows. Eight negative mutations cover added, folded, duplicated or missing run scalars, including the setup-go exception. The synthetic setup-go positive control now models the reviewed third run step.
- **Retry condition:** Change the topology only if an independently reviewed workflow adds/removes a real execution step, with matching positive and negative CI evidence.

### Material success: 153-case reachability proof

- **Outcome / observed evidence:** [Autonomous Learning Guard #40679924009](https://github.com/m-shogo/memories-project/actions/runs/40679924009) completed SUCCESS on exact `e8e161a909785e2914e0e0b75ac60f397c04ea92`. The job log proves 52 source-negative workflows, 63 direct Python commands, 153 executed reachability negative fixtures, 128 canonical learning negatives, 1,186 helper ancestor negatives and canonical append-only PASS.
- **Why safe / reusable mechanism:** The common read-only CI guard and synthetic fixtures changed; the reviewed workflows, production evidence, credentials, traffic, readiness and promotion authority did not.
- **Protected-authority check:** All nine protected authority blob SHAs remain unchanged; `productionDecision=NO_GO`, OPS-P0-007 prerequisite-blocked with zero registered/eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records and final candidates. Human promotion is separate and was not invoked.
- **Learning boundary:** Supplemental append-only history is not canonical learning authority and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
- **Next safe target:** Audit the ordering of the exact-source verification step relative to direct validator execution, without weakening the existing reviewed topology or external blockers.

## 2026-10-28 — Exact-source verification must precede validator execution

### Material failure: legitimate third-step clone validator rejected

- **Symptom / observed evidence:** [Autonomous Learning Guard #40680150913](https://github.com/m-shogo/memories-project/actions/runs/40680150913) on exact `85fc5dbe` FAILED for `.github/workflows/migration-evidence-registry-source-negative.yml`: `direct Python validators must execute in reviewed second run step`.
- **Verified root cause:** The reviewed migration-evidence workflow runs one Python source validator in its second step and an additional independent authority negative validator inside a disposable exact-source clone in its third step. The first order guard incorrectly required every Python command to be in step two.
- **Failed approach:** Applying a universal second-step-only rule without accounting for the observed, reviewed third-step clone.
- **Correction / executable recurrence guard:** [`817d4c35`](https://github.com/m-shogo/memories-project/commit/817d4c353ffb867f5e58545b275b1d700d0116ab) requires at least one direct Python validator in the reviewed second run step, allows the third-step Python command only for the exact migration-evidence workflow, and still requires source verification before any validator. Two synthetic step-order negatives cover the ordinary and setup-go positive controls, raising reachability negatives from 153 to 155.
- **Retry condition:** Expand the third-step exception only after reviewing another concrete executable, exact-source workflow and adding corresponding negative proof; do not generalize it.

### Material success: reviewed step order and independent clone preserved

- **Outcome / observed evidence:** [Autonomous Learning Guard #40680259125](https://github.com/m-shogo/memories-project/actions/runs/40680259125) completed SUCCESS on exact `817d4c353ffb867f5e58545b275b1d700d0116ab`. The job log proves 52 source-negative workflows, 63 direct Python commands, 155 executed reachability negative fixtures, 128 canonical learning negatives, 1,186 helper ancestor negatives and canonical append-only PASS.
- **Why safe / reusable mechanism:** The common read-only guard now binds source verification to the first run step and Python validator execution to the reviewed second step, with one narrowly scoped disposable-clone exception. Reviewed workflow source, credentials, production traffic, evidence, readiness and human promotion were not changed.
- **Protected-authority check:** Nine protected contract/registry blob SHAs remain unchanged. `productionDecision=NO_GO`; OPS-P0-007 remains prerequisite-blocked with zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, request-bound recovery evidence, complete typed eight-domain non-resurrection records or final candidates. No human promotion.
- **Learning boundary:** This append-only addendum is not canonical learning authority and never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.
- **Next safe target:** Audit the independently reviewed third-step clone's source binding and ensure no other source-negative workflows can acquire unreviewed post-validator execution authority. Do not retry unchanged canonical learning transport, Quay MinIO HTTP 401 or human approval blockers.

## 2026-10-28 — Reviewed migration disposable clone source binding

### Material failure prevented: third-step clone source could drift

- **Symptom / observed evidence:** The reviewed migration-evidence-registry source-negative workflow runs a third-step independent authority negative validator in a disposable clone. Before this change, the shared guard allowed the third-step Python command without checking the clone origin, checkout SHA, clean-source assertions, trap or script identity. A different source could theoretically be validated; no actual bypass was observed.
- **Verified root cause:** The prior step-order exception constrained the Python command's location but not the source identity of the subprocess's working tree.
- **Failed approach:** Treating a reviewed third-step Python exception as sufficient execution proof without binding the exact clone shell.
- **Correction / executable recurrence guard:** [`cf986150`](https://github.com/m-shogo/memories-project/commit/cf9861503032d1046961bdf32cb3d4965e134459) binds the complete reviewed third-step clone command sequence and creates a synthetic positive migration fixture with a distinct validator script. Eight independent negatives reject remote source substitution, wrong checkout, missing `--no-hardlinks`, missing checkout or sandbox `cd`, short-circuiting, malicious trap and omitted nested clean-source check.
- **Retry condition:** Revisit only after independent review of a changed clone workflow, preserving exact-source positive/negative CI evidence.

### Material success: 163-case exact-source CI

- **Outcome / observed evidence:** [Autonomous Learning Guard #40680578166](https://github.com/m-shogo/memories-project/actions/runs/40680578166) completed SUCCESS on exact `cf9861503032d1046961bdf32cb3d4965e134459`. The job log proves 52 source-negative workflows, 63 direct Python commands, 163 executed reachability negative fixtures, 128 canonical learning negatives, 1,186 helper ancestor negatives and canonical append-only PASS.
- **Why safe / reusable mechanism:** The common read-only CI guard and synthetic fixtures changed; reviewed workflows, production source/evidence, credentials, traffic, readiness and human promotion did not.
- **Protected-authority check:** Nine protected contract/registry blob SHAs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007 prerequisite-blocked with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records or final candidates. Human promotion remains separate.
- **Learning boundary:** Supplemental append-only history cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
- **Next safe target:** Bind the two other reviewed third-step Go/local-migration shells to their exact execution and clone-source authority. Do not retry unchanged canonical learning transport, Quay MinIO HTTP 401 or human approval blockers.

## 2026-10-28 — Unsafe JavaScript replacement interpolation, rollback to known-good guard

### Material failure: generated Python source expanded unexpectedly

- **Symptom / observed evidence:** [`49b40e1c`](https://github.com/m-shogo/memories-project/commit/49b40e1c803a7faf09f4a0a923527268c3c54846) unintentionally expanded `scripts/validate-memory-os-entry-docs.py` from 83,009 to 239,230 characters during a proposed Go third-step guard patch. The generated guard excerpt contained unrelated Python source after a regex ending in `$'`. The intended 166-case validator was **not verified** and must not be reported as a success.
- **Verified root cause:** JavaScript `String.replace(search, replacementString)` interprets `$'` inside a replacement string as the entire unmatched suffix. The Go test regex contains `$'`, so direct replacement expanded the suffix into the new Python source. The pre-write size check had a lower bound but no upper bound.
- **Failed approach:** Unbounded direct JavaScript replacement with source text containing dollar-sign sequences, followed by a one-sided size sanity check.
- **Correction:** [`6870e236`](https://github.com/m-shogo/memories-project/commit/6870e23653a09bc5dcffa448d9ea37b48510afee) restored the exact previously validated Git blob `dd40b79439af3f009dd0c37cd65c917e8018a291` (83,009 characters; 163 reachability fixtures) via an expected-HEAD Git tree/ref lease, preserving intervening concurrent metrics commits.
- **Recurrence guard:** For any future source patch, use a replacement callback (`() => replacement`) or deterministic slicing, never raw replacement strings containing `$` tokens. Enforce both lower and upper byte/line change budgets, inspect the full inserted region, and require exact-source CI before treating a patch as successful.
- **Retry condition:** Do not repeat the Go third-step patch until the interpolation method and two-sided size precondition are changed and the restored exact-source CI is confirmed. This is a scoped code-authoring blocker, not a reason to retry unchanged MinIO, canonical learning transport or human promotion blockers.

### Material success: concurrency-safe rollback

- **Outcome / observed evidence:** The first rollback preparation detected concurrent branch advancement `49b40e1c` to `6fb39351` and refused its stale lease. A fresh read confirmed the corrupted file blob unchanged; the rebuilt rollback commit `6870e236` successfully restored the known-good 163-case source without force-pushing or rewriting other commits.
- **Why safe / reusable mechanism:** Git blob SHA restoration plus current branch/target rereads and an expected-HEAD lease provided bounded, non-destructive reconciliation. No production workflow, generation/objective/drill/recovery evidence, credential, traffic, readiness or promotion source was written.
- **Protected-authority check:** Nine protected contract/registry blob SHAs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007 remains prerequisite-blocked with zero real evidence or final candidates. Canonical learning is still separate and unmodified.
- **CI status:** Exact-source CI for restored `6870e236` was in progress at this append; do not assert success until its completed job log is inspected.
- **Learning boundary:** This supplemental append-only failure/success record is not canonical learning authority or production evidence and cannot satisfy backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-28 — Reviewed Go third-step execution bound

### Material failure prevented and recurrence correction

- **Symptom / observed evidence:** The reviewed live-object-stage source-negative workflow has a third step running two named Go tests, followed by tracked/untracked clean-source checks. The common guard previously bound its step count and action pin but not the exact Go command. An echo-only replacement could therefore leave the Python source validator green while silently omitting Go coverage.
- **Verified root cause:** Third-step execution authority was not bound to the reviewed Go command and clean checks.
- **Failed approach:** The first patch attempt used raw JavaScript replacement and caused unsafe source expansion (recorded above). A second attempt correctly used deterministic slicing and two-sided source-size bounds but initially omitted the `git diff --check` line from the synthetic Go positive control; this was corrected before exact-source success.
- **Correction / executable recurrence guard:** [`ff5c3cfd`](https://github.com/m-shogo/memories-project/commit/ff5c3cfd9334d703309d8422f02e462b319f223b) binds the complete reviewed Go third-step shell. [`f85f8224`](https://github.com/m-shogo/memories-project/commit/f85f82245ce21d7720bc2b5e94a768cb12cd6550) completes the synthetic positive shell. Three new negatives reject echo-only Go execution, missing `-count=1` and an unreviewed working directory, raising shared reachability negatives to 166.
- **Retry condition:** Only modify this exact Go command after a reviewed Go test/toolchain policy change, with positive and negative exact-source CI proof. All future source patches must use deterministic slicing or a callback and two-sided size bounds.

### Material success: exact-source 166-case CI

- **Outcome / observed evidence:** [Autonomous Learning Guard #40681290423](https://github.com/m-shogo/memories-project/actions/runs/40681290423) completed SUCCESS on exact `f85f82245ce21d7720bc2b5e94a768cb12cd6550`. Job logs prove 52 workflows, 63 direct Python commands, 166 executed reachability negative fixtures, 128 canonical learning negatives, 1,186 helper ancestor negatives and canonical append-only PASS.
- **Why safe / reusable mechanism:** Only the common read-only entrypoint validator and synthetic fixtures changed; reviewed workflows, production source/evidence, credentials, traffic, readiness and human promotion were untouched.
- **Protected-authority check:** Nine protected contract/registry blob SHAs remained unchanged. `productionDecision=NO_GO`, OPS-P0-007 prerequisite-blocked with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records or final candidates. Human promotion is separate and was not invoked.
- **Learning boundary:** This append-only supplemental record is not canonical learning authority and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
- **Next safe target:** Bind the remaining reviewed local-migration-recovery third-step clone source and clean checks, using the corrected bounded patch mechanism. Do not retry unchanged canonical learning transport, Quay MinIO HTTP 401 or human approval blockers.

## 2026-10-28 — Local recovery third-step disposable clone is exact-source bound

### Material failure prevented: unbounded third-step clone authority

- **Symptom / observed evidence:** The reviewed `.github/workflows/local-migration-recovery-source-negative.yml` has a third run step that clones the checked-out source and executes `validate-memory-os-local-migration-recovery-artifact-reconcile-negative.py`. The shared 166-case CI reachability guard permitted that third run step by count and ordering, but did not bind its complete clone origin, checkout ref, clean-worktree checks, command or cleanup trap. A modified third-step shell could skip the independent negative while the second-step Python validator remained visible. This was a static bypass risk, not an observed production incident.
- **Verified root cause:** The shared guard had exact third-step shell bindings for the migration-evidence clone and live-object Go test, but not for the separately reviewed local-recovery clone.
- **Failed approach:** Counting a reviewed third run step without checking its complete executable source/command topology is insufficient to prove the independent local-recovery validator ran.
- **Correction / executable recurrence guard:** [a8b8ed6d](https://github.com/m-shogo/memories-project/commit/a8b8ed6da0beecf6a0fbf433c7570214d0aade11) binds the exact reviewed local-recovery third-step shell, clone origin, `--no-hardlinks`, detached current-HEAD checkout, pre/post clone clean-source checks, script identity, EXIT cleanup trap and parent clean-source check. A distinct synthetic positive control and 10 negative mutations cover remote substitution, wrong checkout, missing clone protections/checks, wrong execution directory, echo-only validator, malicious trap and omitted final clean checks. The shared inventory rises from 166 to 176 executable negatives.
- **Retry condition:** Change this exact shell binding only after an independently reviewed local-recovery workflow change, with matching positive and negative exact-source CI. Preserve two-sided source-size budgets and deterministic slicing/callback-based replacements; do not retry unchanged large canonical-learning payload, MinIO HTTP 401 or human promotion blockers.

### Material success: observed CI and protected authority

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40682028745](https://github.com/m-shogo/memories-project/actions/runs/40682028745) completed **SUCCESS** on `a8b8ed6da0beecf6a0fbf433c7570214d0aade11`. The job log explicitly reports 52 reviewed source-negative workflows, 63 direct Python commands, **176 executed reachability negatives**, 128 canonical learning negatives, 1,186 helper-ancestor negatives, append-only canonical learning PASS and clean read-only execution. The GitHub compare API shows this code commit changed only `scripts/validate-memory-os-entry-docs.py` (77 additions, 2 deletions). Pre-write static checks counted 176 unique literal fixture keys and bounded source growth to 4,609 characters; the exact reviewed third-step shell was compared line-for-line with the workflow.
- **Why safe / reusable mechanism:** An existing CI-reachable read-only guard now proves the previously unbounded third-step clone topology; no reviewed workflow, production evidence, generation/objective/drill/recovery registry, credential, traffic, readiness or human promotion was modified. Future changes must preserve a positive exact-source control and fail-closed negative inventory.
- **Protected-authority check:** The 9 protected authority contract/registry Git blob SHAs, plus the production-shaped drill registry and canonical learning blob, were identical before and after the code commit (11 exact blob checks). Production status remains `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with zero registered and semantically eligible generations, approved recovery objectives, executable reviewed drill requests, generation recovery evidence, complete typed eight-domain records and final candidates. Preflight still requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current objective. Reviewed requests are planning-only, new generation evidence is request-bound, final candidates require complete typed coverage and independent review, and human promotion remains separate/non-automatic.
- **Learning boundary:** This append-only addendum is supplemental history, **not** the canonical learning authority and never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, independent review or promotion evidence. The canonical 4.17 MB learning write transport blocker has not changed; no unchanged failed write was retried.
- **Next safe target:** Audit the remaining supplemental learning append-only CI reachability and trigger topology without changing production authority or retrying unchanged permission/external-evidence blockers.

## 2026-10-28 — Closed reviewed second-step validator shell

### Material failure prevented: executable shell appended outside validated command sequence

- **Symptom / observed evidence:** A bounded read-only audit of all 52 reviewed source-negative workflows found their second run steps follow the same executable pattern: fail-closed shell setup, one or more direct Python validators, optional `git diff --check`, tracked `git diff --exit-code`, and final untracked clean-source check. The previous common reachability guard checked the presence, ordering and reachability of selected commands but did not reject an additional arbitrary command after the final clean-source check or between the reviewed commands. No actual production incident was observed.
- **Verified root cause:** The parser validated required shell statements as members of a run block instead of comparing the complete non-comment executable second-step sequence to the reviewed grammar.
- **Failed approach:** Presence-only checks of Python and clean-source statements cannot prove that unreviewed shell commands did not execute before or after those statements.
- **Correction / executable recurrence guard:** [923271f8](https://github.com/m-shogo/memories-project/commit/923271f8618a7c96ad16fe863fdf252916349977) closes the second-step executable grammar for reviewed workflows while preserving harmless comments and the existing synthetic nested-subshell positive control. A distinct real-path synthetic positive control and seven new negative fixtures reject arbitrary commands before/between/after validation, duplicated or reordered clean checks and extra shell function/checks. The shared source-negative fixture inventory advances from 176 to 183.
- **Retry condition:** Change the reviewed shell grammar only when a real workflow requires an independently reviewed new executable command and the exact-source positive/negative CI confirms it. Do not retry unchanged canonical large-file transfer, workflow-write permission, MinIO HTTP 401 or human-promotion blockers.

### Material success: exact-source CI and invariant preservation

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40682425930](https://github.com/m-shogo/memories-project/actions/runs/40682425930) completed **SUCCESS** on `923271f8618a7c96ad16fe863fdf252916349977`. Job logs prove 52 reviewed source-negative workflows, 63 direct Python commands, **183 executed semantic negatives**, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and clean-source PASS. The GitHub compare API reports only `scripts/validate-memory-os-entry-docs.py` changed (64 additions, 1 deletion); pre-write checks found 183 unique literal negative fixture names with a 3,447-character bounded source increase.
- **Why safe / reusable mechanism:** The shared read-only CI entrypoint now rejects extra shell execution even if every previously required validator and clean check remains visible. All 52 current reviewed second-step shells were inspected in bounded batches and matched the reviewed executable grammar. No workflow file, production registry/evidence, credential, traffic, readiness or promotion authority was changed.
- **Protected-authority check:** All nine protected contract/registry blob SHAs, plus the production-shaped failure-drill registry and canonical learning blob, remained unchanged after the code commit. Production status is `NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, human-approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records or final candidates. Preflight eligibility, current reviewed request binding, independent review and separate human promotion requirements remain untouched.
- **Learning boundary:** This append-only supplemental record does not replace the canonical learning authority and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, independent review or promotion gates.
- **Next safe target:** Audit whether the supplemental learning addenda are independently protected by append-only CI triggers; the existing canonical learning workflow does not currently list the addenda path. Respect the recorded unchanged workflow-write permission blocker rather than attempting an unsafe or repeated workflow mutation.

## 2026-10-28 — Third-step validator and Go-test source trigger reachability

### Material failure prevented: independent third-step sources absent from event filters

- **Symptom / observed evidence:** The common source-negative CI scanner checked workflow self-triggering and the scripts invoked as standalone `python scripts/...` lines, but the reviewed local-recovery third step invokes its independent validator inside `(cd "$temp/repo" && python ...)`, which was not in the standalone-command inventory. The live-object third step executes named Go tests whose source files were also outside that inventory. The actual reviewed workflows currently include these paths in both PR and push filters; the risk was a future removal that would leave a visible valid third-step command but stop CI from triggering when its own source changes. No production failure was observed.
- **Verified root cause:** Reachability was inferred from standalone Python command extraction and workflow self-triggering, without a separate dependency list for reviewed third-step execution.
- **Failed approach:** Exact shell binding and a self-trigger are insufficient if a change to the independently executed validator or reviewed Go test source does not trigger the workflow.
- **Correction / executable recurrence guard:** [71127518](https://github.com/m-shogo/memories-project/commit/71127518639f3cc000c3e7042a13e458ecf0f41c) explicitly requires the local-recovery independent validator and three reviewed Go test source files in **both** PR and push path filters. The synthetic Go positive fixture now contains the reviewed test-source paths. Five negative fixtures remove PR, push or both source triggers and must fail closed; the common inventory increases from 183 to 188.
- **Retry condition:** Update this source dependency list only after a reviewed change to the independent local-recovery validator or named Go tests, with exact-source CI. Do not retry unchanged workflow-write permission, canonical 4.17 MB learning transport, MinIO HTTP 401 or human-promotion blockers.

### Material success: CI evidence and protected authority

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40682710605](https://github.com/m-shogo/memories-project/actions/runs/40682710605) completed **SUCCESS** on `71127518639f3cc000c3e7042a13e458ecf0f41c`. The job log reports 52 source-negative workflows, 63 direct Python commands, **188 executed reachability negative fixtures**, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and read-only clean-source PASS. GitHub compare shows only `scripts/validate-memory-os-entry-docs.py` changed (39 additions, 1 deletion); source growth was bounded to 2,324 characters with 188 unique literal fixture keys.
- **Why safe / reusable mechanism:** The shared CI-reachable read-only guard now couples third-step execution authority to PR/push source-trigger reachability without changing any reviewed workflow or the actual Go tests, local recovery code, production evidence, credentials, traffic, readiness or promotion.
- **Protected-authority check:** Nine protected contract/registry blob SHAs, the production-shaped drill registry and the canonical learning blob were unchanged after the code commit. Production remains `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved recovery objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records or final candidates. The current human-approved objective, distinct eligible environments, current reviewed-request binding, independent review and human promotion requirements were not weakened.
- **Learning boundary:** This supplementary append-only record is neither the canonical learning authority nor production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, independent review or promotion evidence.
- **Next safe target:** Audit supplemental learning addenda/records for independent append-only CI trigger coverage. The canonical learning workflow does not currently list the addenda path; the previously recorded workflow-write permission blocker remains unchanged, so avoid repeating that write until its retry condition changes. Continue independent read-only source and CI audits.

## 2026-10-28 — Negative fixtures must reject for the intended diagnostic

### Material failure prevented: wrong-reason negative acceptance

- **Symptom / observed evidence:** The common 188-case source-negative suite previously counted any nonempty issue list as a passing mutation. A fixture could be rejected for an unrelated workflow permission or trigger error while the targeted second-step shell, clone-source or third-step dependency guard was broken. This is a test-harness coverage risk discovered by source review; no production incident or observed bypass occurred.
- **Verified root cause:** The suite asserted only that `source_negative_reachability_issues()` returned at least one issue, not that the intended invariant produced a case-specific diagnostic.
- **Failed approach:** Treating any fail-closed rejection as proof of the mutation's intended safety property is insufficient; unrelated errors can mask regressions.
- **Correction / executable recurrence guard:** [57ab4e04](https://github.com/m-shogo/memories-project/commit/57ab4e0495db58b7391387055452553a5aedc9f8) binds **33** existing local-clone, migration-clone, reviewed Go, third-step trigger and closed-shell negative fixtures to their expected diagnostic families. It rejects a mutation that fails for the wrong reason, pins the 33-case diagnostic-bound inventory, and adds an independent wrong-reason control using an unrelated workflow-permission mutation. The overall source-negative inventory remains 188; no misleading new fixture count was claimed.
- **Retry condition:** Extend the case-specific diagnostic map after verifying a new fixture's actual intended failure class. Revisit mappings on reviewed guard diagnostic changes or exact-source CI regression; do not relax them merely to pass unrelated errors. Do not retry unchanged canonical learning transport, workflow-write permission, MinIO HTTP 401 or human-promotion blockers.

### Material success: observed exact-source execution

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40683013021](https://github.com/m-shogo/memories-project/actions/runs/40683013021) completed **SUCCESS** on `57ab4e0495db58b7391387055452553a5aedc9f8`. Logs show 52 reviewed workflows, 63 direct Python commands, 188 executed source-negative fixtures (including the 33 diagnostic-bound cases), 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and clean read-only execution. GitHub compare shows the commit changed only `scripts/validate-memory-os-entry-docs.py` (41 additions, 2 deletions); the source patch was bounded to 1,984 additional characters.
- **Why safe / reusable mechanism:** Reused the repository's previously proven case-specific diagnostic binding pattern inside an existing read-only CI-reachable guard. No reviewed workflow, production evidence, generation/objective/drill registry, credential, traffic, readiness or human promotion was written.
- **Protected-authority check:** The nine protected contract/registry Git blob SHAs, production-shaped failure-drill registry and canonical learning blob remained unchanged after the code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records and final candidates all remain zero. Human promotion is separate and non-automatic.
- **Learning boundary:** This addendum is supplementary append-only history, never canonical learning authority or production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, independent review or promotion evidence.
- **Next safe target:** Extend intended-diagnostic binding to additional high-risk source-negative fixture families, and independently audit addenda append-only CI reachability without retrying the unchanged workflow-write blocker.

## 2026-10-28 — Action/toolchain negatives bound to intended diagnostics

### Material failure prevented: unrelated rejection masks action-source regression

- **Symptom / observed evidence:** The source-negative suite already covered checkout ref, credential retention, setup-python, setup-go and pinned-action mutations, but a nonempty unrelated issue list could count as a pass even if the targeted action/toolchain guard regressed. This was a static test-harness risk, not an observed production failure.
- **Verified root cause:** The generic negative loop accepted any failure without requiring the expected action/toolchain source-authority diagnostic.
- **Failed approach:** Relying only on the 188-case fixture inventory and overall rejection is not enough to prove a specific source-binding invariant.
- **Correction / executable recurrence guard:** [dfb09743](https://github.com/m-shogo/memories-project/commit/dfb0974395c683476c75cfa7d5cea0df80e5b77b) binds 28 additional reviewed checkout, Python/Go toolchain and pinned-action negative fixtures to their exact diagnostic families. The diagnostic-bound inventory rises from 33 to **61**, while the total semantic fixture inventory remains 188.
- **Retry condition:** Update a case-specific mapping only after a reviewed action/toolchain policy or diagnostic change and exact-source CI proof. Do not weaken the mapping for unrelated errors or retry unchanged external blockers.

### Material success: exact-source CI and protected authority

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40683232588](https://github.com/m-shogo/memories-project/actions/runs/40683232588) completed **SUCCESS** on `dfb0974395c683476c75cfa7d5cea0df80e5b77b`. Logs prove 52 reviewed workflows, 63 direct Python commands, 188 executed source-negative fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and read-only clean-source PASS. The code commit changed only `scripts/validate-memory-os-entry-docs.py` (47 additions, 1 deletion), with a bounded 1,881-character source increase.
- **Why safe / reusable mechanism:** Reused proven intended-diagnostic negative binding to protect source, toolchain and action execution authority without modifying any reviewed workflow, production evidence, credentials, traffic, readiness or promotion.
- **Protected-authority check:** Nine protected contract/registry Git blob SHAs, the production-shaped drill registry and canonical learning blob remained unchanged after the code commit. Production remains `NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records and final candidates. Human production promotion remains separate and non-automatic.
- **Learning boundary:** This supplementary append-only history is not canonical learning authority or production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, independent review or promotion evidence.

### Newly confirmed scoped blocker: supplemental learning has no independent CI trigger

- **Symptom / observed evidence:** The current `.github/workflows/autonomous-learning-guard.yml` includes the canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` in both PR and push path filters but **does not include** `docs/operations/autonomous-learning-addenda/**` or `docs/operations/autonomous-learning-records/**`. Exact-head GitHub Actions queries for four supplemental-history-only commits (`e078f8d0`, `052831d8`, `c3f8a9e6`, `15bef507`) each returned zero runs. No CI PASS is asserted for those history-only commits.
- **Verified root cause:** The existing workflow's explicit event path filters exclude the supplemental learning directories. This is an append-only CI reachability gap; it is not a production gate or evidence failure.
- **Failed approach:** Treating the canonical learning authority's append-only CI step as if it automatically covered separate supplemental files would be an incorrect claim.
- **Correction / recurrence guard:** Read-only inventory and exact-head Actions queries identify the gap without modifying workflow authority. A complete executable correction requires an authorized workflow trigger plus append-only comparison of existing supplemental history and negative proof. The previously recorded workflow-write permission blocker has no observed changed precondition, so no repeated workflow mutation was attempted.
- **Retry condition:** Revisit only after verified workflow-write permission changes or a separately reviewed, already-triggered authorized CI path can enforce supplemental append-only history. Until then, preserve addenda through target-SHA checks, fresh branch rereads, prefix-only writes and post-write GitHub compare verification, and explicitly distinguish that from independent CI enforcement.
- **Next safe target:** Extend case-specific negative diagnostic binding to remaining high-risk workflow metadata and shell mutation families; independently review a permitted append-only CI route only when its retry condition changes.

## 2026-10-28 — Workflow metadata and permission negatives prove intended rejection

### Material failure prevented: metadata guard masked by unrelated fixture failure

- **Symptom / observed evidence:** Workflow/job/step metadata and permission mutations were part of the shared 188-case source-negative suite, but a generic nonempty error result could allow the targeted metadata/permission invariant to regress unnoticed. The affected fixtures include workflow concurrency/environment/defaults, job container/environment/strategy/runner/timeout, step shell/working-directory/ID/timeout, and duplicate/elevated permissions. No actual production compromise was observed.
- **Verified root cause:** These cases were not included in the intended-diagnostic binding map; the negative harness previously treated unrelated rejection as sufficient.
- **Failed approach:** Presence-only negative acceptance is insufficient to prove the specific metadata or permission authority guard still rejects its mutation.
- **Correction / executable recurrence guard:** [74ce3778](https://github.com/m-shogo/memories-project/commit/74ce377889b6c9e25a1004b7485e997f4f3fa96d) adds **21** reviewed workflow/job/step metadata and permission fixtures to their exact expected diagnostic families. The diagnostic-bound inventory advances from 61 to **82**, while the overall source-negative suite remains 188 cases.
- **Retry condition:** Revise these mappings only for an independently reviewed workflow metadata/permission policy change with exact-source positive/negative CI. Do not loosen mappings to accommodate unrelated errors; do not retry unchanged canonical learning transport, workflow-write permission, MinIO HTTP 401 or human-promotion blockers.

### Material success: exact-source CI and invariant preservation

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40683515557](https://github.com/m-shogo/memories-project/actions/runs/40683515557) completed **SUCCESS** on `74ce377889b6c9e25a1004b7485e997f4f3fa96d`. Job logs show 52 source-negative workflows, 63 direct Python commands, 188 executed reachability negative fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and clean read-only execution. The code commit changed only `scripts/validate-memory-os-entry-docs.py` (42 additions, 1 deletion), with a bounded 1,962-character source increase.
- **Why safe / reusable mechanism:** The existing CI-reachable read-only guard now requires the expected failure class for 82 high-risk source-negative mutations. Reviewed workflows, production evidence, generation/objective/drill registries, credentials, traffic, readiness and promotion authority were not changed.
- **Protected-authority check:** Nine protected contract/registry Git blob SHAs, the production-shaped failure-drill registry and canonical learning blob remained unchanged after the code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records and final candidates all remain zero. Human promotion is separate and non-automatic.
- **Learning boundary:** This append-only supplemental history is not canonical learning authority or production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, independent review or promotion evidence.
- **Next safe target:** Expand intended-diagnostic binding to remaining source-negative shell and event-topology mutations only after verifying their exact rejection diagnostics; separately retain the supplemental-history CI trigger gap as a scoped workflow-permission blocker.

## 2026-10-28 — Event and job reachability negatives bound to intended diagnostics

### Material failure prevented

- **Symptom / evidence:** Fifteen existing source-negative fixtures for shadowed YAML event authority, PR/push filter drift, missing trigger paths, conditional steps, disabled/duplicate job conditions and missing HEAD verification previously passed on *any* rejection. This is a static harness masking risk, not an observed production incident.
- **Verified root cause:** The shared negative loop bound only 82 fixtures to intended diagnostics; these 15 had a nonempty-issue assertion.
- **Failed approach:** Treating 188 counted fixtures and an unrelated rejection as sufficient proof of each event/job/source invariant.
- **Correction / executable recurrence guard:** [3f9f91cd](https://github.com/m-shogo/memories-project/commit/3f9f91cd75e620aac07cba642fb9e19bd4190700) binds eight event-filter, two trigger, two conditional-step, two job-condition and one exact-HEAD mutation to their expected diagnostics. Diagnostic-bound cases **82 → 97**, total executable source-negative fixtures **188**.
- **Retry condition:** Change a mapping only following an independently reviewed event/job/source policy or diagnostic change with exact-source CI. Do not retry unchanged canonical learning transport, workflow-write permission, MinIO HTTP 401 or human-approval blockers.

### Material success

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40686717459](https://github.com/m-shogo/memories-project/actions/runs/40686717459) **SUCCESS** for `3f9f91cd75e620aac07cba642fb9e19bd4190700`: 52 reviewed workflows, 63 direct Python commands, 188 source-negative fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and read-only clean execution. Compare shows only `scripts/validate-memory-os-entry-docs.py` changed (38 additions, 1 deletion).
- **Why safe / reusable mechanism:** Existing read-only CI guard now rejects the 15 mutations for their intended CI reachability invariant; reviewed workflows, production evidence, backup/restore, RPO/RTO/skew, credentials, traffic, readiness and promotion were untouched.
- **Protected-authority check:** Production status, OPS-P0-007 snapshot, generation/objective/drill/evidence/non-resurrection/promotion registries, production-shaped drill registry, canonical learning and learning contract blobs were unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records and final candidates all zero. Human promotion remains separate.
- **Boundary:** Supplemental append-only history is not canonical learning authority or production/readiness evidence. Supplemental-history CI-trigger gap remains blocked on unchanged workflow-write authority.

## 2026-10-28 — Shell validator bypass negatives require intended diagnostics

### Material failure prevented

- **Symptom / evidence:** 26 already executed source-negative mutations for help-only/redirected Python commands, inert heredocs, uninvoked shell functions, interpreter alias/hash/PATH/source/eval substitution, masking traps, shell AND/OR short-circuit and conditional branch/loop execution could pass on an unrelated nonempty error. This is a static CI-harness masking risk, not an observed production incident.
- **Verified root cause:** The shared 188-fixture negative harness bound 97 cases to intended diagnostic families, but left these 26 shell bypass cases unbound.
- **Failed approach:** Accepting any failure as proof of the targeted validator execution invariant.
- **Correction / executable recurrence guard:** [80ca9c68](https://github.com/m-shogo/memories-project/commit/80ca9c684082c3a172a0a59b09326a55579ae04a) binds 26 existing cases to exact intended command, heredoc, function, interpreter, trap, short-circuit or conditional-control diagnostics. Diagnostic-bound inventory **97 → 123**; total executable fixtures remain **188**.
- **Retry condition:** Revise a mapping only after independently reviewed shell/CI policy or diagnostic changes and exact-source CI proof. Do not retry unchanged canonical learning HTTP/2, workflow-write permission, MinIO HTTP 401 or human-approval blockers.

### Material success

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40686960405](https://github.com/m-shogo/memories-project/actions/runs/40686960405) **SUCCESS** on `80ca9c684082c3a172a0a59b09326a55579ae04a`. Logs prove 52 reviewed workflows, 63 direct Python commands, 188 source-negative fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and clean read-only execution. GitHub compare shows only `scripts/validate-memory-os-entry-docs.py` changed (55 additions, 1 deletion).
- **Why safe / reusable mechanism:** Extended existing CI-reachable read-only negative proof without modifying workflows, production evidence, credentials, traffic, backup/restore, RPO/RTO/skew, readiness or promotion.
- **Protected-authority check:** Production status, OPS-P0-007 snapshot, generation/objective/drill/evidence/non-resurrection/promotion registries, production-shaped drill registry, canonical learning and learning contract blob SHAs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records and final candidates remain zero. Human promotion remains separate.
- **Boundary:** This append-only supplemental record is not canonical learning authority or production/readiness evidence; the supplemental-history CI-trigger gap remains blocked by unchanged workflow-write authority.

## 2026-10-28 — Clean-source and HEAD negative diagnostics; corrected inverted-HEAD classification

### Material failure: incorrect diagnostic mapping

- **Symptom / observed evidence:** Initial [3479ba5b](https://github.com/m-shogo/memories-project/commit/3479ba5b2b8ec9546b85e2520bcece5b615037a6) failed exact-source [Autonomous Learning Guard #40687248628](https://github.com/m-shogo/memories-project/actions/runs/40687248628). Job log: `source-negative negative rejected for wrong reason: inverted source HEAD comparison: ['missing, shadowed or duplicated exact-source HEAD comparison']`.
- **Verified root cause:** The fixture replaces the exact `test "$(git rev-parse HEAD)" = "$expected"` line with an inverted `!=` comparison, so the exact-line cardinality guard rejects first. The initial mapping incorrectly expected the later complete-source-shell diagnostic.
- **Failed approach:** Classifying the inverted comparison by its semantic intention without checking the actual deterministic diagnostic precedence.
- **Correction / executable recurrence guard:** [53fa2b1b](https://github.com/m-shogo/memories-project/commit/53fa2b1b10e10345dea9552b0e6d5fc2f1588d41) moves this fixture from `source_guard_cases` to `head_cardinality_cases`; no diagnostic assertion was weakened or removed. The existing case-specific failure assertion is the executable recurrence guard.
- **Retry condition:** Reclassify this case only if the reviewed exact-source HEAD check or diagnostic precedence changes, after a targeted negative and exact-source CI proof. Do not repeat the known incorrect source-shell expectation with unchanged guard ordering.

### Material success: 25 additional intended-diagnostic bindings

- **Outcome / observed evidence:** The corrected exact-source [Autonomous Learning Guard #40687357130](https://github.com/m-shogo/memories-project/actions/runs/40687357130) completed **SUCCESS** on `53fa2b1b10e10345dea9552b0e6d5fc2f1588d41`. The new tests bind four clean-check short-circuit cases, two heredoc cases, two function cases, trap/eval masking, three HEAD-cardinality cases (including inverted HEAD), eleven source-verification shell mutations and validator-before-verification ordering. Diagnostic-bound fixtures **123 → 148**, while total executable fixtures remain **188**. Logs show 52 workflows, 63 Python commands, 188 source-negative fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and clean read-only execution.
- **Why safe / reusable mechanism:** Reused the existing CI-reachable read-only negative harness to require the intended clean-source or exact-source rejection, without modifying workflows, production evidence, credentials, traffic, backup/restore, RPO/RTO/skew, readiness or promotion. The fix is a one-line fixture-group relocation.
- **Protected-authority check:** Production status, OPS-P0-007 snapshot, generation/objective/drill/evidence/non-resurrection/promotion registries, production-shaped drill registry, canonical learning and learning contract Git blob SHAs remained unchanged after both code writes. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records and final candidates remain zero. Human promotion remains separate and non-automatic.
- **Boundary / retry condition:** This append-only supplemental learning is not canonical authority or production/readiness evidence. The unchanged supplemental-history CI-trigger and canonical learning transport blockers were not retried. Expand remaining case bindings only after checking actual diagnostic precedence.

## 2026-10-28 — CI step metadata and interpreter environment negatives bound

### Material failure prevented

- **Symptom / evidence:** Nineteen already-executed mutations of extra/folded/duplicate run steps, step PR-head environment, interpreter PATH/PYTHONPATH/BASH_ENV, cross-step GITHUB_PATH/GITHUB_ENV, shell override, shadow job and continue-on-error previously passed the generic negative assertion even if their intended execution authority check regressed. No production incident was observed.
- **Verified root cause:** The 188-fixture harness had 148 intended-diagnostic bindings but not these 19 CI metadata/execution cases.
- **Failed approach:** Counting any unrelated failure as proof of the targeted CI step or interpreter invariant.
- **Correction / executable recurrence guard:** [f864442b](https://github.com/m-shogo/memories-project/commit/f864442b4b2398d7e585a3d031b289c1de37bcc8) binds eight run-step, three step-environment, three interpreter-environment, two cross-step environment and three other job/shell/continue-on-error mutations to their expected diagnostic families. Diagnostic-bound cases **148 → 167**, executable source-negative fixtures remain **188**.
- **Retry condition:** Revise mappings only following independently reviewed CI execution policy or diagnostic changes with exact-source positive/negative proof; do not retry unchanged canonical learning transport, workflow-write permission, MinIO HTTP 401 or human-approval blockers.

### Material success

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40687584147](https://github.com/m-shogo/memories-project/actions/runs/40687584147) completed **SUCCESS** on `f864442b4b2398d7e585a3d031b289c1de37bcc8`. Logs show 52 workflows, 63 direct Python commands, 188 source-negative fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and clean read-only execution. GitHub compare shows only `scripts/validate-memory-os-entry-docs.py` changed (39 additions, 1 deletion).
- **Why safe / reusable mechanism:** Reused an existing CI-reachable read-only negative harness without changing reviewed workflows, production evidence, credentials, traffic, backup/restore, RPO/RTO/skew, readiness or promotion.
- **Protected-authority check:** Production status, OPS-P0-007 snapshot, generation/objective/drill/evidence/non-resurrection/promotion registries, production-shaped drill registry, canonical learning and learning contract Git blob SHAs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records and final candidates all zero. Human promotion remains separate.
- **Boundary:** This append-only supplemental record cannot satisfy canonical learning or production/readiness gates. The supplemental-history CI-trigger gap remains blocked on unchanged workflow-write authority.

## 2026-10-28 — All 188 source-negative fixtures bound to intended diagnostics

### Material failure prevented

- **Symptom / evidence:** The final 21 existing fixtures for conditional/masked/missing tracked and untracked clean-source checks, early exit/disabled errexit, skipped or masked validator commands, missing invoked scripts and Go source-verification order were still accepted by generic nonempty-issue rejection. This is a static harness regression risk, not observed production behavior.
- **Verified root cause:** The shared negative suite executed 188 mutations but only 167 required the intended diagnostic; an unrelated issue could satisfy the remaining cases.
- **Failed approach:** Assuming fixture execution plus any failure proves the particular invariant under test.
- **Correction / executable recurrence guard:** [0af4b4ee](https://github.com/m-shogo/memories-project/commit/0af4b4ee8c1dedffba23bc4c9cc112fbf0b9453d) binds the final 21 cases to exact expected clean-source, validator-execution, missing-script and source-order diagnostics. Diagnostic-bound inventory **167 → 188 of 188**; no fixture was removed or bypassed.
- **Retry condition:** Change a case's expected diagnostic only when its reviewed execution policy or deterministic guard precedence changes and exact-source CI proves the new behavior. Do not repeat the earlier incorrect inverted-HEAD classification or unchanged external blockers.

### Material success

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40687835667](https://github.com/m-shogo/memories-project/actions/runs/40687835667) **SUCCESS** on `0af4b4ee8c1dedffba23bc4c9cc112fbf0b9453d`. Logs prove 52 source-negative workflows, 63 direct Python commands, 188 executed diagnostic-bound source-negative fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and clean read-only execution. GitHub compare shows only `scripts/validate-memory-os-entry-docs.py` changed (53 additions, 1 deletion).
- **Why safe / reusable mechanism:** All existing source-negative fixtures now require a matching intended diagnostic from the same read-only CI-reachable validator. No reviewed workflow, production evidence, credentials, traffic, backup/restore, RPO/RTO/skew, readiness or promotion was changed.
- **Protected-authority check:** Production status, OPS-P0-007 snapshot, generation/objective/drill/evidence/non-resurrection/promotion registries, production-shaped drill registry, canonical learning and learning contract blob SHAs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records and final candidates all zero. Human promotion remains separate and non-automatic.
- **Boundary / next safe target:** This supplemental append-only history is not canonical learning authority or production/readiness evidence. Next independently audit the intended-diagnostic mapping inventory against actual fixture keys, so newly added fixtures cannot silently fall back to generic rejection; do not retry unchanged workflow-write or canonical learning transport blockers.

## 2026-10-28 — Exact diagnostic equality prevents substring masking

### Material failure prevented

- **Symptom / evidence:** Even after all 188 source-negative fixtures were bound to intended diagnostic families, the harness used `any(expected_issue in issue for issue in issues)`. An unrelated diagnostic with the expected phrase as a prefix/suffix or nested text could falsely count as proof. This was found by static code review, not an observed production incident.
- **Verified root cause:** Substring membership rather than complete issue equality; three dynamic diagnostic families (local-recovery trigger, Go-test trigger and missing invoked script) had intentionally partial expected strings.
- **Failed approach:** Accepting partial text matches as proof of the exact intended CI guard.
- **Correction / executable recurrence guard:** [0ca3802e](https://github.com/m-shogo/memories-project/commit/0ca3802e6c6171f2bdcfa8f55c0532985ec1b18d) replaces substring matching with `expected_issue not in issues` (exact list membership) and binds the dynamic cases to explicit event, script and Go-test paths. All **188 of 188** existing source-negative fixtures must now emit the exact intended diagnostic, not merely a containing string.
- **Retry condition:** Change expected issue strings only after reviewed diagnostic changes with exact-source CI and negative proof; never loosen to substring matching for unrelated errors or repeat unchanged external blockers.

### Material success

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40688105219](https://github.com/m-shogo/memories-project/actions/runs/40688105219) **SUCCESS** on `0ca3802e6c6171f2bdcfa8f55c0532985ec1b18d`. Logs show 52 workflows, 63 direct Python commands, 188 source-negative fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and clean read-only execution. GitHub compare shows only `scripts/validate-memory-os-entry-docs.py` changed (18 additions, 8 deletions).
- **Why safe / reusable mechanism:** Strengthened a read-only CI-reachable negative classifier without changing reviewed workflows, production evidence, backup/restore, RPO/RTO/skew, credentials, traffic, readiness or promotion.
- **Protected-authority check:** Production status, OPS-P0-007 snapshot, generation/objective/drill/evidence/non-resurrection/promotion registries, production-shaped drill registry, canonical learning and learning contract Git blobs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records and final candidates remain zero. Human promotion remains separate.
- **Boundary / next safe target:** This supplemental append-only record is not canonical learning authority or production/readiness evidence. Next add an independent synthetic negative proving the exact-match classifier rejects forged containing diagnostics, while preserving the unchanged supplemental-history CI-trigger blocker.

## 2026-10-28 — Executable negative proof of exact diagnostic classifier

### Material failure prevented

- **Symptom / evidence:** The prior 188-case exact diagnostic comparison was not independently exercised against forged prefix, suffix and nested issue strings. A future regression from exact equality back to substring matching could silently weaken all intended-diagnostic assertions. This is a static test-harness risk, not an observed production failure.
- **Verified root cause:** The equality check was inline with fixture execution and had no independent classifier negative control.
- **Failed approach:** Relying only on the real fixture suite to prove the matching operator's strictness.
- **Correction / executable recurrence guard:** [ad64093b](https://github.com/m-shogo/memories-project/commit/ad64093beb90bfe5bf96e5ddd9139412022a4ebc) adds `exact_source_negative_diagnostic` and an eight-case synthetic classifier suite covering exact match, unrelated issues, empty input, prefix/suffix/nested collisions and multiple misleading issues. The same helper is used for all **188** fixture assertions.
- **Retry condition:** Alter the classifier only after a reviewed exact diagnostic policy change and an executable negative proving that unrelated containing strings still fail. Do not retry unchanged external blockers.

### Material success

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40688323865](https://github.com/m-shogo/memories-project/actions/runs/40688323865) completed **SUCCESS** on `ad64093beb90bfe5bf96e5ddd9139412022a4ebc`. Logs confirm 52 source-negative workflows, 63 Python commands, 188 source-negative fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and read-only clean execution. GitHub compare shows only `scripts/validate-memory-os-entry-docs.py` changed (26 additions, 1 deletion).
- **Why safe / reusable mechanism:** New executable classifier negatives run through the already CI-reachable read-only entrypoint guard. Reviewed workflows, production evidence, backup/restore, RPO/RTO/skew, credentials, traffic, readiness and promotion remain untouched.
- **Protected-authority check:** Production status, OPS-P0-007 snapshot, generation/objective/drill/evidence/non-resurrection/promotion registries, production-shaped drill registry, canonical learning and learning contract blob SHAs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records and final candidates all zero. Human promotion remains separate.
- **Boundary / next safe target:** This append-only supplemental record is not canonical learning authority or production/readiness evidence. Next inspect source-negative trigger/event parser semantics for comment, quote and duplicate-key evasions without changing protected authority or retrying the unchanged supplemental-history workflow permission blocker.

## 2026-10-28 — Ordered negative path filters cannot cancel source-negative CI

### Material failure prevented

- **Symptom / observed evidence:** The common event-path parser checked that required workflow and validator paths appeared in PR/push filters, but GitHub applies ordered negative `!path` patterns. A later exclusion can cancel an earlier required positive match while leaving that positive string present. This is a reviewed static CI-reachability bypass, not an observed production incident.
- **Verified root cause:** `source_negative_event_paths` admitted any unique nonempty path list, including negative exclusions.
- **Failed approach:** Presence-only positive path inventory checks without accounting for GitHub's ordered path exclusion semantics.
- **Correction / executable recurrence guard:** [70fc9af2](https://github.com/m-shogo/memories-project/commit/70fc9af26cc00028a0cb7544359526ab1f3c2231) rejects any `!path` in reviewed source-negative event filters. Two new PR/push fixtures append a negative exclusion after the required validator path and must receive the exact `missing/ambiguous PR and push path-filter authority` diagnostic. Total and diagnostic-bound fixture inventories **188 → 190**, all exact-match.
- **Retry condition:** Admit negative path patterns only after an independently reviewed event-filter semantics policy, proof that required triggers cannot be excluded, and exact-source positive/negative CI. Do not retry unchanged external blockers.

### Material success

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40688671338](https://github.com/m-shogo/memories-project/actions/runs/40688671338) **SUCCESS** on `70fc9af26cc00028a0cb7544359526ab1f3c2231`. Logs show 52 source-negative workflows, 63 direct Python commands, 190 executed exact-diagnostic source-negative fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and read-only clean execution. GitHub compare shows only `scripts/validate-memory-os-entry-docs.py` changed (15 additions, 3 deletions).
- **Why safe / reusable mechanism:** Read-only parser and negative fixtures now fail closed on trigger exclusions; no workflow, production evidence, credentials, traffic, backup/restore, RPO/RTO/skew, readiness or promotion was changed.
- **Protected-authority check:** Production status, OPS-P0-007 snapshot, generation/objective/drill/evidence/non-resurrection/promotion registries, production-shaped drill registry, canonical learning and learning contract Git blobs remained unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records and final candidates remain zero. Human promotion remains separate.
- **Boundary / next safe target:** Supplemental append-only history is not canonical learning authority or production/readiness evidence. Continue read-only audit of GitHub event filter semantics and CI reachability; do not retry the unchanged workflow-write permission or canonical learning transport blockers.

## 2026-10-28 — Whitespace-shadowed YAML root keys rejected by shared source-negative CI

### Material failure: symptom, observed evidence, root cause, failed approach, correction, recurrence guard, retry condition

- **Symptom / evidence:** Read-only inspection found the common source-negative workflow scanner recognized only root keys with an immediately adjacent colon. Valid YAML root entries such as `on :` and `jobs :` could shadow an earlier reviewed key without appearing in the scanner's root-key inventory. This was a static bypass, not an observed production incident. All 52 current reviewed source-negative workflows were independently read and have exactly the four canonical root rows.
- **Verified root cause:** `^([A-Za-z][A-Za-z0-9_-]*):` does not match YAML mapping keys with whitespace before `:`. The event parser and job parser still saw the original `on:` and `jobs:` text, so they did not independently prove uniqueness of the parsed YAML authority.
- **Failed approach:** A root-key regex that counts only adjacent-colon spellings is not a complete YAML mapping-authority inventory; checking required strings alone cannot reject shadowed YAML keys.
- **Correction / executable recurrence guard:** [6a2aee09](https://github.com/m-shogo/memories-project/commit/6a2aee0919e2bf655b8cbe7a80a3a94691d699a8) pins every noncomment, nonblank, unindented root row to the four reviewed root entries. Two new exact-diagnostic semantic negatives reject `on :` and `jobs :` shadows; source-negative fixture inventory 190 → 192. A separate local three-case root-shape smoke test passed before write.
- **Retry condition:** Revisit only after independently reviewed source-negative workflow root topology changes, with positive and shadow-key negative CI proof. Do not retry unchanged canonical learning large-file transport, supplemental-history workflow write permission, Quay MinIO HTTP 401, or human-promotion blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / observed evidence:** Exact-source [Autonomous Learning Guard #40695393410](https://github.com/m-shogo/memories-project/actions/runs/40695393410) completed **SUCCESS** on code SHA `6a2aee0919e2bf655b8cbe7a80a3a94691d699a8`. Job logs prove 52 source-negative workflows, 63 direct Python commands, 192 executed source-negative semantic fixtures, 128 canonical learning negatives, 1,186 helper-ancestor negatives, canonical append-only PASS and clean-source validation.
- **Why safe / reusable mechanism:** The change modifies only the existing CI-reachable read-only entrypoint validator; no reviewed workflow, production generation/objective/drill/recovery evidence, credential, traffic, readiness, typed eight-domain review or promotion authority was modified.
- **Protected-authority check:** All 11 protected production/OPS-P0-007/registry/learning contract/canonical learning Git blob SHAs were unchanged immediately after the code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED` with zero registered or semantically eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records and final candidates. Human production promotion remains separate and non-automatic. This supplemental append-only learning record is not canonical learning authority or any production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.
- **Next safe target:** Audit YAML whitespace-shadowed job-level and step-level metadata keys that could skip CI execution or suppress failure; add executable negatives only where the existing scanner lacks coverage.

## 2026-10-28 — Whitespace-shadowed job and step execution keys fail closed

### Material failure: symptom, observed evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** The shared CI source-negative scanner previously counted job and step metadata only when the colon immediately followed the key. YAML keys such as `if : false`, `permissions : {contents: write}`, `continue-on-error : true` and `run : echo skipped` can shadow reviewed job/step authority without appearing in that inventory. This is a verified static guard gap, not an observed production incident. Independent read-only inspection of all 52 reviewed workflows found five canonical job metadata rows per workflow and only reviewed step metadata.
- **Verified root cause:** `^ {4}KEY:` and `^ {8}KEY:` extraction misses valid whitespace-before-colon mapping keys, while exact required-key presence remains true. A shadowed job condition can skip the job; shadowed step metadata can skip or mask the validator.
- **Failed approach:** Relying on adjacent-colon key extraction and a visible Python command as complete YAML execution authority.
- **Correction / executable recurrence guard:** [b407a835](https://github.com/m-shogo/memories-project/commit/b407a8353dd35a5ec893593163208d428a13eb77) requires every live four-space job and eight-space step metadata row to match the reviewed adjacent-colon key vocabulary. Five new exact-diagnostic negative fixtures reject shadowed job `if`, job permissions, validator-step `if`, `continue-on-error` and `run`. The fixture inventory advances 192 → 197. Seven local metadata-shape positive/negative smoke checks passed before write.
- **Retry condition:** Revisit only if independently reviewed job/step YAML topology or execution authority changes, with exact-source positive and negative proof. Do not repeat unchanged canonical learning transport, supplemental-history CI-trigger write permission, Quay MinIO HTTP 401 or human-approval blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / observed evidence:** Exact-source [Autonomous Learning Guard #40695700348](https://github.com/m-shogo/memories-project/actions/runs/40695700348) completed **SUCCESS** for `b407a8353dd35a5ec893593163208d428a13eb77`. Its logs prove 52 source-negative workflows, 63 direct Python validator commands, 197 executed semantic negatives, 128 canonical learning negatives, canonical append-only PASS, helper-ancestor negative checks and clean-source validation.
- **Why safe / reusable mechanism:** Only the existing CI-reachable read-only entrypoint validator was changed. No workflow, production evidence, generation, objective, drill, typed eight-domain record, credential, traffic, readiness or human promotion authority was modified.
- **Protected-authority check:** All 11 protected production/OPS-P0-007/registry/learning-contract/canonical-learning Git blob SHAs remained unchanged after the code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`, with zero registered/eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records or final candidates. Human promotion remains separate and non-automatic. This supplemental append-only record is not canonical learning authority or production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.
- **Next safe target:** Audit two-space YAML job header aliases and whitespace-shadowed job IDs; ensure the single reviewed source-negative job cannot be replaced by a later valid YAML mapping key.

## 2026-10-28 — Whitespace/quoted source-negative job ID shadows rejected

### Material failure: symptom, observed evidence, root cause, failed approach, correction, recurrence guard, retry condition

- **Symptom / evidence:** The common source-negative job cardinality check counted only two-space unquoted job keys with an adjacent colon. A second valid YAML mapping key `source-admission : {}` or `'source-admission': {}` could shadow the reviewed job ID while the original still appeared in the count. An unreviewed extra job using a spaced colon could also escape the count. This was a static CI-reachability guard gap, not an observed production incident. Read-only inspection of all 52 reviewed source-negative workflows confirmed exactly one unquoted canonical job header (`source-admission:` or `source-negative:`).
- **Verified root cause:** `^  [A-Za-z0-9_-]+:\s*$` recognizes only the adjacent-colon unquoted spelling; it cannot establish uniqueness of the effective YAML mapping key.
- **Failed approach:** Counting a syntactically present reviewed job without inventorying every live two-space YAML job-header row.
- **Correction / executable recurrence guard:** [9fa838de](https://github.com/m-shogo/memories-project/commit/9fa838dec16bcb29f5c4f10f7ad55c23ef038f78) requires exactly one live job-header row, equal to one of the two independently observed reviewed job IDs. Three new exact-diagnostic negatives reject spaced shadow, quoted shadow and spaced unreviewed extra job. Executable source-negative fixtures 197 → 200; five local header-shape positive/negative smoke checks passed before write.
- **Retry condition:** Revisit only after an independently reviewed job ID or job-count change, with exact-source positive and shadow-key negative CI proof. Do not retry unchanged canonical learning transfer, supplemental-history workflow-write permission, Quay MinIO HTTP 401 or human-approval blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40695934953](https://github.com/m-shogo/memories-project/actions/runs/40695934953) completed **SUCCESS** on `9fa838dec16bcb29f5c4f10f7ad55c23ef038f78`. Job logs prove 52 source-negative workflows, 63 direct Python commands, 200 executed source-negative negatives, 128 canonical learning negatives, canonical append-only PASS, helper-ancestor validation and clean-source validation.
- **Why safe / reusable mechanism:** Only the existing CI-reachable read-only entrypoint validator changed; reviewed workflows and production generation/objective/drill/recovery evidence, typed eight-domain records, credentials, traffic, readiness and human promotion were not touched.
- **Protected-authority check:** All 11 protected production/OPS-P0-007/registry/learning-contract/canonical-learning Git blob SHAs remained unchanged after the code commit. `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`, with zero registered or semantically eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records and final candidates. Human promotion remains separate. This supplemental append-only learning is not canonical learning authority or production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.
- **Next safe target:** Audit whitespace-shadowed workflow/job permission leaf keys (`contents : write`) that could elevate effective permissions despite a visible `contents: read`; preserve the reviewed read-only CI authority.

## 2026-10-28 — Quoted and spaced CI permission leaf shadows rejected

### Material failure: symptom, observed evidence, root cause, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** The common source-negative scanner required a visible `contents: read` at workflow and job level but counted only immediately adjacent-colon `contents:` spellings. YAML `contents : write` or `'contents': write` in the same mapping could shadow the read-only leaf without affecting the original text. This is a static CI permission-authority gap, not an observed production or credential incident. Independent read-only inspection of all 52 source-negative workflows confirmed a single exact `contents: read` leaf at both scopes.
- **Verified root cause:** Presence checks and `^  contents:`/`^      contents:` regexes did not inventory every live mapping row in the respective YAML permission blocks.
- **Failed approach:** Treating a visible read-only permission leaf as proof that no later semantically equivalent YAML key can elevate the effective permission.
- **Correction / executable recurrence guard:** [a2e421f7](https://github.com/m-shogo/memories-project/commit/a2e421f717d9e7240e0b3ff49fdce290fb693411) requires exact singleton `contents: read` permission rows at both workflow and job scopes. Four new exact-diagnostic negatives reject spaced and quoted shadows at each scope. Source-negative fixture inventory 200 → 204; six local permission-leaf shape smoke checks passed before write.
- **Retry condition:** Revisit only after independently reviewed CI permission scope or YAML policy changes, with positive and quoted/spaced shadow-key negative proof. Do not retry unchanged canonical learning large-file transfer, supplemental-history workflow write permission, Quay MinIO HTTP 401 or human approval blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** Exact-source [Autonomous Learning Guard #40696164640](https://github.com/m-shogo/memories-project/actions/runs/40696164640) completed **SUCCESS** on `a2e421f717d9e7240e0b3ff49fdce290fb693411`. Job logs confirm 52 reviewed workflows, 63 direct Python commands, 204 executed semantic negatives, 128 canonical learning negatives, canonical append-only PASS, helper-ancestor validation and clean read-only execution.
- **Why safe / reusable mechanism:** Only the CI-reachable read-only entrypoint validator was changed. No workflow, production evidence, recovery generation/objective/drill/evidence registry, typed eight-domain record, credential, traffic, readiness or human promotion authority was modified.
- **Protected-authority check:** All 11 protected production/OPS-P0-007/registry/learning-contract/canonical-learning Git blob SHAs remained unchanged after the code commit. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable reviewed requests, request-bound recovery evidence, complete typed eight-domain records or final candidates. Human promotion remains separate and non-automatic. This supplemental append-only learning cannot satisfy canonical learning, production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
- **Next safe target:** Audit workflow filename extension coverage and CI-trigger reachability for `.yaml` source-negative workflows; do not claim coverage without a runnable trigger path or retry unchanged workflow-write permissions.

## 2026-10-28 — Source-negative .yaml extension and supplementary-history trigger remain scoped CI-reachability blockers

### Material failure: symptom, observed evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** Read-only GitHub tree audit finds 52 reviewed `*-source-negative.yml` workflows and zero `*-source-negative.yaml` workflows. The CI-reachable common validator currently inventories only `workflows.glob("*-source-negative.yml")`. The canonical `autonomous-learning-guard.yml` PR/push path filters include its own workflow and the shared validator script, but do not include `*-source-negative.yaml` or supplementary `autonomous-learning-addenda/**`. A future new `.yaml` workflow or a supplemental-learning-only commit would not automatically invoke this common guard through those path filters. This is a verified static coverage limitation; no actual `.yaml` workflow or production incident was observed.
- **Verified root cause:** The extension-limited inventory and the existing workflow's reviewed exact PR/push trigger lists do not cover the additional extension or supplemental learning history. Merely extending a Python glob would not prove CI reachability for a `.yaml`-only change.
- **Failed approach:** Treating a locally executable inventory check, or a guard triggered only when its own script changes, as complete automated coverage of independently changed `.yaml` workflows or supplemental history.
- **Correction / recurrence guard:** No speculative workflow mutation was made. Existing `.yml` workflows and the exact-source 204-case common validator remain protected. Preserve this explicit known gap until a reviewed workflow-trigger change and a negative CI test can establish source-change reachability. Do not add an untriggered `.yaml` guard and claim the CI reachability contract is satisfied.
- **Retry condition:** Revisit only after the recorded workflow-write permission blocker materially changes, or a separately verified existing CI path demonstrably triggers on `.yaml` and supplemental-history changes. Then extend the canonical workflow inventory and exact trigger policy together, with negative tests for a new `.yaml` workflow and addenda-only commit. Do not retry the unchanged workflow-write blocker or Quay MinIO HTTP 401/human promotion blockers.

### Material success: observed outcome/evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** This run performed a bounded read-only GitHub tree, workflow-path and validator-source audit. It did not add a workflow, mutate permissions or fabricate CI evidence. The four earlier exact-source code CI runs remain separately evidenced, most recently [#40696164640](https://github.com/m-shogo/memories-project/actions/runs/40696164640) SUCCESS on the 204-fixture validator source.
- **Why safe / reusable mechanism:** A scoped coverage gap is retained as an explicit retry-conditioned blocker, rather than hidden by an untriggered check or used to halt independent safe hardening.
- **Protected-authority check:** The 11 protected production/OPS-P0-007/registry/learning contract/canonical learning blobs remained unchanged during this audit. `productionDecision=NO_GO` and OPS-P0-007=`PREREQUISITES_BLOCKED`; no generation, objective, request, recovery evidence, typed eight-domain coverage, candidate or human promotion was created. Supplemental learning is not canonical learning or production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-28 — Independent incident-control CI root YAML shadows fail closed

### Material failure: symptom, observed evidence, root cause, failed approach, correction, recurrence guard, retry condition

- **Symptom / evidence:** The independent incident-control source-negative semantic trigger check accepted a later root-level `on :`, quoted `'on':`, `permissions :` or `jobs :` after the canonical `permissions:` boundary. The entire reviewed event prefix still matched. This was a static CI execution/authority guard gap, not a production incident; the separate full Git blob pin still rejected actual unreviewed workflow drift.
- **Verified root cause:** `validate_trigger_reachability` compared only the prefix before `\npermissions:\n`; it did not inventory effective YAML root mapping keys after that boundary. The failed approach was to rely on a correct-looking event prefix or on a blob digest alone for semantic recurrence proof.
- **Correction / executable recurrence guard:** [b602e041](https://github.com/m-shogo/memories-project/commit/b602e041d95eefdee2cbdac0c7547373da9f2bac) pins the complete reviewed root-key sequence independently for publisher and read-only source-negative CI. Eight new negative fixtures (four shadows × two workflows) require the exact root-shadow diagnostic, rather than an unrelated rejection. Read-only prewrite checks proved both baseline root inventories and all eight mutation shapes.
- **Retry condition:** Revisit only after independently reviewed workflow root topology changes, with exact-source and exact-diagnostic negative proof. Do not retry unchanged canonical learning transport, supplementary-learning workflow-trigger permission, Quay MinIO HTTP 401 or human-approval blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** Exact-source [Incident Control Authority Source Negative #40704585243](https://github.com/m-shogo/memories-project/actions/runs/40704585243) completed **SUCCESS** on `b602e041`. The job log confirms 26 omitted and 16 added trigger negatives, two shortened inventories, three event-topology negatives, **eight exact-diagnostic root-shadow negatives**, 13 source mutations and 14 shell event/ref/SHA runtime cases.
- **Why safe / reusable mechanism:** Only the existing CI-triggered read-only source-negative validator changed. Publisher and independent workflows and their reviewed Git blobs were untouched. A later effective YAML root-key override now fails even if the event prefix is still byte-for-byte valid.
- **Protected-authority check:** Eleven production/OPS-P0-007/registry/learning-contract/canonical-learning Git blob SHAs remained unchanged after the code commit. `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`; no registered/eligible generation, approved objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain record, final candidate or human promotion was created. This supplemental history is not canonical learning authority or production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-28 — Operability inventory PR CI root YAML shadows fail closed

### Material failure: symptom, observed evidence, root cause, failed approach, correction, recurrence guard, retry condition

- **Symptom / evidence:** The operability inventory PR publisher and its independent source-negative CI validator had the same semantic boundary gap: a later root `on :`, `'on':`, `permissions :` or `jobs :` did not change the validated event prefix. This was an observed static guard gap, not a production failure. Reviewed workflow Git blob checks still independently rejected source drift.
- **Verified root cause / failed approach:** Prefix-only `validate_trigger_reachability` checked bytes before the first canonical `permissions:` and did not reject effective root-level YAML aliases after it. Exact-source blob pinning is not a substitute for executable semantic regression negatives.
- **Correction / executable recurrence guard:** [900c9f56](https://github.com/m-shogo/memories-project/commit/900c9f563eb68cd896fa4f070fa1fd8fb6fa45a0) requires the exact publisher and independent root-key sequences. Eight negative fixtures each demand the exact root-shadow rejection. Both baseline roots and all eight mutation shapes passed bounded prewrite checks.
- **Retry condition:** Revisit only after an independently approved workflow root-key change and renewed exact-source/negative CI evidence. Do not repeat unchanged external or permission blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** Exact-source [Operability Admission Inventory PR Source Negative #40704654048](https://github.com/m-shogo/memories-project/actions/runs/40704654048) completed **SUCCESS** on `900c9f56`. Its job log proves 29 trigger omissions, 12 additions, two shortened inventories, three event-topology negatives, **eight exact-diagnostic root-shadow negatives**, 12 event/base/SHA runtime cases and 20 source mutation cases.
- **Why safe / reusable mechanism:** Only the CI-reachable read-only negative validator changed; no publisher, CI workflow, operational authority or production evidence was modified. The same semantic root-key inventory pattern can be reused where a different independent validator currently proves only the event prefix.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning Git blob SHAs were unchanged after the code commit. Production remains `NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED`, with zero admitted production-equivalent generation/objective/request/evidence/typed eight-domain/final-candidate records. Human promotion remains separate and non-automatic. Supplemental learning never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
- **Next safe target:** Audit the independent incident-control diagnostic source-negative CI for the same root-key semantic boundary; keep unchanged .yaml and supplemental-history trigger gaps scoped until workflow-write permission or a verified existing trigger path changes.
