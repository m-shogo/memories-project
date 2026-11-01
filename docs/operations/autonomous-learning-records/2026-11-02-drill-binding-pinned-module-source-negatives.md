# Supplemental OPS learning — pinned module source negatives (2026-11-02)

Append-only operational learning under the canonical learning policy and mandatory contract. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** The pinned module importers had runtime guards for multi-link, oversized, and mid-read changed module source, but the CI-reached negative suite exercised only leaf/parent symlink swaps and descriptor cleanup faults. The three guards could regress without a dedicated executable failure case.
- **evidence:** At starting HEAD `b695afb6`, both importers checked `st_nlink == 1`, `st_size <= 1 MiB`, and stable pre/post `fstat`/leaf identity. The negative suite did not create a hardlink, oversized source or mutate a module file after its first `fstat`. This was a negative-proof gap, not observed production corruption.
- **rootCauseOrUnknown:** Verified absence of independent negative fixtures for three existing runtime checks; no actual malicious repository mutation was observed.
- **failedApproach:** Assuming a present fail-closed runtime check and successful symlink tests prove all other pinned-source invariants.
- **correction:** [`f7df842d`](https://github.com/m-shogo/memories-project/commit/f7df842d24648998f0bf16ccd9804471e25d8668) extends the existing isolated CI-reached negative suite with hardlinked module source, oversized source, and an injected in-place file append between descriptor `fstat` and stream read.
- **recurrenceGuard:** The shared fixture executes each of the three negatives independently for both importer scripts, requires the correct fail-closed diagnostic, retains the benign positive import and symlink/cleanup controls, and verifies no external code-execution marker is written.
- **retryCondition:** Revisit if the pinned module source checks, imported source size budget, filesystem semantics, or CI reachability change. Do not retry unchanged MinIO HTTP 401, workflow permissions, external evidence or human promotion blockers.

## Material success

- **outcome:** The existing runtime source-invariant guards now have executable negative proof in both independent importers.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41336426886](https://github.com/m-shogo/memories-project/actions/runs/41336426886) completed **SUCCESS** at code HEAD `f7df842d`. Job logs show both importer `PASS pinned module import` lines explicitly covering hardlink, size and mid-read cases, followed by `Drill generation eligibility binding reconcile negative suite PASS` and `production decision: NO_GO`. These are isolated validator results, not production evidence.
- **whySafe:** Only the existing read-only synthetic negative suite changed. The hardlink, oversized source and mutation were created inside a disposable temporary directory, not a canonical registry or production evidence path.
- **reusableMechanism:** For a descriptor-pinned executable source reader, pair each separate metadata guard with a negative case that exercises its precise rejection boundary and a positive control.
- **protectedAuthorityCheck:** The protected ten Git blob SHAs remain unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, Production Status `b55ee4ad` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. Registered and semantically eligible generations remain separate; preflight still requires unsuperseded eligible generations from distinct environments plus a human-approved current objective; reviewed requests are planning-only, request-bound recovery evidence and complete typed eight-domain coverage plus independent review remain mandatory; human promotion remains separate and non-automatic.

## Next safe target

Audit pinned-module stream-close behavior separately from raw descriptor-close behavior, preserving the primary error on ordinary stream-close faults. Check the existing source-negative and CI entrypoint topology before adding tests. Independently continue seeking a permitted non-skipped Focused Go Test path before MinIO.
