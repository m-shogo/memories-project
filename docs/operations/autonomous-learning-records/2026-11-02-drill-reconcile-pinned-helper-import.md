# Supplemental OPS learning — pinned reconciler helper imports (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. **Never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered/semantically eligible generation, approved objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — canonical helper loader reopened mutable path

- **symptom:** The drill-request reconciler's `load_module(path,name)` admitted a repository-contained helper and executed `spec.loader.exec_module(module)` after its pathname check. The SourceFileLoader could reopen a different file between check and import. No real malicious substitution or production compromise was observed.
- **evidence:** At pre-change `d25d3f3aac75fc96eaaa087647a34e4ebdf06532`, the reconciler used `require_repo_file` and `spec.loader.exec_module` for the drill writer, semantic eligibility helper and recovery objectives writer. The existing pinned post-validator source reader and its negative fixtures were available for reuse.
- **rootCauseOrUnknown:** Verified helper import source TOCTOU and overly broad repository-file admission. Whether external runner file substitution was possible in practice remains unknown.
- **failedApproach:** Treating repository containment plus Python's pathname-based loader as equivalent to a reviewed, pinned executable module.
- **correction:** [`91373c19`](https://github.com/m-shogo/memories-project/commit/91373c19a164298b12cfc8f65be012c5596a64bf) reuses the existing bounded no-follow source reader, closes the helper allowlist to the three reviewed paths, and compiles/executes only pinned source bytes into the reviewed module namespace. Private import output and exception details remain suppressed.
- **recurrenceGuard:** The existing CI-reachable drill reconcile rollback negative suite checks the canonical writer positive import, private noisy success/failure source, unreviewed repository helper rejection and synthetic substituted writer FD rejection before execution. Existing ancestor-swap and source-pinning negatives remain active.
- **retryCondition:** Reassess only when the reviewed helper set, module execution semantics, pinned source reader, CI fixture or exact-source CI outcome changes. Do not retry unchanged MinIO HTTP 401, workflow permission or human-evidence blockers.

## Material success — pinned and closed helper module execution

- **outcome:** The three reviewed reconciler helpers execute verified pinned source bytes instead of reopening the mutable script pathname, and an arbitrary repository file cannot be used as a helper.
- **evidence:** Exact-source [Backup Restore Drill Request Reconcile Rollback #41356307747](https://github.com/m-shogo/memories-project/actions/runs/41356307747) completed **SUCCESS** for `91373c19a164298b12cfc8f65be012c5596a64bf`. Job `124996979204` logs show `PASS: drill reconcile helper import executes pinned source, rejects unreviewed targets and substituted FDs, suppresses private errors`, `Memory OS backup/restore drill request reconcile rollback negative suite PASS`, `production decision: NO_GO`, and `production decision changed: false`. Other workflows at this HEAD were not all complete at observation and are not claimed successful.
- **whySafe:** The atomic commit modified only the reconciler and its existing synthetic negative suite. No reviewed workflow, production status, registry, credential, traffic, evidence or promotion authority changed; canonical helper imports and rollback tests passed.
- **reusableMechanism:** Reuse a tested pinned source reader for both child script execution and in-process module import; preserve module metadata via `spec_from_file_location`/`module_from_spec` but replace `SourceFileLoader.exec_module` with `exec(compile(pinned_bytes))`. Keep a closed helper path allowlist and executable substitution negative.
- **protectedAuthorityCheck:** Exact Git compare `d25d3f3a..91373c19` lists only two Python paths. Ten protected blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, recovery objectives `f4d74f33`, drill request registry `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO` and `PREREQUISITES_BLOCKED`; no synthetic/learning CI result satisfies separate production or human promotion gates.

## Next safe target

Audit the independent drill-request admission validator's `load_module` source reopen while preserving its existing `spec_from_file_location`/module-transport negative tests. Do not change workflow permissions, production evidence, OPS-P0-007 gates or promotion authority.
