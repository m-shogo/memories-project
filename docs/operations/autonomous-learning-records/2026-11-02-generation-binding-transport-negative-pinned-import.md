# Supplemental OPS learning — generation-binding transport negative pins validator bytes (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, human-approved objective, reviewed request, request-bound recovery, typed eight-domain coverage, independent review, final candidate, or promotion evidence.

## Material failure

- **symptom:** The generation-binding transport negative harness used a checked canonical validator pathname but reopened its executable bytes through `SourceFileLoader.exec_module`.
- **evidence:** At prior `so` HEAD `dc1e0696ce1c40c6341172527142ba4954f52754`, `scripts/validate-memory-os-backup-restore-generation-binding-transport-negative.py::load_validator` checked `is_file`, `is_symlink` and `resolve`, then used the pathname-based loader. No actual adversarial execution was observed.
- **rootCauseOrUnknown:** Verified source-level pathname TOCTOU; real exploitation remains unknown.
- **failedApproach:** Treating canonical pathname checks and a module spec as sufficient authority to execute source that the loader later reopens.
- **correction:** [`45635751`](https://github.com/m-shogo/memories-project/commit/456357516ab6c5a69951384a4214fb190f4d5cd4) pins bounded bytes from owned no-follow directory and leaf descriptors, validates regular unique non-writable source and safe parent identity, closes owned descriptors and executes the captured source.
- **recurrenceGuard:** The existing CI-reachable transport negative exercises a positive fixture, rejects writable source and proves that a parent rename/symlink swap after byte capture cannot execute the redirected canary. The canary remains unchanged.
- **retryCondition:** Revisit on module import/descriptor/permission/parent identity or CI trigger changes. Do not retry unchanged publisher-coupled writer modifications, Quay MinIO 401, canonical large-blob transport, workflow-write permission or missing human evidence.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41393977328](https://github.com/m-shogo/memories-project/actions/runs/41393977328) completed **SUCCESS** on exact source `456357516ab6c5a69951384a4214fb190f4d5cd4`; job `125111216721` logged `PASS: generation-binding transport validator pinned after parent swap`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`. [Backup Restore Admission Chain #41393977324](https://github.com/m-shogo/memories-project/actions/runs/41393977324) also completed SUCCESS.
- **evidence:** Observed GitHub Actions run conclusions and targeted negative logs; synthetic CI only.
- **whySafe:** Only the independent read-only transport negative harness changed; the production-capable Generation Evidence publisher's push triggers exclude it. Synthetic tests use disposable directories and preserve canary bytes.
- **reusableMechanism:** Exact path allowlist plus bounded FD-pinned source, stable pre/post source and parent metadata, no SourceFileLoader pathname reopen, and real post-capture parent-swap negative.
- **protectedAuthorityCheck:** The post-code `so` tree kept production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, request-bound evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion `99cb895f`, canonical learning `b809c69d`, and mandatory learning contract `87712ea9` unchanged. Registered/semantically eligible generations remain 0/0; human-approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage and final candidate remain 0. Distinct unsuperseded eligible environments, current human-approved objective, executable request binding, complete typed coverage, independent review and separate nonautomatic human promotion remain mandatory.

## Next safe target

Make the new pinned-import Negative Test invocations non-removable through the existing read-only reconcile workflow AST reachability guard. Then audit remaining independently reachable negative-harness importers.
