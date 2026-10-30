# Supplemental OPS learning — Upload Route hardlinked source input identity (2026-10-30)

Append-only supplemental learning only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy: `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound evidence, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure — hardlink alias not detected by path resolution

- **symptom:** A Go source, module, Python validator, workflow or JSON input with two hardlink names can satisfy the existing strict resolved-path equality while sharing its inode with an unreviewed alias. This is a prospective static source-identity gap, not an observed production compromise.
- **evidence:** The prior `require_unaliased_go_path` checked `path.is_symlink()` and `path.resolve(strict=True)` equality but did not check link count. A disposable regular file showed `st_nlink=1`, `os.link` raised both names to `st_nlink=2`, and unlinking the alias restored `st_nlink=1`.
- **rootCauseOrUnknown:** Verified: hardlinks preserve lexical and resolved path identity but introduce an additional inode name.
- **failedApproach:** Treating strict resolution and symlink rejection as sufficient proof of single-name source ownership.
- **correction:** [`3aeb8a98`](https://github.com/m-shogo/memories-project/commit/3aeb8a986e101103f9b45d51aa3bfd477d78962b) rejects non-single-link regular files in the shared Upload Route source-path guard.
- **recurrenceGuard:** The CI-bound disposable `os.link` negative requires the exact existing source-alias diagnostic, and the restored single-link positive proves normal files remain accepted.
- **retryCondition:** Reconsider a legitimate hardlinked input only after reviewing inode ownership, the exact dependency/source inventory, executable negatives, exact-source CI and protected authorities. Do not retry unchanged workflow-write, MinIO HTTP 401, canonical large-file transfer or human-promotion blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41025435794](https://github.com/m-shogo/memories-project/actions/runs/41025435794) completed **SUCCESS** on exact source `3aeb8a986e101103f9b45d51aa3bfd477d78962b`.
- **evidence:** Job logs show append-only PASS, 509 canonical fail-closed negatives, 193 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only checks PASS. The hardlink fixture runs inside the existing suite and is not separately counted in 509.
- **whySafe:** Only the existing read-only negative validator changed (+17/-1 lines); the hardlink fixture operates in a disposable directory. No Go production source, workflow, credentials, traffic, evidence, generation, objective, request, recovery, eight-domain review or promotion authority changed.
- **reusableMechanism:** Couple strict source path resolution with regular-file link-count identity and a hardlink-negative/restoration-positive pair; do not equate this static guard with complete transitive build or runtime dependency closure.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged through the code commit and subsequent verification: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, final candidate and human promotion all absent. Preflight still requires distinct unsuperseded semantically eligible environments and a current human-approved recovery objective; independent review and human promotion remain separate.

## Next safe target

Reject non-regular filesystem inputs before read (FIFO/socket/device), preserve source-only CI reachability caveats, and continue the Go/Python transitive dependency and pre-MinIO focused-test audit without changing workflow YAML.
