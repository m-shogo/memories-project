# Supplemental OPS learning — strict prewrite HEAD ref snapshot stability (2026-10-31)

Append-only operational learning only. The canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. No part of this record can satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure risk and correction

- **symptom:** A concurrent `HEAD` branch-ref move can change the commit against which `git diff --cached HEAD` is interpreted while the workflow source bytes and `.git/index` remain unchanged. A strict prewrite source proof must not silently accept a moving commit authority.
- **evidence:** At `6ae410aa26e9ec3c1fa3816c5e6f3d92b3b8f4d6`, the auditor checked `.git` and index metadata before/after Git commands but did not bind the `HEAD` commit identity. A disposable Git fixture with two commits sharing the same workflow bytes showed that changing a loose `refs/heads/*` ref after a clean cached workflow diff leaves index/root metadata unchanged and moves `git rev-parse HEAD`. This is a local control, not a production event.
- **rootCauseOrUnknown:** Verified missing before/after `HEAD^{commit}` comparison. ABA ref changes between snapshots and full Git object-store integrity remain outside this bounded proof.
- **failedApproach:** Relying on clean cached workflow diff, raw blob parity and stable `.git/index` metadata as complete commit-ref authority.
- **correction:** [`1bc3e23d`](https://github.com/m-shogo/memories-project/commit/1bc3e23dde9c122ef7660c8d39c1f916a6e23b5b) snapshots a verified 40/64-hex `HEAD^{commit}` before the audit and rechecks the exact commit identity after the workflow source read; mismatch fails closed.
- **recurrenceGuard:** One real-Git negative moves the loose branch ref immediately after a successful cached workflow diff, requires the exact `prewrite Git HEAD changed during audit` diagnostic, verifies the index/root snapshots did not drift, and confirms restoration positive. Canonical fail-closed negatives increase from 584 to **585**.
- **retryCondition:** Reconsider only after a reviewed branch-ref model change or reproducible source-control race with equivalent exact-source negative and restoration positive. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical-learning full-text transport or human approval blockers.

## Material test failure and corrected isolation

- **symptom:** The initial ref-movement fixture failed its own independent-metadata control, even though the auditor detected a ref movement.
- **evidence:** Exact-source [CI #41084762937](https://github.com/m-shogo/memories-project/actions/runs/41084762937) FAILED at `prewrite HEAD ref control also changed metadata identity`. Local nanosecond-resolution stat reproduction confirmed that `git update-ref HEAD` also changes the `.git` directory mtime/ctime, so the fixture was confounded by the earlier metadata guard.
- **rootCauseOrUnknown:** Verified extra filesystem side effects from Git's normal ref update path; not a failure of the new HEAD predicate itself.
- **failedApproach:** Using `git update-ref` to demonstrate a HEAD-only mutation independent of the existing `.git` metadata snapshot guard.
- **correction:** [`939b053a`](https://github.com/m-shogo/memories-project/commit/939b053a668d0d9d30862bc7e090ea1607bceb71) changes only the disposable loose `refs/heads/*` ref file at the controlled subprocess boundary, preserving the index and `.git` root metadata.
- **recurrenceGuard:** The test independently checks unchanged device/inode/mode/size/mtime/ctime for both index and metadata root, plus the changed HEAD and restored success.
- **retryCondition:** Use a normal Git ref-update control only for tests of the combined metadata/ref guard, not for isolation of a HEAD-only drift, unless its filesystem side effects are explicitly neutralized and measured.

## Material success and protected-authority check

- **outcome:** Strict read-only prewrite audit now rejects a moving HEAD ref independently of index and workflow raw-blob stability.
- **evidence:** Exact-source [Autonomous Learning Guard #41085046200](https://github.com/m-shogo/memories-project/actions/runs/41085046200) for `939b053a668d0d9d30862bc7e090ea1607bceb71` completed **SUCCESS**. Logs show append-only PASS, learning contract PASS, **585** canonical fail-closed negatives, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, 52-workflow source-negative reachability, entry-document PASS and read-only completion.
- **whySafe:** Only two read-only Python guard/test files changed. All ref mutations were confined to disposable local test repositories. No workflow YAML, runtime, traffic, credentials, generation/objective, reviewed drill request, recovery evidence, typed eight-domain coverage, independent review or promotion authority changed.
- **reusableMechanism:** Prove source identity at the ref layer separately from filesystem inode and content layers; use controlled fault injection that changes only the intended authority dimension.
- **protectedAuthorityCheck:** Both code commits changed only the read-only auditor and its negative suite. All ten protected authority blobs remain unchanged, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and the six generation/objective/request/evidence/non-resurrection/promotion registries. Canonical learning full text was not transferred; supplemental learning cannot replace it.
- **production boundary:** `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no approved current recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, final candidate, independent review or human promotion.

## Next safe target

Bound the Upload Route Go dependency/CI trigger gap without workflow writes: `httpserver/server.go` imports `httpapi`, whose upload handler imports `internal/upload`; `internal/upload/service.go` and `go.mod` currently reach MinIO-first broad Go CI, not the focused reconcile workflow. Add read-only exact-source classification negatives and preserve the independent MinIO-free focused test path as a blocked requirement until authorized workflow coverage exists.
