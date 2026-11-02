# Supplemental OPS learning — generation transaction pinned importer invalid acquired FD negatives (2026-11-02)

Append-only learning governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, human-approved recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human production-promotion evidence.

## Material failure / regression coverage gap

- **symptom:** The pinned transaction writer importer validated exact integer/nonnegative acquired descriptors, but its read-only negative harness had no malformed `os.open` return cases at ROOT, ancestor or leaf acquisition.
- **evidence:** At `so` HEAD `a8216bf1e5acd90fc85b4b85263c7cd534dac119`, `pinned_writer_source` already checked `type(fd) is int and fd >= 0` before each owned append, while `prove_pinned_writer_import` lacked explicit invalid-acquisition/cleanup tests. Prior `2026-11-02-drill-binding-module-invalid-acquired-fd.md` recorded a real CI fixture failure caused by confusing absolute path depth with actual acquisition count. No real malformed CPython syscall return or production incident was observed.
- **rootCauseOrUnknown:** Verified missing regression coverage in this independent transaction importer. Real-world malformed descriptor returns or malicious injection are unknown.
- **failedApproach:** Assuming successful `os.open` calls or existing source checks alone prove ownership; reusing absolute pathname depth as an injection ordinal is explicitly prohibited by prior learning.
- **correction:** Commit [`56abcc70`](https://github.com/m-shogo/memories-project/commit/56abcc70ec8202f7a920bc9861850c274876de80) adds 12 synthetic malformed FD cases (`None`, `True`, `-1`, `"7"`) across exactly three acquisitions (ROOT, `scripts` ancestor, leaf).
- **recurrenceGuard:** The read-only suite asserts the injection was reached at the actual `os.open` ordinal, demands the domain `descriptor invalid` failure, and checks that only previously acquired real FDs were closed once in reverse order. `os.open`/`os.close` are restored on every path; existing pinned-source positive, hardlink, chmod, and parent-swap tests remain.
- **retryCondition:** Revisit only if descriptor acquisition order, ownership rules, Python syscall wrappers, fixture layout or exact-source CI trigger changes. Do not repeat the absolute-path-depth fixture error or retry unchanged MinIO 401, writer/publisher coupling, canonical large-blob retrieval or missing human evidence.

## Material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41396898895](https://github.com/m-shogo/memories-project/actions/runs/41396898895) completed **SUCCESS** on `56abcc70ec8202f7a920bc9861850c274876de80`; job `125120060425` logged `generation evidence registry transaction negative PASS`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. The source diff shows the 12 malformed-acquisition cases are invoked before the transaction tests.
- **evidence:** GitHub Actions conclusion, exact-source job output and reviewed committed test source. Synthetic CI only; no production recovery evidence.
- **whySafe:** Only the independently read-only negative harness changed. The production-capable publisher does not trigger on its path. All injected acquisitions occur in disposable source fixtures and no production authority is modified.
- **reusableMechanism:** Exercise every actual owned-FD acquisition stage with malformed returns, prove no invalid value is closed, and assert reverse cleanup of already owned real FDs; never infer acquisition order from absolute path components.
- **protectedAuthorityCheck:** Post-code GitHub blob SHAs unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), environment generations `bfd1b045`, approved objectives `f4d74f33`, reviewed requests `acebcd02`, request-bound evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion review `99cb895f`, canonical learning `b809c69d`, learning contract `87712ea9`. Registered/semantically eligible generations remain 0/0, and current approved objective, executable reviewed request, request-bound recovery, typed coverage and final candidate remain 0. Independent review and separate human promotion gates remain unchanged.

## Next safe target

Reuse the malformed ROOT/ancestor/leaf FD acquisition regression mechanism in the generation-evidence and generation-binding transport pinned importer negatives, preserving independently read-only exact-source CI.
