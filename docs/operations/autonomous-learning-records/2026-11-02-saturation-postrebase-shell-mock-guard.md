# Supplemental OPS learning — saturation post-rebase shell guard semantics (2026-11-02)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Local mocked shell execution and CI are not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material scoped failure mode

- **symptom:** A lexical post-rebase guard marker alone cannot establish that the shell function actually rejects divergent ancestry, changed critical paths, or a failed fetch. A no-op body or an `exit 0` in a failure branch would be a false-positive guard.
- **evidence:** Reviewed `.github/workflows/controlled-saturation-repeatability.yml` blob `1f4b20c0` contains `verify_critical_source` immediately after `git pull --rebase origin so`; its body checks `merge-base --is-ancestor` and a critical-path `git diff`, exiting 75 on failed ancestry/diff. The preexisting negative suite only pinned lexical body tokens/adjacency. No actual stale publication was observed.
- **rootCauseOrUnknown:** The lexical-versus-executable distinction is verified. Actual real-world exploitability and permissions of the other three soak publishers remain unknown.
- **failedApproach:** Treating a source marker and a `git diff` string as sufficient execution evidence, or executing an arbitrary changed workflow body with real Git network access.
- **correction:** [`0d618f27`](https://github.com/m-shogo/memories-project/commit/0d618f27a97e6210f2a795ed77d41f8a194c2be4) adds `prove_saturation_postrebase_shell_semantics` to the existing read-only autonomous learning negative suite. It exact-pins the reviewed shell function body before executing it with a local Bash `git()` mock, isolated environment and temporary push transcript.
- **recurrenceGuard:** Positive noncritical descendant must exit 0 and emit exactly one synthetic push marker. Divergent ancestry and critical drift must exit 75 without a push; failed fetch must be nonzero without a push. Mutation controls deliberately bypass ancestry, bypass critical diff, or replace `exit 75` with `exit 0`, proving the fixture distinguishes the unsafe behavior.
- **retryCondition:** Revisit if the reviewed function body, workflow permission model, shell semantics, or exact-source CI outcome changes. Writer changes remain blocked until independent source-lease, shell control-flow, permissions, bounded reconcile and CI review.

## Material safe progress

- **outcome:** One read-only negative-suite code commit was accepted on `so`. Local isolated Bash mock prototype passed four normal/failure scenarios (safe, divergent, critical, fetch failure). Exact-source [Autonomous Learning Guard #41443158752](https://github.com/m-shogo/memories-project/actions/runs/41443158752) was **in progress** at record creation; this record does not claim CI SUCCESS.
- **evidence:** Re-read of `0d618f27` confirmed the exact source-body pin, isolated Bash function and three mutation cases; its sole code target is `scripts/validate-autonomous-learning-system-negative.py`. The real publisher workflows were not executed or modified.
- **whySafe:** The mock shadows all `git` calls, has no credentials, uses a temporary directory and never pushes to the real remote. It cannot satisfy a production gate.
- **reusableMechanism:** Combine immutable source-body binding with isolated shell behavior checks and mutation controls, keeping lexical inventories separate from executable evidence.
- **protectedAuthorityCheck:** Post-code Git tree re-read found all ten protected authority blob SHAs unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, contract `87712ea9`.

## Next safe target

Confirm the exact-source CI outcome and, independently, pin the critical-path array that the reviewed guard actually checks. The three unguarded soak publisher rebase paths remain scoped unknowns, not a reason to mutate write-capable workflows without authorization. Maintain `productionDecision=NO_GO`.
