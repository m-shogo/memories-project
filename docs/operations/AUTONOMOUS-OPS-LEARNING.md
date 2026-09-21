# Autonomous Operations Learning

This is an append-only operational learning log for autonomous work on branch `so`.
It records reusable execution lessons only. It is not production evidence, readiness authority,
a promotion decision, a recovery objective, or drill evidence.

## 2026-09-20 — Blocked workflow write must not stop unrelated safe progress

### What worked
- Fail-closed OPS-P0-007 authority was preserved: missing real production-equivalent evidence did not become readiness.
- `productionDecision=NO_GO` remained authoritative.
- Permission limitations were not bypassed with force-push, history rewriting, direct ref tricks, or fabricated evidence.
- The blocked workflow mutation was identified explicitly rather than silently treated as complete.

### What went poorly
- The autonomous loop was stopped after encountering a workflow-write permission blocker.
- That incorrectly promoted a scoped implementation blocker into a project-wide stop condition.
- It also prevented useful read-only audits and safe non-workflow hardening from continuing.

### Durable correction
1. A permission or external-evidence blocker is scoped to the affected write/evidence path; it is not a global stop condition.
2. After a blocked write, re-read current `so` and continue to the next independent, high-value, safe target.
3. Use CI wait time for validator diagnostics, negative-suite review, deterministic-authority drift checks, and existing-contract discovery.
4. Do not repeatedly retry an unchanged permission failure. Record it once and retry only after a relevant state/permission change.
5. Before every write, re-read the target file and current `so` authority so concurrent changes are not overwritten.
6. Prefer extending existing validators/contracts/tests over adding parallel authorities.
7. Keep learning records separate from evidence records: this file can improve execution behavior but can never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion gates.
8. A run ends early only when every remaining high-value target is genuinely blocked by external/human evidence or would require unsafe/speculative change.

### OPS-P0-007 invariants to retain
- Registered environment generations and semantically preflight-eligible generations are distinct states.
- Preflight can consume only unsuperseded, semantically eligible generations from distinct environments and an explicitly human-approved current recovery objective.
- Reviewed drill requests are planning authority only.
- New generation recovery evidence stays bound to a current executable reviewed request.
- Final production-equivalent recovery candidates require all existing generation/objective gates, complete typed eight-domain non-resurrection coverage, and independent review.
- Human production-promotion review is a separate non-automatic decision.
- No autonomous process may invent production-equivalent generations, recovery objectives, drill/production evidence, credentials, production traffic, readiness, or promotion.

## 2026-09-20 — Learning must be a closed loop, not a diary

### Durable correction
1. Every material failure must produce a reusable lesson: observed symptom, verified root cause when known, failed approach, correction, and a guard that prevents recurrence.
2. Every material success must record why it was safe and which invariant or check made it succeed, so later work can reuse the mechanism rather than rediscover it.
3. Before implementing a fix, search this learning log and existing contracts/scripts/workflows for the same failure class. Repeating a known failed approach without changed preconditions is a regression.
4. Prefer executable guards over prose: when practical, turn a lesson into a validator, negative test, deterministic check, or bounded reconcile rule. Documentation alone is not considered full prevention when an executable guard is feasible.
5. After each change, verify the intended behavior and also verify protected authorities did not drift. Record only observed results.
6. Periodically compact repeated lessons into stable rules while preserving the historical entries; do not delete failure history merely because the current implementation is green.
7. Track scoped blockers with their retry condition. A blocker is retried only when that condition changes; meanwhile unrelated safe work continues.
8. Treat autonomous improvement as: observe -> diagnose -> search prior knowledge -> change -> validate -> persist lesson -> re-read current authority -> continue.

## 2026-09-20 — A guard needs negative proof and CI reachability

### Observed outcome
- The learning contract is now bound to a canonical positive validator and a dedicated negative validator.
- The negative suite covers weakened mandatory rules, a weakened `NO_GO` default, broken validator binding, missing learning authority, missing executable guard, and removal of the anti-regression lesson.

### Why this is safer
- A validator existing in the repository is not enough: its fail-closed behavior must be exercised against representative weakening mutations.
- The contract now names both guards, and the positive validator fails closed if either binding or file disappears.

### Remaining gap / retry condition
- The current `Operability Contracts` workflow does not yet invoke these new learning validators; repository search found no existing invocation.
- Previous workflow-file mutation is a known permission blocker. Do not retry that unchanged write path merely to wire CI.
- Retry workflow wiring only after workflow-write permission changes, or when an existing non-workflow CI entrypoint can safely invoke the learning guards without duplicating authority.
- Until then, do not claim the learning negative suite is CI-enforced or passing; only its repository binding is established.

## 2026-09-20 — Negative fixtures must satisfy the positive control before mutation

### Symptom
- The autonomous-learning negative suite's temporary positive control could not satisfy the canonical validator after the validator began requiring both positive and negative guard files.

### Evidence
- `validate-autonomous-learning-system.py` requires `scripts/validate-autonomous-learning-system-negative.py` to exist, while the negative suite's `seed()` copied only the contract, learning authority, and positive validator.

