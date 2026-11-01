# Supplemental OPS learning — bounded current promotion review bytes and JSON (2026-11-01)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure 1 — unbounded current promotion review payload and private parsing errors

- **symptom:** The promotion source-order validator read current review bytes and JSON without a byte cap and included raw file/JSON exception details in failures. An oversized or malformed current review could consume excess memory or disclose unnecessary diagnostic text before immutable comparison.
- **evidence:** At source blob `d0c6f0eb`, `validate_row` used `path.read_bytes()` and `load_json` used unbounded `path.read_text()`; both included raw exception details. The newly bounded committed creation blob did not bound the current payload. No actual oversized production review or secret disclosure was observed.
- **rootCauseOrUnknown:** Verified separate unbounded current-file and JSON readers. Actual adversarial control or exposure is unknown.
- **failedApproach:** Assuming the committed-blob 1 MiB size preflight also bounded independent current-file reads and JSON parsing.
- **correction:** [`d1c2d104`](https://github.com/m-shogo/memories-project/commit/d1c2d1043234452d68f0d7f17e936d7dc1d49087) adds a shared 1 MiB + 1 sentinel bounded byte reader for current review files and JSON, rejects obvious symlink/nonfile paths, requires bytes transport and uses fixed private failure classes. The existing current-vs-committed exact-byte comparison and human review chronology remain unchanged.
- **recurrenceGuard:** The existing CI-invoked `--self-test` exercises real bounded bytes and JSON positives, oversized input, invalid UTF-8, malformed JSON, symlink, directory and restored-positive controls, checking source fixtures remain unchanged.
- **retryCondition:** Revisit on reviewed review-size/encoding policy changes, exact-source regression or new file-descriptor race evidence. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permission or human production evidence blockers.

## Material failure 2 — double-escaped invalid UTF-8 negative fixture

- **symptom:** The first generated invalid UTF-8 negative used source `b"\\\\xff"` rather than the intended `b"\\xff"`, so it represented literal backslash characters rather than the invalid byte `0xff`.
- **evidence:** After code commit `d1c2d104`, the exact source inspection showed the double backslash. The prewrite `invalidFixture` check was false, but the initial change was published before that check was enforced. The first source CI was SUCCESS, which did not prove the intended invalid-UTF-8 path because malformed JSON could independently reject the fixture.
- **rootCauseOrUnknown:** Verified JS-to-Python source escaping mismatch, a known failure class in prior learning. The original test's diagnostic path was not a valid proof of UTF-8 rejection.
- **failedApproach:** Treating a malformed JSON rejection as sufficient for the intended invalid UTF-8 negative and allowing an advisory prewrite fixture check to pass into publication.
- **correction:** [`38c1df66`](https://github.com/m-shogo/memories-project/commit/38c1df66cbd4d194e10a1fa5dc142a9020b0571f) re-read latest `so` and target, replaced the exact double-backslash source literal with a single-backslash byte escape, and verified exact replacement multiplicity before writing.
- **recurrenceGuard:** Source-escape prewrite checks must be mandatory abort conditions, not merely logged diagnostics. Use exact source-byte inspection and a single-backslash Python bytes literal for malformed UTF-8 fixtures; never reuse the known double-escaped construction.
- **retryCondition:** Revisit only on fixture generation changes or a new exact-source regression; no unchanged broken fixture retry.

## Material success — corrected exact-source CI

- **outcome:** Current promotion review bytes and JSON are bounded and fail-closed, with a correctly encoded invalid-UTF-8 negative.
- **evidence:** [Backup Restore Promotion Review Source Order #41312201939](https://github.com/m-shogo/memories-project/actions/runs/41312201939) and [Backup Restore Promotion Review #41312201842](https://github.com/m-shogo/memories-project/actions/runs/41312201842) completed **SUCCESS** at corrected exact code HEAD `38c1df66cbd4d194e10a1fa5dc142a9020b0571f`. The prior code HEAD `d1c2d104` also had CI SUCCESS but did not establish the intended invalid-UTF8 negative. Neither is production readiness.
- **whySafe:** Only one read-only Python validator changed. All oversized, malformed and symlink inputs are disposable test fixtures; no production review, generation, objective, request, recovery evidence, credential, traffic, readiness or promotion was created.
- **reusableMechanism:** Bound both committed and current evidence reads, suppress raw parsing errors, and verify the actual negative fixture's bytes rather than trusting a syntactically valid but semantically wrong test.
- **protectedAuthorityCheck:** Ten protected blobs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, approved objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion registry `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`. Preflight requires unsuperseded semantically eligible generations from distinct environments and a current explicitly human-approved recovery objective; reviewed requests are planning-only; new evidence remains bound to a current executable reviewed request; final candidates require complete typed eight-domain coverage and independent review; human promotion remains separate/nonautomatic.

## Next safe target

Audit current-file open/read identity and symlink race handling with a bounded FD-based negative; do not conflate this with the still-unverified real pre-MinIO Focused Go Test execution path.
