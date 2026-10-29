# Supplemental OPS learning — Upload Route runtime command identity and JS replacement guard (2026-10-30)

Append-only supplemental history only; canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under mandatory `contracts/operations/autonomous-learning-system.json`. This cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure 1 — prewrite JavaScript replacement expanded Go test regex

- **Symptom:** A proposed generated Python validator patch unexpectedly duplicated the source suffix, causing the prewrite unique-anchor check to report two occurrences of an existing function call instead of one. **No repository write occurred.**
- **Observed evidence:** The reviewed Go test `-run` command includes the shell regex suffix `$'`. The JavaScript generator initially passed a replacement string containing that sequence to `String.replace`. A bounded reproduction showed `"prefix TARGET suffix".replace("TARGET", "go test -run '^(TestA|TestB)$'")` produces a duplicated `suffix` because JavaScript interprets `$'` as the post-match string. A replacement callback preserves the literal `$'`. The first candidate failed the prewrite exact-anchor count and was not uploaded.
- **Verified root cause:** JavaScript replacement-string interpolation of `$'` caused suffix expansion; not a GitHub or Python runtime failure.
- **Failed approach:** Passing untrusted/generated source text containing dollar-sign replacement metacharacters as a direct `String.replace` replacement string.
- **Correction / executable recurrence guard:** Use `source.replace(anchor, () => replacement)` for literal source generation, and require exact anchor cardinality, one target function definition, bounded diff size and a fresh HEAD/blob read before any write. These checks stopped the malformed candidate; no new repository-side JavaScript generator guard was added.
- **Retry condition:** Only retry after using callback-based literal replacement and passing deterministic prewrite anchor/size/structure checks. Never repeat the original string replacement approach on content containing `$'`.

## Material failure 2 — prewrite size budget mismatch

- **Symptom/evidence:** A corrected callback-based candidate had 74 new lines but 146,034 characters, exceeding the locally chosen 145,000-character prewrite cap; no GitHub write occurred.
- **Verified root cause:** The cap was lower than the measured current source (142,014 characters) plus the intended bounded 4,020-character addition.
- **Failed approach:** Applying an absolute size cap without reconciling it against measured baseline plus approved diff.
- **Correction / recurrence guard:** Compact the new test/helper implementation, re-read current source and validate +66 lines, 145,695 total characters, one target function and a 150,000-character bounded ceiling. The resulting patch passed prewrite checks.
- **Retry condition:** Recompute a bounded file-size ceiling from actual baseline and reviewed diff before any further large-validator edit.

## Material failure 3 — previously unguarded workflow command drift

- **Symptom:** Both Upload Route workflows could change their Python validators, `pip` arguments, `go test` target/filter, or compiled Python script list while retaining reviewed action identities, trigger paths and Go/Python source import fingerprints.
- **Observed evidence/root cause:** Read-only workflow inspection found an identical ordered set of **10 direct Python/Go command invocations** in both Publisher and PR workflows. Existing static source guards did not fingerprint these workflow command/continuation inputs. This was a prospective execution-graph gap, not observed production drift.
- **Failed approach:** Treating unchanged workflow action identities and source import fingerprints as proof that the invoked runtime command graph was unchanged.
- **Correction / executable recurrence guard:** [`da80a132`](https://github.com/m-shogo/memories-project/commit/da80a132d420d047e03c3fa4c5408cfd6582e9cb) pins the exact ordered ten-command normalized surface, including shell continuations, in both actual workflows. Six negative fixtures reject changed/added/removed Python/Go commands and Go test filter changes; a continuation positive control verifies parser behavior. This is bounded direct-command inspection, not complete shell/dataflow or third-party action closure.
- **Retry condition:** Review any legitimate workflow runtime command or test scope change with updated Go/Python inputs, exact-source CI, protected authority check and explicit trigger reachability review; do not narrow workflow triggers without complete closure.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40941569596](https://github.com/m-shogo/memories-project/actions/runs/40941569596) **SUCCESS** on exact source `da80a132d420d047e03c3fa4c5408cfd6582e9cb`. Logs confirm contract PASS, 201 printed fail-closed negatives, 74 fanout synthetic, 1186 helper-ancestor negatives, append-only, entry-document and read-only PASS. Six new nested negatives are not separately included in printed 201.
- **Why safe:** Only the CI-reachable read-only negative validator changed (+66 lines); the prewrite failed candidates were never uploaded. No workflow YAML, production source, credentials, traffic, generation/objective, reviewed request, recovery evidence, typed eight-domain records, independent review or human promotion changed.
- **Reusable mechanism:** Bind runtime command identity independently of static source imports and action refs; use callback-based literal code generation and structural prewrite checks to avoid source duplication.
- **Protected-authority check:** Post-code-commit canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and protected registries unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations, human-approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records, final candidates and human promotion remain zero. Preflight requires distinct unsuperseded semantically eligible environments and explicitly human-approved current objective; reviewed requests remain planning-only, evidence request-bound, independent review and promotion separate.

## Next safe target

Audit shell command prefix/inline execution escapes and Go/Python runtime inputs beyond direct command lines; preserve 109 reviewed static inputs and 81 uncovered inputs per workflow as lower bounds, and do not change workflow triggers without complete closure and authorized writes.
