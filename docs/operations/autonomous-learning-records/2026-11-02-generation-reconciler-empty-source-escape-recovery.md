# Supplemental OPS learning — empty reconciler source and escaped-newline fixture recovery (2026-11-02)

Append-only history under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This record, diagnostic fixture and synthetic CI are **never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, human-approved recovery objective, executable reviewed request, request-bound evidence, typed eight-domain coverage, independent review, final candidate or human production-promotion authority.

## Material failure — missing empty-source rejection

- **symptom:** The independently read-only generation-evidence reconciler negative harness accepted a zero-byte reconciler source at its pinned reader's metadata boundary.
- **evidence:** At `so` HEAD `ccd068bc2e56807887a7ede23398ea006294abbd`, `pinned_reconciler_source` required `0 <= before.st_size <= MAX_RECONCILER_SOURCE_BYTES`. This would allow an empty module to be compiled/executed as an import. No production incident or actual corrupted module observed.
- **rootCauseOrUnknown:** Verified non-strict lower bound for a mandatory executable source; actual exploitation unknown.
- **failedApproach:** Treating a zero-byte executable source as a valid bounded source merely because its length was not negative.
- **correction:** [`63b2f901`](https://github.com/m-shogo/memories-project/commit/63b2f9019f41f749aee1ac18421a9805b9aaf05a) requires `0 < before.st_size` and adds a disposable zero-byte source negative with exact `reconciler source type/size unsafe` rejection and a restored positive control.
- **recurrenceGuard:** The empty-source negative must fail before compile/import, and a fresh positive import must succeed after restoring the reviewed marker source.
- **retryCondition:** Revisit if pinned source size semantics or exact-source read-only CI reachability changes.

## Material failure — escaped newline in the new fixture

- **symptom:** The initial empty-source negative fixture restored literal backslash-n bytes rather than a newline, producing a `SyntaxError` in the post-restoration positive import.
- **evidence:** [Generation Evidence Reconcile Negative #41399660864](https://github.com/m-shogo/memories-project/actions/runs/41399660864) on `63b2f901` failed with `SyntaxError: unexpected character after line continuation character` at the fixture marker. [Backup Restore Admission Chain #41399660813](https://github.com/m-shogo/memories-project/actions/runs/41399660813) also FAILED on that source with its raw validator output suppressed; the independent negative CI exposed the exact cause. The workflow committed a redacted diagnostic at [`fabc04dd`](https://github.com/m-shogo/memories-project/commit/fabc04dd7a5ed59a6eeddd9c3cec2e62c4903ca4) with `productionEvidence=false` and `productionReady=false`. No production evidence was created.
- **rootCauseOrUnknown:** Verified double-escaped newline in the generated Python fixture, not a verified reconciler source reader bypass. Admission Chain's private raw log was unavailable, so its exact internal failing assertion is not independently known.
- **failedApproach:** Generating a Python string literal through nested escape layers without checking the resulting fixture bytes; a previously recorded class of fixture failure was inadvertently repeated.
- **correction:** [`23b4d8c3`](https://github.com/m-shogo/memories-project/commit/23b4d8c3c8b5b0daf4a4510e68dc8db4736c318c) corrected the immediate literal. [`e1a42e7b`](https://github.com/m-shogo/memories-project/commit/e1a42e7b81d0503a58ccf6b5a4903e894d8dd4d1) replaced escape-sensitive newline text with `chr(10)`, reusing the established fixture-safe pattern.
- **recurrenceGuard:** Use `chr(10)` for synthetic Python source restoration; require the actual post-restoration `load_reconciler().SOURCE_MARKER == "reviewed"` positive control, plus the exact zero-byte rejection, in the read-only CI. Never interpret a private Admission Chain diagnostic as production evidence.
- **retryCondition:** Revisit if fixture source serialization, nested escaping, or exact-source CI changes. Do not repeat unchanged canonical learning 4.17 MB upload, Quay MinIO 401, publisher-coupled writer edits or absent human evidence.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41400006783](https://github.com/m-shogo/memories-project/actions/runs/41400006783) completed **SUCCESS** on exact HEAD `23b4d8c3c8b5b0daf4a4510e68dc8db4736c318c`; job `125129584853` logged `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. [Generation Evidence Reconcile Negative #41400054755](https://github.com/m-shogo/memories-project/actions/runs/41400054755) completed **SUCCESS** on exact HEAD `e1a42e7b81d0503a58ccf6b5a4903e894d8dd4d1`; job `125129738158` logged the same suite PASS and `NO_GO`. Both jobs logged the pinned reconciler importer positive/parent-swap control.
- **evidence:** GitHub Actions exact-source conclusions, job logs, and the three code diffs. These are synthetic safety tests only; the failing Admission Chain run is not retroactively SUCCESS.
- **whySafe:** Only the independently read-only reconciler negative harness changed; the production publisher's trigger excludes it. The workflow-generated failure diagnostic is explicitly non-production, and the protected authorities remain unchanged.
- **reusableMechanism:** Enforce nonempty bounded executable source, test an actual empty file, restore reviewed bytes with escape-proof `chr(10)`, and verify a positive import after the negative.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs unchanged: Production Status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. Registered/semantically eligible generations `0/0`; approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage and final candidate all `0`. Independent review and separate human production promotion remain mandatory.

## Next safe target

Close the reconciler negative harness's raw `OSError` source-read disclosure boundary with an exact private-error normalization negative, while retaining the existing pinned parent/source identity checks.
