# Supplemental OPS learning — canonical ancestor aliases, path faults, and acquired-FD identity (2026-11-01)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, final-candidate, or human-promotion evidence.

## Material failure 1 — stable ancestor alias

- **symptom:** The direct canonical reader could accept an existing symlinked parent if its leaf and parent metadata remained stable. Separate CLI root checks already rejected aliases; this is a direct-reader gap, not an observed production incident.
- **evidence:** Starting HEAD `2be785dd` only compared parent snapshots before/after the read; a disposable parent-swap fixture left an unchanged symlink pointing to the same leaf.
- **rootCauseOrUnknown:** Verified that unchanged parent metadata is not proof of canonical directory identity; the original order also probed the aliased leaf before rejecting the ancestor.
- **failedApproach:** Relying on post-read drift detection and higher-level CLI alias rejection.
- **correction:** [`a77e4dba`](https://github.com/m-shogo/memories-project/commit/a77e4dba2951e7494706dbb242832c4005179310) requires every ancestor to be a directory; [`10ea0430`](https://github.com/m-shogo/memories-project/commit/10ea0430d30ad15204199bb3b695face2048e72b) rejects aliases before leaf `lstat`.
- **recurrenceGuard:** [`e1f92518`](https://github.com/m-shogo/memories-project/commit/e1f92518e8a417f2c146c4489c391da6bed5759e) adds a stable-symlink negative with exact diagnostic and unchanged leaf; [`4fe8fe96`](https://github.com/m-shogo/memories-project/commit/4fe8fe9674dae08002ef1a8fe04b4cacb1750044) uses a deterministic spy to forbid even leaf metadata probing through that alias.
- **retryCondition:** Revisit on parent-chain acquisition, alias semantics, read order or CI reachability changes. Do not retry unchanged MinIO/permission blockers.

### Material success 1

- **outcome:** A pre-existing ancestor alias is rejected before dereferencing the canonical leaf.
- **evidence:** Exact-source Autonomous Learning Guard [#41292482105](https://github.com/m-shogo/memories-project/actions/runs/41292482105) SUCCESS on `e1f92518` and [#41292737582](https://github.com/m-shogo/memories-project/actions/runs/41292737582) SUCCESS on final code HEAD `4fe8fe96`.
- **whySafe:** Only the read-only validator and disposable negatives changed; original descriptor ownership, inode, metadata and bounded-read checks remain.
- **reusableMechanism:** Validate ancestor inode types before leaf access; pair stable-alias negatives with a no-leaf-probe assertion.
- **protectedAuthorityCheck:** Ten protected Git blobs remained unchanged; production decision remains NO_GO and OPS-P0-007 remains PREREQUISITES_BLOCKED.

## Material failure 2 — malformed path metadata/open exceptions

- **symptom:** Injected `ValueError`/`TypeError` from initial `Path.lstat` or `os.open` escaped the controlled unreadable-authority diagnostic. No production fault was observed.
- **evidence:** Previous acquisition handlers caught only `OSError`; four deterministic negative cases now exercise both exception types at both boundaries.
- **rootCauseOrUnknown:** Verified incomplete acquisition exception normalization.
- **failedApproach:** Assuming all path acquisition faults manifest as `OSError`.
- **correction:** [`9b03ec23`](https://github.com/m-shogo/memories-project/commit/9b03ec23d197c4c53def47cdd650fe9dca34a43c) normalizes `OSError`, `ValueError` and `TypeError` to the existing diagnostic.
- **recurrenceGuard:** [`296af502`](https://github.com/m-shogo/memories-project/commit/296af50261dcec7b8e9d9ad696a087cc932a7739) verifies exact rejection, external FD canary preservation and subsequent valid-read recovery.
- **retryCondition:** Revisit on observed new exception classes or acquisition API changes, not unchanged external dependency failures.

### Material success 2

- **outcome:** All four injected metadata/open faults fail closed with a controlled diagnostic.
- **evidence:** Exact-source Autonomous Learning Guard [#41292561772](https://github.com/m-shogo/memories-project/actions/runs/41292561772) SUCCESS on `296af502`.
- **whySafe:** Only a rejection boundary broadened; no authority or evidence was modified.
- **reusableMechanism:** Normalize untrusted acquisition-interface failures and test canary plus recovery.
- **protectedAuthorityCheck:** Ten protected blobs unchanged; no production or promotion authority created.

## Material failure 3 — invalid acquired descriptor identity

- **symptom:** A malformed synthetic `os.open` return (`None`, `True`, `-1`, float, string) could reach `fdopen` or numeric cleanup without establishing descriptor ownership. Ordinary CPython `os.open` was not observed to behave this way.
- **evidence:** Prior reader entered the ownership region immediately after `os.open` returned; `bool` is an `int` subclass.
- **rootCauseOrUnknown:** Verified missing exact acquired-FD type and nonnegative range validation; a valid integer's OS ownership still depends on the trusted syscall.
- **failedApproach:** Treating every successful `os.open` return as an owned raw descriptor.
- **correction:** [`da27ce48`](https://github.com/m-shogo/memories-project/commit/da27ce48e816a9891c105f16cb9fcff491ba69eb) requires `type(fd) is int` and `fd >= 0` before `fdopen`/cleanup.
- **recurrenceGuard:** [`2cb2375a`](https://github.com/m-shogo/memories-project/commit/2cb2375a6f8982d07c3d06b09715f679c13ab2cb) injects five invalid values, forbids `fdopen` and `os.close` on them, and checks external canary and valid-read recovery.
- **retryCondition:** Revisit on changed FD ownership/allocator semantics or a new observed malformed return; never close an unverified numeric alias.

### Material success 3

- **outcome:** Invalid synthetic acquisition results are rejected without treating them as owned descriptors.
- **evidence:** Exact-source Autonomous Learning Guard [#41292613972](https://github.com/m-shogo/memories-project/actions/runs/41292613972) SUCCESS on `2cb2375a`; final combined source [#41292737582](https://github.com/m-shogo/memories-project/actions/runs/41292737582) also SUCCESS.
- **whySafe:** A fail-closed pre-ownership check was added; normal valid `os.open` integer behavior remains unchanged.
- **reusableMechanism:** Validate strict FD type/range before stream creation and numeric cleanup; forbid use/close of invalid returns in negatives.
- **protectedAuthorityCheck:** Ten protected authorities unchanged; production/recovery evidence and human promotion untouched.

## Material failure 4 — incomplete prewrite status JSON read

- **symptom:** An initial append-only lesson creation attempt stopped before any write with `SyntaxError: Expected double-quoted property name in JSON`.
- **evidence:** The prewrite authority check requested only lines 1–10 of the 98 KB production status JSON, then attempted `JSON.parse` on the incomplete document. GitHub `so` and target absence were re-read; no commit resulted from that attempt.
- **rootCauseOrUnknown:** Verified incomplete JSON transport, not malformed production authority.
- **failedApproach:** Parsing a deliberately line-truncated authority as a complete JSON document.
- **correction:** Re-fetch the entire production status before parsing and re-check the current `so` HEAD, canonical learning/contract SHAs, all ten protected blobs and new target path.
- **recurrenceGuard:** Parse only a full JSON authority for prewrite decisions; require exact `productionDecision=NO_GO`, protected digest agreement and target nonexistence before create.
- **retryCondition:** Retry only with complete document bytes or an explicitly safe field-level parser; never infer a production decision from truncated JSON.

### Material success 4

- **outcome:** The incomplete read caused no repository mutation; full-authority prewrite validation subsequently passed.
- **evidence:** Complete production status JSON parsed with `productionDecision=NO_GO`; starting protected blobs and final code HEAD `4fe8fe96` matched the re-read tree before this new learning-file create.
- **whySafe:** The failed prewrite path exited before the mutation; retry used complete, independently checked authority.
- **reusableMechanism:** Fail closed on incomplete JSON transport and re-read authority before retrying a write.
- **protectedAuthorityCheck:** Canonical learning, mandatory contract, production status and seven other protected registries retain their original blob identities.

## Exact-source validation, authority boundary and next target

Git compare `2be785dd..4fe8fe96` changed only the existing read-only Python validator and negative-suite file. Final code-head [Autonomous Learning Guard #41292737582](https://github.com/m-shogo/memories-project/actions/runs/41292737582) completed SUCCESS: clean-source, append-only, learning contract/executable negatives, helper-ancestor reachability and read-only checks. Earlier exact-source successes on `e1f92518`, `296af502`, `2cb2375a` were also observed. This is **not** real Focused Go Test execution or production evidence.

Protected Git blob prefixes remained unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed drill request registry `acebcd02`, generation recovery evidence registry `ae7e57ef`, typed eight-domain non-resurrection registry `26bb1cc7`, human promotion review registry `99cb895f`.

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations `0/0`, approved objectives `0`, executable reviewed requests `0`, request-bound evidence `0`, complete typed eight-domain records `0`, final candidates `0`. Preflight requires unsuperseded semantically eligible generations from distinct environments and a current explicitly human-approved recovery objective. Reviewed requests are planning authority only; new generation evidence requires a current executable reviewed request; typed eight-domain non-resurrection coverage, independent review and human production promotion remain separate and mandatory. Learning never satisfies these or any production/backup/restore/RPO/RTO/skew/drill/credential/traffic/readiness gate.

**Next safe target:** Audit remaining canonical parent-chain metadata interface faults, and seek an authorized independent pre-MinIO non-skipped Focused Go Test path. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permissions or human approval blockers.
