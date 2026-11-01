# Supplemental OPS learning — JSON parent-swap and raw-FD cleanup double-fault proof (2026-11-02)

Append-only learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** The new pinned planning JSON readers checked ancestor pathname identity and preserved primary errors across descriptor cleanup failures, but their CI-reached negative suite did not prove either branch against a parent directory swapped *after* descriptor acquisition or a close fault occurring with and without a primary read failure.
- **evidence:** At HEAD `fd0a36c4`, the two `pinned_read` implementations had ancestor `lstat`/FD identity checks and a `finally` cleanup guard; the prior negative suite covered static symlinks, hardlinks, mid-read file mutation, EOF and nonbytes, but not a post-acquisition parent swap or `os.close` double fault. No production failure was observed.
- **rootCauseOrUnknown:** Verified independent executable-proof gap for existing runtime guards; actual malicious path substitution or close failure in production unknown.
- **failedApproach:** Assuming static parent-symlink rejection and a normal positive read also prove the later parent-path identity and cleanup-exception precedence branches.
- **correction:** [`487f2d99`](https://github.com/m-shogo/memories-project/commit/487f2d995d9907167938ad6f7a82eba7b2611beb) adds isolated parent rename-to-symlink during the first `os.read`, and after-effect `os.close` `ValueError` injection on both successful and already-failing reads. The reader implementations did not require modification.
- **recurrenceGuard:** The existing CI-reached drill generation binding reconcile negative suite executes the new cases independently for both validator and reconciler JSON readers, requires exact fail-closed diagnostics, restores all monkeypatches and temporary directory paths, and confirms canonical contract and drill registry bytes unchanged.
- **retryCondition:** Revisit only when ancestor identity verification, FD cleanup, exception precedence or exact-source CI topology changes. Do not retry unchanged Quay MinIO HTTP 401, workflow permissions or external production evidence blockers.

## Material success

- **outcome:** The existing JSON reader guards now have executable proof for an after-acquisition ancestor swap and cleanup faults both on a successful body and while preserving an earlier validation error.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41342232264](https://github.com/m-shogo/memories-project/actions/runs/41342232264) completed **SUCCESS** on code HEAD `487f2d99`. Logs explicitly show `PASS pinned JSON: both readers reject leaf/parent symlink, hardlink, EOF, nonbytes and mutation, parent swap, cleanup double fault; fragmented positive`, `Drill generation eligibility binding reconcile negative suite PASS` and `production decision: NO_GO`. This is synthetic CI validation only, not a Go test or real restore.
- **whySafe:** Only an existing negative-test script changed. The path swap and close faults operate on disposable temporary JSON fixtures; canonical production and recovery authorities, credentials, traffic, permissions and promotion remain untouched.
- **reusableMechanism:** For a pinned reader, test both static and after-acquisition ancestor substitutions, plus after-effect close faults with and without a primary failure. The latter must not mask the earlier validation failure or report a successful read with failed cleanup.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs remained unchanged after the test commit: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. All generation, objective, current executable reviewed request, request-bound evidence, eight-domain coverage, independent review and separate human promotion gates remain strict.

## Next safe target

Audit the pinned JSON readers' descriptor acquisition return-type boundary (invalid `os.open` results must never be closed or passed to `fstat`) and ensure the negative suite remains reachable. Continue the approved pre-MinIO Focused Go Test path investigation without permission changes.
