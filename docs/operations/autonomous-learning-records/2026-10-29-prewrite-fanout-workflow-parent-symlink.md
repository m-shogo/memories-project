# Supplemental OPS learning — reject symlinked workflow parent in prewrite fanout (2026-10-29)

Append-only supplemental learning only; canonical learning authority `docs/operations/AUTONOMOUS-OPS-LEARNING.md`, mandatory contract `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent review or human-promotion evidence.

## Material failure / path alias gap

- **Symptom:** The prewrite fanout auditor rejected a symlinked `.github/workflows` leaf but could accept a normal directory reached through a symlinked `.github` ancestor, reading workflows outside the intended repository path.
- **Observed evidence:** Before the change, `matching_workflows` checked only `directory.is_symlink()` and each workflow leaf. An isolated filesystem fixture showed `root/.github` symlinked to an external directory while `root/.github/workflows.is_symlink()` remained false and `is_dir()` true. No unauthorized production read/write was observed.
- **Verified root cause:** Leaf-only symlink rejection does not detect path aliases in parent components.
- **Failed approach:** Treating the final workflow directory and file as sufficient path identity checks.
- **Correction / executable recurrence guard:** [`9aeca96e`](https://github.com/m-shogo/memories-project/commit/9aeca96ec11d66c0231974f113b19d4695eaaea5) rejects symlinks in the workflow directory or any ancestor. The auditor self-test uses an isolated symlinked `.github` parent; the CI-bound negative suite also requires the real CLI to exit 1 with the exact `PREWRITE TRIGGER AUDIT FAILED: workflow directory missing or symlinked` diagnostic.
- **Retry condition:** Revisit only if repository root/path resolution semantics change, with isolated filesystem and actual CLI fixtures. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical learning large-append transport or human-promotion blockers.

## Material success

- **Observed outcome / evidence:** [Autonomous Learning Guard #40898070662](https://github.com/m-shogo/memories-project/actions/runs/40898070662) completed SUCCESS on exact source `9aeca96ec11d66c0231974f113b19d4695eaaea5`. Logs confirm **162** fail-closed learning negatives, **33** fanout synthetic cases, entrypoint document validation PASS, append-only/clean-source checks PASS, and unchanged conservative counts of 88 operability / 3 rate-limit possible matches.
- **Why safe:** Only the read-only prewrite fanout script and its CI-bound negative validator changed. Test symlinks were created under temporary directories; no workflow YAML, external MinIO, credentials, traffic, recovery evidence or human promotion was touched.
- **Reusable mechanism:** Verify every ancestor component of an authority path for symlink aliases, not only the final leaf; bind the real CLI rejection code and exact diagnostic to a disposable negative fixture.
- **Protected-authority check:** Production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `NO_GO`; canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remain unchanged. Registered/eligible generations, human-approved current objective, executable reviewed request, generation-bound evidence, complete typed eight-domain record, final candidate and human promotion remain absent/separate.

## Next safe target

Fail closed on ambiguous repository-relative path control characters in the prewrite CLI and separately audit indirect workflow_run/workflow_call reachability; do not use direct fanout as proof of complete transitive execution.
