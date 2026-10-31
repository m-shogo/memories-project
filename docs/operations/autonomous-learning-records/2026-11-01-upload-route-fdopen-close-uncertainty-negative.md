# Supplemental OPS learning — fdopen close uncertainty (2026-11-01)

Append-only execution learning under `contracts/operations/autonomous-learning-system.json`. **Never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion evidence.

## Material failure class — unproven close ordering

- **symptom:** During failed fdopen acquisition, `os.close(descriptor)` can raise before or after consuming the staged FD. A later cleanup retry could close an independent owner of the recycled numeric descriptor, or mask the original fdopen failure. This was a coverage gap and source-level risk, **not** an observed production incident.
- **evidence:** The earlier `69662b18` implementation already preserved the original exception, added a bounded `fdopen stage descriptor close status unknown` note and avoided retry. Before this commit there was no direct two-ordering negative for that particular close. [`e4c02a64`](https://github.com/m-shogo/memories-project/commit/e4c02a64a4f983a8abb5d01622b3643a899116c6) adds `before-fdopen-close` and `after-fdopen-close` real-filesystem faults with a recycled FD and independent canary in the latter case.
- **rootCauseOrUnknown:** Verified test coverage gap. A raising close does not prove whether the syscall consumed the FD; actual ownership is explicitly unknown without independent observation.
- **failedApproach:** Treating a failed close as proof of retained ownership, retrying the same number, or letting the secondary close failure replace the primary fdopen exception.
- **correction:** Keep the existing single bounded close and original-error preservation; prove both effect orderings. A pre-effect fault may leave an unlinked stage FD open, which is reclaimed **only by the isolated test** after restoring the fault; no leak-free claim is made.
- **recurrenceGuard:** The existing pre-MinIO CI entrypoint AST-binds the live two-case loop, actual `module.os.close = fail_fdopen_close` injection and recycled canary assertion. Independent source-negative mutations reject removal of the injection or one ordering.
- **retryCondition:** Revalidate after changes to fdopen ownership, staged identity, close exception semantics, cleanup, or CI reachability. Do not retry an ambiguously consumed descriptor without independently proven ownership; the fstat/close window is not atomic FD CAS.

## Material safe success — exact-source validation

- **outcome:** Both isolated close faults preserve the primary fdopen error and bounded uncertainty note; neither changes original or independent canary bytes, and neither leaves a staged pathname.
- **evidence:** [Autonomous Learning Guard #41241075376](https://github.com/m-shogo/memories-project/actions/runs/41241075376) **SUCCESS** on exact `e4c02a64` (601 canonical fail-closed negatives, 39 supplemental history fixtures, 52 workflows / 63 direct Python commands / 204 source-negative fixtures, 195 fanout synthetics, 1,186 helper-ancestor mutations, append-only and read-only). [Operability Contracts #41241075282](https://github.com/m-shogo/memories-project/actions/runs/41241075282) also **SUCCESS**.
- **whySafe:** Only a disposable test and the existing read-only CI entrypoint changed. No workflow YAML, runtime reconciler, production evidence, recovery, credential, traffic or promotion authority was modified.
- **reusableMechanism:** Inject both pre-/post-effect close faults on the owned descriptor, recycle its number to a separate canary, preserve the primary exception and uncertainty note, and reclaim only verified test-owned FDs after restoring the fault.
- **protectedAuthorityCheck:** All ten protected blob SHAs stayed unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 `dbaa36b0`, generations `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`. The earlier supplemental learning file was also present during the exact-source CI append-only check.

## Strict boundary, blockers, next safe target

`productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`, registered/semantically eligible generations **0/0**. Preflight requires unsuperseded semantically eligible generations from distinct environments plus a current explicitly human-approved recovery objective. Reviewed drill requests are planning-only; new generation evidence requires a current executable reviewed request; final candidates need complete typed eight-domain non-resurrection coverage and independent review; human promotion is separate/nonautomatic. No such evidence or approval was fabricated.

[Upload Route #41241075261](https://github.com/m-shogo/memories-project/actions/runs/41241075261) FAILED at the unchanged MinIO startup step before focused Go/HTTP tests. Workflow-write permission, supplemental-learning-only Push/PR CI trigger gap and independent pre-MinIO Go execution remain scoped blockers with unchanged retry conditions. This learning-only commit has no separately observed exact-source CI success.

**Next safe target:** Inject a failed fdopen exception-path `fstat` probe while the stage FD remains owned; require primary-error preservation, bounded unknown-ownership note, no unverified close and test-only reclamation. Avoid atomic FD CAS claims.
