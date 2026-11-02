# Supplemental OPS learning — generation-binding transport refuses inert safety flags (2026-11-02)

Append-only supplemental learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, approved objective, reviewed request, request-bound recovery, typed eight-domain coverage, independent review, final-candidate or human-promotion evidence.

## Material failure / latent unsafe condition

- **symptom:** The read-only generation-binding transport negative harness treated a defined `O_DIRECTORY`, `O_NOFOLLOW` or `O_NONBLOCK` name as sufficient even if its value was zero, a boolean or a noninteger.
- **evidence:** At `so` HEAD `1099e60302238f3fbd0fdae4a279a1dcad4f0890`, `scripts/validate-memory-os-backup-restore-generation-binding-transport-negative.py::pinned_validator_source` used `all(hasattr(os, flag) ...)`. Zero-valued flags would silently remove intended OS open semantics. This is a verified source-level guard gap, **not** evidence of actual platform compromise.
- **rootCauseOrUnknown:** Verified name-existence check rather than exact positive-integer capability validation. Real-world flag corruption or malicious substitution is unknown.
- **failedApproach:** Assuming a present safety flag constant guarantees its effective protection.
- **correction:** Commit [`95dbff87`](https://github.com/m-shogo/memories-project/commit/95dbff87a0d6a9b9834701fb0897248389f1066b) requires each of the three constants to be an exact positive `int` before opening any owned source FD.
- **recurrenceGuard:** The existing independently read-only CI-reachable generation-binding transport negative harness now substitutes `0`, `False` and `"inert"` for each flag, demands the precise fail-closed diagnostic, restores each constant and still verifies a positive pinned-source control and parent-swap canary.
- **retryCondition:** Revisit only if the safety-flag API, source importer, descriptor ownership or CI trigger topology changes. Do not retry unchanged publisher-coupled writer changes, Quay MinIO HTTP 401, canonical large-blob retrieval or absent human recovery evidence.

## Material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41395784909](https://github.com/m-shogo/memories-project/actions/runs/41395784909) completed **SUCCESS** at `95dbff87a0d6a9b9834701fb0897248389f1066b`; job `125116694360` logged `PASS: generation-binding transport validator pinned after parent swap`, `Memory OS generation-binding loader transport negative PASS`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. [Admission Chain #41395784842](https://github.com/m-shogo/memories-project/actions/runs/41395784842) also completed SUCCESS at the same source.
- **evidence:** Observed GitHub Actions conclusions and exact-source job output. Synthetic CI only; no production evidence or readiness.
- **whySafe:** Only a disposable-fixture, read-only negative harness changed. Its exact-source workflow uses `contents: read` and does not grant production-publisher authority; the write-capable Generation Evidence publisher does not trigger on this harness path.
- **reusableMechanism:** Reject inert safety flags by checking exact positive integer type/value and inject zero/boolean/string substitutions before any FD acquisition; retain a positive control and after-capture parent-swap negative.
- **protectedAuthorityCheck:** After the code commit, GitHub blob SHAs remained unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), environment generations `bfd1b045`, approved objectives `f4d74f33`, reviewed requests `acebcd02`, request-bound evidence `ae7e57ef`, typed eight-domain non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d` and mandatory learning contract `87712ea9`. Registered/semantically eligible generations remain 0/0; approved current objective, executable reviewed request, request-bound recovery evidence, complete typed coverage and final candidate remain 0. All preflight, independent-review and separate nonautomatic human-promotion gates remain intact.

## Next safe target

Extend the same read-only generation-binding transport importer suite with hardlink rejection and parent-mode race negatives; do not modify publisher-coupled writer code.
