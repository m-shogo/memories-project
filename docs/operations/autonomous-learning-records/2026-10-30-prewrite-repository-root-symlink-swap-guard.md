# Supplemental OPS learning — repository-root symlink-swap identity guard (2026-10-30)

Append-only operational learning only; canonical learning authority and mandatory contract remain unchanged. This record **cannot** satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery, complete typed eight-domain non-resurrection, independent review or human-promotion gates.

## Material failure risk and executable recurrence prevention

- **symptom:** The prewrite fanout audit now reconciled the workflow directory and `.github` parent, but did not recheck the repository-root pathname after reading workflow files. Renaming the checkout root and substituting a symlink to the same tree could leave all descendant inodes stable while changing the root path identity.
- **evidence:** Source inspection at `cbbe27e5` showed no before/after `repo_root.lstat` comparison. A disposable local filesystem control demonstrated unchanged workflow leaf and directory inodes after a root rename/symlink substitution. This is a prospective source-identity gap, **not** an observed production incident.
- **rootCauseOrUnknown:** Verified missing final checkout-root identity reconciliation independent of descendant inode checks.
- **failedApproach:** Treating an initial root/ancestor symlink check and stable workflow descendants as sufficient proof that the checkout root itself was unchanged during the audit.
- **correction:** [`25b8f5df`](https://github.com/m-shogo/memories-project/commit/25b8f5df9ad50b9687f173d69af27af9b6dd0bcb) captures repository-root type, device, inode, mtime and ctime before enumeration, then rejects a changed or symlinked root at the final boundary.
- **recurrenceGuard:** The CI-reachable negative validator constructs a disposable checkout-like tree, verifies an LF-terminated real workflow and a normal direct-match positive, then renames the root and creates a symlink to its original contents during the reader. It requires exact `prewrite repository root changed during audit` rejection and verifies the swap occurred. The fixture includes a byte assertion for final LF (hexadecimal `0A`), avoiding the previously recorded escaping failure.
- **retryCondition:** Revisit only if repository-root identity or filesystem semantics change, with exact-source CI and protected-authority comparison. This is a bounded read-only audit, not a complete filesystem snapshot, proof of CI transitive closure, or authorization to change workflows.

## Material success and protected authority

- **outcome:** [Autonomous Learning Guard #41042370000](https://github.com/m-shogo/memories-project/actions/runs/41042370000) completed **SUCCESS** on exact source `25b8f5df9ad50b9687f173d69af27af9b6dd0bcb`.
- **evidence:** CI job logs confirm append-only and learning contract PASS, 517 canonical fail-closed negatives, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only PASS. The new root-swap negative executes inside the harness but is not separately counted among the 517.
- **whySafe:** Only the read-only prewrite auditor and CI-reachable negative validator changed. The root substitution occurs solely in a disposable temporary directory; no workflow YAML, production runtime, credential, traffic, backup/restore, generation/objective, recovery evidence, typed eight-domain review or promotion authority was changed.
- **reusableMechanism:** Treat checkout-root identity as an independent source authority from descendant inode identity, and test a real root alias substitution at the reader boundary.
- **protectedAuthorityCheck:** GitHub comparison from `cbbe27e5` to `25b8f5df` lists only two Python scripts. All ten protected authorities remain unchanged, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639` and OPS-P0-007 snapshot `dbaa36b0`. `productionDecision=NO_GO`; OPS-P0-007 is `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, approved objective 0, executable reviewed request 0, request-bound evidence 0, complete typed eight-domain record 0, final candidate 0 and no separate human promotion.

## Next safe target

Audit the remaining ancestor-chain source identity and complete Go/Python transitive input plus Push/PR trigger coverage before any workflow change. Focused Upload Route Go tests remain after MinIO startup in existing workflows. Do not retry unchanged Quay 401, workflow-write permission, canonical learning transport or human approval. A learning-only HEAD does not prove full production admission SUCCESS.
