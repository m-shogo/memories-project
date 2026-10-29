# Supplemental OPS learning — learning-guard event shadow and branch filter (2026-10-29)

Append-only supplemental learning only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, recovery generation/objective, typed eight-domain non-resurrection, independent review or human-promotion gates.

## Material failure / previously unguarded mutation class

- **Symptom:** A quoted duplicate `on`, `push` or `pull_request` YAML mapping, or a changed/missing `branches: [so]` mapping, could invalidate a claimed Autonomous Learning Guard event trigger while the existing path-only classifier still accepted the reviewed list.
- **Observed evidence:** At starting `so` head `d99fa69b931415f7bc23e2f5cbd5530e5bf9fdff`, `autonomous_learning_guard_event_paths` counted only literal unquoted event keys and did not inspect the event block preceding `paths:`. The actual reviewed workflow has `branches: [so]` for both push and pull_request. This was a static coverage defect, not an observed production failure.
- **Verified root cause:** Event-path identity alone does not prove unique YAML event authority or the branch scope under which that event is eligible to run.
- **Failed approach:** Treating a literal `on:` and event key count plus path-list equality as sufficient proof of CI event-filter authority.
- **Correction:** [`dc59a0ff`](https://github.com/m-shogo/memories-project/commit/dc59a0ff4785903c4e355398b0fab095559d3a3b) now rejects quoted or duplicate root/event keys and requires the exact reviewed `branches: [so]` prefix for each event before accepting the path list.
- **Executable recurrence guard:** Nine added semantic negative fixtures cover missing PR event, wildcard path, single/double-quoted `on` shadows, quoted push/PR shadows, wrong push branch, missing PR branch and shadowed branch. Each must reject with the exact `Autonomous Learning Guard event trigger authority changed` diagnostic (the wildcard/missing-event cases were previously present and were upgraded to the unified fixture table).
- **Retry condition:** Revisit only after a separately reviewed event/branch authority change, with exact-source CI and protected-authority checks. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permission, canonical large-learning transport or human-promotion blockers.

## Material success

- **Outcome / evidence:** [Autonomous Learning Guard #40895252742](https://github.com/m-shogo/memories-project/actions/runs/40895252742) completed **SUCCESS** for exact source `dc59a0ff4785903c4e355398b0fab095559d3a3b`. Logs show canonical contract validation PASS, 146 fail-closed canonical negative cases, prewrite fanout audit PASS (16 synthetic cases), entrypoint document validation PASS, and the independent helper-ancestor step completed successfully.
- **Why safe:** Only a read-only CI-bound negative validator was changed (+21/-8 lines); no workflow, production authority, credentials, traffic, recovery evidence or promotion was written.
- **Reusable mechanism:** Parse both event-key uniqueness and branch-filter scope before asserting trigger-path reachability; bind mutations to exact expected diagnostics and independently verify the real workflow source.
- **Protected-authority check:** Production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `NO_GO`; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` are unchanged. OPS-P0-007 remains blocked; no registered or semantically eligible generations, approved current recovery objective, executable reviewed request, generation-bound evidence, complete typed eight-domain record, final candidate or human promotion was admitted.

## Next safe target

Strengthen the read-only prewrite workflow fanout auditor against duplicate event mappings, unresolved aliases, inline path comments and GitHub minimatch constructs that Python `fnmatch` cannot safely classify. Verify its actual CLI with bounded synthetic fixtures before trusting a narrowed fanout estimate.
