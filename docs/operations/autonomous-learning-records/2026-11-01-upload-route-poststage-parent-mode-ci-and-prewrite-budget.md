# Supplemental OPS learning — poststage parent-mode authority and prewrite budget (2026-11-01)

Append-only operational learning under `contracts/operations/autonomous-learning-system.json`. The canonical 4.17 MB `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains authoritative, unchanged and not fully transportable through the available GitHub connector. **This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.**

## Material failure risk A — poststage parent permission drift

- **symptom:** After pinned-parent staging, the Upload Route writer's final parent check compared only device and inode. A directory chmod during staged fsync could retain the same inode while changing who can modify the publication namespace. This is a source-verified latent gap, not an observed production compromise.
- **evidence:** Starting `so` `e6c5d812821b74d73dd34e722fbb5a9b5f8a53a4`, `atomic_write_bytes` used `(pinned_parent.st_dev, pinned_parent.st_ino) == (live_parent.st_dev, live_parent.st_ino)` before `os.replace`. The new disposable negative changes parent mode `0700 → 0777` during `fsync` and demands a fixed parent-drift rejection with unchanged target bytes, retained chmod and no temporary residue.
- **rootCauseOrUnknown:** Verified missing parent `st_mode` binding after staging. Parent `st_ctime_ns` cannot simply be compared to its pre-staging value because creating the private stage legitimately changes directory ctime. A transient mode ABA remains outside this bounded check; atomic leaf CAS is not claimed.
- **failedApproach:** Treating stable directory device/inode and no-follow descriptor-relative publication as sufficient proof of unchanged directory write authority.
- **correction:** [`9b01bd8d`](https://github.com/m-shogo/memories-project/commit/9b01bd8da213ad55273e418ad3543ccef64ded86) binds pinned/live parent device, inode and mode to the initial parent before publication, and checks live mode again after publication.
- **recurrenceGuard:** The actual Upload Route rollback negative now injects a real chmod during staged fsync; the existing pre-MinIO entrypoint requires that negative, the AST-normalized proof, and a source mutation that removes the parent-mode predicate. [Autonomous Learning Guard #41221685590](https://github.com/m-shogo/memories-project/actions/runs/41221685590) completed SUCCESS on the final exact code SHA.
- **retryCondition:** Revisit if directory permission/ACL semantics, staging order, prepublication mode binding, exact-source CI or the reviewed concurrency model changes. Do not claim the bounded check detects mode ABA or prevents a final-check-to-replace race.

## Material CI failure B — AST literal normalization

- **symptom:** [Autonomous Learning Guard #41221367152](https://github.com/m-shogo/memories-project/actions/runs/41221367152) FAILED on `9b01bd8d`; downstream entrypoint logs reported `upload-route symlink rollback negative is not CI-bound`.
- **evidence:** The new source binder searched `ast.unparse(proof)` for `root.chmod(0o777)`. Python's AST unparser normalizes that integer literal to `root.chmod(511)`, independently reproduced with `ast.parse`/`ast.unparse`. The raw source mutation still correctly needs `0o777`.
- **rootCauseOrUnknown:** Verified representation mismatch between raw source text and AST-unparsed text; no failure of the real parent-mode negative was demonstrated by that diagnostic.
- **failedApproach:** Comparing raw octal spelling directly against normalized AST output.
- **correction:** [`9193287e`](https://github.com/m-shogo/memories-project/commit/9193287e8e73488aa3c3939d4a608c69e642f316) uses `root.chmod(511)` only in the AST binding while retaining the original raw-text mutation.
- **recurrenceGuard:** The same entrypoint must pass both AST proof binding and exact raw-text source mutation; its full execution is part of the exact-source Autonomous Learning Guard.
- **retryCondition:** Revisit if Python AST normalization or proof syntax changes. Never weaken the executable negative to accommodate a spelling mismatch.

## Material CI failure C — existing bounded prewrite line limit

- **symptom:** [Autonomous Learning Guard #41221498317](https://github.com/m-shogo/memories-project/actions/runs/41221498317) FAILED on `9193287e`. The nested negative validator reported `prewrite CLI real-entrypoint positive control failed`.
- **evidence:** The entrypoint grew to 4,108 physical lines while `PREWRITE_MAX_SOURCE_LINES=4096`. The existing real-entrypoint prewrite positive uses the checked-in file and rejects an over-budget baseline. This is a recurrence of the previously documented source-bound line-budget class.
- **rootCauseOrUnknown:** Verified source size exceeded the mandatory existing prewrite bound; the nested stderr did not expose a more specific failure, so this explanation is supported by the independent line-count check and validator source.
- **failedApproach:** Adding additional readable guard lines without checking the existing 4,096-line prewrite bound before publication.
- **correction:** [`15f61535`](https://github.com/m-shogo/memories-project/commit/15f615350ae05acf0301b13c02d17ec743b78907) compacts only equivalent read-only guard expressions and marker tuples to 4,094 physical lines without relaxing the bound or dropping predicates.
- **recurrenceGuard:** The existing real-entrypoint prewrite CLI positive remains executable and fail-closed. Future source changes must check physical line count and run the real prewrite control **before** publication, not infer eligibility from syntax alone.
- **retryCondition:** Revisit only on an explicitly reviewed prewrite budget/policy change or new exact-source CI failure. Do not expand the line cap merely to make a regression pass.

## Material safe success and protected authority

- **outcome:** The parent chmod-after-staging negative and both source bindings are CI-reachable, and the prewrite line budget is restored without relaxing mandatory checks.
- **evidence:** [Autonomous Learning Guard #41221685590](https://github.com/m-shogo/memories-project/actions/runs/41221685590) **SUCCESS** on exact code HEAD `15f615350ae05acf0301b13c02d17ec743b78907`: 601 canonical fail-closed negatives, 39 supplemental history fixtures, actual Upload Route append-only/symlink/rollback negatives, 52 workflow / 63 direct Python command / 204 negative fixture reachability, 195 fanout synthetic cases, 1,186 helper-ancestor mutations, entrypoint PASS, read-only/clean-source PASS. [Operability Contracts #41221685674](https://github.com/m-shogo/memories-project/actions/runs/41221685674) and [Reconcile Backup Restore Policy #41221685653](https://github.com/m-shogo/memories-project/actions/runs/41221685653) also completed SUCCESS on the same code HEAD.
- **whySafe:** The three code commits changed only the Upload Route Python reconciler, its disposable negative harness, and the existing read-only entrypoint. No workflow YAML, production/backup/restore evidence, credentials, traffic, objectives, generation registries, readiness or promotion authority was written. Independent Metrics commits were retained, not overwritten.
- **reusableMechanism:** Bind directory permission state to the initially observed parent, inject a chmod at the staged-fsync boundary, require exact rejection and residue checks, distinguish AST-normalized literals from raw source, and enforce the prewrite budget before publishing.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs were unchanged at final code HEAD: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, environment generations `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion `99cb895f`.

## Scoped blockers and next safe target

The known Quay MinIO HTTP 401 prevents the focused Upload Route Go/HTTP tests from starting; no Go test success is claimed. Workflow-write permission and supplemental-learning-only Push/PR trigger coverage remain blocked. The canonical learning full-blob connector transport limit remains unchanged; no unchanged blocker was manually retried.

OPS-P0-007 remains `PREREQUISITES_BLOCKED`; registered and semantically preflight-eligible generations are **0/0**. No explicitly human-approved current recovery objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain non-resurrection, independent review, final recovery candidate or human promotion exists. Reviewed requests are planning authority only. **`productionDecision=NO_GO`**.

**Next safe target:** inspect whether a private pinned staging file can gain a second hardlink during fsync and pass the final stage check, then design a disposable real-link negative and fail-closed single-link predicate without treating a staged-file link check as complete data-exposure prevention. Independently retain the pre-MinIO Go trigger/order gap until workflow authority changes.
