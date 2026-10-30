# Supplemental OPS learning — strict prewrite Git metadata/index source authority (2026-10-31)

Append-only operational learning only. The canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure risk and executable correction

- **symptom:** Strict Git-index workflow-source proof could read an index pathname replaceable through a group/world-writable `.git` directory, or an index inode writable/aliased through an unreviewed hardlink or symlink.
- **evidence:** At baseline `346d3111283bf533d2a5b860afbf16bc325c4afd`, the auditor rejected `.git` symlink/gitdir-file roots and Git environment overrides but did not inspect `.git` write permissions or `.git/index` file type, link count and write permissions. A disposable Git repository demonstrated that `git ls-files --stage` still succeeds with group/world-writable metadata root or index. No production compromise was observed.
- **rootCauseOrUnknown:** Verified missing metadata root/index filesystem authority predicates; the actual runner's group trust and other Git internals' write-authority closure remain outside this scoped proof.
- **failedApproach:** Treating the existence of a normal `.git` directory and a clean index/blob comparison as sufficient when another principal could replace or mutate the index.
- **correction:** [`d0926fbb`](https://github.com/m-shogo/memories-project/commit/d0926fbb2f6e03586bd53bf71d3ad667a1f0d1c2) rejects group/world-writable `.git`, and requires `.git/index` to be a unique regular non-group/world-writable inode before running Git inspection.
- **recurrenceGuard:** Six actual strict-CLI negatives cover group/world-writable metadata directory, group/world-writable index, index hardlink and index symlink. Each checks exact failure/empty stdout and a clean restoration positive. Printed canonical fail-closed negatives increase from 574 to **580**.
- **retryCondition:** Only reconsider after an independently reviewed shared-repository/index ownership model, changed authority precondition, complete positive/negative controls and exact-source CI. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical-learning transport or human promotion blockers.

## Material success and protected-authority check

- **outcome:** Read-only Git metadata root/index authority guard and six CLI negatives landed on `so` at `d0926fbb2f6e03586bd53bf71d3ad667a1f0d1c2`.
- **evidence:** Exact-source [Autonomous Learning Guard #41081250318](https://github.com/m-shogo/memories-project/actions/runs/41081250318) completed SUCCESS. Job logs show append-only PASS, learning contract PASS, **580** canonical negatives, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document PASS and clean/read-only completion.
- **whySafe:** Only the read-only auditor and CI-bound negative validator changed. All Git metadata chmod/link mutations were executed in disposable repositories, not the production checkout or GitHub branch authority. No workflow YAML, service runtime, credentials, traffic, recovery, generation/objective, typed eight-domain or promotion authority changed.
- **reusableMechanism:** Validate source metadata ownership at the directory and index inode level before trusting Git index contents, and test both writable modes and alternate inode names through actual strict CLI execution.
- **protectedAuthorityCheck:** GitHub compare for the code commit lists exactly the two read-only Python scripts. Ten protected authority paths remain unchanged, including canonical learning blob `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639` and OPS-P0-007 snapshot `dbaa36b0`. Full canonical learning text was not transferred; the blob identity and supplemental history do not replace it.
- **production boundary:** `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, no human-approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate, independent review or human promotion.

## Next safe target

Detect **active Git split-index** in strict prewrite source authority. A separate `sharedindex.*` object is not covered by the ordinary `.git/index` inode check. Reject active split-index while allowing stale sharedindex files after explicit deactivation, with a real Git negative/positive.
