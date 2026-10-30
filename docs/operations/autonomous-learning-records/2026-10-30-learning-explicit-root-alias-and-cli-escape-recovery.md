# Supplemental OPS learning — explicit root alias rejection and CLI escape recovery (2026-10-30)

Append-only supplemental learning/history under the unchanged mandatory `contracts/operations/autonomous-learning-system.json`. The canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` blob is unchanged but could not be transferred in full. Never use this record as production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery-objective, reviewed-request, request-bound evidence, typed eight-domain non-resurrection, independent review or promotion evidence.

## Material failure A — explicit repository root alias

- **symptom:** The canonical validator's `--repo-root` path was immediately resolved, so a caller-supplied symlinked root or symlinked ancestor could silently become an apparently canonical real directory. No production incident is claimed.
- **evidence:** Previous `main()` called `validate(args.repo_root.resolve())` without retaining the caller-supplied path. Disposable local Python fixtures showed that both a root symlink and an ancestor symlink differ between `Path.absolute()` and `Path.resolve()` while resolving to a valid repository directory. Prior learning had guarded symlinked canonical file parents but not this CLI root-selection boundary.
- **rootCauseOrUnknown:** Verified loss of caller-supplied root identity before validation; a real attacker-controlled runner alias was not observed.
- **failedApproach:** Treating resolution of an unreviewed explicit root alias as proof of its source authority.
- **correction:** [`cb54c0ab`](https://github.com/m-shogo/memories-project/commit/cb54c0ab8c36d68336e26a4496d38d9f52f9903d) rejects a lexical absolute root that differs from its resolved path before calling the canonical validator.
- **recurrenceGuard:** [`5f58ca3e`](https://github.com/m-shogo/memories-project/commit/5f58ca3e58771402c79eecfb9c6837223eebe463) adds actual CLI positives on a real disposable root and exact negatives for root and ancestor symlink aliases. These nested cases do not change the printed canonical negative count.
- **retryCondition:** Revisit only for a reviewed legitimate root alias with explicit source-identity policy, actual CLI positive/negative proof, exact-source CI and protected-authority comparison.

## Material failure B — CLI newline expectation escaped twice

- **symptom:** [Autonomous Learning Guard #41048529724](https://github.com/m-shogo/memories-project/actions/runs/41048529724) FAILED in the new root-alias positive control.
- **evidence:** The exact-source job log shows `RuntimeError: canonical root alias positive control failed` at the newly added fixture. Read-back of the committed Python source showed two literal backslashes before `n` in both expected CLI strings; the real CLI emits an actual newline. The first positive rejected before the alias negatives executed.
- **rootCauseOrUnknown:** Verified fixture-string over-escaping during code construction, not a failure of the root-alias guard. No broader runtime cause is claimed.
- **failedApproach:** Treating a displayed escaped source snippet as sufficient proof that a Python string literal decodes to a newline.
- **correction:** [`77f0fd3d`](https://github.com/m-shogo/memories-project/commit/77f0fd3d4915988afcbdd5a9fcec1d3bf186c5a1) reduces the two string literals to one source backslash before `n`, preserving exact stdout/stderr checks.
- **recurrenceGuard:** Byte/code-point inspection confirmed one source backslash in each corrected literal; the actual positive and both negative CLI cases run in the CI-bound suite. Future fixture construction must verify literal escape depth and exact emitted diagnostics before treating a CI run as successful.
- **retryCondition:** Retry only after the source literal is corrected and exact-source CI confirms the fixture runs. The precondition changed at `77f0fd3d`; do not repeat the original over-escaped source.

## Material success — corrected exact-source CI

- **outcome:** [Autonomous Learning Guard #41048573247](https://github.com/m-shogo/memories-project/actions/runs/41048573247) completed **SUCCESS** on exact source `77f0fd3d4915988afcbdd5a9fcec1d3bf186c5a1`.
- **evidence:** Job logs confirm append-only PASS, learning contract PASS, **542 canonical fail-closed cases**, **195 fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and clean/read-only completion. Root-alias CLI cases are nested and do not inflate the 542 count.
- **whySafe:** Changes were confined to the two CI-reachable read-only Python validators. Symlinks and disposable canonical authority copies existed only in temporary fixture directories; no production/backup/recovery/promotion authority was modified.
- **reusableMechanism:** Preserve explicit source-root lexical identity before canonicalization; pair it with real CLI positive and alias-negative tests, and independently verify escape depth in exact diagnostic fixtures.
- **protectedAuthorityCheck:** The code diff changed only the two read-only validators. Ten protected blob SHAs remain unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill-request/recovery-evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0, no current human-approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review, final candidate or human promotion.

## Next safe target

Reuse the bounded descriptor-pinned reader for the separate prewrite baseline/candidate Python file path, which still uses a size preflight followed by unbounded `read_text()`. Add actual CLI hardlink/mode/oversize negatives without modifying workflow YAML. Independently continue Go/Python transitive CI trigger closure.
