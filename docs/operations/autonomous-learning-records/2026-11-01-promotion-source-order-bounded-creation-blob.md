# Supplemental OPS learning — bounded human promotion creation blob transport (2026-11-01)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — unbounded human promotion review creation blob read

- **symptom:** The promotion source-order `creation_blob` called `git show` without checking the committed object's size, bounded timeout, output type or exact byte count, and embedded raw Git stderr in errors. A pathological or oversized committed review blob could consume unbounded resources or expose private diagnostics.
- **evidence:** At source blob `771917b9`, `creation_blob` used one unbounded `git show` subprocess with `stdout/stderr=PIPE`, no timeout, no exact byte check and a diagnostic interpolating `completed.stderr.decode(...)`. No actual leak, hang or forged review was observed.
- **rootCauseOrUnknown:** Verified missing committed-size preflight and subprocess transport validation in this separate promotion review reader. Actual adversarial input or exploitation is unknown.
- **failedApproach:** Trusting downstream current-vs-committed byte comparison as a substitute for a bounded, private, exact-byte Git object read.
- **correction:** [`2950be65`](https://github.com/m-shogo/memories-project/commit/2950be65851207bdd48e905da1862ebe204ec0ee) adds a strict `git cat-file -s` size preflight, a 1 MiB maximum, a 20-second timeout for size and content calls, stderr suppression, exact integer exit and output-type checks, and exact returned-byte count matching the committed size. Existing trusted Git executable, sanitized environment, immutable review comparison and source-order chronology remain intact.
- **recurrenceGuard:** The existing CI-invoked `--self-test` now executes the actual `creation_blob` consumer with a positive and 12 zero/oversized/malformed/bool/nonzero/timeout/unavailable/byte-mismatch/wrong-type negatives. Its fake Git checks both exact commands, environment, private stderr, 20-second timeout, size-first phase ordering, fixed nonprivate diagnostics and 19-call multiplicity.
- **retryCondition:** Revisit on reviewed promotion payload size/transport policy changes, Git runner changes or exact-source CI regression. Do not retry unchanged external MinIO HTTP 401, workflow-write permission or human production evidence blockers.

## Material success — exact-source promotion CI

- **outcome:** The committed creation blob is now size-preflighted, bounded and byte-exact before immutable review comparison.
- **evidence:** [Backup Restore Promotion Review Source Order #41312077536](https://github.com/m-shogo/memories-project/actions/runs/41312077536) and [Backup Restore Promotion Review #41312077500](https://github.com/m-shogo/memories-project/actions/runs/41312077500) completed **SUCCESS** at exact code HEAD `2950be65851207bdd48e905da1862ebe204ec0ee`. These are validator CI outcomes, not human approval or production readiness.
- **whySafe:** Only one read-only Python validator changed. The test uses synthetic blobs and mocked subprocess responses; it creates no reviews, generations, objectives, recovery evidence, credentials, traffic, readiness or promotion.
- **reusableMechanism:** Preflight committed object size before reading content, enforce typed bounded subprocess transport and exact byte count, then compare to the current review bytes. Use CI-reachable actual-reader positive/negative controls rather than prose-only assurance.
- **protectedAuthorityCheck:** Ten protected blobs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion registry `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`. Preflight requires unsuperseded semantically eligible generations from distinct environments and a current explicitly human-approved objective; reviewed requests are planning-only; new recovery evidence remains current-executable-request-bound; final candidates need complete typed eight-domain non-resurrection and independent review; human promotion is separate/nonautomatic.

## Next safe target

Bound the current review payload read and JSON parsing before comparing against the now-bounded creation blob; audit the same path for symlink/race and private diagnostic exposure. The real pre-MinIO Focused Go Test execution path remains independently unverified.
