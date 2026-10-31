# Supplemental OPS learning — pinned reader pathname identity and CI negative recovery (2026-10-31)

Append-only operational learning only. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, or promotion evidence.

## Material failure A — descriptor stability did not prove live pathname identity

- **symptom:** A pinned descriptor could still return bytes for an inode no longer reachable through the reviewed path after an independent leaf replacement or parent symlink swap. This is a source-verified latent risk, not an observed production incident.
- **evidence:** At `fecd5ece`, `read_regular_bytes` compared descriptor metadata before/after reading but did not perform a final live pathname `lstat` or ancestor alias check. Existing prior learning `2026-10-30-learning-canonical-descriptor-pinned-read.md` documented descriptor-plus-final-path identity as a reusable safe pattern.
- **rootCauseOrUnknown:** Verified missing final pathname identity check; no production race occurrence is claimed.
- **failedApproach:** Treating a stable open descriptor as sufficient proof that the current pathname still points to that descriptor's inode.
- **correction:** [`3fa42352`](https://github.com/m-shogo/memories-project/commit/3fa42352fa292eae29930628f0660b2da366b8f6) checks live ancestor symlinks and leaf `lstat` regular type, device/inode/mode/size/mtime/ctime after the descriptor read.
- **recurrenceGuard:** [`ddd43ba4`](https://github.com/m-shogo/memories-project/commit/ddd43ba467e605ffab8093660c2397372f309660) adds actual disposable same-content leaf-replacement and parent-symlink-swap negatives. A frozen descriptor `fstat` isolates the final pathname check so the new proof cannot pass merely because ctime changed. [`7c70803e`](https://github.com/m-shogo/memories-project/commit/7c70803ed34f93056722431fb73658cb632bb82c) connects the new proof directly to the pre-MinIO CI entrypoint.
- **retryCondition:** Revisit if the path reader, directory/leaf identity, parent symlink policy or test execution graph changes. The final check is bounded; it is not a directory-fd transaction or protection against a swap after validation.

## Material failure B — first CI binding used an ambiguous text mutation

- **symptom/evidence:** [Autonomous Learning Guard #41178354781](https://github.com/m-shogo/memories-project/actions/runs/41178354781) **FAILED** on `7c70803e` with exact diagnostic `upload-route ctime-only negative fixture drift`. Canonical 601 negatives passed, but the entry-document guard failed before the real Upload Route negative could execute.
- **rootCauseOrUnknown:** Verified: the new negative mutation required a unique occurrence of `"parent-symlink-swap"`, but the source contained that literal both in the scenario tuple and in the expected diagnostic branch. A whole-source occurrence count was not a valid binding to the actual loop authority.
- **failedApproach:** Using an unscoped text occurrence count as evidence that a specific executable scenario was uniquely present.
- **correction:** [`ab920626`](https://github.com/m-shogo/memories-project/commit/ab920626d9497ba627d033aa6b30df5152110d76) restricts the binding to the actual AST `for scenario in (...)` tuple, requires exactly the two reviewed cases, and mutates only the unique scenario tuple span.
- **recurrenceGuard:** The entry-document validator requires the new negative's direct `main` call, actual `module.read_regular_bytes` transport, exactly one AST scenario loop with both cases, and a negative mutation proving a missing case is rejected. Existing ctime-only mutation negatives remain mandatory.
- **retryCondition:** Reconsider only on a reviewed scenario-loop topology change, a changed CI execution binding or a fresh exact-source failure. Do not repeat broad literal-count mutation without a changed precondition.

## Material safe success

- **outcome/evidence:** [Autonomous Learning Guard #41178583341](https://github.com/m-shogo/memories-project/actions/runs/41178583341) **SUCCESS** on exact corrected code HEAD `ab920626`. Logs prove 601 canonical fail-closed negatives, 39 supplemental-history fixtures, actual Upload Route rollback/symlink/path-swap negatives through `upload-route append-only scan and symlink negatives verified`, 195 fanout synthetics, 1,186 helper-ancestor negatives, and append-only, learning contract, entry-document and read-only PASS.
- **whySafe:** Only the Upload Route Python reconciler and two read-only negative/CI-entrypoint scripts changed. All race fixtures operate in disposable directories, no real production reconciler or production evidence was executed or fabricated, and no workflow YAML was changed.
- **reusableMechanism:** Pair pinned descriptor checks with final live path/ancestor checks and use scenario-scoped AST mutations to prove the exact negative case remains executable.
- **protectedAuthorityCheck:** All ten protected blob SHAs unchanged after corrected HEAD: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, and six registries `bfd1b045`, `f4d74f33`, `acebcd02`, `ae7e57ef`, `26bb1cc7`, `99cb895f`. The intervening independent metrics bot commit modified only a diagnostic fixture; protected authority did not drift.
- **scoped blockers:** Upload Route workflow still failed at `Start local MinIO` before focused Go/HTTP tests. No production or promotion success is inferred. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved objective 0, executable reviewed request 0, request-bound evidence 0, complete typed eight-domain record 0, independent review 0, human promotion absent.

## Next safe target

Audit the Upload Route reconciler's remaining `Path.read_text` helper and replace its unpinned read with the already-reviewed safe regular-file reader, with real FIFO/symlink/invalid-UTF-8 negatives. Keep the unchanged external MinIO 401, supplemental learning Push/PR reachability and workflow permission blockers scoped; do not treat learning as production authority.
