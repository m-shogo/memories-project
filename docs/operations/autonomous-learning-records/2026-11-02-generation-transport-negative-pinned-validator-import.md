# Supplemental OPS learning — generation transport negative pins validator source (2026-11-02)

Append-only history subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, human-approved objective, reviewed request, request-bound evidence, typed eight-domain coverage, independent review, final candidate, or human-promotion evidence.

## Material failure

- **symptom:** The generation-evidence transport negative harness admitted a canonical validator path but reopened it with `spec.loader.exec_module` after checking the pathname.
- **evidence:** At prior `so` HEAD `3827d8668d7c977ea62095307aa34881cdf22185`, `scripts/validate-memory-os-backup-restore-generation-evidence-transport-negative.py::load_validator` checked `is_file`, `is_symlink` and `resolve`, then delegated the executable source reopen to `SourceFileLoader`. This was a verified source-level TOCTOU gap, not an observed malicious execution.
- **rootCauseOrUnknown:** Verified independent pathname reopening after validation. Real-world exploitation is unknown.
- **failedApproach:** Assuming a checked canonical path or import spec alone establishes immutable executable source authority.
- **correction:** [`a1e36e47`](https://github.com/m-shogo/memories-project/commit/a1e36e47168302c1d8b89f60d488049100869059) pins bounded validator bytes using owned no-follow parent/leaf descriptors, rejects writable or hardlinked source and unsafe parents, checks pre/post inode and parent identity, and executes only the captured source snapshot.
- **recurrenceGuard:** An existing CI-reachable synthetic negative proves a writable source and hardlink are rejected and a real after-capture parent symlink swap cannot execute a redirected canary. Source-byte identity and cleanup remain checked. The read-only generation evidence reconcile-negative workflow runs the transport negative.
- **retryCondition:** Revisit only if the validator import boundary, file metadata, descriptor ownership, source bounds, or read-only workflow trigger changes. Do not retry unchanged publisher-coupled writer changes, Quay MinIO HTTP 401, canonical large-blob transport or absent human evidence.

## Material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41393558165](https://github.com/m-shogo/memories-project/actions/runs/41393558165) completed **SUCCESS** at `a1e36e47168302c1d8b89f60d488049100869059`; job `125109922286` logged `PASS: generation transport validator importer pinned against writable/hardlink/parent swap`, `Memory OS generation-evidence execution transport negative PASS`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`. [Backup Restore Admission Chain #41393558199](https://github.com/m-shogo/memories-project/actions/runs/41393558199) also completed SUCCESS.
- **evidence:** Observed exact-source workflow conclusions and targeted job logs. These are synthetic CI observations, not production recovery or promotion evidence.
- **whySafe:** Only a read-only negative harness changed, with independently reachable exact-source CI; the production-capable Generation Evidence publisher's push paths exclude the modified script. Synthetic fixture changes occur in disposable directories and canary bytes are asserted unchanged.
- **reusableMechanism:** Use allowlisted source identity, owned no-follow descriptor chain, bounded bytes and stable inode/parent checks; compile and execute pinned bytes instead of re-opening a path. Exercise an after-capture parent-swap negative.
- **protectedAuthorityCheck:** Post-code `so` tree preserved production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, approved objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion review `99cb895f`, canonical learning `b809c69d` and learning contract `87712ea9`. Registered and semantically eligible generations remain 0/0; human-approved current objective, executable reviewed request, request-bound recovery, complete typed eight-domain coverage and final candidate remain 0. Preflight and final candidate require all original gates; human production promotion is separate and nonautomatic.

## Next safe target

Inspect the distinct generation-binding transport negative harness importer, which still uses pathname-reopening module execution and has an independent read-only exact-source CI trigger without publisher coupling.
