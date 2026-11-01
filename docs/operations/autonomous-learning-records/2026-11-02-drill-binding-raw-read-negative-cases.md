# Supplemental OPS learning — pinned raw-read negative cases (2026-11-02)

Append-only operational learning subordinate to the canonical learning authority and mandatory contract. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion gates.

## Material failure

- **symptom:** The new owned-FD bounded `os.read` loop had no independent negative proof for premature EOF or non-bytes return values, and no positive proof that multiple valid short reads reassemble the complete source.
- **evidence:** At starting HEAD `84b3e959`, both importers checked exact bytes and final size, but the existing suite only tested a normal positive import and mid-read mutation. No actual malformed raw read was observed in production.
- **rootCauseOrUnknown:** Verified synthetic proof gap in the new reader's return-type, loop and early-EOF branches; real-world occurrence unknown.
- **failedApproach:** Treating a successful ordinary module import as proof of all bounded loop outcomes.
- **correction:** [`6664d482`](https://github.com/m-shogo/memories-project/commit/6664d482f15c482e5d62563408e6baf3c4be5b99) adds an isolated two-byte-at-a-time positive control and negative cases for premature `b""` EOF and `None` instead of bytes, executed against both importers.
- **recurrenceGuard:** Existing CI-reached binding reconcile negative suite now proves short reads produce a complete compiled module and invalid/early reads fail closed with exact diagnostics, preserving all prior symlink, hardlink, size, mid-read, close and double-fault tests.
- **retryCondition:** Revisit on changes to the source read loop, type/length requirements, or exact-source CI. Do not retry unchanged MinIO HTTP 401, workflow permissions, missing external evidence or human promotion blockers.

## Material success

- **outcome:** The raw source loop now has executable positive and negative coverage for fragmented reads, premature EOF and non-bytes results in both independent importers.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41336657434](https://github.com/m-shogo/memories-project/actions/runs/41336657434) completed **SUCCESS** on code HEAD `6664d482`. Job logs explicitly report both importer `PASS pinned module import` lines with `fragmented, EOF, nonbytes`, `Drill generation eligibility binding reconcile negative suite PASS`, and `production decision: NO_GO`. This is CI validator evidence, not a non-skipped Go test or real production restore.
- **whySafe:** Only the existing synthetic negative suite changed. All modified inputs and execution markers are disposable temporary fixtures; no production authority, workflow, credential or traffic was changed.
- **reusableMechanism:** Pair a bounded raw-byte loop with a fragmented-read positive control and exact-diagnostic negatives for invalid result type and premature EOF.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. Registered and semantically eligible generations remain separate; preflight requires unsuperseded eligible generations from distinct environments and a current human-approved recovery objective; reviewed requests are planning-only; generation recovery evidence requires a current executable reviewed request; complete typed eight-domain non-resurrection coverage, independent review and human promotion remain separate non-automatic gates.

## Next safe target

Audit the separate planning JSON authority reader's path-acquisition boundary without weakening its strict JSON semantics. Reuse pinned-source checks where appropriate; keep any tests isolated and preserve production NO_GO. Continue checking for an approved pre-MinIO Focused Go Test path.