### Root cause
- The fixture definition did not evolve with the validator's new self-binding invariant.

### Failed approach
- Treating repository-level guard binding as sufficient without checking that isolated test fixtures reproduce the complete canonical authority set.

### Correction
- The negative fixture now seeds both executable guards before running its positive control.
- Negative coverage now also removes or rebinds the negative guard itself, so this dependency cannot silently regress.

### Recurrence guard
- A negative suite that mutates a fail-closed authority must first establish an unmodified positive control using the same isolated fixture. Fixture dependencies must include every authority required by that canonical positive validator.

### Retry condition
- CI execution remains a separate reachability gap. Do not claim this suite passed in CI until an observed CI path invokes it successfully.

## 2026-09-20 — Destructive negative fixtures need an external canonical harness

### Symptom
- Operability Contracts run `35504771227` reached the autonomous-learning guards, the positive guard passed, but the negative suite failed on `remove executable guard` before the canonical validator could classify the mutation.

### Evidence
- CI reported Python could not open the fixture-local `scripts/validate-autonomous-learning-system.py` after that case intentionally deleted it; the expected `AUTONOMOUS LEARNING VALIDATION FAILED` diagnostic was therefore never emitted.

### Root cause
- The negative-suite runner executed the validator from inside the same mutable fixture whose validator-presence invariant it was testing.

### Failed approach
- Using the system under destructive mutation as the test harness for proving that the same system detects its own deletion.

### Correction
- The negative suite now executes the immutable canonical validator from the checked-out source tree while passing the isolated fixture through `--repo-root`.
- The fixture still contains and can delete its bound validator, so the canonical harness can observe and reject that missing authority deterministically.

### Recurrence guard
- When a negative case can delete or corrupt the executable under test, execute a trusted harness outside the mutation boundary and point it at the isolated fixture. Do not weaken the expected diagnostic merely to accommodate interpreter-startup failure.

### Retry condition
- Re-evaluate only from a CI run whose head includes the canonical-harness correction; do not rerun the known-broken `61c3f2a` attempt and call it new evidence.

## 2026-09-20 — CI callers and guards must share an explicit invocation interface

### Symptom
- Static inspection after the destructive-fixture correction found that the operability entrypoint invokes every learning guard with `--repo-root`, while the negative guard did not accept that option.

### Evidence
- `scripts/validate-memory-os-entry-docs.py` invokes both bound guards as `<guard> --repo-root <repository>`; the negative guard previously had no argument parser.

### Root cause
- CI reachability was validated as a textual binding, but the callable interface between the shared entrypoint and each guard was not kept consistent.

### Failed approach
- Treating a guard path appearing in the CI entrypoint as sufficient proof that the guard is invocable through that entrypoint.

### Correction
- The negative guard now accepts `--repo-root` and uses that explicit source root for fixture seeding and the immutable canonical harness.

### Recurrence guard
- Shared CI entrypoints must pass only an interface supported by every bound executable, and reachability reviews must check invocation compatibility as well as path presence.

### Retry condition
- Claim CI success only after a new Operability Contracts run whose head contains this interface correction completes successfully; older runs remain historical evidence only.

## 2026-09-21 — Negative-proof hardening write is a scoped blocker

### Symptom
- A planned hardening change to `scripts/validate-autonomous-learning-system-negative.py` could not be written through the available repository write path.

### Evidence
- The attempted write was blocked before a repository commit was created. The branch remained at `ed711a9`; the canonical positive validator still enforces `opsP0007EvidenceMustBeReal=true`, `humanPromotionReviewIsSeparate=true`, exact failure/success field sets, and exact closed-loop order, while the negative suite does not yet mutate each of those authorities independently.

### Root cause or unknown
- The write-path restriction is external to the repository content; no repository-level cause has been verified. Treat the root cause as unknown until the write capability or policy state changes.

### Failed approach
- Attempting to extend the existing negative-suite file while its write path was blocked.

### Correction
- Do not weaken or duplicate the canonical authority to work around the blocker. Preserve the identified mutations as the next executable hardening target and continue independent read-only audits and safe writes elsewhere.

### Recurrence guard
- Treat a blocked target path as scoped. Do not retry the same mutation through equivalent write routes while the precondition is unchanged, and do not claim missing negative cases are implemented merely because the positive validator enforces the invariant.

### Retry condition
- Retry the negative-suite hardening only after the repository write capability/policy for that target changes, or a pre-existing canonical executable extension point is found that can add the same negative proof without creating parallel authority.

## 2026-09-21 — Declared non-resurrection negatives need observed execution, not compilation

### Symptom
- The typed non-resurrection contract declares a canonical `negativeAdmissionValidator` and `negativeAdmissionCases`, but static workflow inspection shows the admission PR job compiles `scripts/validate-memory-os-backup-restore-non-resurrection-negative.py` without invoking that suite in the visible validation command sequence.

