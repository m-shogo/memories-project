# Supplemental OPS learning — hidden-suffix Upload Route aliases and CI closeout (2026-10-31)

Append-only operational learning under `contracts/operations/autonomous-learning-system.json`. This record is **never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review, final-candidate or human-promotion evidence.

## Material failure A — suffix filtering masked an unsafe scan alias

- **symptom:** `current_authority_files()` skipped entries with suffixes outside `.go/.json/.py/.yml/.yaml/.md` before checking `path.is_symlink()`. A symlinked directory or file with an unreviewed suffix could be silently omitted rather than fail closed. This is a source-verified latent scope defect, not an observed production write.
- **evidence:** On `e29f00b1`, the source ordered `if path.suffix not in allowed_suffixes: continue` before the alias check. The repository Git tree contained zero tracked symlinks under the five scan roots, so the correction does not knowingly reject a reviewed current input. The disposable negative now creates `docs/operations/learning-alias.txt` pointing to protected canonical learning, after removing the existing `.md` alias so the new case cannot pass because of the old one.
- **rootCauseOrUnknown:** Verified: candidate alias validation was gated by a mutable-file extension filter, although path aliases affect authority scope independently of suffix.
- **failedApproach:** Treating a restricted extension list as a sufficient security boundary before symlink rejection.
- **correction:** [`a9f4c38d`](https://github.com/m-shogo/memories-project/commit/a9f4c38d29963d8ae68282f2231893e055362a75) moves the candidate alias rejection before suffix filtering, after exclusions for explicitly protected learning/fixture/evidence scopes. It extends the actual disposable negative, binds the live proof to the CI entrypoint and adds an executable source mutation that replaces `if path.is_symlink()` with `if False`. The scanner's reviewed fragment SHA-256 was updated in the same commit to `2e6cb80c64fae77f01b3a75cef73e0b9e7ec4b117ca0ca372ee29ca4b8020269`.
- **recurrenceGuard:** The real `.txt` alias negative requires a typed rejection and never mutates protected learning. The entrypoint AST binding requires `prove_learning_scan_boundary` as a direct `main()` call and checks its alias transport, and `has_upload_route_scan_root_binding` enforces alias validation before suffix filtering with a deterministic weakening mutation.
- **retryCondition:** Re-evaluate if scan extension policy, protected-scope exclusions, symlink handling or CI binding changes. This check does not make `Path.rglob` a directory-fd transaction or close every possible concurrent path-swap race.

## Material failure B — negative mutation did not match the actual literal

- **symptom/evidence:** [Autonomous Learning Guard #41190304672](https://github.com/m-shogo/memories-project/actions/runs/41190304672) FAILED on exact `a9f4c38d`: the canonical 601 negative cases passed, but the entrypoint validator reported `upload-route ctime-only negative fixture drift`. The new mutation searched for the standalone literal `"learning-alias.txt"` even though the actual proof contains `"docs/operations/learning-alias.txt"`.
- **rootCauseOrUnknown:** Verified: an unscoped expected literal did not match the full path string in the actual fixture; the negative guard failed closed, rather than silently omitting the new case.
- **failedApproach:** Assuming a filename suffix was a complete Python string literal without inspecting the exact fixture source.
- **correction:** [`6bbb0e73`](https://github.com/m-shogo/memories-project/commit/6bbb0e73b76c26ee805151a52c215a4797752e71) matches and mutates the full `docs/operations/learning-alias.txt` fixture literal, preserving the AST scenario and direct CI binding.
- **recurrenceGuard:** The existing source-negative mutation loop rejects a missing/nonunique literal or a mutation that still passes. Before adding a source mutation, count the exact reviewed source substring and use a function/scenario-scoped match rather than a guessed filename fragment.
- **retryCondition:** Revisit when the negative fixture path, scenario topology or entrypoint source binding changes; do not retry the unchanged failed literal.

## Material failure C — connector operation budget during Git object construction

- **symptom/evidence:** After four verified Git blob creations and one tree creation for `a9f4c38d`, a single oversized connector orchestration returned `Code Mode exceeded the maximum number of tool calls` before creating a commit or moving `so`.
- **rootCauseOrUnknown:** Verified: the orchestration exceeded the connector call budget; no branch update was attempted by the interrupted call. The exact undocumented budget is unknown.
- **failedApproach:** Combining all source reads, blob writes, tree construction, commit creation and branch CAS publication in one connector execution.
- **correction:** Re-read `so`, confirmed the original HEAD `e29f00b1` and unchanged target blob, verified all four entries in the unattached tree `4afbe572`, then created the commit and published via expected-head CAS in a smaller independent call.
- **recurrenceGuard:** Separate bounded Git object preparation from branch publication, verify tree entries and re-read latest branch authority before commit/ref updates. Never assume a failed connector call implies a branch mutation, and never blindly retry an unchanged large orchestration.
- **retryCondition:** Revisit the single-call strategy only if the connector operation budget/capability materially changes.

## Material safe success

- **outcome/evidence:** [Autonomous Learning Guard #41190587272](https://github.com/m-shogo/memories-project/actions/runs/41190587272) completed **SUCCESS** on exact corrected code HEAD `6bbb0e73b76c26ee805151a52c215a4797752e71`. Job logs prove 601 canonical fail-closed negatives, 39 supplemental history fixtures, the actual Upload Route append-only/symlink negative, 52 workflow / 63 direct Python command / 204 reachability fixtures, 195 fanout synthetics, 1,186 helper-ancestor negative mutations and append-only/read-only PASS. Operability Contracts and the independent rate-limit, backup/restore and observability policy workflows also completed SUCCESS on the same source HEAD.
- **whySafe:** Changes were limited to the existing Upload Route Python scanner, disposable negative, reviewed fragment digest and read-only CI entrypoint. The test uses a temporary workspace; no real production/recovery evidence, workflow YAML, credentials, traffic, readiness or human approval was written.
- **reusableMechanism:** Validate authority aliases before convenience filters, pair a real external-canary fixture with a positive-control ordinary file, and bind the actual negative and source weakening mutation to independent pre-MinIO CI.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation/objective/drill-request/generation-evidence/non-resurrection/promotion registries `bfd1b045`, `f4d74f33`, `acebcd02`, `ae7e57ef`, `26bb1cc7`, `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0. No approved recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review, final candidate or human promotion exists. Reviewed requests are planning authority only; preflight requires unsuperseded eligible generations from distinct environments and explicit current human approval.

## Scoped blockers and next safe target

[Upload Route #41190304660](https://github.com/m-shogo/memories-project/actions/runs/41190304660) failed at the known MinIO bootstrap, before focused Go/HTTP tests; no success for that path is claimed. Workflow write permission and supplemental-learning-only Push/PR CI reachability remain blocked. No unchanged external or human blocker was manually retried.

Next safe target: design a pinned directory-fd/no-follow atomic publication path and a deterministic parent-swap canary for `atomic_write_bytes`, without assuming atomic leaf CAS. Independently review pre-MinIO focused Go test reachability while workflow write permission remains scoped.
