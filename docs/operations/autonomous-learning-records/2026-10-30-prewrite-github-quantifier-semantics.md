# Supplemental OPS learning — GitHub path quantifier semantics (2026-10-30)

Append-only supplemental learning under `contracts/operations/autonomous-learning-system.json`. Canonical learning remains separate. This record cannot satisfy any production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion gate.

## Material semantic failure and correction

- **symptom:** A read-only workflow prewrite fanout auditor used Python `fnmatch` to classify GitHub Actions `paths` patterns. Its `?` and `+` handling could silently miss a matching workflow.
- **evidence:** [GitHub's official Workflow Syntax — Filter pattern cheat sheet](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#filter-pattern-cheat-sheet) specifies `?` as zero/one of the preceding character and `+` as one/more of the preceding character. Python `fnmatch` instead treats `?` as exactly one arbitrary character and `+` as a literal. For `scripts/a.py`, patterns `scripts/a.py?`, `scripts/a+.py` and `scripts/aa?.py` all fail Python `fnmatch` but can match under the documented GitHub syntax.
- **rootCauseOrUnknown:** Verified cross-engine glob grammar mismatch; no production incident or external CI outage is claimed.
- **failedApproach:** Using `fnmatch.fnmatchcase` as if it were a complete GitHub path-pattern interpreter, without conservative treatment of unsupported quantifiers.
- **correction:** [`a10eb92b`](https://github.com/m-shogo/memories-project/commit/a10eb92b5456c833619ba5fe12bf2905b01b20e4) treats any positive `?`/`+` path pattern as a possible match and adds three synthetic and three real CLI fixture cases. The exact ordered fixture identity digests are reconciled to 42 and 25 cases.
- **recurrenceGuard:** Existing CI-reachable `scripts/validate-autonomous-learning-system-negative.py` invokes the real auditor against all three patterns and checks exact match counts/identities; both suites pin their ordered case-label inventories. This is a conservative direct fanout estimate, never permission to write or a transitive workflow-call proof.
- **retryCondition:** Narrow this conservative classification only if a separately verified GitHub-compatible glob interpreter and corresponding positive/negative fixtures are available. Do not retry unchanged MinIO, canonical large-learning transport, workflow-write permission or human approval blockers.

## Scoped prewrite orchestration failure

- **symptom/evidence:** The first local orchestration for this code change stopped at JavaScript parsing with `SyntaxError: Unexpected token 'new'` before any GitHub write.
- **rootCauseOrUnknown:** Verified use of reserved identifier `new` as a JavaScript function parameter.
- **failedApproach:** Running an unparsed helper declaration with `function once(s,old,new)`.
- **correction:** Renamed the parameter to `replacement`, re-read latest `so` and target files, and reran the guarded write. No remote branch mutation occurred during the failed prewrite attempt.
- **recurrenceGuard/retryCondition:** Preserve parse-before-remote-write execution and exact source/diff/fixture preflight; retry only after correcting syntax and re-reading the branch lease. No external blocker was involved.

## Observed success and protected authority

- **outcome/evidence:** [Autonomous Learning Guard #40911910123](https://github.com/m-shogo/memories-project/actions/runs/40911910123) completed **SUCCESS** on exact source `a10eb92b5456c833619ba5fe12bf2905b01b20e4`, with **179** learning fail-closed cases, **52** fanout synthetic cases, **1,186** helper-ancestor negatives, append-only and contract PASS, and the unchanged 9-workflow shared entrypoint direct-match set classified `BLOCKED_KNOWN_WRITER_CAS`.
- **whySafe:** Only the read-only fanout audit and its existing CI-reachable negative harness changed. No workflow, production service, recovery evidence, credential, traffic or promotion authority was changed.
- **reusableMechanism:** Documented cross-engine pattern discrepancies become bounded conservative matching plus executable real-CLI negatives, not speculative claims of complete workflow reachability.
- **protectedAuthorityCheck:** Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` and all six generation/objective/drill/evidence/non-resurrection/promotion registries remained unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; all required real evidence and human promotion gates remain unsatisfied.
- **limitation/nextSafeTarget:** Canonical learning content is still unavailable through the large-file connector; only its blob identity is verified. Next audit the documented zero-directory semantics of `**/` against Python `fnmatch` and add bounded zero-directory variants plus exact CLI negatives if independently confirmed.