### Evidence
- The contract binds `scripts/validate-memory-os-backup-restore-non-resurrection-negative.py` as `negativeAdmissionValidator` and enumerates fail-closed cases.
- `.github/workflows/backup-restore-non-resurrection-admission.yml` includes the negative validator in path triggers and `py_compile`, while the PR validation command sequence invokes source-binding, load, transport, contract-path, and registry-aggregate negative suites but not the bound main negative suite.
- The main negative suite itself contains executable rejection cases for typed eight-domain evidence, review binding/digests/independence, production-boundary relabeling, registry drift, and rollback.

### Root cause or unknown
- The repository contains the executable suite and CI dependency declarations, but the observed PR execution list does not establish runtime reachability for that bound suite. Whether the push job invokes it later is not proven by the currently inspected workflow excerpt, so treat full workflow reachability as unknown rather than assuming it.

### Failed approach
- Treating workflow path triggers and successful Python compilation as equivalent to observed execution of a bound negative validator.

### Correction
- Do not claim the declared non-resurrection negative suite is CI-executed until a canonical CI command path or an observed run proves invocation. Prefer wiring through an existing non-workflow canonical entrypoint if one exists; do not retry the unchanged workflow-write blocker merely to add a command.

### Recurrence guard
- For every contract-bound negative validator, distinguish four states: declared, trigger-reachable, compile-checked, and runtime-invoked. Only runtime invocation plus an observed exact-source successful run counts as CI execution proof.

### Retry condition
- Revisit wiring when either workflow-write capability changes or an existing canonical executable entrypoint can invoke the suite without duplicating authority. If later inspection proves an existing push/runtime invocation, record that observed path and close only this reachability gap; do not rewrite working CI unnecessarily.

## 2026-09-21 — Transitive validator invocation counts only when the call chain is verified

### Outcome
- The previously suspected typed non-resurrection main-negative reachability gap was narrowed: the canonical admission validator directly invokes the bound main negative suite, and both PR and push workflow paths invoke that admission validator.

### Evidence
- `scripts/validate-memory-os-backup-restore-non-resurrection-admission.py` binds `NEGATIVE` to `scripts/validate-memory-os-backup-restore-non-resurrection-negative.py` and calls `run_validator(NEGATIVE, "non-resurrection negative admission suite")` before returning PASS.
- `.github/workflows/backup-restore-non-resurrection-admission.yml` invokes `python scripts/validate-memory-os-backup-restore-non-resurrection-admission.py` in both the read-only PR path and the push admission path; the bounded push revalidation function invokes it again after resetting to latest `origin/so`.

### Why safe
- No workflow or production evidence authority was changed. The audit followed the existing canonical call chain rather than adding duplicate CI wiring.
- The finding does not by itself claim a new exact-source CI success; it establishes static runtime reachability only.

### Reusable mechanism
- Reachability audits must follow transitive executable calls, not only top-level workflow command lists. Classify a validator as statically runtime-reachable when a workflow-invoked canonical validator deterministically invokes it and fails closed on its nonzero exit.
- Keep observed exact-source CI success as a separate proof layer from static transitive reachability.

### Protected-authority check
- This correction changes learning history only. `productionDecision=NO_GO`, real OPS-P0-007 evidence requirements, typed eight-domain coverage, independent review, and separate human promotion authority remain unchanged.

## 2026-09-21 — Cross-layer admission guards should be reused before adding new mutations

### Outcome
- A cross-layer audit found existing executable negative proof for the highest-risk prerequisites at the front of OPS-P0-007: semantic generation eligibility is distinct from registration, two distinct environments remain required, and the recovery objective must be current and explicitly approved.
- No duplicate validator or parallel authority was added.

### Evidence
- `scripts/validate-memory-os-backup-restore-drill-preflight-negative.py` rejects legacy registered-generation aliases, removal of semantic preflight eligibility, removal of distinct-environment binding, weakening the minimum generation count from two to one, and removal of the current-approved-objective requirement.
- `scripts/validate-memory-os-recovery-objectives-negative.py` independently rejects arbitrary repository files as approval, objective/value binding drift, duplicate or missing approval evidence, reviewer identity aliasing, invalid objective values, mutable aliases, and production-evidence relabeling.
- Exact-source Backup Restore Admission Chain run `35567992636` completed successfully at head `eaac4107274270f220e055f0be55c33405458b61`; this is CI evidence for that admission-chain head, not production evidence.

### Why safe
- The audit reused existing executable guards instead of weakening, duplicating, or replacing authority.
- It did not create generations, recovery objectives, drill requests, recovery evidence, credentials, traffic, readiness, or promotion state.

### Reusable mechanism
- Before adding a cross-layer negative case, inspect both the composing admission-chain suite and the canonical layer-specific negative suites. A boundary is not considered missing merely because the aggregate suite does not duplicate a mutation already enforced by a transitively invoked canonical layer guard.
- Preserve separate proof labels: static executable coverage, CI reachability, exact-source CI success, and production evidence are distinct states.

### Protected-authority check
- `productionDecision=NO_GO` remains unchanged. Registered generations remain distinct from semantically preflight-eligible generations; reviewed drill requests remain planning-only; new recovery evidence still requires a current executable request; typed eight-domain coverage and independent review remain candidate gates; human production promotion remains separate and non-automatic.
