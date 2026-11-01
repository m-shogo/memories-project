# Supplemental OPS learning — rollback from the same validated pinned JSON snapshot (2026-11-02)

Append-only learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion gates.

## Material failure

- **symptom:** The drill generation binding reconciler still captured `original_contract_text = CONTRACT.read_text(...)` from a mutable pathname separately from the newly pinned strict JSON `load(CONTRACT)`. Its rollback source could therefore differ from the validated authority, or follow a substituted path.
- **evidence:** At HEAD `9086bc85`, `_reconcile()` read original text before calling `load(CONTRACT)`; only `load` had no-follow directory-FD and source identity checks. This was a verified source-level TOCTOU and rollback-snapshot consistency gap; no production corruption was observed.
- **rootCauseOrUnknown:** Verified two independent reads of the same planning contract, one of which bypassed the pinned JSON reader. Real-world exploitation unknown.
- **failedApproach:** Assuming hardening the parsed JSON read alone also protected the earlier raw rollback snapshot.
- **correction:** [`8022d882`](https://github.com/m-shogo/memories-project/commit/8022d882bf34455a08b2e9bf6a3e691cb60202bb) makes the reconciler's strict `load(CONTRACT, include_raw=True)` return the validated parsed object and the exact source bytes from one pinned FD snapshot. Rollback text derives from those same UTF-8 bytes, not a second pathname read. The option requires an exact boolean.
- **recurrenceGuard:** The existing CI-reached binding reconcile negative suite now verifies that a noncanonical-whitespace valid JSON source returns both the expected parsed object and its byte-identical original rollback snapshot, and rejects a nonboolean raw-snapshot option. Existing isolated transactional rollback and strict JSON negatives remain active.
- **retryCondition:** Revisit only if rollback byte-preservation semantics, JSON parser/source coupling, pinned path reader or exact-source CI changes. Do not retry unchanged MinIO HTTP 401, workflow write permissions, or absent human/external production evidence.

## Material success

- **outcome:** The reconciler's validation and rollback snapshots now originate from one pinned authority read, preserving exact original bytes without a separate unguarded pathname open.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41341832005](https://github.com/m-shogo/memories-project/actions/runs/41341832005) completed **SUCCESS** at code HEAD `8022d882`. Job logs report strict JSON negative suites and `Drill generation eligibility binding reconcile negative suite PASS`, with `production decision: NO_GO`. The new exact-byte and invalid-option controls are part of that executed suite. This is not a non-skipped Go test or real restore.
- **whySafe:** Only the reconciler's read-only snapshot derivation and an existing disposable-fixture negative suite changed. No production, generation, objective, reviewed request, recovery evidence, typed non-resurrection, independent review, credential, traffic, workflow permission or human promotion authority changed.
- **reusableMechanism:** For transactional rollback, derive original bytes and parsed authority from a single validated pinned read; never independently reopen a mutable path to capture the rollback baseline.
- **protectedAuthorityCheck:** Ten protected blob SHAs remained unchanged after code commit: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. Registered and semantically eligible unsuperseded generations remain distinct, a current human-approved objective is mandatory, reviewed requests are planning-only, recovery evidence must bind to a current executable reviewed request, complete typed eight-domain non-resurrection and independent review remain required, and human promotion remains separate/nonautomatic.

## Next safe target

Add isolated after-acquisition parent-path substitution and raw-FD close-double-fault negative proof to both pinned JSON readers. Continue independent Go test execution-path audit without weakening workflow permissions or OPS-P0-007.
