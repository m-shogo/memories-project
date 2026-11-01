# Supplemental OPS learning — malformed canonical stream interfaces (2026-11-01)

Append-only operational history subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered/semantically eligible environment generation, approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final recovery candidate or human-promotion evidence.

## Material failure

- **symptom:** An unexpected ordinary `TypeError` or `AttributeError` from canonical stream acquisition/read, or an object missing the required stream interface, could escape the reviewed single-line fail-closed diagnostic. This is a synthetic stream-interface failure class, not an observed production incident.
- **evidence:** At source HEAD `2861373b`, the canonical reader normalized only `OSError` and `ValueError`. A synthetic `fdopen` TypeError, `read` TypeError or `fdopen` returning `None` would raise an unreviewed exception, despite outer raw-FD cleanup.
- **rootCauseOrUnknown:** Verified ordinary exception-class gap at the canonical stream boundary. The Python runtime is not claimed to return malformed streams under normal `os.fdopen` semantics; these are injected failure modes.
- **failedApproach:** Treating the prior OSError/ValueError guard as covering all ordinary malformed stream-interface failures. A broad catch-all that could obscure programmer errors or cancellation was not adopted.
- **correction:** [`c237c895`](https://github.com/m-shogo/memories-project/commit/c237c89551a630e7764b263f7a053739a43ef6d8) adds `TypeError` and `AttributeError` to the narrow canonical unreadable-authority handler, preserving `ValidationFailure` and leaving `BaseException` cancellation outside.
- **recurrenceGuard:** [`c1ffae1c`](https://github.com/m-shogo/memories-project/commit/c1ffae1c1743f14e4038b69a62f7d621bac420d9) adds three CI-reached real-FD negative cases: `fdopen` TypeError, missing stream interface, and `read` TypeError. All assert exact diagnostic, retained FD closure, external canary integrity and subsequent positive recovery. Fixture canary initialization is deliberately before the matrix, avoiding the recorded earlier use-before-definition failure.
- **retryCondition:** Revisit if stream interface contracts, ordinary exception types, descriptor ownership or executable negative reachability change. Do not retry unchanged MinIO HTTP 401 or workflow write-permission blockers.

## Material success

- **outcome:** Malformed canonical stream interfaces fail closed through the reviewed diagnostic without leaking the owned raw descriptor or corrupting an independent canary.
- **evidence:** [Autonomous Learning Guard #41284675020](https://github.com/m-shogo/memories-project/actions/runs/41284675020) SUCCESS on exact runtime HEAD `c237c895`; [Autonomous Learning Guard #41284687905](https://github.com/m-shogo/memories-project/actions/runs/41284687905) SUCCESS on exact test HEAD `c1ffae1c`. The same CI-reached canonical suite includes 601 fail-closed negatives, 195 fanout synthetic cases, 1,186 helper-ancestor negatives, and append-only/read-only checks. These results are not production or recovery evidence.
- **whySafe:** Only the read-only canonical validator and disposable negative tests changed. No workflow permission, production route, credential, traffic, readiness, generation/objective registry, recovery evidence, typed eight-domain coverage, independent review or human promotion was changed.
- **reusableMechanism:** Normalize narrowly enumerated ordinary malformed stream-interface failures at the authoritative boundary, preserving original domain validation errors and OS-owned descriptor cleanup; test before/after acquisition and missing-interface cases against real FD state.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs remained unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0 and approved objectives 0. Human objective approval, executable reviewed request binding, complete typed eight-domain non-resurrection, independent review and separate non-automatic human promotion remain mandatory.

## Next safe target

Inspect exact-source Go package initializer coverage and the independent Pre-MinIO Focused Go execution path without changing workflow permissions or treating static/synthetic checks as Go test success.
