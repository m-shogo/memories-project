# Supplemental OPS learning — direct owned-FD module source read (2026-11-02)

Append-only execution learning under the canonical autonomous-learning policy and contract. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion evidence.

## Material failure

- **symptom:** Both newly pinned module importers duplicated the owned source descriptor and wrapped it in a separately closing `fdopen` stream. Stream-close faults could create a second uncertain ownership/exception boundary, including masking a primary read failure, even though raw descriptor cleanup was guarded.
- **evidence:** At starting HEAD `14f441bb`, both `load_module` helpers used `with os.fdopen(os.dup(source_fd), "rb") as stream`. Existing canonical [stream-close learning](2026-11-01-canonical-stream-close-fault-preservation.md) had already shown that context-manager close faults can replace an earlier read/validation exception. No actual module stream-close fault or production compromise was observed.
- **rootCauseOrUnknown:** Verified unnecessary duplicate descriptor and stream ownership boundary in a bounded regular-file reader; real-world occurrence unknown.
- **failedApproach:** Relying on the outer raw-descriptor cleanup guard to cover a distinct inner `with stream` close boundary.
- **correction:** [`c0e47685`](https://github.com/m-shogo/memories-project/commit/c0e476853c8d6ad30ed1a2bc2378c8773d361eb2) removes the duplicate stream entirely. Both importers read directly from the already-owned `source_fd` with a bounded `os.read` loop, require exact bytes results, and retain the pre/post inode, size and timestamp identity checks. Raw descriptor cleanup remains single-attempt and primary-error preserving.
- **recurrenceGuard:** The existing CI-reached binding negative suite now injects a real in-place file mutation through `os.read`, not `os.fdopen`, and checks both importers reject it before executing any external marker. Existing positive, symlink, hardlink, size and close-double-fault cases remain active.
- **retryCondition:** Revisit if bounded raw read semantics, descriptor ownership, module source verification, or exact-source CI changes. Do not retry unchanged MinIO HTTP 401, workflow permissions, external production evidence or human promotion blockers.

## Material success

- **outcome:** Both pinned module readers now have one owned source descriptor rather than an extra non-owning/duplicated stream cleanup boundary.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41336551974](https://github.com/m-shogo/memories-project/actions/runs/41336551974) completed **SUCCESS** at code HEAD `c0e47685`. Logs confirm the existing synthetic module positive and negative suite for both independent importers and `production decision: NO_GO`. This does not establish actual production restore, Go test or readiness.
- **whySafe:** Only two read-only module import helpers and their existing synthetic negative suite changed. No protected registry, production traffic, credential, workflow permission or promotion authority was touched.
- **reusableMechanism:** Prefer a bounded read loop on the already-pinned owned descriptor to introducing a second stream close/ownership boundary. Keep exact bytes-type, source-size and metadata checks and a real mid-read mutation negative.
- **protectedAuthorityCheck:** All ten protected blob SHAs remain unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. Registered and semantically eligible generations remain distinct; preflight requires unsuperseded eligible generations from distinct environments plus a current human-approved objective; reviewed requests remain planning-only; recovery evidence requires a current executable reviewed request; typed eight-domain coverage, independent review and separate human promotion remain mandatory.

## Next safe target

Exercise the raw-read loop with short valid reads, premature EOF and non-bytes return values for both importers; ensure the exact-source CI still passes without changing any protected authority. Independently audit the approved Go test execution path before MinIO.
