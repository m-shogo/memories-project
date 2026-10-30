# Supplemental OPS learning — workflow parent symlink-swap identity guard (2026-10-30)

Append-only operational learning only. The canonical learning authority and mandatory contract remain unchanged. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved objective, executable reviewed request, request-bound recovery, complete typed eight-domain non-resurrection, independent review or human-promotion evidence.

## Material failure risk and executable recurrence prevention

- **symptom:** The prewrite workflow auditor checked `.github` for symlinks before enumeration, and later verified workflow leaf and `.github/workflows` directory identity, but did not recheck the `.github` ancestor. A parent-directory rename followed by a symlink to the same directory could preserve the workflow leaf and directory inodes while changing the path authority during the audit.
- **evidence:** Source inspection at `356db00c` showed only a pre-enumeration ancestor symlink check. A disposable local filesystem control confirmed that the leaf inode and workflow-directory inode remain identical after replacing the `.github` path with a symlink to the renamed original directory. No production incident or production-path mutation was observed.
- **rootCauseOrUnknown:** Verified absence of a final ancestor identity check; checking only a stable leaf inode and workflow directory inode does not prove an unchanged ancestor path.
- **failedApproach:** Treating a one-time parent symlink precheck and a stable workflow-directory inode as sufficient checkout-path identity across enumeration and read.
- **correction:** [`239ff336`](https://github.com/m-shogo/memories-project/commit/239ff336ac6833397e6add24c05fb932ae09aba6) snapshots the `.github` parent metadata and fails closed if its final type, device, inode, mtime or ctime differs before accepting direct matches.
- **recurrenceGuard:** The CI-reachable negative validator creates a disposable checkout-like workflow tree, proves a clean baseline, then performs an actual `.github` rename-and-symlink substitution while the reader executes. It requires the exact `workflow directory parent changed during audit` diagnostic and verifies the symlink swap occurred. Fixture bytes are explicitly checked to end in LF (hexadecimal `0A`), preventing a previously recorded over-escaping failure.
- **retryCondition:** Revisit only if the source identity algorithm or supported filesystem semantics change; this remains a bounded read-only audit and does not claim complete concurrency atomicity, workflow trigger closure, or permission to write protected workflows.

## Observed success and protected authority

- **outcome:** [Autonomous Learning Guard #41041692121](https://github.com/m-shogo/memories-project/actions/runs/41041692121) completed **SUCCESS** on exact source `239ff336ac6833397e6add24c05fb932ae09aba6`.
- **evidence:** CI logs report append-only and learning contract PASS, 517 canonical fail-closed negatives, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only PASS. The new real parent-swap fixture runs inside the negative harness and is not separately counted in the 517.
- **whySafe:** Only the read-only Python fanout auditor and CI-reachable negative validator changed. The symlink swap runs in a disposable temporary directory; no workflow YAML, production runtime, traffic, credential, generation, recovery, typed eight-domain review or promotion authority was modified.
- **reusableMechanism:** Protect ancestor path identity separately from stable leaf and directory inode identity, with a real filesystem alias substitution at the exact reader boundary.
- **protectedAuthorityCheck:** GitHub comparison from `356db00c` to `239ff336` lists only two Python scripts. All ten protected authority blobs remain unchanged, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639` and OPS-P0-007 snapshot `dbaa36b0`. `productionDecision=NO_GO`; OPS-P0-007 is `PREREQUISITES_BLOCKED` with registered/eligible generations 0/0, approved objective 0, executable reviewed request 0, request-bound evidence 0, complete typed eight-domain record 0, final candidate 0 and no separate human promotion.

## Next safe target

Complete Go/Python transitive input closure and exact Push/PR trigger coverage without modifying workflow YAML under the existing permission blocker. Focused Upload Route Go tests remain after MinIO startup in current CI; do not retry unchanged Quay HTTP 401, canonical large-file transfer or human approval. This learning-only HEAD does not establish a full production admission chain SUCCESS.
