# Supplemental OPS learning — post-read parent metadata and nonregular leaf no-open guards (2026-11-01)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final recovery candidate or human promotion evidence.

## Material failure class 1 — unproved post-read metadata cleanup

- **symptom:** The existing canonical parent-chain negative suite checked chmod/symlink drift but did not inject malformed *post-read* parent `lstat` return objects or verify descriptor closure under that fault. This is a negative-proof coverage gap, not an observed production defect.
- **evidence:** Source at prior HEAD `a991f5d3` contained post-open chmod and parent-swap cases but no second-`lstat` `None`/missing-`st_mode` injection. The reader's outer `except (OSError, ValueError, TypeError, AttributeError)` and owned-FD `finally` already handled this path, but their joint behavior lacked direct proof.
- **rootCauseOrUnknown:** Verified missing executable negative coverage for malformed post-read parent metadata and owned-FD cleanup. No runtime defect was reproduced in the unmodified reader.
- **failedApproach:** Treating the existence of a broad outer exception handler and adjacent parent-drift tests as proof of post-read malformed metadata and resource ownership safety.
- **correction:** [`12d84870`](https://github.com/m-shogo/memories-project/commit/12d84870d72e7b03dec92631aa449db40403b62d) adds two deterministic malformed second-`lstat` cases. [`1f4a5364`](https://github.com/m-shogo/memories-project/commit/1f4a53643bd76fb5de58351af8121db2e3f06668) adds exact owned-descriptor acquisition inventory and EBADF-after-cleanup proof.
- **recurrenceGuard:** Existing CI-bound direct canonical reader negative now requires precisely two parent metadata reads, one owned leaf descriptor, exact unreadable-authority rejection, owned FD closure, external FD canary preservation and subsequent valid-read recovery for `None` and missing-`st_mode` post-read returns.
- **retryCondition:** Revisit when the reader's post-read metadata ordering, FD ownership or cleanup semantics change, or when an observed new metadata failure class appears. No unchanged external dependency/permission retry.

### Material success 1

- **outcome:** Both malformed post-read parent metadata cases fail closed with exact diagnostics and no owned FD left open.
- **evidence:** Exact-source [Autonomous Learning Guard #41297450245](https://github.com/m-shogo/memories-project/actions/runs/41297450245) SUCCESS on `12d84870` and [#41297470066](https://github.com/m-shogo/memories-project/actions/runs/41297470066) SUCCESS on `1f4a5364`. Both job logs show canonical contract PASS, 601 fail-closed negatives PASS, Memory OS entrypoint PASS and 1,186 helper ancestor mutations PASS.
- **whySafe:** Only the existing read-only negative validator and disposable temporary fixtures changed. No production data, real credentials, traffic, recovery evidence, reviewed objectives or promotion authorities were modified.
- **reusableMechanism:** Fault-inject a *second* metadata read after descriptor acquisition; require an owned-FD inventory and EBADF proof rather than inferring cleanup from an external canary alone.
- **protectedAuthorityCheck:** Ten protected blobs unchanged at each write; `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and approved objectives 0.

## Material failure class 2 — nonregular rejection without proof of pre-open ordering

- **symptom:** Existing direct FIFO and symlink negatives asserted the correct rejection diagnostics but did not prove the reader avoided attempting `os.open` on those nonregular leaf paths.
- **evidence:** At `1f4a5364`, both negatives called the reader directly after creating the actual FIFO or dangling symlink; their assertions did not instrument descriptor acquisition. An implementation could still attempt a nonblocking FIFO or `O_NOFOLLOW` open and reject later while passing these existing tests.
- **rootCauseOrUnknown:** Verified negative-proof gap in side-effect ordering, not an observed production incident.
- **failedApproach:** Treating the correct final error text as proof that a potentially unsafe acquisition boundary was never crossed.
- **correction:** [`79c72f45`](https://github.com/m-shogo/memories-project/commit/79c72f45e87c535dd6f30e834dc37e81daa07368) wraps each actual FIFO/symlink direct-reader negative in an `os.open` spy that raises if the canonical leaf is opened.
- **recurrenceGuard:** Exact existing diagnostics remain mandatory (FIFO: `canonical authority changed during read`; symlink: `unreadable authority`) **and** the negative suite now rejects any descriptor-acquisition attempt for either leaf type. No test weakens the error expectation to a generic failure.
- **retryCondition:** Revalidate on preflight type ordering, `os.open` semantics, or exact diagnostic authority changes. Do not repeat the known unified nonregular-diagnostic regression.

### Material success 2

- **outcome:** Actual FIFO and dangling symlink leaves are rejected before `os.open` while retaining their distinct diagnostics.
- **evidence:** Exact-source [Autonomous Learning Guard #41297819577](https://github.com/m-shogo/memories-project/actions/runs/41297819577), job `124822287539`, SUCCESS on `79c72f45`. Logs show append-only PASS, canonical learning contract PASS, 601 fail-closed negatives PASS, source-negative CI reachability 52 workflows / 63 direct Python commands / 204 negative fixtures, prewrite fanout 195 synthetic cases PASS, Memory OS entrypoint PASS and helper ancestor 1,186 negative mutations PASS.
- **whySafe:** Only synthetic/direct temporary-file tests in the existing CI-reachable negative suite changed; no workflow YAML, runtime production path, evidence or promotion authority changed.
- **reusableMechanism:** Pair exact diagnostic checks with an explicit forbidden-operation spy to prove pre-open ordering; retain positive control and recovery checks.
- **protectedAuthorityCheck:** Canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation `bfd1b045`, objectives `f4d74f33`, reviewed request `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain non-resurrection `26bb1cc7`, promotion review `99cb895f` remained unchanged. `productionDecision=NO_GO`; OPS-P0-007 stays `PREREQUISITES_BLOCKED`; semantically eligible generations remain distinct from registered generations; preflight still requires unsuperseded eligible generations from distinct environments plus explicitly human-approved current objective; reviewed requests are planning-only until executable; new generation recovery evidence remains request-bound; typed eight-domain coverage and independent review remain required; human production promotion is separate and non-automatic. Learning cannot satisfy production/backup/restore/RPO/RTO/skew/drill/credential/traffic/readiness/promotion gates.

## Next safe target

Audit leaf post-read malformed metadata and parent-chain ABA swaps for a deterministic guard without claiming an unimplemented pinned-parent acquisition model. Independently seek an authorized pre-MinIO non-skipped real Focused Go Test path; existing Quay MinIO HTTP 401, workflow-write permissions and missing human production evidence remain scoped blockers, not reasons to stop unrelated safe work.
