# Supplemental OPS learning — pinned drill request negative child execution (2026-11-02)

Append-only execution learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. **Never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, approved objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent-review, final-candidate or human promotion evidence.

## Material failure — negative child script pathname reopened after review

- **symptom:** The drill-request admission validator checked its canonical negative-suite pathname and then executed `python <path>`, leaving a mutable-path reopen between review and child execution. No malicious runner filesystem replacement or production incident was observed.
- **evidence:** At pre-change `7109786c35454bcb1fe3129fe230d417191295c6`, `scripts/validate-memory-os-backup-restore-drill-request.py` used `require_exact_repo_file(NEGATIVE,...)` and `subprocess.run([sys.executable, str(NEGATIVE)])`. Environment isolation, DEVNULL output, timeout and strict typed result checks were already present. Prior [pinned negative child learning](2026-11-02-drill-binding-pinned-negative-child-stdin.md) records the same failure mode and a CI-proven mechanism.
- **rootCauseOrUnknown:** Verified child executable-source TOCTOU in the reviewed code. Actual adversarial access to runner files is unknown.
- **failedApproach:** Assuming that a canonical path precheck guaranteed the later child Python interpreter would execute the same script bytes.
- **correction:** [`d71a8405`](https://github.com/m-shogo/memories-project/commit/d71a84056d5fe63a488ae8ddba37892059d19760) adds a bounded no-follow pinned reader for the reviewed negative suite with directory/leaf mode, link and identity checks and primary-error-preserving FD cleanup. The child executes verified source bytes via stdin and a fixed `python -c` bootstrap, retaining canonical script-directory import semantics.
- **recurrenceGuard:** Existing CI-reachable `validate-memory-os-backup-restore-drill-request-load-negative.py` now requires exact pinned input bytes, fixed bootstrap, reviewed target, isolated environment, 120-second timeout, private output and strict return-code/exception classes. A new synthetic substituted-leaf-FD negative must reject before subprocess.
- **retryCondition:** Revisit only if the negative-suite source, loader semantics, reviewed child path, exact-source CI, or pinned reader boundary changes. Do not retry unchanged MinIO 401, workflow-write permission or absent external human-evidence blockers.

## Material success — bounded reviewed negative-suite source transport

- **outcome:** The reviewed negative suite is supplied to its child interpreter as a verified pinned source snapshot rather than an executable pathname reopen.
- **evidence:** Exact-source [Backup Restore Drill Request Reconcile Rollback #41355952763](https://github.com/m-shogo/memories-project/actions/runs/41355952763) completed **SUCCESS** at `d71a8405` with `production decision: NO_GO` and `production decision changed: false`. In [Drill Request Admission #41355952859](https://github.com/m-shogo/memories-project/actions/runs/41355952859), the `Validate and reconcile planning authority` and `Enforce drill request admission validation` steps were observed **SUCCESS**, which run the existing negative-source test, at record preparation. The overall Admission workflow was still in progress and is **not** claimed successful.
- **whySafe:** The atomic code/test commit changed only the admission validator and its synthetic load-negative suite. Reviewed negative script identity, workflow, production status, registry, credential, traffic and promotion authority were not changed. The synthetic substituted source is rejected before child execution.
- **reusableMechanism:** Pin reviewed Python script source with no-follow descriptors and identity checks; pass exact bytes via stdin to a fixed direct-script-compatible bootstrap; exercise source substitution and private process transport in the existing CI path.
- **protectedAuthorityCheck:** Exact code commit changed only the two Python paths. All ten protected Git blobs remain unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objectives `f4d74f33`, drill request registry `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO` and OPS-P0-007 `PREREQUISITES_BLOCKED`. No learning or CI result is admitted as production evidence or human promotion authority.

## Reused material failure — stale source publisher guard

- **symptom:** [Drill Request Admission #41355818867](https://github.com/m-shogo/memories-project/actions/runs/41355818867) for the preceding code HEAD `488083e8` finished **FAILED** after validator success.
- **evidence:** The publisher fetched `origin/so` advancing from `488083e8` to `7109786c` and exited 75 with `Drill planning source HEAD changed during reconciliation; refusing stale derived authority.`
- **rootCauseOrUnknown:** Verified concurrent branch advancement invalidated exact-source publication, matching the previously recorded stale-source guard. This is not a validator failure.
- **failedApproach:** Publishing derived planning authority from an obsolete HEAD.
- **correction:** Reuse the existing fail-closed exact-source guard; do not weaken, force-push or replay an unchanged stale run.
- **recurrenceGuard:** The publisher compares `origin/so` to captured `SOURCE_SHA` before publication and exits 75 on mismatch.
- **retryCondition:** Only a fresh source-bound run after the reviewed authority/source precondition changes; no unchanged stale replay.

## Next safe target

Audit the canonical helper `load_module` path reopen in the drill-request validator and reconciler. Preserve existing private-import and loader-transport negatives; do not alter production authority, workflow permissions or human promotion.
