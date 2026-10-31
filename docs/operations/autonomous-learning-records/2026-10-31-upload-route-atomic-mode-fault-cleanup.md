# Supplemental OPS learning — upload-route atomic mode fault cleanup (2026-10-31)

Append-only operational learning only. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed drill request, request-bound evidence, typed eight-domain non-resurrection, independent review or promotion evidence.

## Material failure / uncovered fault boundary

- **symptom:** The existing Upload Route atomic mode-preservation negative exercised successful 0644/0755 replacements and new-file 0600 creation, but did not fault-inject `fchmod` or `fsync` after temporary-file staging. This was an observed **test-coverage gap**, not an observed production write failure.
- **evidence:** At source `5872f649`, `prove_atomic_mode_preservation` checked only successful mode-preserving publication; `prove_atomic_replace_failure` rejected `os.replace` failures, but neither exercised `os.fchmod` nor `os.fsync` failure. The writer stages through `mkstemp`, `fdopen`, `fchmod`, `fsync`, `os.replace` and `finally: temporary.unlink(missing_ok=True)`.
- **rootCauseOrUnknown:** Verified missing deterministic fault fixtures for two post-staging operations. No claim is made that either operation actually failed in production or that an OS-level race has been eliminated.
- **failedApproach:** Treating successful mode preservation and a separate rename-failure test as sufficient proof of all atomic publication error paths.
- **correction:** [ca58a47c](https://github.com/m-shogo/memories-project/commit/ca58a47c717b60a8fcb3b1d66867fc8f4aa3d74d) adds `prove_atomic_mode_failure_cleanup` to the existing read-only rollback negative. Disposable 0755 files receive synthetic `fchmod` and `fsync` failures, and each case asserts exact original bytes, original mode, and no new temporary residue. The original transport is restored in `finally`.
- **recurrenceGuard:** The existing MinIO-independent `scripts/validate-memory-os-entry-docs.py` now AST-requires a single direct `main()` call to the new proof and actual `module.atomic_write_bytes` use. The live rollback negative runs under a 30-second bounded subprocess with exact PASS stdout and empty stderr; a renamed/commented-out proof is not a substitute.
- **retryCondition:** Revisit when the atomic writer's `fdopen`/`fchmod`/`fsync`/`replace` transport, CI call graph, mode policy, or filesystem ownership model changes. The already documented path-check-to-replace race requires a separate reviewed no-follow/locking design; do not treat this fault fixture as a concurrency proof.

## Material safe success

- **outcome:** Two deterministic atomic fault paths are now exercised before external MinIO bootstrap, with cleanup and mode preservation verified on disposable files.
- **evidence:** [Autonomous Learning Guard #41174224857](https://github.com/m-shogo/memories-project/actions/runs/41174224857) completed **SUCCESS** on exact code commit `ca58a47c`. The append-only, learning contract/executable negatives, independent helper-ancestor reachability and read-only steps all completed successfully. [Upload Route #41174224859](https://github.com/m-shogo/memories-project/actions/runs/41174224859) failed at unchanged `Start local MinIO`; focused Go/HTTP tests did not execute and are **not** claimed as passed.
- **whySafe:** Only the disposable rollback negative and the already CI-reachable read-only entrypoint were changed. No workflow YAML, production registry, recovery evidence, credential, traffic, human approval or promotion authority was written. No production reconciler was run by this task.
- **reusableMechanism:** Inject failures immediately before atomic publication, require byte/mode preservation and absence of temporary residue, restore monkeypatched transports, and bind the real executable proof to a MinIO-independent CI entrypoint.
- **protectedAuthorityCheck:** All ten protected Git blobs remained unchanged after `ca58a47c`: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill-request/recovery-evidence/non-resurrection/promotion registries `bfd1b045`, `f4d74f33`, `acebcd02`, `ae7e57ef`, `26bb1cc7`, `99cb895f`. These records are not admission evidence.

## Strict admission boundary and next safe target

`productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with registered/semantically preflight-eligible generations 0/0. Preflight requires unsuperseded semantically eligible generations from distinct environments plus an explicitly human-approved current recovery objective. Reviewed drill requests are planning authority only; new generation recovery evidence must be bound to a current executable reviewed request. Final candidates additionally require complete typed eight-domain non-resurrection coverage and independent review. Human production promotion is separate and never automatic.

Next safe target: audit and exercise `fdopen` descriptor-acquisition failure cleanup and residual atomic path race semantics without touching workflow YAML or retrying unchanged MinIO HTTP 401, supplemental-only CI trigger permission, or human approval blockers. This learning-only commit does not itself establish a new full-chain exact-source CI SUCCESS.
