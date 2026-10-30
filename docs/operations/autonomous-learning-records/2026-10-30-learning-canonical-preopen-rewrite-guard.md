# Supplemental OPS learning — same-inode pre-open canonical authority rewrite (2026-10-30)

Append-only supplemental learning/history under the mandatory `contracts/operations/autonomous-learning-system.json`; never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human-promotion evidence. Canonical learning blob `b809c69d` is unchanged but its full body remains unavailable through the connector.

## Material failure — pre-open same-inode rewrite

- **symptom:** The first descriptor-pinned canonical authority reader rejected a different inode and post-open modifications, but could accept an in-place rewrite of the same inode between its initial `lstat()` and subsequent `fstat()`. No production incident is claimed.
- **evidence:** An isolated Python reproduction of the new reader's metadata predicates monkeypatched `os.open` to rewrite a six-byte file to seven bytes after the initial `lstat`; the previous predicate accepted `b"ALTERED"` as the canonical snapshot. The existing code compared only `(st_dev, st_ino)` before/after open, not the pre-open `st_size`, `st_mtime_ns` or `st_ctime_ns`.
- **rootCauseOrUnknown:** Verified incomplete equality between the preflight and opened-descriptor metadata snapshots; absolute immunity to arbitrary adversarial swap-back and filesystem timestamp behavior is not claimed.
- **failedApproach:** Treating a stable inode identity as sufficient proof that its content was not rewritten before the descriptor opened.
- **correction:** [`22de49ba`](https://github.com/m-shogo/memories-project/commit/22de49ba37ed7c94e10d1b7c3f194513a4791b92) rejects any preflight/open mismatch in size, mtime or ctime, preserving the descriptor/path post-read checks.
- **recurrenceGuard:** [`81258dbb`](https://github.com/m-shogo/memories-project/commit/81258dbbf702cbf2221cbda9e04077d8e1e31a53) adds a deterministic in-place rewrite-before-open helper negative and restoration. It also extends the existing parent-mode CLI suite with a world-writable checkout-root negative, with fixture-state fingerprinting of the root directory mode. The latter is counted in the canonical CLI case total; the nested rewrite proof is not.
- **retryCondition:** Revisit on verified metadata timestamp ambiguity, same-metadata byte rewrite, parent swap or platform-specific descriptor behavior; require executable negative/positive proof and exact-source CI. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical learning full-transfer or human promotion blockers.

## Material success — exact-source CI

- **outcome:** [Autonomous Learning Guard #41048135688](https://github.com/m-shogo/memories-project/actions/runs/41048135688) completed **SUCCESS** on exact source `81258dbbf702cbf2221cbda9e04077d8e1e31a53`.
- **evidence:** Job logs show append-only PASS, contract PASS, **542 canonical fail-closed cases** (541 before), **195 fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS and clean/read-only completion. A local isolated prototype confirmed the new metadata equality rejects the in-place pre-open rewrite.
- **whySafe:** Only the two CI-reachable read-only Python validators changed; negative mutations are disposable and do not touch production or protected authorities.
- **reusableMechanism:** Compare pre-open pathname metadata with the opened descriptor and compare the descriptor with the final pathname after bounded reading. Test root-directory write authority separately from leaf/inner-parent checks.
- **protectedAuthorityCheck:** The code diff changed only `scripts/validate-autonomous-learning-system.py` and `scripts/validate-autonomous-learning-system-negative.py`. All ten protected blobs remain unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill-request/recovery-evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, no approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review, final candidate or human promotion.

## Next safe target

Audit explicit `--repo-root` symlink/ancestor aliases: the current CLI resolves the input root before validation, potentially discarding its original path identity. Use real CLI negative cases, and continue independent Go/Python transitive CI trigger coverage without changing workflow YAML.
