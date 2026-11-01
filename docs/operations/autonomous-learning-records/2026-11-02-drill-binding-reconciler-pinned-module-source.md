# Supplemental OPS learning — pinned reconciler module source (2026-11-02)

Append-only learning under the canonical autonomous-learning authority and mandatory contract. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion evidence.

## Material failure

- **symptom:** The drill-generation binding reconciler still re-opened Python module pathnames through `SourceFileLoader.exec_module` after pre-import canonical path validation, even after the independent validator's import boundary was hardened.
- **evidence:** At starting HEAD `be5b502d`, the reconciler `load_module` used `require_exact_repo_file` followed by `spec.loader.exec_module`. The previously added isolated leaf/parent symlink swap negatives applied only to the validator, leaving the reconciler import boundary untested. No actual malicious repository swap was observed.
- **rootCauseOrUnknown:** Verified source-level duplicated loader path with an independent pathname reopening boundary; real-world exploit unknown.
- **failedApproach:** Treating a validated module pathname or the separate validator's new pinned import as sufficient protection for the reconciler's own import.
- **correction:** [`e7d8e4e6`](https://github.com/m-shogo/memories-project/commit/e7d8e4e64aa1165e2f45095827b21b53b3b0e36e) applies the same bounded pinned-descriptor source acquisition, no-follow ancestor/leaf opening, stable file metadata check and compiled snapshot execution to the reconciler.
- **recurrenceGuard:** The existing CI-reached binding reconcile negative suite now reuses the exact positive/leaf-swap/parent-swap fixture against both independent import paths, verifying that neither executes an external marker.
- **retryCondition:** Revisit only if either canonical module loader changes, the imported module inventory or Python platform semantics change, or exact-source CI fails. Do not repeat unchanged external MinIO, workflow-permission, evidence or human-promotion blockers.

## Material success

- **outcome:** Both binding validator and reconciler reject the tested post-check symlink swaps while preserving a positive module import.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41336128797](https://github.com/m-shogo/memories-project/actions/runs/41336128797) completed **SUCCESS** on code HEAD `e7d8e4e6`. Job logs explicitly show both `PASS pinned module import` lines and `Drill generation eligibility binding reconcile negative suite PASS`. This is validator/CI evidence only, not an actual recovery drill or production readiness.
- **whySafe:** Only the reconciler and the existing read-only negative suite changed in the code commit. The test uses isolated temporary paths and never modifies a protected production/recovery registry, workflow permission, credential or traffic.
- **reusableMechanism:** Reuse the same source-pinning negative control across each independent execution boundary rather than assuming one protected importer covers all consumers.
- **protectedAuthorityCheck:** Git comparison from `c5de256a` through `e7d8e4e6` includes only the two importers, the existing negative suite, and the earlier append-only learning record. All ten protected authority blob SHAs remain unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, approved objective registry `f4d74f33`, reviewed drill request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, and promotion review registry `99cb895f`. Registered and semantically preflight-eligible generations are distinct; preflight requires unsuperseded eligible generations from distinct environments and explicitly human-approved current objective; reviewed drill requests are planning-only; recovery evidence requires a current executable reviewed request; complete typed eight-domain coverage and independent review precede any final candidate; human promotion is separate/non-automatic.

## Next safe target

Audit descriptor cleanup failures in the two pinned module importers: an unsuccessful close must not be silently treated as a fully safe import, and the original failure must remain authoritative when cleanup also fails. Extend the shared isolated negative suite and preserve the protected-authority boundary. Continue searching for a verified, authorized non-skipped pre-MinIO Focused Go Test path.
