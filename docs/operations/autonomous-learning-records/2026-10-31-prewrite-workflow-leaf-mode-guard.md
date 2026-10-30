# Supplemental OPS learning — prewrite workflow leaf write authority (2026-10-31)

Append-only learning, not production evidence. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. This record must not satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure risk

- **symptom:** A workflow YAML leaf with group/world write permission could be rewritten by an unreviewed principal after source inspection while its path, inode and initial bytes remain otherwise valid.
- **evidence:** At parent-guard baseline `840304d50ea90a83786cfb78668cfaa901d2f3e8`, the bounded workflow descriptor reader rejected nonregular files, hardlinks, oversized files and path/inode/ctime drift but did not reject unsafe leaf write-mode bits. A disposable local chmod control showed `0o664` and `0o666` retain the same inode and bytes while granting group/world write authority. This is prospective source-authority exposure, not observed production compromise.
- **rootCauseOrUnknown:** Verified missing `0o020`/`0o002` mode predicates on the descriptor snapshot; whether an actual runner has an untrusted principal with those permissions is unknown.
- **failedApproach:** Inferring a protected workflow source solely from raw blob equality, stable inode and directory identity without considering independent leaf write authority.
- **correction:** [`57de4079`](https://github.com/m-shogo/memories-project/commit/57de4079a85829a25654d1374cc6e939f1964f7b) rejects group/world writable leaf modes before reading source bytes, in both ordinary and strict Git-index audit paths.
- **recurrenceGuard:** Four descriptor negatives (2 modes × strict/non-strict) plus two real-CLI negatives require exact fail-closed diagnostics, with clean positive and restored positive controls. Canonical printed negatives increase from 566 to **572**.
- **retryCondition:** Reconsider only with a reviewed runner group/ACL ownership policy, changed precondition, exact-source positive/negative CI and protected-authority checks. Do not retry unchanged MinIO 401, workflow-write permission, canonical learning transport or human-promotion blockers.

## Material success and protected-authority check

- **outcome:** The leaf permission guard and six executable negative controls landed on `so` at `57de4079a85829a25654d1374cc6e939f1964f7b`.
- **evidence:** Exact-source [Autonomous Learning Guard #41079856551](https://github.com/m-shogo/memories-project/actions/runs/41079856551) completed SUCCESS. Job logs report append-only PASS, contract/negative PASS (**572** canonical cases), **195** fanout synthetic cases, **1,186** helper ancestor negative mutations, entry-document PASS and clean read-only completion.
- **whySafe:** Only two read-only Python validator files changed; all chmod mutations occur in disposable test directories. No workflow YAML, service runtime, credential, traffic, backup/restore, generation, recovery, non-resurrection, review or promotion authority changed.
- **reusableMechanism:** Verify both source-byte/inode identity and group/world write authority at the descriptor used for bounded parsing, with separate strict and non-strict real tests.
- **protectedAuthorityCheck:** GitHub compare from `840304d5` to `57de4079` changes only `scripts/audit-memory-os-workflow-trigger-fanout.py` and `scripts/validate-autonomous-learning-system-negative.py`. Ten protected authorities remain untouched; canonical learning blob `b809c69d`, contract blob `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` are unchanged. Full canonical learning text was not retrieved, and this record is not a substitute.
- **production boundary:** Current source authorities still state `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and no approved recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, final candidate, independent review or human promotion.

## Next safe target

Audit Git index/worktree executable-bit parity: raw workflow bytes and clean `git diff --cached` can mask a worktree executable-mode change. Prove with disposable Git fixture and fail closed in strict source identity without altering workflows.
