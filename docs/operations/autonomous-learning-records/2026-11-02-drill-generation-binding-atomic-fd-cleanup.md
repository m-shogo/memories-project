# Supplemental OPS learning — drill-generation binding atomic FD and cleanup ownership (2026-11-02)

Append-only operational learning subordinate to the canonical learning policy. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion evidence.

## Material failure

- **symptom:** Drill-generation eligibility binding atomic writer could leak its raw descriptor on `os.fdopen` failure, and a secondary `os.unlink` cleanup exception could replace the primary `os.replace` rejection.
- **evidence:** At starting HEAD `349abcff`, `atomic_write_text` handed `fd` to a default-owning stream without a retained-ownership fallback if `fdopen` failed. Its `finally` always unlinked the temp without preserving active exception priority. The existing negative suite did not exercise the two-fault path. No actual production failure or corrupted authority was observed.
- **rootCauseOrUnknown:** Verified descriptor ownership and Python `finally` precedence in inspected source; real-world occurrence unknown.
- **failedApproach:** Assuming `fdopen` always acquires FD ownership, and allowing cleanup to overwrite an already-active write exception.
- **correction:** [`227772d2`](https://github.com/m-shogo/memories-project/commit/227772d2fc1df54285bae7b7c1f4ec87a8d6501c) retains the raw descriptor with `closefd=False`, closes it once, converts write failures to a fixed private-safe `Fail`, and preserves a primary exception while treating standalone cleanup failure as an error.
- **recurrenceGuard:** Existing CI-reached binding reconcile negative suite now injects `fdopen` failure and asserts FD closure/temp cleanup, then injects primary replace OSError and secondary unlink ValueError; checks fixed-class rejection, isolated byte/mode preservation, temp cleanup, and unchanged canonical binding contract/drill registry. Existing atomic replace negative was updated to require the new fixed-class diagnostic.
- **retryCondition:** Revisit on a reviewed atomic writer/rollback change or exact-source CI regression. Do not repeat unchanged external MinIO, permissions, evidence or promotion blockers.

## Material success

- **outcome:** Synthetic FD acquisition failure and atomic double-fault are rejected without canonical mutation; reviewed post-validation remains intact.
- **evidence:** [Backup Restore Drill Generation Eligibility Binding #41333013044](https://github.com/m-shogo/memories-project/actions/runs/41333013044) completed SUCCESS at exact code HEAD `227772d2`. This is a validator/negative result, not a reviewed drill or recovery evidence.
- **whySafe:** Only the existing binding reconciler and its CI-reached isolated negative suite changed. No protected production status, OPS-P0-007 snapshot, registry, workflow permission or production evidence was modified.
- **reusableMechanism:** Keep ownership of raw FD across stream creation and closure, never retry an uncertain post-effect close, test two independent injected faults, and preserve the primary exception in `finally`.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain non-resurrection `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved recovery objectives 0, current executable reviewed requests 0, request-bound evidence 0, complete typed eight-domain coverage 0, final candidates 0. Preflight requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current objective; reviewed requests remain planning-only, generation recovery evidence is request-bound, complete typed eight-domain coverage plus independent review is mandatory for final candidates, and human promotion remains separate and nonautomatic.

## Next safe target

Verify the binding reconciler's rollback-failure diagnostic priority after the new fixed-class atomic writer rejection; add an isolated negative that proves both primary and rollback failure are retained without treating the result as readiness.
