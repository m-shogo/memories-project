# Supplemental OPS learning — pinned stage cleanup and primary-error preservation (2026-11-01)

Append-only execution learning under `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate, or human promotion evidence. The canonical learning authority remains unchanged.

## Material failure class A — staged-fstat negative did not independently check parent FD closure

- **symptom:** The existing initial/recovery `fstat` fault cases checked staged descriptor closure but did not independently assert that the pinned parent directory capability was closed. This was a coverage gap, not an observed live FD leak.
- **evidence:** The baseline `fb4b241a` negative proof checked `original_fstat(captured[0][0])` but had no matching pinned-parent descriptor assertion.
- **rootCauseOrUnknown:** Verified omission of a separate parent capability closure assertion in the disposable test.
- **failedApproach:** Treating the staged descriptor's EBADF check as proof that all acquired descriptors were closed.
- **correction:** [`ebebe46a`](https://github.com/m-shogo/memories-project/commit/ebebe46a6be01bd083ec349dece94a0146a14d48) captures the actual pinned parent FD for all five `fstat` fault scenarios and requires EBADF after failure.
- **recurrenceGuard:** The existing CI-reached proof function and entrypoint AST binding require the actual parent-FD assertion. A source-negative mutation replaces the descriptor check with an unrelated FD and must be rejected.
- **retryCondition:** Revisit when parent capability acquisition, stage descriptor handoff, `fstat` recovery, or the proof binding changes.
- **outcome/evidence:** [Autonomous Learning Guard #41233476859](https://github.com/m-shogo/memories-project/actions/runs/41233476859) and [Operability Contracts #41233476764](https://github.com/m-shogo/memories-project/actions/runs/41233476764) both completed SUCCESS on the exact `ebebe46a` source.
- **whySafe:** Only read-only validation and disposable fault fixtures changed. No production reconciler or protected evidence authority was written.
- **reusableMechanism:** Capture every independently owned descriptor and verify closure with the original `fstat` callable after restoring injected faults.
- **protectedAuthorityCheck:** All ten protected authority Git blob SHAs were unchanged.

## Material failure class B — cleanup stat error could mask the primary publication error

- **symptom:** The publication `finally` handler caught `FileNotFoundError` but not other `os.stat` errors, so a cleanup permission fault could replace the original `os.replace` failure. No live production corruption was observed.
- **evidence:** Pre-change `atomic_write_bytes` cleanup had no non-ENOENT `os.stat` catch. The isolated test now injects a primary publication failure followed by a cleanup `PermissionError`.
- **rootCauseOrUnknown:** Verified exception replacement during cleanup because only a missing-name exception was handled.
- **failedApproach:** Assuming cleanup `stat` cannot fail independently after publication failure.
- **correction:** [`69a77f22`](https://github.com/m-shogo/memories-project/commit/69a77f222c9de4378e56077371428c45ca5e4f88) captures `sys.exception()`, preserves the primary exception, adds bounded diagnostic notes when descriptor identity or cleanup `stat` cannot be verified, and never unlinks an unverified stage name.
- **recurrenceGuard:** The disposable fault proof checks the original exception, retained private stage, original authority bytes, and diagnostic note. EntryPoint source-negative mutations reject removal of primary-error capture or narrowing of the cleanup exception handler.
- **retryCondition:** Revisit if stage identity, `stat` cleanup, exception notes, or Python runtime support changes.
- **outcome/evidence:** [Autonomous Learning Guard #41233877404](https://github.com/m-shogo/memories-project/actions/runs/41233877404) and [Operability Contracts #41233877474](https://github.com/m-shogo/memories-project/actions/runs/41233877474) completed SUCCESS on exact source.
- **whySafe:** Cleanup remains fail-closed: uncertain stage ownership is not inferred from a pathname; only the primary exception and bounded diagnostic are preserved.
- **reusableMechanism:** Capture the active exception before nested cleanup, add an uncertainty note rather than replacing it, and retain the unverified private name.
- **protectedAuthorityCheck:** All ten protected authority Git blob SHAs were unchanged.

## Material failure class C — unlink status can be uncertain even after an error

- **symptom:** A direct `os.unlink` in publication cleanup could mask the primary failure; a fault after the syscall had already removed the stage would also make a blanket "retained" diagnostic false.
- **evidence:** The pre-change cleanup used unguarded descriptor-relative `os.unlink`. The disposable proof now injects both pre-unlink and post-actual-unlink `PermissionError` after a primary replace failure.
- **rootCauseOrUnknown:** Verified unguarded cleanup exception path; the precise name state is unknowable from an error alone.
- **failedApproach:** Equating an unlink exception with proof that a staged name still exists.
- **correction:** [`f4d77d4d`](https://github.com/m-shogo/memories-project/commit/f4d77d4d22b2123442420851a85b30d160772f65) preserves the primary exception and reports private staged unlink status as unknown without retrying an ambiguous syscall.
- **recurrenceGuard:** Both disposable scenarios require original bytes/mode and independent canary preservation, primary exception identity, bounded uncertainty note, and correct observed pre/post stage state.
- **retryCondition:** Revisit on unlink transport, parent FD cleanup, or staging ownership policy changes.
- **outcome/evidence:** The first CI attempt on `f4d77d4d` FAILED in [Autonomous Learning Guard #41234205694](https://github.com/m-shogo/memories-project/actions/runs/41234205694) and [Operability Contracts #41234205853](https://github.com/m-shogo/memories-project/actions/runs/41234205853), due to a test-source binding error detailed below. The corrected [Autonomous Learning Guard #41234441283](https://github.com/m-shogo/memories-project/actions/runs/41234441283) and [Operability Contracts #41234441216](https://github.com/m-shogo/memories-project/actions/runs/41234441216) completed SUCCESS on exact `a4e8bb70` source.
- **whySafe:** Existing descriptor-relative, no-follow and inode checks remain intact. Tests use only disposable files and never create production evidence.
- **reusableMechanism:** Fault a cleanup syscall both before and after its actual effect; preserve the primary exception and describe uncertain status rather than inferring completion.
- **protectedAuthorityCheck:** All ten protected authority Git blob SHAs remained unchanged.

## Material failure D — a second `scenario` loop broke the reviewed executable AST binding

- **symptom:** The new unlink proof was rejected as `upload-route symlink rollback negative is not CI-bound`.
- **evidence:** [Autonomous Learning Guard #41234205694](https://github.com/m-shogo/memories-project/actions/runs/41234205694) and [Operability Contracts #41234205853](https://github.com/m-shogo/memories-project/actions/runs/41234205853) FAILED. The existing AST guard required exactly one `for scenario` tuple in `prove_atomic_initial_fstat_failure_cleanup`; the added unlink loop reused that target name, yielding two. The earlier supplemental learning had already established that executable loop topology, not label presence, is mandatory.
- **rootCauseOrUnknown:** Verified test-loop target collision with the existing canonical AST count.
- **failedApproach:** Adding another loop named `scenario` inside the same proof function without preflighting the existing exact-loop source binding. This known source-binding failure class must not be repeated.
- **correction:** [`a4e8bb70`](https://github.com/m-shogo/memories-project/commit/a4e8bb70fabec74e3a9dbdc256de51252656710e) uses a separate `unlink_scenario` target and binds its exact two-case executable tuple with a dedicated source-negative mutation.
- **recurrenceGuard:** The canonical CI entrypoint now requires exactly one five-case `scenario` loop and exactly one two-case `unlink_scenario` loop. A mutation removing the post-unlink case is rejected; token presence alone cannot satisfy the executable topology.
- **retryCondition:** Revisit only when reviewed proof loop structure or AST binding changes; preflight exact loop targets and source-line budget before publishing.
- **outcome/evidence:** Exact-source [Autonomous Learning Guard #41234441283](https://github.com/m-shogo/memories-project/actions/runs/41234441283) and [Operability Contracts #41234441216](https://github.com/m-shogo/memories-project/actions/runs/41234441216) SUCCESS. The guard also verified 601 canonical negatives, 52 workflows, 63 direct Python commands, 204 source-negative fixtures, 195 fanout synthetics and 1,186 helper-ancestor mutations.
- **whySafe:** Only executable negative proof and read-only source binding changed in the correction. No protected authority or production evidence was modified.
- **reusableMechanism:** Give independent proof loops distinct target names and assert their exact AST tuple shape, with a negative mutation for dropped cases.
- **protectedAuthorityCheck:** All ten protected authority Git blob SHAs were unchanged.

## Material execution blocker — concurrent metrics HEAD update during prepared-tree publication

- **symptom:** The first prepared correction tree could not be committed against the original `f4d77d4d` HEAD because `so` advanced.
- **evidence:** HEAD moved to [`2bc606de`](https://github.com/m-shogo/memories-project/commit/2bc606de94b0a336fde9a4fddfc6269bcac1082e), changing only `docs/fixtures/memory-os-operability/metrics-alerting-validation.last.json`. The pre-commit HEAD check aborted; no stale commit or ref update occurred.
- **rootCauseOrUnknown:** Verified concurrent independent metrics fixture update; no protected authority drift.
- **failedApproach:** A tree prepared from a stale base cannot be safely published after HEAD changes.
- **correction:** Re-read latest `so`, both target blobs and mandatory contract; reuse only verified prepared blob objects in a fresh tree based on the new HEAD, then commit and publish with expected-SHA CAS.
- **recurrenceGuard:** Pre-commit and pre-CAS HEAD checks, target blob SHA checks, protected-authority tree comparison, and no force-push. The successful corrected commit is `a4e8bb70`.
- **retryCondition:** Reconcile again only on a newly observed HEAD change, after independently reviewing changed paths and authority blobs.

## Protected admission, known scoped blockers, next safe target

All ten protected blobs remain unchanged through `a4e8bb70`: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, environment generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion `99cb895f`.

`productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with registered / semantically eligible generations 0/0 and no human-approved current recovery objective. Only unsuperseded semantically eligible generations from distinct environments and an explicitly approved current objective may pass preflight. Reviewed drill requests are planning-only; new recovery evidence must be bound to a current executable reviewed request. Complete typed eight-domain non-resurrection coverage, independent review and separate non-automatic human promotion remain mandatory. No production-equivalent generation, objective, credential, traffic, readiness or evidence was invented.

The known Quay MinIO startup failure persists in [Upload Route #41234205713](https://github.com/m-shogo/memories-project/actions/runs/41234205713) before focused Go/HTTP tests; no Go success is claimed. Workflow-write permission, supplemental-learning-only Push/PR CI reachability and independent pre-MinIO focused Go execution remain scoped blockers with unchanged retry conditions; do not retry them without changed preconditions. This learning-only commit does not itself establish a new exact-source CI success.

**Next safe target:** Audit the final pinned-parent and staged-guard FD close exception paths with disposable before/after-close fault injection. Preserve primary failure diagnostics without retrying an ambiguously completed close, and do not claim that uncertain descriptor closure is leak-free.
