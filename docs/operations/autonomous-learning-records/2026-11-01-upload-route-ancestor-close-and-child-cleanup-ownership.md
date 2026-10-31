# Supplemental OPS learning — ancestor FD handoff and child cleanup ownership (2026-11-01)

Append-only operational execution learning under `contracts/operations/autonomous-learning-system.json`. It is **never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final recovery candidate or human-promotion evidence. Canonical learning remains unchanged.

## Material failure A — ancestor FD could be closed twice after an ambiguous close

- **symptom:** `open_pinned_parent` retained the old ancestor FD number in its outer cleanup scope after an inner `os.close(fd)` failed. A post-effect close failure could therefore cause the outer exception handler to close a recycled descriptor belonging to an independent file. No live production corruption was observed.
- **evidence:** Baseline `8fc9bded` source closed the same `fd` in the inner traversal and outer exception handler. The new disposable proof deliberately closes the ancestor, reuses its numeric FD for an independent canary and raises an error; it requires that the canary FD remain open.
- **rootCauseOrUnknown:** Verified ambiguous FD ownership after the inner close and unconditional outer retry against the same numeric FD. A failed close does not prove whether its syscall effect occurred.
- **failedApproach:** Retry an ambiguously completed close, or treat the old descriptor number as still owned after a close exception.
- **correction:** [`5f2463f6`](https://github.com/m-shogo/memories-project/commit/5f2463f66d3fe999d52e3542fce7c607cfa71fd0) transfers ownership to a local `closing_fd` and sets outer `fd=None` *before* closing. It closes the newly opened child at most once, preserves the primary failure and propagates bounded ancestor/child cleanup uncertainty notes.
- **recurrenceGuard:** Two isolated pre-/post-effect ancestor-close cases in the CI-reached Upload Route rollback negative, with an independent recycled-FD canary; the canonical AST binding requires the ownership release and actual test loop, and source-negative mutations reject missing release or disabled injection.
- **retryCondition:** Revalidate on changes to descriptor traversal, ownership handoff, `os.close` fault behavior or the reviewed source-negative binding. Never retry an ambiguous FD close without independently proven ownership.

## Material failure B — source-negative marker collision and obsolete descriptor expectation

- **symptom:** Initial exact-source CI for `5f2463f6` FAILED with `upload-route ctime-only negative fixture drift`. After correcting the marker and opener binding, `4ea6cb58` FAILED with `upload-route learning scan guard missing verified PASS: negative-proof-failure`.
- **evidence:** [Autonomous Learning Guard #41238469464](https://github.com/m-shogo/memories-project/actions/runs/41238469464) and other entrypoint consumers rejected the first source. [Autonomous Learning Guard #41238657307](https://github.com/m-shogo/memories-project/actions/runs/41238657307) rejected the second. Source inspection identified a duplicate `synthetic parent traversal close failure` marker and the old AST opener requirement `os.close(fd)`; the existing traversal test also demanded both FDs be closed even when the first close failed before its effect.
- **rootCauseOrUnknown:** Verified full-source mutation marker collision and stale source binding, followed by a test expectation inconsistent with deliberately unknown pre-effect close ownership.
- **failedApproach:** Add a fault with an existing globally unique mutation marker without counting all source occurrences; require leak-free closure of a descriptor whose close was synthetically prevented.
- **correction:** [`4ea6cb58`](https://github.com/m-shogo/memories-project/commit/4ea6cb589386dec2228e1a7b80d8b1c231fae543) scopes the new fault marker and updates the AST opener/source-negative checks. [`156925f8`](https://github.com/m-shogo/memories-project/commit/156925f8937faf714e8d12cb39f8ada29b7ba842) corrects the old test to require child closure but explicitly retain and test-only reclaim the uncertain ancestor FD.
- **recurrenceGuard:** Unique source mutation targets, exact two-case AST loop checks, a negative that removes the FD ownership release, and an executable test that distinguishes the old ancestor from the newly opened child. Keep the CI entrypoint within 4,096 lines.
- **retryCondition:** Revisit only when the source-negative target inventory, AST normalization, descriptor fault semantics or existing proof expectations change. Do not repeat the colliding marker or assume close completion.

## Material success A — exact-source recovery and authority preservation

- **outcome:** The corrected ancestor handoff no longer closes a recycled canary FD in either isolated close-fault ordering; the prior traversal proof now explicitly distinguishes uncertain ancestor ownership from released child ownership.
- **evidence:** [Autonomous Learning Guard #41238820391](https://github.com/m-shogo/memories-project/actions/runs/41238820391), [Operability Contracts #41238820394](https://github.com/m-shogo/memories-project/actions/runs/41238820394) and [Reconcile Backup Restore Policy #41238820327](https://github.com/m-shogo/memories-project/actions/runs/41238820327) completed SUCCESS on exact code HEAD `156925f8`.
- **whySafe:** The correction affects descriptor handling and disposable read-only negative tests, preserving no-follow, pinned directory, inode, rollback and publication guards. The pre-effect FD may remain open after an ambiguous close and is not claimed leak-free; the test alone reclaims it after restoring the fault hook.
- **reusableMechanism:** Release FD ownership before a potentially ambiguous close; never retry a stale numeric descriptor, and test both syscall-effect orderings with an independent canary.
- **protectedAuthorityCheck:** All ten canonical protected Git blob SHAs remained unchanged; no generation, objective, recovery evidence, credential, traffic, readiness or promotion was fabricated.

## Material success B — child cleanup failure cannot consume recycled canary

- **outcome:** The independent child-FD cleanup fault now has executable before-/after-effect coverage. The original ancestor-close failure and bounded secondary cleanup uncertainty survive; an FD reused by the canary is not closed again.
- **evidence:** [`9fa87884`](https://github.com/m-shogo/memories-project/commit/9fa878844655f6dddd39c9eb1b85cc4ef3c2d0d5) adds a distinct two-case disposable proof and source-negative AST binding. [Autonomous Learning Guard #41239171399](https://github.com/m-shogo/memories-project/actions/runs/41239171399) and [Operability Contracts #41239171328](https://github.com/m-shogo/memories-project/actions/runs/41239171328) completed SUCCESS on exact code HEAD. Guard logs confirm 601 canonical negatives, 39 supplemental history fixtures, 52 workflow / 63 direct Python / 204 source-negative reachability fixtures, 195 fanout synthetics and 1,186 helper ancestor mutations.
- **whySafe:** No production authority was changed. Faults and canary live only inside disposable local directories, and the test verifies the original file and independent canary bytes.
- **reusableMechanism:** Distinguish primary close error from secondary cleanup error; test before- and after-effect cleanup independently, preserve diagnostic notes, and never retry an uncertain child FD.
- **protectedAuthorityCheck:** All ten protected blobs remained unchanged at code HEAD `9fa87884`, including canonical learning, learning contract, production decision, OPS-P0-007, generation/objective/request/evidence/typed eight-domain/promotion registries.

## Scoped blockers and next safe target

`productionDecision=NO_GO` and OPS-P0-007=`PREREQUISITES_BLOCKED` remain authoritative. Registered and semantically preflight-eligible generations are 0/0. Preflight requires unsuperseded semantically eligible generations from distinct environments and a current explicitly human-approved recovery objective; reviewed drill requests are planning-only, new recovery evidence requires a current executable reviewed request, complete typed eight-domain non-resurrection coverage and independent review are mandatory for final candidates, and human promotion is separate/non-automatic.

The known [Upload Route #41239171227](https://github.com/m-shogo/memories-project/actions/runs/41239171227) still failed at Quay MinIO HTTP 401 before focused Go/HTTP tests. Workflow-write permission, supplemental-learning-only Push/PR CI reachability and an independent pre-MinIO Go test path remain unchanged scoped blockers. Do not retry unchanged blockers. The final learning-only HEAD does not itself establish an independent exact-source CI success.

**Next safe target:** Audit `open_pinned_parent` child-open failure plus outer cleanup-close uncertainty. Prove the original open error is not masked by a before-/after-effect cleanup fault, without retrying a descriptor whose ownership is unknown.
