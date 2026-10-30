# Supplemental OPS learning — multiline YAML flow and CI recovery (2026-10-30)

Append-only supplemental history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed executable request, request-bound recovery evidence, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure — prospective multiline-flow trigger undercount

- **Symptom:** The prewrite direct-trigger matcher could report no push/PR trigger for valid YAML `on: [\n  *events\n]` or a multiline flow mapping with a merge alias, even though those values may resolve to push/PR events. This is a static-parser defect, not an observed production incident.
- **Observed evidence:** The previous narrow parser only inspected first-line inline values and literal block event mappings. Local Python reproductions returned false for multiline aliases, escaped event scalars and flow-map merge values. The actual checked-out workflow tree was not modified.
- **Verified root cause:** Multiline flow collections and comment-separated flow values were outside the reviewed grammar but were silently classified as non-matches.
- **Failed approach:** Treating absence of a literal same-line event token as proof of a dispatch-only YAML flow collection.
- **Correction:** [`41aca98f`](https://github.com/m-shogo/memories-project/commit/41aca98f1cfa1c3aba61b76c6c5295b88615afc6) conservatively matches incomplete first-line flow collections and flow values after comment/blank lines.
- **Executable recurrence guard:** Eight ordered, identity-pinned positive/negative fixtures were added both to the audit self-test and the actual CLI negative suite; existing single-line dispatch-only forms remain non-matches. The nested literal fixture is deliberately conservative, not proof of real trigger dispatch.
- **Retry condition:** Revisit only after an exact-source CI counterexample or a reviewed semantics-preserving YAML parser changes the precondition; do not infer transitive workflow-call reachability from direct matching.

## Material failure — over-precise fixture expectation

- **Symptom:** Initial exact-source [Autonomous Learning Guard #41002118305](https://github.com/m-shogo/memories-project/actions/runs/41002118305) FAILED on `nested flow literal`.
- **Observed evidence:** The CI traceback identifies `prewrite fanout CLI undercount/misclassification: nested flow literal`. The existing conservative regex for indented `on:` keys also matches an indented `on: [` line within a YAML literal block.
- **Verified root cause:** The newly added negative expected an exact YAML non-match, whereas the pre-existing matcher intentionally over-approximates indented event-key syntax. This was a test expectation error, not a new production failure.
- **Failed approach:** Requiring a precise zero-match result from an explicitly conservative parser without checking the prior guard's diagnostic precedence.
- **Correction:** [`373b8dce`](https://github.com/m-shogo/memories-project/commit/373b8dced10f10256bd72451061b8e5183b21b79) renames the case `nested flow literal conservative` and expects the existing bounded conservative match; it does not weaken the indented-key guard.
- **Executable recurrence guard:** The case remains in both exact-identity fixture inventories and actual CLI execution. [Exact-source CI #41002287200](https://github.com/m-shogo/memories-project/actions/runs/41002287200) completed SUCCESS with 419 reported canonical fail-closed negatives and 1,186 helper-ancestor mutations.
- **Retry condition:** Change this expectation only if a separately reviewed YAML-aware implementation can prove that nested literal syntax is safely excluded without introducing an event undercount.

## Material success — exact-source CI visibility recovered

- **Observed outcome/evidence:** The previously reported PR-only workflow-run visibility limitation was resolved for this read-only query by GitHub REST `GET /repos/m-shogo/memories-project/actions/runs?head_sha=<SHA>`. It returned completed SUCCESS [#40996644840](https://github.com/m-shogo/memories-project/actions/runs/40996644840) for prior exact code SHA `9053e612`, SUCCESS [#40996448599](https://github.com/m-shogo/memories-project/actions/runs/40996448599) for `db548021`, and SUCCESS [#41002287200](https://github.com/m-shogo/memories-project/actions/runs/41002287200) for `373b8dce`. The first attempted `41aca98f` run was correctly recorded as FAILED, not masked by subsequent success.
- **Why safe:** This uses read-only workflow-run and job-log retrieval, requires exact `head_sha`, `status=completed` and `conclusion=success`, and cannot manufacture production evidence or alter a workflow.
- **Reusable mechanism:** Query Actions run collections by exact head SHA and verify run ID, conclusion and job logs; never treat empty combined statuses or a PR-filtered wrapper as evidence of push-run success. If a new exact SHA has no completed run, mark CI UNVERIFIED.
- **Protected-authority check:** The code diff from `e10e2710` through `373b8dce` touched only two read-only Python validators. All ten protected authority Blob SHAs remained unchanged, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639` and OPS-P0-007 snapshot `dbaa36b0`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, with registered/eligible generations 0/0 and no human promotion authority.

## Next safe target

Verify block-style scalar/alias event values, reconcile all fixture counts with executed tests, and continue MinIO-independent Go-only CI reachability plus complete Go/Python transitive dependency and trigger coverage audits. The canonical learning large-file transport, workflow-write permission, Quay MinIO HTTP 401 and human approval blockers have unchanged preconditions and were not retried.
