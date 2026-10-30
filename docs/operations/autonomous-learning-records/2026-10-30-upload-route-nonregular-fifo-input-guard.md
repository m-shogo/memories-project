# Supplemental OPS learning — reject non-regular Upload Route source inputs (2026-10-30)

Append-only supplemental history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract is `contracts/operations/autonomous-learning-system.json`. This learning record is **never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — non-regular filesystem input

- **symptom:** A named pipe with a `.go` source filename can pass strict `Path.resolve` identity and symlink checks, yet a later `read_text` on it may block the static dependency audit indefinitely. This is a prospective audit availability/safety gap, not a production incident.
- **evidence:** In a disposable filesystem, `os.mkfifo(path)` creates an existing path for which `resolve(strict=True)` succeeds, `is_symlink()` is false, and both `is_file()` and `is_dir()` are false. The earlier shared source guard did not require a regular file or directory.
- **rootCauseOrUnknown:** Verified: the prior guard proved path spelling but did not prove an acceptable filesystem object type before consuming inputs.
- **failedApproach:** Treating any resolved, non-symlink path as a safe static compile input.
- **correction:** [`e0ee9c97`](https://github.com/m-shogo/memories-project/commit/e0ee9c977f017d22b988c8a6d77e3e6e590bbc7f) requires every guarded source path to be a regular file or directory, retaining the hardlink and symlink restrictions.
- **recurrenceGuard:** The CI-bound disposable FIFO negative uses `os.mkfifo`, asserts the exact source-alias diagnostic, and removes the pipe without opening it. Existing regular-file, directory, symlink, hardlink and restored-file positives/negatives continue running.
- **retryCondition:** Reconsider a legitimate non-regular input only with a reviewed bounded nonblocking reader, explicit source-type contract, executable negative/positive controls, exact-source CI and protected-authority comparison. Do not retry unchanged MinIO, workflow permission, canonical learning transfer or human-promotion blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41025587082](https://github.com/m-shogo/memories-project/actions/runs/41025587082) completed **SUCCESS** on exact source `e0ee9c977f017d22b988c8a6d77e3e6e590bbc7f`.
- **evidence:** CI job logs confirm append-only PASS, learning contract PASS, 509 canonical fail-closed negatives, 193 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only checks PASS. The FIFO fixture is nested and not a separate increment to the displayed 509.
- **whySafe:** Only the read-only negative validator changed (+15 lines); the FIFO was created and removed in a disposable test directory, never opened or used as production evidence. No workflow YAML, Go runtime, credentials, traffic, generation, objective, recovery, eight-domain, review or promotion authority changed.
- **reusableMechanism:** Establish regular-file/directory type identity before any static source read, paired with a named-pipe negative that must reject without blocking.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0 and all distinct objective, executable request, request-bound evidence, typed eight-domain, independent review and human-promotion prerequisites remain unmet. Reviewed drill requests alone cannot execute recovery or promote production.

## Next safe target

Verify Git tracing is blocked before read-only prewrite Git commands; continue auditing Go-only source-change CI reachability and Go/Python dependency closure without changing workflow YAML.
