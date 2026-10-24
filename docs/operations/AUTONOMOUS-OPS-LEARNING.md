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

## 2026-09-21 — Stale drill requests already have executable candidate invalidation proof

### Outcome
- The next cross-layer target did not require a new validator: the canonical generation-evidence negative suite already proves both halves of the lifecycle boundary. New evidence is rejected once its reviewed drill request is no longer current/executable, while historical evidence remains auditable only when the explicit historical-validation mode is used and cannot remain a current candidate.
- No duplicate mutation or parallel authority was added.

### Evidence
- `scripts/validate-memory-os-backup-restore-generation-evidence-negative.py` first establishes a valid request-bound generation record and a complete typed overlay, proving the record can satisfy the candidate predicate while the request is current.
- The same isolated fixture then advances the recovery-objective authority, sets `currentExecutableRequestCount` to zero, rejects normal validation as `stale drill request for new evidence`, accepts only `validate_record(..., require_current_drill_request=False)` for historical audit, and asserts `candidate(valid) is False`.
- The admission-chain validator separately requires `newEvidenceRequiresCurrentlyExecutableDrillRequest`, `historicalEvidenceMayRemainAuditableAfterDrillRequestStales`, and `staleRequestEvidenceCannotRemainCurrentCandidate` as mandatory true invariants.

### Why safe
- The proof uses temporary registries and explicitly reports that canonical registries are not mutated. It does not manufacture production-equivalent generations, objectives, production evidence, credentials, traffic, readiness, or promotion.
- Reusing the existing executable guard avoids divergent definitions of request currency and candidate invalidation.

### Reusable mechanism
- For lifecycle boundaries, prefer one fixture that demonstrates the positive state transition and then mutates only the lifecycle authority needed to make the prior evidence stale. Require separate assertions for new-write rejection, historical auditability, and current-candidate invalidation; none implies the others automatically.
- Do not add aggregate-chain mutations merely to duplicate a layer-specific lifecycle proof that is already executable and bound by chain invariants.

### Protected-authority check
- `productionDecision=NO_GO` remains unchanged. Reviewed drill requests remain planning authority only; new generation evidence still requires a current executable reviewed request; historical evidence cannot become current solely by remaining append-only; typed eight-domain coverage and independent review remain additional candidate gates; human production promotion remains separate and non-automatic.


## 2026-09-25 — Repository work must use the GitHub connector and scoped blockers must not disable the loop

### Symptom
- Repository work was summarized from prior state instead of always grounding the run in the connected GitHub repository, and a scoped write blocker was escalated into disabling the recurring autonomous hardening loop.

### Evidence
- The user explicitly required `@GitHub` on every memories-project run.
- The existing learning authority already states that a scoped permission blocker is not a project-wide stop condition and that unchanged blockers must not be retried.

### Root cause or unknown
- Root cause: execution discipline drift. A scoped safety/write constraint was interpreted too broadly, and connector-grounding was treated as optional instead of a run precondition.

### Failed approach
- Relying on remembered/prior reported repository state as if it were current.
- Disabling the recurring autonomous loop because one target write path was blocked.

### Correction
- Every memories-project run starts by using the GitHub connector to read current `so`, this learning authority, and the autonomous-learning contract before repository decisions.
- A scoped blocker is recorded with its retry condition; the run then advances independent safe targets.
- The recurring loop is not disabled merely because one repository target or permission path is blocked.

### Recurrence guard
- Treat connector-grounded current-state reads as a mandatory run precondition for memories-project work.
- Treat automation disablement as a separate control-plane action, not an automatic consequence of a repository blocker; only disable it when explicitly requested or when the whole run is genuinely unsafe/invalid rather than one target being blocked.
- Reports must distinguish freshly observed GitHub state from historical context.

### Retry condition
- A known blocked write path may be retried only when its recorded permission/capability/precondition changes. Connector reads themselves are retried only on a new run or after a concurrent-state change that requires re-grounding.

### Protected-authority check
- This lesson is execution-policy history only. It cannot satisfy production evidence/readiness. `productionDecision=NO_GO`, real OPS-P0-007 evidence requirements, typed eight-domain coverage, independent review, and separate human promotion authority remain unchanged.


## 2026-09-25 — Target-specific write safety remains scoped even when other writes succeed

### Symptom
- A direct update to `scripts/validate-memory-os-backup-restore-promotion-review-negative.py` was blocked before GitHub created a commit while adding the candidate-revival negative proof.

### Evidence
- Current `so` remained at `1ec679f8b903719775366c34608829d607edcf15` after the rejected update.
- The intended change was limited to an isolated synthetic negative fixture: after supersession revokes `currentDecisionId`, make the same synthetic recovery candidate current again and prove both reconcile and append validation refuse to reactivate the historical review.
- A prior learning-log write succeeded through the GitHub connector, so repository write capability is not globally absent.

### Root cause or unknown
- Root cause is unknown outside the repository. The rejection occurred in the execution safety layer before a GitHub commit, and no repository validation failure was observed.

### Failed approach
- Retrying a direct contents update to the already-known blocked promotion-review negative-suite target merely because a different file had become writable.

### Correction
- Keep the promotion-review negative-suite path as a scoped blocker. Do not route around it with alternate Git object writes or parallel authority.
- Continue read-only audits and independent safe targets while preserving the exact candidate-revival test design for a later changed precondition.

### Recurrence guard
- A successful write to one repository path does not by itself satisfy the retry condition for a separately blocked target path. Retry conditions are target/capability specific.
- Before retrying a blocked target, require evidence that the target-specific safety/capability state changed, not merely that unrelated repository writes work.

### Retry condition
- Retry this promotion-review negative-suite mutation only after target-specific write policy/capability changes or the canonical file itself changes in a way that demonstrates a new write precondition. Until then, audit without rewriting it.

### Protected-authority check
- No production-equivalent generation, objective, review, evidence, credential, traffic, readiness, or promotion state was created. `productionDecision=NO_GO` and separate human promotion authority remain unchanged.


## 2026-09-26 — CI reachability must be repository-wide and write blockers remain target-specific

### Symptom
- A focused typed non-resurrection registry mode/lock-cleanup negative suite exists but was not reachable from the canonical typed non-resurrection admission validator or the end-to-end admission-chain runner.
- A minimal attempt to make the canonical typed admission validator invoke that existing suite was blocked before GitHub created a commit.

### Evidence
- `scripts/validate-memory-os-backup-restore-non-resurrection-registry-mode-negative.py` proves successful 0640 mode preservation, exact byte/mode rollback, temporary-file cleanup, and lock release/reacquisition after synthetic close failure.
- `scripts/validate-memory-os-backup-restore-non-resurrection-admission.py` invokes semantic and contract-path negative suites but not the registry-mode suite.
- `scripts/validate-memory-os-backup-restore-admission-chain-full.py` invokes the typed admission validator but not the registry-mode suite directly.
- Earlier repository-wide auditing corrected false positives: several ordering and independent-review execution suites omitted from the full runner are nevertheless runtime-invoked by dedicated workflows. Full-runner omission alone is therefore not proof of CI unreachability.
- The attempted update to the typed admission validator was rejected by the execution safety layer before a GitHub commit; `so` remained unchanged.

### Root cause or unknown
- Reachability gap root cause: the focused registry publication/lock negative suite was added without a verified canonical runtime caller in the inspected admission path.
- Write rejection root cause is unknown outside the repository; no repository validator failure or GitHub commit failure was observed.

### Failed approach
- Treating absence from one aggregate runner as sufficient evidence of CI unreachability.
- Attempting a direct contents update to the typed admission validator while its target-specific write capability was not known to be allowed.

### Correction
- Classify reachability only after tracing dedicated workflows and transitive canonical callers.
- Preserve the registry-mode suite as an existing executable guard; do not duplicate its assertions.
- Keep the typed admission-validator mutation as a scoped blocked target and continue independent audits rather than routing around the safety layer.

### Recurrence guard
- A CI reachability finding must distinguish direct aggregate-runner invocation, transitive invocation, dedicated-workflow invocation, and observed exact-source CI execution.
- A suite is called unreachable only after the relevant repository-wide runtime call graph has been checked.
- A blocked target file is not retried until its target-specific precondition changes; unrelated writable files do not satisfy that retry condition.

### Retry condition
- Retry wiring `validate-memory-os-backup-restore-non-resurrection-registry-mode-negative.py` into a canonical caller only after the target caller file changes or target-specific write policy/capability changes. Until then, continue read-only reachability and authority audits.

### Protected-authority check
- No production-equivalent generation, objective, drill request/evidence, credential, traffic, readiness, or promotion authority was created. `productionDecision=NO_GO`, real OPS-P0-007 evidence requirements, typed eight-domain coverage, independent review, and separate human promotion authority remain unchanged.


## 2026-09-26 — Dependency bootstrap failures must remain observable and must not masquerade as capacity evidence

### Symptom
- Scheduled Capacity Ramp run `36193439393` failed before the ramp executed because the local MinIO dependency could not start.

### Evidence
- The failing job reached `Start local MinIO dependency` after PostgreSQL became healthy.
- `docker run quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z` exited 125 with `unauthorized: access to the requested resource is not authorized`.
- Every ramp execution, publication, reconciliation, diagnostic, and success-enforcement step after dependency startup was skipped, so the run produced no capacity result and no privacy-safe diagnostic commit.
- A later scheduled load-foundation reconciliation succeeded at current head; that does not convert the failed capacity run into capacity evidence.

### Root cause or unknown
- Verified immediate cause: the configured MinIO image reference was not pullable by the GitHub-hosted runner at execution time.
- The external registry-side reason for denying that image is unknown from repository evidence alone.

### Failed approach
- Treating dependency startup as an unconditional pre-step outside the workflow's bounded failure-capture path. A bootstrap failure therefore bypasses the existing diagnostic recorder entirely.

### Correction
- Keep this run classified as infrastructure/dependency-bootstrap failure, not a capacity regression and not capacity evidence.
- Future workflow hardening should bring dependency startup into the bounded diagnostic path and use a repository-reviewed, pullable dependency image reference without weakening exact-source binding or production boundaries.
- Do not retry the already-known workflow-write blocker merely to apply that change; first require the workflow-write retry condition to change.

### Recurrence guard
- Capacity/load workflows that depend on external containers should make dependency bootstrap failure observable through the same privacy-safe diagnostic authority as test/validator failure.
- A dependency-start failure must leave `capacityBoundaryEstablished=false`, must not reconcile capacity readiness, and must not be inferred as an application capacity failure.
- External image availability is an execution prerequisite, not production evidence.

### Retry condition
- Retry workflow hardening only after workflow-write capability/policy changes or the canonical workflow file itself changes, satisfying the recorded target-specific retry condition. Re-run the capacity ramp only after the dependency image is demonstrably pullable from the runner path.

### Protected-authority check
- No capacity result, production traffic, credential, readiness, or promotion authority was created from the failed run. `productionDecision=NO_GO` remains authoritative, and OPS-P0-007 generation/objective/request/typed-coverage/independent-review/human-promotion boundaries remain unchanged.


## 2026-09-26 — In-flight cancellation reconcile negative guard is not CI-reachable from its owning workflow

### Symptom
- The in-flight parser cancellation reconciler has a focused negative suite, but its owning workflow does not execute that suite and does not include it in path triggers.

### Evidence
- `scripts/validate-memory-os-parser-inflight-cancellation-reconcile-negative.py` proves executable-authority substitution rejection, atomic mode preservation, rollback after post-write aggregate rejection, and atomic-replace failure cleanup.
- `.github/workflows/parser-inflight-cancellation.yml` executes the positive validator/reconciler/operability chain but not that negative suite.
- Sibling parser restart and process-group workflows both execute their corresponding reconcile-negative suites.
- A minimal workflow update to add the existing negative suite to push/PR triggers, py_compile, and execution was rejected by the execution safety layer before GitHub created a commit.

### Root cause or unknown
- Reachability root cause: the focused negative suite exists without a runtime invocation in the owning in-flight workflow.
- The workflow-write rejection is external to repository validation; its exact cause is unknown.

### Failed approach
- Directly updating `.github/workflows/parser-inflight-cancellation.yml` while workflow-write capability remained unavailable.

### Correction
- Treat the suite as existing executable coverage but not observed CI coverage.
- Do not duplicate its assertions. Wire the existing suite only when the workflow target becomes writable.
- Continue independent read-only audits instead of retrying the unchanged workflow blocker.

### Recurrence guard
- For each parser evidence family, require symmetry between a focused reconcile-negative suite and an owning workflow runtime invocation/path trigger before calling the failure boundary CI-covered.
- Repository existence of a negative validator alone does not satisfy CI reachability.

### Retry condition
- Retry the in-flight workflow mutation only after `.github/workflows/parser-inflight-cancellation.yml` changes on `so` or workflow-write policy/capability demonstrably changes.

### Protected-authority check
- No production-equivalent evidence, readiness, credential, traffic, or promotion authority was created. `productionDecision=NO_GO` remains unchanged; OPS-P0-007 real-evidence, typed eight-domain coverage, independent-review, and separate human-promotion boundaries remain authoritative.



## 2026-09-26 — Authority-writing overlays require explicit runtime reachability and atomic publication

### Symptom
- The mixed-version chaos overlay can mutate the canonical production operability authority, but no canonical workflow/runtime caller was found for it, and its publication path uses direct `Path.write_text()` with direct `write_bytes()` rollback instead of the repository's stronger atomic-publication pattern.

### Evidence
- `scripts/reconcile-memory-os-chaos-mixed-version-overlay.py` validates candidate/local mixed-version SIGKILL recovery and requires `productionDecision=NO_GO`, `approvedReleaseCount=0`, `releaseCompatibilityEvidence=false`, and `productionEvidence=false` before updating OPS-P0-009.
- Its mutation path writes `production-operability-status.json` with `STATUS.write_text(...)`; post-write validator failure restores bytes with `STATUS.write_bytes(original_status)`.
- Repository code search for the exact mixed-version overlay filename returned no caller.
- `.github/workflows/reconcile-chaos-authority.yml` path triggers, py_compile set, and execution sequence include the in-flight overlay and process-group focused negative guard but do not include the mixed-version overlay.
- The sibling in-flight overlay already uses same-directory tempfile creation, flush/fsync, `os.replace`, cleanup, and atomic rollback, demonstrating an existing reusable mechanism.

### Root cause or unknown
- Verified design gap: the mixed-version overlay was added without explicit canonical runtime reachability and retained an older non-atomic publication/rollback implementation.
- The historical reason those stronger mechanisms were not adopted is unknown.

### Failed approach
- Treating the existence of an authority-writing reconciler and its internal post-write validators as sufficient operational coverage without proving a canonical runtime caller.
- Treating direct write plus byte rollback as equivalent to atomic publication.

### Correction
- Do not count the mixed-version overlay as CI/runtime-covered until a canonical caller is explicit and observed.
- When the target becomes writable, reuse the existing in-flight/process-group atomic publication pattern rather than inventing another writer.
- Add focused negative proof for atomic replace failure/cleanup and rollback before relying on the overlay's mutation boundary.

### Recurrence guard
- Every script that can mutate a protected authority must have both an explicit canonical runtime caller and deterministic mutation-boundary tests.
- Authority writers should use same-directory temporary publication with fsync and atomic replace for both forward publication and rollback when the filesystem contract permits it.
- Repository existence, importability, or internal validation alone does not satisfy `ciReachabilityRequired`.

### Retry condition
- Harden or wire the mixed-version overlay only after its script/workflow target changes on `so` or target-specific write capability/policy demonstrably changes. Until then, continue independent read-only audits and do not route around the blocker.

### Protected-authority check
- This lesson is execution-policy history only. Candidate/local mixed-version evidence remains non-production evidence; it cannot create an approved release, production-equivalent recovery evidence, readiness, credentials, traffic, or promotion authority. `productionDecision=NO_GO` and all OPS-P0-007 generation/objective/request/eight-domain/independent-review/human-promotion boundaries remain unchanged.



## 2026-09-27 — Incident-control authority writer is the reusable hardened mutation-boundary reference

### Outcome
- Read-only cross-family audit identified `scripts/reconcile-memory-os-incident-control-authority.py` as an existing hardened reference for protected-authority reconciliation rather than creating another writer pattern.

### Evidence
- The reconciler rejects symlinked or path-substituted data, validator and workflow authorities.
- It binds the execution transport, atomic replacement transport and atomic writer to construction-time canonical objects through `CANONICAL_SUBPROCESS_RUN`, `CANONICAL_OS_REPLACE` and `CANONICAL_ATOMIC_WRITE_BYTES`.
- Its atomic writer preserves the existing file mode, flushes and fsyncs the same-directory temporary file, publishes with atomic replace, and cleans temporary residue.
- Its focused reconcile-negative suite exercises authority/validator-chain/transport/writer substitution plus publication and rollback boundaries.
- The reconciler requires `productionDecision=NO_GO`, keeps OPS-P0-002 PARTIAL, and preserves the human-tabletop, paging, external-contact, production-recovery and independent-review gaps.

### Why safe
- This run changed only append-only learning history. It did not modify production evidence, operability status, incident evidence, credentials, traffic, readiness or promotion authority.
- The reference mechanism is fail-closed and explicitly preserves unresolved human and production gaps.

### Reusable mechanism
- For protected-authority writers, prefer the existing incident-control pattern: exact non-symlink repository authority checks; construction-time binding of subprocess, replacement transport and writer; mode-preserving same-directory tempfile + fsync + atomic replace; exact byte/mode rollback; focused negative substitution tests; and a canonical CI caller.
- Keep failure injection behind isolated test seams rather than weakening the production transport binding.

### Protected-authority check
- No production-equivalent generation, objective, recovery evidence, credential, traffic, readiness or promotion authority was created or inferred.
- `productionDecision=NO_GO` remains mandatory. OPS-P0-007 real-evidence, distinct-environment semantic eligibility, explicitly human-approved current recovery objective, current executable reviewed request, typed eight-domain non-resurrection coverage, independent review and separate human promotion authority remain unchanged.


## 2026-09-29 — Repeatability hardening write remains externally blocked after branch advancement

### Symptom
- The controlled-saturation repeatability mutation-boundary hardening could not be written even after the recorded retry precondition changed.

### Evidence
- Branch `so` advanced from `da6fdb527d5f42d90a1cf8bb52d3ee2127b98e9c` to `f55f48c9b6dda8788be15f001866c42acfbe1f84`.
- The target reconciler remained at blob `a30ec769ca2fffd27672abb878ee13c46e90bdac`.
- A fresh write attempt adding mode preservation and construction-time subprocess/replacement/writer binding was blocked before GitHub created a commit.

### Root cause or unknown
- The repository content does not explain the refusal. Root cause remains an external write safety/capability restriction.

### Failed approach
- Retrying the target write solely because branch advancement satisfied the prior broad retry condition did not restore write capability.

### Correction
- Narrow the retry condition: branch advancement alone is insufficient when the target blob and write capability are unchanged. Continue independent safe audits and do not route around the blocked mutation boundary.

### Recurrence guard
- For an externally blocked target, require either a target-blob change relevant to the planned mutation or an observed write-capability/policy change before retrying; unrelated branch movement is not enough.

### Retry condition
- Retry controlled-saturation repeatability hardening only after its target blob changes in a way requiring reconciliation, or repository write capability/policy demonstrably changes.

### Protected-authority check
- No repository mutation occurred. Production evidence/readiness was not changed or inferred; `productionDecision=NO_GO` and OPS-P0-007 boundaries remain mandatory.


## 2026-09-30 — Parser restart reconciler binds mutable execution and replacement transports

### Outcome
- Hardened the parser restart authority reconciler so ancestry checks, validator execution and atomic replacement retain construction-time transport bindings instead of consulting mutable module attributes at call time.
- Extended the existing focused negative suite to substitute both mutable `subprocess.run` and `os.replace` and prove the bound paths still execute, publish bytes and preserve file mode.

### Evidence
- Commit `d93b46fce7e5e7bc2f8f852b9be672d82331f396` changed only `scripts/reconcile-memory-os-parser-restart-matrix.py` and `scripts/validate-memory-os-parser-restart-reconcile-negative.py`.
- The reconciler now captures `subprocess.run` in the ancestry and validator helpers and captures `os.replace` in the atomic writer at function construction time.
- The focused negative substitutes the mutable module transports and requires HEAD ancestry, canonical parser validator execution, successful atomic publication, exact payload replacement and preservation of mode `0640`.
- The existing `parser-restart-matrix.yml` already path-triggers, compiles and executes the focused negative for pull-request and non-pull-request paths. No new workflow authority was required.
- Immediately after publication GitHub reported zero combined-status contexts and zero commit-associated pull-request workflow runs, so no CI PASS is inferred from absence of runs.

### Why safe
- The change strengthens only mutation transport binding and its negative proof; it does not manufacture or alter production evidence, recovery evidence, credentials, traffic, readiness or promotion authority.
- Existing same-directory temporary publication, fsync, mode preservation, atomic replacement, rollback and validator semantics remain intact.

### Reusable mechanism
- When an authority writer already has atomic publication and mode preservation, construction-time default-argument binding is a bounded way to prevent later mutation of module transport attributes from changing the executed subprocess or replacement primitive.
- Pair the binding with a focused substitution negative that mutates the public module attribute and proves the bound path remains functional; do not count static binding alone as proof.

### Protected-authority check
- Post-change re-read confirmed `contracts/operations/production-operability-status.json` remains `productionDecision=NO_GO`.
- No learning or local/CI result is promoted into production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence. OPS-P0-007 distinct-environment semantic eligibility, explicitly human-approved current recovery objective, current executable reviewed request, typed eight-domain non-resurrection coverage, independent review and separate human promotion authority remain unchanged.


## 2026-09-30 — Live-load mode-preservation retry remains externally blocked after target change

### Symptom
- A bounded hardening retry for the live-load authority writer could not be written even though the recorded target-change retry condition was satisfied.

### Evidence
- Branch `so` was freshly observed at `80726616e0055ad3c3355324e4ea7f152fbfcbcd`.
- `scripts/reconcile-memory-os-live-load-status.py` was freshly observed at blob `758317d3920af062fda315ae42b0c2da0e4004ad`, different from the previously reported blocked target state.
- The proposed change only imported `stat`, captured the existing authority mode, applied that mode to the same-directory fsynced temporary file, and retained the existing atomic `os.replace` publication.
- The repository write was rejected by the execution safety layer before GitHub created a commit.

### Root cause or unknown
- Root cause remains unknown outside repository content. No repository validator or GitHub commit failure was observed.

### Failed approach
- Retrying the previously blocked live-load writer after target change did not restore write capability for this target.

### Correction
- Do not route around the safety layer or weaken the writer. Preserve the mode-preservation change as a bounded future hardening target and continue independent safe audits.

### Recurrence guard
- A target-blob change permits one fresh retry, but a fresh external rejection establishes a new scoped blocker. Do not repeatedly retry equivalent live-load writer mutations after that rejection.

### Retry condition
- Retry live-load writer hardening only after another relevant target-blob change or an observable target-specific write-capability/policy change.

### Protected-authority check
- No repository mutation was created by the failed write. Learning remains non-production evidence. `productionDecision=NO_GO` and OPS-P0-007 real-evidence, distinct-environment semantic eligibility, explicit human recovery-objective approval, current executable reviewed request, typed eight-domain coverage, independent review, and separate human promotion authority remain mandatory.


## 2026-09-30 — Capacity-ramp transport-binding hardening is externally blocked

### Symptom
- The bounded capacity-ramp authority reconciler could not be hardened to retain construction-time subprocess and atomic-replacement transports.

### Evidence
- Branch `so` was freshly observed at `0bd7b9b462d67dd1064ed4355c5277df061e4416`.
- `scripts/reconcile-memory-os-capacity-ramp-status.py` was freshly observed at blob `d1fe1c9c7302cfbe861caf249acd611983103513`.
- The reconciler already preserves file modes, fsyncs same-directory temporary files, uses atomic replacement, and rolls back bytes plus modes transactionally, but validator execution still calls mutable `subprocess.run` and publication still calls mutable `os.replace`.
- A minimal write binding those two transports at function construction time was rejected before GitHub created a commit.

### Root cause or unknown
- Root cause remains external/unknown; no repository validator or GitHub commit failure was produced.

### Failed approach
- Directly hardening the previously unblocked capacity-ramp reconciler through a normal contents update did not pass the execution safety layer.

### Correction
- Do not route around the refusal or weaken existing atomic/mode-preserving behavior. Continue independent authority-family audits and preserve this as a bounded future hardening target.

### Recurrence guard
- Treat capacity-ramp transport binding as a scoped blocker. Do not repeat an equivalent write while both the target blob and write capability/policy remain unchanged.

### Retry condition
- Retry only after a relevant change to the capacity-ramp reconciler blob or an observable target-specific write-capability/policy change.

### Protected-authority check
- The failed write created no repository mutation. Capacity-ramp/local CI evidence remains non-production evidence; `productionDecision=NO_GO` and all OPS-P0-007 generation/objective/request/eight-domain/independent-review/human-promotion boundaries remain unchanged.


## 2026-09-30 — Controlled-saturation reconcile-negative CI wiring is externally blocked

### Symptom
- The existing controlled-saturation direct-reconcile negative could not be wired into its owning workflow's path trigger, compile stage, and runtime validation stage.

### Evidence
- Branch `so` was freshly observed at `322c21981aefc8b3208f214428e4fdc50c1a3b40` immediately before the write.
- `.github/workflows/controlled-saturation-ramp.yml` was freshly observed at blob `22d597431f6998ea3f9bcd303cf7c35c1fc9233b`.
- `scripts/validate-memory-os-controlled-saturation-ramp-authority-negative.py` exists at blob `68a6e46a843d0d780606a990d0c9993c0d823f2f` and proves canonical-authority substitution rejection plus atomic-replacement failure rollback/residue behavior, but the owning workflow neither path-triggers on it nor compiles/runs it.
- A minimal workflow-only change adding that existing negative to the path trigger, `py_compile`, and a pre-load runtime stage was rejected by the execution safety layer before GitHub created a commit.

### Root cause or unknown
- Root cause remains external/unknown; no repository validator or GitHub commit failure was produced.

### Failed approach
- Directly wiring the already-existing focused negative into the controlled-saturation workflow through a normal contents update did not pass the execution safety layer.

### Correction
- Do not route around the refusal or weaken the workflow. Continue independent safe authority-family work and retain this as a bounded CI-reachability target.

### Recurrence guard
- Treat controlled-saturation reconcile-negative workflow wiring as a scoped blocker. Do not repeat an equivalent workflow write while both the workflow blob and write capability/policy remain unchanged.

### Retry condition
- Retry only after a relevant change to the controlled-saturation workflow blob or an observable workflow-write capability/policy change.

### Protected-authority check
- The failed workflow write created no repository mutation. The negative remains non-production guard evidence; `productionDecision=NO_GO` and all OPS-P0-007 generation/objective/request/eight-domain/independent-review/human-promotion boundaries remain unchanged.


## 2026-10-03 — Explicit failure injection must follow construction-time transport binding

### Outcome
- Repaired the parser-restart focused negative so atomic replacement failure is injected through the canonical writer's explicit `_replace` seam rather than by mutating `module.os.replace`.
- Construction-time transport-mutation resistance remains independently proven by `prove_transport_binding()`.

### Evidence
- Commit `f2467d02e84b3dffaf3b6f5e09485b19157f45b5` changed only `scripts/validate-memory-os-parser-restart-reconcile-negative.py`.
- The reconciler already binds `os.replace` at function construction time; therefore later mutation of `module.os.replace` cannot inject a replacement failure.
- The corrected negative wraps the canonical `atomic_write_bytes` and supplies `_replace=reject_replace`, while retaining byte-integrity and temporary-residue assertions.
- `.github/workflows/parser-restart-matrix.yml` path-triggers on, compiles, and executes this focused negative on push and pull-request paths.
- Immediately after the commit, GitHub exposed zero commit-associated pull-request workflow runs and zero combined-status contexts, so no CI PASS is inferred yet.

### Why safe
- Only negative-test failure injection changed; production writer semantics and protected authority content were untouched.
- The post-change protected-authority re-read confirmed `productionDecision=NO_GO`.

### Reusable mechanism
- Once a production transport is construction-time bound, real failure-path tests must inject failure through an explicit isolated seam accepted by the canonical writer/helper.
- Keep module-attribute mutation exclusively for proving that construction-time binding resists later mutation; do not use the same mutation as the mechanism for simulating the transport failure.
- Preserve rollback bytes/mode and residue assertions independently from transport-binding resistance.

### Protected-authority check
- No production-equivalent generation, objective, recovery evidence, credential, traffic, readiness or promotion authority was created or inferred.
- OPS-P0-007 distinct-environment semantic eligibility, explicitly human-approved current recovery objective, current executable reviewed request, typed eight-domain non-resurrection coverage, independent review and separate human promotion authority remain unchanged.


## 2026-10-06 — Cross-workflow raw-diagnostic persistence guard is externally blocked

### Symptom
- A CI-reachable monotonic guard preventing new repository diagnostics from persisting raw subprocess output could not be added to the existing operability entrypoint.

### Evidence
- `scripts/validate-memory-os-entry-docs.py` was freshly observed at blob `aa7acc3b6da67fec4701f303281a27025931d5d3`.
- Existing workflows including parser restart, live-load reconciliation, and deletion container-kill still construct `memory-os-validator-diagnostic.v1` records with a raw `output` field.
- The proposed bounded check reused the existing CI entrypoint, admitted only an explicit transitional legacy set, rejected any new offender, and rejected stale exceptions after repair.
- The normal contents update was rejected by the execution safety layer before GitHub created a commit.

### Root cause or unknown
- Root cause is external/unknown. No repository validator failure or GitHub commit failure was produced.

### Failed approach
- Extending the existing CI-reachable entry-doc validator with the cross-workflow diagnostic-persistence guard did not pass the execution safety layer.

### Correction
- Do not create a parallel production/readiness authority and do not retry equivalent writes while the target blob and write capability remain unchanged. Continue independent audits and preserve raw logs as runner-local-only in future writable targets.

### Recurrence guard
- Treat this entrypoint mutation as a scoped blocker. The intended executable rule remains: repository diagnostics may retain digest, byte count, exit/stage metadata, but new raw subprocess-output persistence must fail closed; transitional exceptions must only decrease.

### Retry condition
- Retry only after `scripts/validate-memory-os-entry-docs.py` changes from blob `aa7acc3b6da67fec4701f303281a27025931d5d3` or an observable target-specific write-capability/policy change.

### Protected-authority check
- The failed write created no repository mutation. Learning and diagnostics remain non-production evidence; `productionDecision=NO_GO` and all OPS-P0-007 generation/objective/request/eight-domain/independent-review/human-promotion boundaries remain unchanged.

## 2026-10-09 — Release writer CLI guard proof write is a scoped blocker

### Symptom
- An isolated negative proof that the release baseline writer's live CLI calls its canonical authority guard could not be added to the already CI-invoked writer-authority negative suite.

### Evidence
- At branch `so` HEAD `bba7c53f9a619d7dd81aa4df7be28b762c519db6`, the target `scripts/validate-memory-os-release-baseline-writer-authority-negative.py` had blob `8ee792f53b2ce704b3ece0b421165489a523a91d`.
- The existing suite checks substitutions by directly invoking `require_actual_cli_authorities()`, but it does not exercise the `main()` call-site binding.
- The proposed change patched only the loaded writer module's guard to raise an exact synthetic `RegistrationFailure`, invoked `main()` with an invalid confirmation, required one exact sentinel rejection, restored `sys.argv` and the monkeypatch, and asserted canonical contract/registry/status bytes, modes and lock absence.
- Nine pre-write structural checks passed. The normal GitHub contents update was rejected by the execution safety layer before any commit was created.

### Root cause or unknown
- The rejection cause is unknown outside the repository. No GitHub commit or repository validator failure was observed.

### Failed approach
- A normal contents update to this specific CI-reachable negative suite did not pass the write safety boundary.

### Correction
- Leave the canonical writer and production authorities untouched. Keep this focused main-call-site negative proof as a future target; continue independent read-only audits and safe targets without routing around the rejected write.

### Recurrence guard
- Do not retry an equivalent mutation on this target while its blob and target-specific write capability/policy remain unchanged. An independently callable guard is not proof that the CLI actually invokes it; bind the call-site with a precise injected sentinel and an invalid confirmation before claiming coverage.

### Retry condition
- Retry only after a relevant change to target blob `8ee792f53b2ce704b3ece0b421165489a523a91d` or an observed target-specific write capability/policy change.

### Observed success and reusable mechanism
- Read-only audit confirmed the existing release baseline registry negative suite is directly invoked by the release-baseline-registry workflow, while its `expect_writer_rejected` and `expect_contract_rejected` currently accept any `Exception`; canonical registry/contract/status are also restored via direct writes in several negative cases.
- This audit was safe because it made no repository mutation. The reusable mechanism is to require exact canonical exception types and isolated temporary fixtures, while keeping static CI reachability distinct from an observed exact-source CI PASS.

### Protected-authority check
- No commit, executable guard, production evidence or readiness was created by the rejected write. The freshly read status still has `productionDecision=NO_GO` and OPS-P0-007 `PARTIAL_FOUNDATIONS_ONLY`, blocking=true. Learning remains append-only and cannot satisfy generation/objective/request/eight-domain/independent-review or separate human-promotion gates.

## 2026-10-12 — Independent deletion-worker failure-boundary negative test write blocked

### Symptom
- An additional CI-reachable Go negative suite for fail-closed deletion-worker boundaries could not be committed.

### Evidence
- Branch `so` was freshly observed at `4dc15bcba6fbc2905a1b783483079cf5b250b85e`.
- The proposed new `services/import-api/internal/accountdelete/worker_boundary_test.go` did not exist; the existing `service_test.go` was blob `1e73c3fc036e84da9fafcd24010822e01d43cc23`.
- `.github/workflows/import-api-security-slice.yml` at blob `ad1aac21ae506c4a4389c4fc68c46e576e469286` path-triggers on `services/import-api/**` and runs `go test -race ./...`.
- Four proposed tests checked that object-key ledger read failure, partial object erasure, database sweep failure, and claim failure never produce successful deletion receipts or cross the wrong erasure boundary.
- The normal GitHub create-file call was rejected by the execution safety layer before a commit was created. No repository-level test result was obtained.

### Root cause or unknown
- The write refusal's root cause remains external/unknown. No repository or GitHub commit error was observed.

### Failed approach
- Adding a new independent in-package Go negative suite via the ordinary GitHub contents API was rejected.

### Correction
- Do not route around the refusal or retry the same target unchanged. Continue independent static audits and retain the proposed tests as an unimplemented guard candidate.

### Recurrence guard
- An isolated test's proposed assertions and static CI reachability are not proof of an executable committed guard or an observed CI PASS. Keep `write blocked`, `CI reachable if committed`, and `CI verified` distinct.

### Retry condition
- Retry only after an observable change in the write capability/policy for the new target or a relevant target-path state change.

### Protected-authority check
- No repository mutation or readiness/evidence record was created by the refused test write. Learning remains non-production evidence; `productionDecision=NO_GO` and all OPS-P0-007 semantic generation eligibility, distinct-environment, human-approved current objective, executable reviewed request, typed eight-domain non-resurrection, independent-review, and separate human-promotion gates remain mandatory.


## 2026-10-15 — Incident admission guard writes remain target-scoped

### Symptom
- The human-tabletop writer negative suite could not be extended with a live CLI call-site sentinel, and the incident-contact-routing validator could not be hardened to reject completion flags with an empty admitted-routing registry.

### Evidence
- Branch `so` was freshly read at `28b8c3c09efa5b52fbb371667c5fb06e892d8504` before both attempted writes.
- The human-tabletop negative-suite target was blob `83a8941ac674b4298ce03f227caa5c9922f30571`; its existing test inspects the source string `require_actual_cli_authorities()` but does not execute a sentinel-injected `main()` call to prove the guard is reached.
- The contact-routing validator target was blob `3494a547a9f896995d54a9e2ec3412525e859ce0`; its registry is empty and its canonical contract currently has all contact-ownership, paging, review and production-evidence flags false. The validator does not compare those completion flags to the empty registry.
- Both normal GitHub contents updates were rejected by the execution safety layer before a commit. No CI run or executable guard resulted from either attempted change.

### Root cause or unknown
- The missing runtime call-site and empty-registry flag assertions are verified code-coverage gaps. The cause of the external write refusal is unknown; no GitHub commit or repository validator failure was observed.

### Failed approach
- Ordinary target-specific contents updates were attempted once each and rejected. Repeating equivalent updates or switching to low-level Git object/ref writes is not an acceptable workaround.

### Correction
- Retain the human-tabletop call-site sentinel design as an unimplemented negative test, and the contact-routing empty-registry flag comparison as an unimplemented validator guard. Continue independent safe audits without treating these proposals as installed protections.

### Recurrence guard
- Require a live injected sentinel when claiming a CLI authority guard is actually invoked; source-text presence alone is insufficient. Require zero admitted routing records to imply no owned external contacts, delivered paging, communication path, independent review, or production evidence. Distinguish a proposed guard, a committed guard, and an observed exact-source CI PASS.

### Retry condition
- Retry the tabletop negative suite only after its blob or target-specific write policy/capability changes. Retry the contact-routing validator only after its blob or target-specific write policy/capability changes. An unrelated successful write does not satisfy either retry condition.

### Observed safe outcome
- Read-only GitHub inspection verified that both existing incident admission workflows execute their bound negative suites, while the two specific new protections are not present. No human tabletop record, contact-routing record, production evidence, credential, traffic, or promotion authority was created. This audit is reusable as a pattern for verifying transitive CI reachability before claiming a new guard is covered.

### Protected-authority check
- The status authority still reports `productionDecision=NO_GO` and OPS-P0-007 `PARTIAL_FOUNDATIONS_ONLY`. This learning record is non-production history only; distinct-environment semantic generation eligibility, explicit human-approved current recovery objective, current executable reviewed request, typed eight-domain non-resurrection, independent review, and separate human production-promotion authority remain mandatory.

## 2026-10-21 — Legacy status-block check must not silently pass after Round 10 migration

### Symptom
- The Security Contracts CI job stops at the legacy status-block check because no Markdown files retain its Round 9 HTML status markers.

### Evidence
- `.github/workflows/security-contracts.yml` invokes `python scripts/render-memory-os-status-block.py --check`.
- The renderer's `find_marked_files()` returns an empty set when the markers are absent and `--check` exits 1.
- Current `README.md` and Round 10 authority use an unmarked current-status format; `scripts/validate-memory-os-entry-docs.py` and `scripts/validate-memory-os-operability.py` are existing canonical checks.
- A bounded update to the renderer at blob `8c25c0fd03ed6b8fd858ea6680d35c0081a270f7` was rejected by the external execution safety layer before a GitHub commit.

### Root cause or unknown
- The CI mismatch is verified: the workflow still calls a marker-based Round 9 renderer after current documents moved to Round 10.
- The write rejection's root cause is unknown outside repository content.

### Failed approach
- Updating the legacy renderer to fail closed by invoking existing Round 10 entrypoint and operability validators when no markers exist was blocked before commit creation.

### Correction
- Preserve the existing Security Contracts gate and Round 10 production authority. Do not add dummy markers, suppress the CI step, claim a passing run, or route around the blocked target.
- When the renderer becomes writable, retain legacy marked-file checks, refuse markerless `--write`, and delegate markerless `--check` to the existing canonical Round 10 validators with bounded execution.

### Recurrence guard
- A generated-document CI check must validate the current document authority rather than require retired historical markers. Markerless fallback must execute current validators and fail closed on missing validators, nonzero exits, or timeout.
- Distinguish source-level CI reachability from observed exact-HEAD CI success.

### Retry condition
- Retry the renderer mutation only after a relevant target-blob change or demonstrated target-specific write-policy/capability change; branch movement or an unrelated successful write is insufficient.

### Protected-authority check
- Before the rejected write, `productionDecision=NO_GO` and OPS-P0-007 `PARTIAL_FOUNDATIONS_ONLY` were observed. No commit or production evidence was created; the semantic-generation, distinct-environment, human recovery-objective, current reviewed-drill-request, typed eight-domain non-resurrection, independent-review and separate human-promotion gates remain mandatory.

## 2026-10-23 — Strict snapshot negative proofs must establish the injected failure and preserve production status

### Outcome
- Strengthened two existing CI-reachable OPS-P0-007 snapshot negatives without changing the generator, admission rules, recovery registries, or production authorities.
- The post-write rollback negative now requires an actually corrupted published candidate to remain after a deliberately failed rollback, until the negative harness explicitly restores the canonical snapshot. Both rollback scenarios also verify canonical production-status bytes and mode are unchanged.
- The atomic-write negative now requires exactly one attempted replacement of the canonical snapshot and the precise injected replacement-error diagnostic, rather than accepting an unrelated atomic-write failure.

### Evidence
- Commit `e52572d1787bf59994fdcb53e72152fcfa561885` modified only `scripts/validate-memory-os-ops-p0-007-admission-snapshot-post-write-rollback-negative.py`. Exact-source workflow run `39922869836` completed SUCCESS; logs confirm the injected invalid candidate, rollback diagnostic, byte/mode cleanup, and unchanged production-status bytes/mode.
- Commit `8791bbb84c653ff8d3c6fbb707faac46fc890ee7` modified only `scripts/validate-memory-os-ops-p0-007-admission-snapshot-atomic-write-negative.py`. Exact-source workflow run `39922917627` completed SUCCESS; logs confirm one canonical replacement attempt, the injected failure, and the workflow's clean-worktree and byte/mode checks.
- Both owning workflows already path-trigger and execute their respective negative scripts. These successes are exact-source CI negative proofs, not production or recovery drill evidence.

### Why safe
- Changes affect negative-test assertions only. No production-equivalent generation, objective, request, restore evidence, credential, traffic, readiness, promotion, or canonical snapshot value was created or modified.
- The tests retain the existing cleanup and fail-closed semantics, and explicitly check canonical authority integrity.

### Reusable mechanism
- A failure-injection negative must prove the intended injected transport failure actually occurred: assert the exact sentinel and bounded target-attempt count, not merely a generic failure class.
- For failed post-write rollback, assert the invalid candidate remains observable before explicit test cleanup; otherwise a silently repaired or never-mutated candidate could yield false confidence.
- Verify unrelated protected authority bytes and modes when exercising mutation boundaries, even when the test is scoped to a different authority.

### Protected-authority check
- Post-commit re-read confirmed `productionDecision=NO_GO`, OPS-P0-007 `PARTIAL_FOUNDATIONS_ONLY`, `blocking=true`, and zero registered/semantically eligible generations, approved objectives, executable requests, recovery evidence, complete typed non-resurrection records, and final recovery candidates.
- Learning remains append-only execution history, not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence. Distinct-environment semantic eligibility, explicit human-approved current objective, current executable reviewed request, all eight typed domains, independent review, and separate human promotion remain mandatory.

## 2026-10-23 — Read-only workflow permission checks must reject write-all and test their own regex

### Symptom
- The first write-all permission hardening commit caused its owning permission-boundary CI workflow to fail on an otherwise valid read-only PR workflow.

### Evidence
- Commit `55ba226e80290995efc30ae397f5317d4060e3fb` added a top-level read-only permission guard and isolated write-all negative fixtures.
- Exact-source run `39923080549` failed at `Prove strict snapshot permission boundary` with `strict snapshot PR workflow must declare top-level contents: read`.
- Inspection of the committed Python raw regex showed doubled escapes (`\\n` and `\\t`) in the pattern, so the expected actual newline was not matched. The existing PR workflow has the intended top-level `permissions:` / `contents: read` declaration.

### Root cause or unknown
- Verified root cause: double-escaping a raw Python regular expression during code generation made the positive-control pattern match a literal backslash-n sequence rather than a newline.

### Failed approach
- Publishing a generated raw-regex guard without first proving that its literal escapes match a real positive fixture. The initial negative fixtures could not establish useful protection because the positive control failed.

### Correction
- Commit `799007e31fe352d2bfdcce52346e73e2b903dea3` replaced the malformed patterns with literal newline-aware expressions and simplified the positive fixture.
- Exact-source permission-boundary workflow run `39923120206` completed SUCCESS, including Python compilation, canonical PR/publisher checks, isolated write-all rejection fixtures, and clean-worktree verification.

### Recurrence guard
- Every new static permission matcher must exercise both a known-valid positive fixture and representative escalation negatives before claiming a protected boundary.
- The committed helper requires a real top-level `contents: read` declaration, rejects any `permissions: write-all` declaration (including job-level), and retains the existing `contents: write` prohibition.
- Do not treat a matching string in a comment or a general YAML fragment as equivalent to a real top-level permission declaration.

### Retry condition
- The initial malformed-regex approach is superseded; do not restore it. Revisit only if GitHub Actions permission syntax changes, the PR workflow's actual permission structure changes, or a new bypass is demonstrated by an executable negative fixture.

### Outcome
- The existing CI-reachable snapshot workflow permission negative now rejects write-all token escalation in addition to direct contents-write escalation.

### Why safe
- Only the permission-boundary negative script changed. No workflow token permissions, production authority, recovery evidence, credentials, traffic, readiness, or promotion were modified.

### Reusable mechanism
- Bind workflow permission checks to explicit positive and negative synthetic YAML snippets and exact-source CI execution. When embedding regular expressions in generated source, check the resulting literal source escapes rather than only the generator string.

### Protected-authority check
- Re-read after correction confirmed `productionDecision=NO_GO`, OPS-P0-007 `PARTIAL_FOUNDATIONS_ONLY`, blocking=true, and unchanged strict admission snapshot. No registered/eligible generations, approved objectives, executable drill requests, generation recovery evidence, complete eight-domain typed records, or final candidates were created.
- This learning entry is append-only history and cannot satisfy any production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion gate. Semantic eligibility from distinct environments, explicit human objective approval, current executable reviewed request, eight typed domains, independent review, and separate human promotion remain required.

## 2026-10-23 — Atomic snapshot failure proof also preserves unrelated production status

### Outcome
- Extended the existing OPS-P0-007 snapshot atomic-write negative to assert the canonical production operability status is unchanged byte-for-byte and mode-for-mode after an injected snapshot replacement failure.

### Evidence
- Commit `322ce2fcb5530671fc70efc763d5ac0496cde73e` changed only `scripts/validate-memory-os-ops-p0-007-admission-snapshot-atomic-write-negative.py`.
- Exact-source workflow run `39923333192` completed SUCCESS. Logs show the injected canonical replacement failure was observed once, the negative passed, and canonical production status bytes/mode remained unchanged. The workflow also checks canonical snapshot digest, mode, temporary residue and clean worktree.
- Separately, exact-source OPS-P0-007 Admission Snapshot Readonly run `39923120147` completed SUCCESS on permission-correction commit `799007e31fe352d2bfdcce52346e73e2b903dea3`. Do not misattribute that run to this later atomic-negative commit.

### Why safe
- This change only adds an integrity assertion to a CI-reachable negative test. It does not alter a writer, production authority, recovery registry, traffic, credentials, readiness, or promotion.

### Reusable mechanism
- In a scoped writer-failure negative, snapshot both the target and adjacent protected authority bytes/modes before failure injection and prove neither drifted afterward. Retain the exact injected-failure sentinel and bounded target-attempt assertion to prevent unrelated failures from producing false PASS.

### Protected-authority check
- Post-change source re-read showed `productionDecision=NO_GO`, OPS-P0-007 `PARTIAL_FOUNDATIONS_ONLY`, blocking=true, and unchanged canonical snapshot/status blobs. Registered generations, semantically eligible generations, approved objectives, executable reviewed requests, recovery evidence, complete typed eight-domain records, and final candidates remain zero.
- This lesson is append-only operational history, not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence. Independent review and separate human promotion remain non-automatic gates.

## 2026-10-23 — Snapshot diagnostic publication must have executable call-site proof, not text fragments

### Symptom
- The existing snapshot workflow permission negative could accept diagnostic writer fragments in comments, string literals, or statically dead Python branches as evidence of crash-safe publication.

### Evidence
- Before correction, `validate_atomic_diagnostic_publication` checked only whether source substrings such as `os.replace(tmp_name, path)`, `os.fsync(handle.fileno())`, and `os.unlink(tmp_name)` appeared in the YAML text. The check did not parse the actual Python heredoc or distinguish executable calls from non-executable text.
- The owning push workflow `.github/workflows/ops-p0-007-snapshot-permission-boundary.yml` invokes the negative suite directly on changes to that suite.

### Root cause or unknown
- Verified: textual presence was incorrectly treated as executable call-site evidence. This was a static guard coverage gap, not an observed failure of the canonical snapshot writer.

### Failed approach
- Relying on source-fragment checks alone, which can be satisfied by comments or dead code.

### Correction
- Commit `631f4bb53487820ccec83eeaa8125dc9b78d3ea7` extends the existing negative suite to parse the publisher's actual Python heredoc, require exact AST call expressions and existing-mode assignment, enforce write/flush/fsync/replace/cleanup ordering, and require replacement plus unlink cleanup within one try/finally.
- Isolated in-memory mutations remove live replacement, flush, fsync, or cleanup while retaining their text in comments, strings, or `if False`; a direct-write substitution is also rejected.

### Recurrence guard
- The committed suite first establishes the canonical positive control, then requires all five mutation cases to fail closed at the intended diagnostic guard. It rejects comment-only, string-only, and statically dead call-site substitutes without modifying canonical workflow or production authority.
- This is stronger static executable-site proof, not evidence that the failure-only publication step has run in CI or that persisted diagnostic output has been privacy-reviewed.

### Retry condition
- Revisit if the publisher changes heredoc structure or a new executable-call bypass is demonstrated. Do not weaken the check to accept comments, strings, or unreachable branches.

### Outcome
- Exact-source `OPS P0 007 Snapshot Permission Boundary` run `39931221464` completed SUCCESS on commit `631f4bb53487820ccec83eeaa8125dc9b78d3ea7`.

### Success evidence
- The run compiled and invoked the bound negative script and completed the clean-worktree step; the job log reports `Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS` and `production decision: NO_GO`.

### Why safe
- The commit modified only the CI-reachable negative suite; it did not change workflow token permissions, the diagnostic publisher, a registry, production status, snapshot authority, credentials, traffic, recovery evidence, or promotion.

### Reusable mechanism
- Extract the exact embedded executable language block, parse syntax rather than trusting substrings, exclude unexecuted definitions and constant-false branches, require call-site ordering and cleanup scope, and mutate a real positive control in memory. Distinguish static executable proof from observed execution of a conditional production-side step.

### Protected-authority check
- Post-commit re-read confirmed `productionDecision=NO_GO`, OPS-P0-007 strict snapshot `PREREQUISITES_BLOCKED`, zero registered/semantically eligible generations, zero approved recovery objectives, zero executable reviewed drill requests, zero recovery evidence, zero complete typed eight-domain records, and zero final candidates. Status and snapshot blobs remained unchanged.
- Learning is append-only operational history, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence. Distinct eligible environments, explicit human-approved current objective, current executable reviewed request, typed eight-domain non-resurrection, independent review, and separate human promotion remain mandatory.

## 2026-10-23 — Snapshot symlink negatives must never clobber fixed shared /tmp paths

### Symptom
- The canonical OPS-P0-007 snapshot negative suite created two external symlink targets at fixed shared `/tmp` paths before testing source and executable-module symlink escape. A preexisting file or attacker-controlled symlink at either path could be overwritten by `write_bytes`.

### Evidence
- Before correction, `run_source_symlink_escape` wrote `/tmp/memory-os-ops-p0-007-objective-authority.json` and `run_module_symlink_escape` wrote `/tmp/memory-os-ops-p0-007-objective-writer.py` without unique ownership. Both functions restored canonical files using `write_bytes` after unlinking symlinks, without explicitly restoring the original file mode.
- The canonical snapshot readonly workflow invokes this negative suite directly and checks protected authority bytes, modes, and worktree cleanliness.

### Root cause or unknown
- Verified design flaw: deterministic filenames in a shared temporary directory do not establish exclusive ownership or safe cleanup. No real collision or exploit was observed.

### Failed approach
- Using fixed shared temporary paths as external test targets and assuming they are unused.

### Correction
- Commit `17b599112566c16ab40fc90e39b5039a0668493b` replaces both fixed paths with unique `tempfile.TemporaryDirectory` contexts outside the checkout. Symlink creation is inside a `try/finally`, and each canonical file's original mode is restored explicitly after the synthetic symlink test.

### Recurrence guard
- Both tests now use per-invocation temporary directories with automatic cleanup, retain canonical validator/generator symlink rejection, and preserve canonical bytes/modes. The existing exact-source readonly workflow executes these paths and verifies all protected authority digests and modes before and after.

### Retry condition
- Revisit if a new fixed shared-path fixture is introduced, a cleanup/mode regression is demonstrated, or the source-binding policy changes. Do not restore fixed shared `/tmp` names merely to simplify fixtures.

### Outcome
- Exact-source `OPS P0 007 Admission Snapshot Readonly` run `39931399713` completed SUCCESS on `17b599112566c16ab40fc90e39b5039a0668493b`; the job log confirms strict snapshot negative PASS, source and module symlink escape rejection, canonical authority byte/mode checks, and `production decision: NO_GO`.
- Exact-source snapshot publisher run `39931399701` also completed SUCCESS without creating a production-equivalent generation or changing production authority.
- The concurrent `Backup Restore Admission Chain Negative` run `39931399618` failed at inventory generation with the previously recorded clean-source-worktree fixture interference. This was an existing upstream blocker, not evidence of failure in the isolated snapshot symlink negative.

### Why safe
- Only a test fixture's external scratch-target allocation and cleanup changed. No canonical writer, production authority, recovery evidence, credentials, traffic, readiness, or promotion was changed.

### Reusable mechanism
- For negative tests that deliberately symlink canonical sources to external targets, allocate unique owner-controlled scratch paths outside the checkout, wrap symlink installation in `try/finally`, and restore exact bytes and original modes. A failing unrelated aggregate CI job must not be misattributed to a passing exact-source focused guard.

### Protected-authority check
- Post-commit re-read confirmed `productionDecision=NO_GO`, strict OPS-P0-007 `PREREQUISITES_BLOCKED`, zero registered and semantically eligible generations, zero human-approved current objectives, zero executable reviewed drill requests, zero recovery evidence, zero complete typed eight-domain records, and zero final candidates. Canonical status, snapshot, and autonomous-learning contract blobs were unchanged.
- This append-only learning entry is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence. Distinct unsuperseded eligible environments, human-approved current recovery objective, current executable reviewed request, typed eight-domain non-resurrection, independent review, and separate non-automatic human promotion remain mandatory.

## 2026-10-23 — Snapshot PR permission guard must reject compact and quoted write grants

### Symptom
- The existing read-only PR workflow guard rejected literal `contents: write` and unquoted `permissions: write-all`, but compact `contents:write`, inline `{contents:write}`, quoted `contents: "write"`, and quoted `permissions: 'write-all'` could evade the string/regex checks.

### Evidence
- Before correction, the guard used `"contents: write" not in workflow` and an unquoted `write-all` line matcher. Synthetic positive/negative regex checks confirmed the valid `contents: read` control and five representative escalation variants can be distinguished.
- The dedicated `.github/workflows/ops-p0-007-snapshot-permission-boundary.yml` directly invokes this negative suite on changes to the script.

### Root cause or unknown
- Verified: formatting-sensitive textual matching was narrower than valid YAML permission syntax. No actual permission escalation or credential exposure was observed.

### Failed approach
- Treating one whitespace/quoting spelling of a GitHub Actions permission as exhaustive proof of a read-only token.

### Correction
- Commit `192486bd936e45945935ff41d79fddae8f72f9ec` normalizes comment tails for permission checking, rejects quoted/unquoted `write-all`, and rejects compact, quoted, and inline-mapping `contents:write`. It retains the mandatory real top-level `contents: read` positive control and the existing escalation negatives.

### Recurrence guard
- The CI-reachable negative suite now includes a quoted write-all fixture plus three compact/quoted contents-write fixtures. Each must fail at the intended permission guard, while the canonical read-only workflow must pass.
- This is a bounded permission-syntax guard, not a full YAML parser. New YAML syntaxes or shell-generated permission authority require their own executable proof.

### Retry condition
- Revisit only if a new valid GitHub Actions permission spelling bypasses these guards or the workflow's permission structure changes; never relax read-only authority to accommodate formatting.

### Outcome
- Exact-source `OPS P0 007 Snapshot Permission Boundary` run `39931809047` completed SUCCESS on `192486bd936e45945935ff41d79fddae8f72f9ec`, including Python compilation, the full positive/negative suite, and clean-worktree verification.

### Success evidence
- The job log confirms `Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS`, top-level read-only permissions, and `production decision: NO_GO`.

### Why safe
- Only the existing CI-reachable negative guard changed. No GitHub Actions workflow permission declaration, production status, recovery authority, credential, traffic, readiness, or promotion was changed.

### Reusable mechanism
- For policy syntax checks, exercise real positive syntax and compact, quoted, inline, and nested escalation variants. Prefer syntax-aware or bounded regex matching over one literal substring, and require exact-source CI execution before reporting an installed guard as verified.

### Protected-authority check
- Post-commit re-read confirmed unchanged production-status and strict OPS-P0-007 snapshot blobs, `productionDecision=NO_GO`, zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, recovery evidence, complete typed eight-domain records, and final candidates. Independent review and separate non-automatic human promotion remain mandatory.
- Learning is append-only operational history only, not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence.

## 2026-10-23 — Snapshot negative subprocesses require bounded timeout and exact failure proof

### Symptom
- The canonical OPS-P0-007 snapshot negative suite invoked its validator and generator through `subprocess.run` without a timeout. A hung child could consume the CI job's entire time budget and leave the negative case without a controlled diagnostic.

### Evidence
- Prior to correction, both `run_validator` and `run_generator_rejects` used `subprocess.run(..., check=False)` without a `timeout` argument. The dedicated snapshot readonly workflow invokes the negative suite with a 10-minute job limit.

### Root cause or unknown
- Verified coverage gap: the negative harness lacked its own subprocess deadline. No real hung validator or generator was observed.

### Failed approach
- Relying solely on the outer CI job timeout for individual subprocess calls.

### Correction
- Commit `2336b5d12326c9ec2a3ceb316cb7ba3401d89acc` routes both call sites through `run_bounded_python` with a 90-second per-child timeout, converting `subprocess.TimeoutExpired` into a controlled, labeled `Fail`.
- A self-contained injected timeout negative monkeypatches `subprocess.run` for both canonical validator and generator paths and requires the exact timeout diagnostic before the unmodified baseline runs.

### Recurrence guard
- The CI-reachable negative suite executes the synthetic timeout proof on every run and fails if a timeout is accepted, misclassified, or not converted to a controlled error. The canonical positive/negative checks remain in the same workflow.

### Retry condition
- Revisit only if legitimate exact-source validator execution exceeds the 90-second per-call bound, or a subprocess descendant cleanup gap is observed. Do not silently remove the timeout or count generic failure as the intended rejection.

### Outcome
- Exact-source `OPS P0 007 Admission Snapshot Readonly` run `39931982089` completed SUCCESS on `2336b5d12326c9ec2a3ceb316cb7ba3401d89acc`, including Python compilation, injected timeout proof, canonical negative cases, and protected-authority digest/mode checks.
- `OPS P0 007 Admission Snapshot` run `39931981960` also completed SUCCESS on the same source.
- `Backup Restore Admission Chain Negative` run `39931981912` failed at the previously documented Source-binding Clean Worktree interference. This independent existing blocker was not retried or changed.

### Why safe
- Only a test harness subprocess wrapper and isolated injected timeout proof changed; canonical validators, generator, production status, snapshot, registries, traffic, credentials, readiness, and promotion remained untouched.

### Reusable mechanism
- Wrap child validators in bounded subprocess calls, convert timeout to an exact typed failure, and prove the timeout branch with a synthetic injected exception before running the real baseline. Keep CI job-level timeout separate from each child's fail-closed deadline.

### Protected-authority check
- Post-commit source re-read confirmed `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, recovery evidence, complete typed eight-domain records, and final candidates. Protected status/snapshot and learning contract blobs were unchanged.
- This append-only learning history is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence. Distinct unsuperseded eligible environments, explicitly human-approved current objective, current executable reviewed request, typed eight-domain non-resurrection, independent review, and separate human production promotion remain mandatory.

## 2026-10-23 — Learning negative proof must distinguish controlled rejection from unexpected validator failure

### Symptom
- The autonomous-learning negative suite accepted any nonzero validator exit with a substring containing `AUTONOMOUS LEARNING VALIDATION FAILED`. The canonical validator also emits `AUTONOMOUS LEARNING VALIDATION FAILED WITH UNEXPECTED ERROR` with exit 2, so an implementation exception could be mistaken for a successful fail-closed negative.

### Evidence
- Before correction, `require_failure` checked only `result.returncode == 0` and the broad diagnostic substring. The `run` helper also had no subprocess timeout.
- The earlier 2026-09-21 write blocker for this target had a changed precondition: GitHub history shows subsequent target-file commits on 2026-09-22 and 2026-09-23, including `c98b0cf`; the current target blob before this change was `06b675b82fbed17701b41e277cef5e9c72caad68`.

### Root cause or unknown
- Verified: substring-only failure classification conflated expected validator rejection with unexpected exceptions. The missing subprocess deadline was an independent bounded-execution gap. No actual unexpected-error false PASS was observed in CI.

### Failed approach
- Counting arbitrary nonzero exits and a shared error-message prefix as sufficient proof of a canonical guard.

### Correction
- Commit `98ca5fdec516a2df3b5d3710bccf1551dc77820b` requires exact exit 1, an anchored `AUTONOMOUS LEARNING VALIDATION FAILED: ` diagnostic, and absence of an interpreter traceback. It also adds a 90-second timeout and controlled timeout failure.
- A self-test rejects four synthetic noncanonical outcomes (exit 0, exit 2 unexpected error, exit 1 unexpected-error prefix, and traceback) and accepts one synthetic canonical exit-1 rejection.

### Recurrence guard
- The existing negative suite executes the classifier self-test before its canonical fixture positive control and 22 fail-closed mutation cases. A generic exception cannot satisfy the intended rejection.
- The `Operability Contracts` workflow statically invokes the shared learning guard entrypoint transitively; its current path filters do not include the learning negative script itself. A new exact-source CI run for this commit has **not** been observed, so this is committed executable coverage plus an isolated 5/5 classifier reproduction, not CI-verified coverage.

### Retry condition
- Do not reintroduce broad substring/nonzero acceptance. Verify the complete suite when an existing workflow runs at an exact source containing this commit or a legitimate path-triggered invocation is available. Do not change protected learning contract or fabricate a trigger solely to claim CI success.

### Outcome
- The target-specific previously blocked path accepted the normal contents update after its recorded blob precondition changed. Isolated Python classifier reproduction returned 5/5 expected outcomes; post-commit source re-read confirmed the timeout, exact-exit, and anchored diagnostic checks.
- No new GitHub Actions run was associated with this commit at the time of observation.

### Why safe
- Only the existing autonomous-learning negative harness changed. Its canonical positive validator, learning contract, production status, recovery authorities, credentials, traffic, readiness, and promotion remained untouched.

### Reusable mechanism
- Require a controlled rejection's exact exit code and diagnostic namespace, reject unexpected errors and tracebacks, prove the classifier with synthetic positive and negative outcomes, and bound child execution. Keep committed guard, isolated reproduction, static CI reachability, and observed exact-source CI success as separate proof levels.

### Protected-authority check
- Post-commit re-read confirmed `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, recovery evidence, complete typed eight-domain records, and final candidates. Canonical status/snapshot and learning contract blobs remained unchanged.
- This append-only learning history is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence. Distinct eligible environments, explicitly human-approved current objective, current executable reviewed request, typed eight-domain non-resurrection, independent review, and separate human promotion remain mandatory.

## 2026-10-23 — Snapshot checkout must bind the actual checkout step, not merely mention the SHA

### Symptom
- The strict snapshot PR workflow guard accepted the presence of `github.event.pull_request.head.sha` anywhere in the workflow, while the publisher guard searched for a `ref: github.sha` text fragment. Either could be satisfied by a comment or unrelated shell assertion after the actual checkout source was changed.

### Evidence
- The canonical PR workflow mentions its expected head SHA both in checkout `with.ref` and a later source-identity assertion. A mutated checkout could therefore use `github.sha` while the loose PR guard still saw the required head-SHA substring.
- The publisher's original `ref: ${{ github.sha }}` text check did not structurally bind that fragment to the actual checkout step.

### Root cause or unknown
- Verified static guard coverage gap: textual presence was treated as proof of the actual checkout source. No real incorrect checkout or malicious workflow change was observed.

### Failed approach
- Relying on an arbitrary SHA string or unanchored `ref:` fragment instead of the `actions/checkout@v4` step's executable `with.ref`.

### Correction
- Commit `a9aeb77b8648804b4019b4144c709c2c41637fa4` adds an anchored checkout-step matcher requiring exactly one checkout and the exact expected event source: PR head SHA for read-only PR validation and event SHA for the publisher.
- Isolated mutations substitute the wrong checkout ref while retaining the correct expression in a comment, and introduce an ambiguous duplicate checkout; all must fail at the intended checkout-source guard.

### Recurrence guard
- The existing CI-reachable permission-boundary negative suite first proves both canonical workflows satisfy exact checkout binding, then rejects comment-only source proof and duplicate checkout steps for each workflow.
- The matcher is intentionally fail-closed for the current checkout-step YAML structure; any legitimate workflow structural change requires an explicit guarded update and new exact-source CI evidence.

### Retry condition
- Revisit if the checkout action version or YAML structure legitimately changes, or a new non-executable source-binding bypass is demonstrated. Do not restore unanchored source-string checks.

### Outcome
- Exact-source `OPS P0 007 Snapshot Permission Boundary` run `39932644650` completed SUCCESS on `a9aeb77b8648804b4019b4144c709c2c41637fa4`. Logs confirm the negative suite PASS and `production decision: NO_GO`.

### Why safe
- Only the existing read-only workflow negative test changed. No checkout workflow, token grant, production authority, recovery registry, credentials, traffic, readiness, or promotion was changed.

### Reusable mechanism
- Validate source identity at the actual executable checkout call site, reject ambiguous duplicate steps, and prove comments or later assertions cannot substitute for that binding. Distinguish static exact-step proof from a production deployment or recovery execution.

### Protected-authority check
- Post-commit re-read confirmed unchanged canonical production status and OPS-P0-007 snapshot blobs, `productionDecision=NO_GO`, zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, recovery evidence, complete typed eight-domain records, and final candidates. Independent review and separate human promotion remain mandatory.
- This append-only lesson cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion gates.

## 2026-10-23 — AST call presence is insufficient when required publication calls are conditional

### Symptom
- The snapshot diagnostic AST guard already excluded literal `if False` and unexecuted function definitions, but it could still count a required call placed under a comparison-dead branch such as `if 1 == 2`.

### Evidence
- The initial AST helper walked executable-looking call nodes and skipped only `ast.If` nodes whose test was an `ast.Constant`. A comparison expression is an `ast.Compare`, so the guard could observe a syntactically present but never-executed fsync or chmod call.

### Root cause or unknown
- Verified: AST node presence does not establish unconditional call reachability through surrounding control-flow ancestors. No actual workflow was observed using such a bypass.

### Failed approach
- Treating an AST call expression as sufficient executable proof without checking whether it is enclosed by a conditional branch.

### Correction
- Commit `3c905a0682849d964c2625c05012ec94b4008785` adds parent-ancestry checks: mkstemp, write, flush, fsync, replace, and unlink may not be nested under a conditional; fchmod must be enclosed by exactly the canonical `existing_mode is not None` guard.
- Two new isolated negative mutations move fsync or chmod under comparison-dead branches while preserving their source text. Both must fail at the intended diagnostic guard.

### Recurrence guard
- The CI-reachable snapshot permission negative now checks required call-site ancestors in addition to exact AST expressions, call ordering, try/finally cleanup, comment-only, quoted, and constant-false substitutions.

### Retry condition
- Revisit if the canonical diagnostic writer legitimately introduces a conditional around a publication call or a new unreachable-control-flow bypass is demonstrated. Do not silently count conditional call presence as a completed atomic publication mechanism.

### Outcome
- Exact-source `OPS P0 007 Snapshot Permission Boundary` run `39932851635` completed SUCCESS on `3c905a0682849d964c2625c05012ec94b4008785`, including Python compilation, the expanded canonical/negative suite, and read-only execution checks.

### Why safe
- Only the existing negative test changed. The publisher workflow, diagnostic output, production authority, recovery evidence, credentials, traffic, readiness, and promotion were not modified.

### Reusable mechanism
- For embedded-language static checks, require both exact AST call expressions and valid control-flow ancestry. Prove dead-code resistance with comparison-false mutations, not just `if False`, and retain exact-source CI evidence separate from actual conditional publisher execution.

### Protected-authority check
- Post-commit re-read confirmed unchanged production status and OPS-P0-007 strict snapshot blobs, `productionDecision=NO_GO`, zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, recovery evidence, complete typed eight-domain records, and final candidates. Independent review and separate human promotion remain mandatory.
- Learning remains append-only operational history and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion gates.

## 2026-10-23 — Snapshot diagnostic publication cannot hide required calls in never-run loops

### Symptom
- The AST publication guard rejected conditional `if` branches but could still count required calls inside `while False` or `for _ in []` loops, even though those bodies never execute.

### Evidence
- Before correction, the required-call ancestor check classified only `ast.If` as conditional. An `ast.While` or `ast.For` ancestor therefore did not invalidate an otherwise exact fsync call.

### Root cause or unknown
- Verified static coverage gap: a call node under a loop does not establish that the loop executes. No actual workflow bypass was observed.

### Failed approach
- Treating all non-`if` AST call ancestors as unconditional publication paths.

### Correction
- Commit `54084547fa834648bbc3fd595e6b47d63040ff6b` extends the ancestor guard to while/for/async-for/match/except-handler control flow and retains the single canonical existing-mode `if` exception for chmod.
- Isolated mutations hide fsync under a constant-false while loop or an empty for loop. Both must be rejected.

### Recurrence guard
- The existing CI-reachable snapshot permission negative proves exact call expressions, order, try/finally cleanup, and the absence of conditional/loop-hidden publication calls.

### Retry condition
- Revisit if the canonical writer legitimately introduces conditional or loop-based publication, or a new unreachable-control-flow bypass is demonstrated. Never infer runtime execution from AST call presence alone.

### Outcome
- Exact-source `OPS P0 007 Snapshot Permission Boundary` run `39933076546` completed SUCCESS on `54084547fa834648bbc3fd595e6b47d63040ff6b`, including Python compilation, canonical positive control, loop-dead negatives, and clean-worktree verification.

### Why safe
- Only the existing negative suite changed. The publisher workflow, canonical status, recovery registries, credentials, traffic, readiness, and promotion were untouched.

### Reusable mechanism
- Inspect all relevant control-flow ancestors of required AST calls and prove unreachable loop substitutions with deterministic in-memory negatives. This is static executable-site assurance, not observed execution of a failure-only publication step.

### Protected-authority check
- Post-commit re-read confirmed unchanged production status and OPS-P0-007 strict snapshot blobs, `productionDecision=NO_GO`, zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, recovery evidence, complete typed eight-domain records, and final candidates. Independent review and separate human promotion remain mandatory.
- Learning is append-only operational history, not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence.

## 2026-10-23 — Learning CI entrypoint requires observed guard PASS, not only exit zero

### Symptom
- The existing operability entrypoint accepted an autonomous-learning child with exit code zero even if the child emitted no validation result, allowing a no-op or truncated negative suite to appear successful.
- The first synthetic classifier fixture committed for this correction used a literal backslash-n instead of a newline and rejected its own valid positive control.

### Evidence
- Before commit `440f3635c91ae84a58fb643d0dcdb227e6ca93c7`, `scripts/validate-memory-os-entry-docs.py` checked only `completed.returncode != 0` and did not capture the two guard outputs.
- The first committed classifier's five synthetic strings ended with `\\\\n` in Python source, so `.strip()` did not match the required PASS text. Several workflows on that commit failed or were cancelled; those runs are not evidence that the corrected guard passed.
- Commit `fb21d1d491fb7e2bd60f8234c9aa665eacfc4c2f` corrected all five fixture escapes to real Python newline escapes. Source re-read confirmed the correction; independent classifier reproduction exercised ten expected accept/reject outcomes. Exact-source Operability Contracts CI was still running when this lesson was recorded.

### Root cause or unknown
- Verified original coverage gap: process exit status alone is not proof that a bound validator actually ran its required checks.
- Verified correction failure: an extra escaping layer in generated source changed intended newline characters into literal backslash-n text. No production validator or recovery evidence failed.

### Failed approach
- Trusting a zero exit without a recognizable success result, and constructing synthetic Python string literals without checking the emitted source escape depth.

### Correction
- The existing CI-reachable entrypoint now captures child stdout/stderr, requires exact positive PASS output, and requires the negative suite's structured PASS count to be numeric and at least 22. Nonzero exit, unexpected stderr, missing output, truncated suite and unbound guard all fail closed.
- A ten-case in-process classifier proof runs before the real bound validators. The corrected fixture strings use Python newline escapes.

### Recurrence guard
- Retain the synthetic positive controls and no-op, nonzero, stderr, truncated, nonnumeric, extra-output and unbound negatives; never treat a child process's exit zero alone as learning-guard execution proof.
- Verify emitted source literals and a full exact-source CI run after changes to generated Python, especially when crossing JavaScript/Python escaping boundaries.

### Retry condition
- Do not restore the exit-only acceptance or double-escaped fixture strings. Revisit the minimum negative-case count or success marker only after the canonical negative suite changes legitimately and an observed new exact-source run establishes its output.

### Outcome
- Two code commits installed and corrected an executable PASS-result classifier in the existing operability CI entrypoint. The source-bound correction is observable; exact-source CI outcome is tracked separately and must not be inferred from the commit.

### Success evidence
- Independent ten-case classifier reproduction returned 10/10 expected outcomes; post-correction re-read found all five intended newline literals and no double-escaped synthetic PASS strings.

### Why safe
- The change is confined to a CI entrypoint and its synthetic classifier, not the learning contract, evidence registries, recovery validators, production status, credentials, traffic, readiness, or promotion.

### Reusable mechanism
- A transitive CI entrypoint should require a child validator's controlled success namespace and minimum expected negative coverage in addition to exit zero, with deterministic negative proof for a no-op child.

### Protected-authority check
- Post-correction re-read confirmed `productionDecision=NO_GO`, unchanged production-status and autonomous-learning contract blobs, and unchanged strict OPS-P0-007 snapshot and empty generation/objective/request/evidence/typed-coverage/promotion registries.
- This append-only lesson is execution history only. It cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates; distinct semantically eligible unsuperseded environments, human-approved current recovery objective, current executable reviewed request, complete typed eight-domain non-resurrection evidence, independent review and separate human promotion remain mandatory.

## 2026-10-23 — Exact-source learning guard output proof completed in Operability Contracts

### Outcome
- The existing operability CI entrypoint's exit-zero-plus-success-marker guard and ten-case classifier proof executed successfully at corrected source commit `fb21d1d491fb7e2bd60f8234c9aa665eacfc4c2f`.

### Evidence
- Exact-source `Operability Contracts` run `39937745962` completed SUCCESS. Its `Validate current entrypoint documents` step completed successfully; job logs show `Memory OS entrypoint document validation PASS`, `autonomous-learning guards: 2`, and `production decision: NO_GO` in the same job.
- The entrypoint captures the positive and negative guard outputs and rejects a missing marker, unexpected stderr, nonzero exit, or fewer than 22 negative cases. The child output is captured rather than emitted to the job log, so the observed evidence is the exact-source parent step's PASS, not separately displayed child stdout.

### Why safe
- The observed result is an execution guard only. No production evidence, recovery objective, registered environment generation, credential, traffic, readiness or promotion authority was written.

### Reusable mechanism
- Trigger an existing owning workflow through a meaningful entrypoint hardening change; require the transitive guard's controlled PASS namespace, run its synthetic negative classifier, and distinguish exact-source parent CI success from direct child log output.

### Protected-authority check
- Source re-read confirmed unchanged production-status and OPS-P0-007 snapshot blobs, `productionDecision=NO_GO`, `PREREQUISITES_BLOCKED`, and zero registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates. Human approval and promotion remain separate.
- This learning history is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Read-only snapshot PR permission must reject every write-capable token scope

### Symptom
- The strict OPS-P0-007 snapshot PR permission guard rejected `contents:write` and `permissions:write-all`, but allowed a token with `actions:write`, `id-token:write`, `pull-requests:write`, or another recognized write scope while `contents:read` remained present.
- The first synthetic test fixture for the extension was incorrectly double-escaped and failed the existing top-level read-only positive check.

### Evidence
- Before commit `159998b57bd89086b5c070645a1a6412755773f7`, `require_readonly_pr_permissions` had no generic write-scope rejection; the canonical PR workflow itself declared only `contents: read`.
- Exact-source permission-boundary run `39937992118` failed with `strict snapshot PR workflow must declare top-level contents: read` while exercising the double-escaped fixture, not because the canonical PR workflow had gained write authority.
- Commit `5a3944ab9392f312522200e3f92081e259dec819` corrected 25 escaped newline sequences and the Python raw regex string. Exact-source `OPS P0 007 Snapshot Permission Boundary` run `39938026887` then completed SUCCESS, including compilation, positive/negative scope fixtures, exact checkout and clean-worktree checks.

### Root cause or unknown
- Verified original guard gap: it matched only contents-write and write-all, rather than all GitHub Actions write-capable permission scopes.
- Verified first-patch failure: generated fixture strings contained literal backslash-n sequences, so a valid synthetic `permissions:\n  contents: read` mapping was not present in the parsed fixture.

### Failed approach
- Assuming a read-only contents scope alone implies a read-only workflow token, and emitting synthetic Python/YAML fixtures without verifying escape depth.

### Correction
- The existing CI-reachable snapshot permission negative now recognizes all 15 supported GitHub Actions token scopes and rejects `write` for any of them, including compact, quoted and inline mapping spellings. It preserves the required real top-level `contents: read` check and existing write-all/contents-write guards.
- Four new negative fixtures exercise actions, id-token, pull-requests and security-events write grants. A comment-only write mention remains a positive read-only control.

### Recurrence guard
- The owning snapshot permission workflow directly executes the strengthened negative script and checks clean source. Its exact-source SUCCESS proves both the canonical read-only control and the new write-scope mutation cases.
- Recheck emitted Python string literals and run exact-source CI before claiming new fixture coverage. Do not use regex text presence alone as proof of a live workflow permission declaration.

### Retry condition
- Do not restore contents-only token checks or double-escaped synthetic fixtures. Revisit if GitHub adds a token permission scope, changes permission YAML semantics, or a new valid write-grant spelling bypasses the executable negatives.

### Outcome
- Two commits installed and corrected the all-scope read-only PR token guard; the final exact-source permission-boundary workflow completed SUCCESS.

### Success evidence
- Isolated Python matcher reproduction distinguished eight valid/invalid permission fixtures (8/8), and exact-source workflow run `39938026887` passed after the correction.

### Why safe
- Only the existing read-only negative test was changed. The PR/publisher workflow permission declarations, snapshot generator, registries, production status, credentials, traffic, readiness and promotion were not modified.

### Reusable mechanism
- For read-only GitHub Actions policy, test the full recognized token-scope vocabulary and syntax variants rather than only `contents`; pair real positive controls with injected write grants, then require an observed exact-source CI PASS.

### Protected-authority check
- Post-correction source re-read confirmed `productionDecision=NO_GO`, unchanged canonical status and OPS-P0-007 strict snapshot blobs, `PREREQUISITES_BLOCKED`, and zero generation/objective/request/evidence/typed-coverage/final-candidate authority. Typed eight-domain evidence, independent review and separate human promotion remain mandatory.
- This append-only operational lesson cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Every mandatory autonomous-learning rule needs independent negative proof

### Outcome
- Extended the canonical autonomous-learning negative suite from 22 to 32 fail-closed mutations and raised the existing CI entrypoint's minimum accepted negative-case count to 32.
- Exact-source `Operability Contracts` run `39938219783` completed SUCCESS on commit `1477039bd1b7caa3832d24e5a506ae3a573faf39`.

### Evidence
- Commit `a465a6204eea0f6ed432c86ad83a54cd7bff3475` added eight independent false-rule mutations plus schema-version downgrade and closed-loop-order mutation, using the existing isolated positive control and canonical harness.
- Commit `1477039bd1b7caa3832d24e5a506ae3a573faf39` raised `MIN_LEARNING_NEGATIVE_CASES` to 32 and made the entrypoint's synthetic count fixtures derive from that constant instead of hard-coded 22/23/21 strings.
- Read-only contract-to-suite inspection found all 10 mandatory rule names represented, with explicit schema and loop mutations. Independent classifier reproduction returned 10/10 expected outcomes at the 32-case floor.
- Exact-source CI job `120362923214` completed SUCCESS; its `Validate current entrypoint documents` step passed and the log shows `Memory OS entrypoint document validation PASS`, `autonomous-learning guards: 2`, and `production decision: NO_GO`. Child stdout is captured by the entrypoint, so the 32-case count is verified through its enforced output parser rather than separately echoed in the CI log.

### Why safe
- Only the isolated learning negative harness and its existing operability entrypoint changed. No learning contract, recovery registry, production evidence, status, credential, traffic, readiness, or promotion authority was modified.

### Reusable mechanism
- Enumerate all mandatory Boolean rules against the canonical contract and mutate each independently after a fixture positive control. Add schema/loop drift cases, then enforce a monotonic minimum negative-suite count at the existing CI caller. Derive synthetic boundary fixtures from the same minimum to prevent count drift.

### Protected-authority check
- Post-change re-read confirmed unchanged autonomous-learning contract, production-status and strict OPS-P0-007 snapshot blobs, `productionDecision=NO_GO`, `PREREQUISITES_BLOCKED`, and zero registered/semantically eligible generations, approved recovery objectives, executable reviewed drill requests, generation recovery evidence, typed eight-domain records and final candidates. Independent review and separate human promotion remain required.
- Learning history is append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — All-scope snapshot PR guard also passed the full readonly snapshot workflow

### Outcome
- The independently triggered exact-source `OPS P0 007 Admission Snapshot Readonly` run `39938026883` completed SUCCESS on the corrected permission guard commit `5a3944ab9392f312522200e3f92081e259dec819`.

### Evidence
- This run is separate from the focused permission-boundary success `39938026887`. Both ran on the same corrected source commit; neither is production recovery evidence.

### Why safe
- Both are read-only CI validation of existing snapshot and permission authorities, with no new generation, objective, drill, recovery, typed-coverage, credential, traffic, readiness or promotion authority.

### Reusable mechanism
- Confirm a focused negative guard in its owning workflow and in an independent aggregate readonly workflow; preserve exact commit attribution for both results.

### Protected-authority check
- Production status remains `NO_GO`; OPS-P0-007 strict snapshot and its real-evidence, typed eight-domain, independent-review and separate human-promotion gates remain unchanged. This learning record is not production evidence.

## 2026-10-23 — Emit only validated learning guard success markers in exact-source CI

### Outcome
- The canonical operability entrypoint now emits the two child validators' previously verified single-line PASS results, making the actual negative-suite case count visible without weakening its output classifier.
- Exact-source `Operability Contracts` run `39938449672` completed SUCCESS on commit `457d864cf9c1c8b9b224a054c00f9fd1c066134b`.

### Evidence
- Commit `457d864cf9c1c8b9b224a054c00f9fd1c066134b` added a success-only print after `learning_guard_passed` returns true; the existing exit, stderr, exact marker, and minimum-count checks remain unchanged.
- CI job `120363687792` logs show `autonomous-learning guard verified: Autonomous improvement/learning contract validation PASS`, `autonomous-learning guard verified: Autonomous learning negative validation PASS (32 fail-closed cases)`, and `Memory OS entrypoint document validation PASS`.
- The same job reports `production decision: NO_GO`. An earlier failure at initial entrypoint commit `440f3635` is concretely visible in reconcile job `120361233206`, which logged three synthetic classifier positive-control failures before the corrected source passed.

### Why safe
- Only the existing CI entrypoint's post-validation diagnostic output changed. It prints no raw child failure output and does not write a production, backup/restore, recovery, credential, traffic, readiness, or promotion authority.

### Reusable mechanism
- When a parent validator captures child output for fail-closed classification, emit the controlled success marker only after exact validation. This provides direct exact-source CI auditability of suite breadth without counting arbitrary exit-zero processes as proof.

### Protected-authority check
- Source re-read confirmed unchanged production-status, autonomous-learning contract and strict OPS-P0-007 snapshot blobs, `productionDecision=NO_GO`, `PREREQUISITES_BLOCKED`, zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, generation recovery evidence, complete typed eight-domain records and final candidates. Independent review and separate human promotion remain required.
- This append-only lesson is operational execution history, not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Required learning failure/success fields now have complete missing-field negative coverage

### Outcome
- Extended the canonical learning negative suite from 32 to 42 fail-closed cases, independently removing each of the seven mandatory failure fields and five mandatory success fields.
- Exact-source `Operability Contracts` run `39938660322` completed SUCCESS on commit `900cb34a2107664b2e8e7d6f07076ebd1afe8a2e`.

### Evidence
- Commit `ee7e752dddc2695671d04ba135dbf7d18b3bb7ee` added six failure-field and four success-field missing-field cases to the existing two representative cases, using isolated fixtures and the unchanged canonical positive validator.
- Commit `900cb34a2107664b2e8e7d6f07076ebd1afe8a2e` raised the CI entrypoint's minimum negative-case count to 42 without altering its dynamic positive/negative classifier fixtures.
- Read-only contract-to-suite inspection found all seven failure and five success field names represented. Exact-source job `120364390078` logs explicitly show `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (42 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.

### Why safe
- Changes were limited to isolated learning negative fixtures and the existing CI entrypoint's minimum accepted test count. No production evidence, backup/restore registry, approved objective, drill, credential, traffic, readiness or promotion authority was changed.

### Reusable mechanism
- Prove every mandatory schema field's fail-closed behavior with an isolated missing-field mutation, retain a canonical positive control, and enforce the resulting minimum test count at a source-bound CI entrypoint that emits only verified PASS markers.

### Protected-authority check
- Post-change re-read confirmed unchanged autonomous-learning contract, production-status and strict OPS-P0-007 snapshot blobs, `productionDecision=NO_GO`, `PREREQUISITES_BLOCKED`, and zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, generation evidence, complete typed eight-domain records and final candidates. Independent review and separate human promotion remain mandatory.
- This append-only learning record is execution history only; it cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Learning CI reachability requires an AST-proven live main call

### Symptom
- The canonical autonomous-learning validator checked that `validate_learning_guards(failures)` appeared as source text in the CI entrypoint. A comment, quoted literal or dead branch could retain that substring without invoking either bound guard.

### Evidence
- Before commit `7b2b88180b8786c0e9dcca257bb66287d872bb71`, the validator enforced a textual fragment list but did not parse the entrypoint's executable `main()` body.
- The existing negative suite covered complete removal of the invocation but did not preserve its text while removing executable reachability.
- An isolated four-case AST reproduction accepted the direct call and rejected comment-only, quoted and `if False` forms.

### Root cause or unknown
- Verified: source-substring presence was being treated as live call-site proof. No actual workflow was observed bypassing the learning guards.

### Failed approach
- Requiring a recognizable invocation fragment without binding it to a direct executable statement in the entrypoint's `main()`.

### Correction
- Commit `7b2b88180b8786c0e9dcca257bb66287d872bb71` parses the bound entrypoint with Python AST, requires one `main` definition and one direct `validate_learning_guards(failures)` expression in its body, and emits controlled validation failures on missing/invalid syntax.
- Commit `7013639b919fedc2c1ac75a1a0828b7b5d745123` added three isolated comment-only, quoted and dead-branch invocation negatives.
- Commit `87b74fadbeb66b4c1fa5b5ece3453065934d61de` raised the existing CI entrypoint's minimum negative suite count to 45.

### Recurrence guard
- The canonical positive validator now fails closed if a comment or non-executed expression substitutes for the direct learning guard invocation. Three dedicated negative mutations retain the textual fragment while proving AST-level rejection.
- The existing CI caller enforces a 45-case minimum, a controlled child PASS marker, and an observed exact-source execution result. This direct-main-call proof does not claim to solve every possible Python control-flow or workflow path-filter bypass.

### Retry condition
- Revisit if the canonical entrypoint legitimately changes its invocation structure or a new reachable-code bypass is demonstrated. Do not weaken the check back to substring-only reachability.

### Outcome
- Exact-source `Operability Contracts` run `39938912571` completed SUCCESS on `87b74fadbeb66b4c1fa5b5ece3453065934d61de`.

### Success evidence
- CI job `120365222642` logs explicitly report `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (45 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.

### Why safe
- Changes affected only the learning positive/negative validators and their existing operability CI entrypoint. No workflow permission declaration, production status, recovery evidence, objective, credential, traffic, readiness or promotion authority was modified.

### Reusable mechanism
- For CI reachability, bind the actual direct call in the executable function body using AST rather than relying on text fragments. Prove comment/literal/dead-branch bypasses with isolated positive-controlled negative fixtures and exact-source CI execution.

### Protected-authority check
- Post-change re-read confirmed unchanged learning contract, production-status and strict OPS-P0-007 snapshot blobs, `productionDecision=NO_GO`, `PREREQUISITES_BLOCKED`, and zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, generation recovery evidence, complete typed eight-domain records and final candidates. Independent review and separate human promotion remain required.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — A live learning main call also needs a live module entrypoint

### Symptom
- The new AST guard verified that `main()` directly calls `validate_learning_guards(failures)`, but a module with `if False: raise SystemExit(main())` or a comment-only main invocation could still retain the entire live `main` function while never executing it.

### Evidence
- Before commit `f6e858ec9cac3a134869319ecca74d6177cb04b4`, the canonical positive validator checked the `main` function body but did not require the module-level `if __name__ == "__main__": raise SystemExit(main())` entrypoint.
- The actual canonical CI entrypoint has exactly this module guard; the existing 45-case negative suite did not mutate it.

### Root cause or unknown
- Verified reachability gap: an executable call inside a function is not proof that the module invokes that function. No real CI bypass was observed.

### Failed approach
- Treating a direct function-body call as sufficient end-to-end execution authority without binding the top-level module entrypoint.

### Correction
- Commit `f6e858ec9cac3a134869319ecca74d6177cb04b4` adds AST equality for exactly one canonical module-level `__main__` guard that raises `SystemExit(main())`.
- Commit `097cbe2cbcd74a940f47945f85604efbd3babea5` adds isolated dead-module-guard and comment-only-main-invocation negatives.
- Commit `79039e83e5ed11fed7e765d186ec5e5c87c64943` raises the existing CI entrypoint's minimum negative-case count to 47.

### Recurrence guard
- The canonical positive validator now requires both the direct learning guard call in `main()` and a live module-level `__main__` entrypoint. The negative suite must reject both synthetic bypasses while the unchanged positive control passes.
- This is AST structural reachability proof, not a claim to solve arbitrary dynamic Python execution or GitHub workflow trigger-policy gaps.

### Retry condition
- Revisit only if the canonical entrypoint legitimately changes its module invocation structure or a new bypass is demonstrated. Do not revert to substring-only or function-body-only proof.

### Outcome
- Exact-source `Operability Contracts` run `39939165018` completed SUCCESS on commit `79039e83e5ed11fed7e765d186ec5e5c87c64943`.

### Success evidence
- CI job `120366055059` logs show `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (47 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.

### Why safe
- Only the canonical learning validators and existing operability CI entrypoint were hardened. No production status, recovery objective, generation, drill request, typed evidence, credentials, traffic, readiness or promotion authority changed.

### Reusable mechanism
- Trace executable reachability from module entrypoint to `main()` to the bound validator call, using AST and isolated dead/comment-only mutations. Enforce the expanded negative-case floor at the exact-source CI caller.

### Protected-authority check
- Post-change re-read confirmed unchanged learning contract, production-status and strict OPS-P0-007 snapshot blobs, `productionDecision=NO_GO`, `PREREQUISITES_BLOCKED`, and zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, generation evidence, complete typed eight-domain records and final candidates. Independent review and separate human promotion remain mandatory.
- This append-only learning history cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Learning authority symlinks must not be accepted as canonical files

### Symptom
- The canonical autonomous-learning validator used `read_text()` and `Path.is_file()`, which follow symlinks. A contract, learning history, bound guard or CI entrypoint symlink could therefore satisfy ordinary file checks while redirecting authority to another path.

### Evidence
- Before commit `fbd51d2399287c7559fecbaae80952cc9702d676`, the validator had no `is_symlink()` check for the five canonical learning authority paths.
- The negative harness already seeds isolated temporary copies of all five files, allowing safe symlink substitution without touching the checked-out source.

### Root cause or unknown
- Verified path-identity gap: following a symlink is not equivalent to validating an exact canonical repository authority file. No real symlink substitution or external file access was observed.

### Failed approach
- Relying on existence and successful reads alone to establish the identity of a protected authority path.

### Correction
- Commit `fbd51d2399287c7559fecbaae80952cc9702d676` rejects symlinks for the learning contract, learning history, positive guard, negative guard and CI entrypoint before parsing or reading them.
- Commit `26fb1a7eb0f9d52cdc845bc94d68010caeb67d61` adds five isolated symlink negative fixtures. Each alias and its target remain inside a disposable temporary fixture; canonical source bytes are not modified.
- Commit `0fa3c2d912fc249d9000296fac5b3c8a73293b8f` raises the CI entrypoint's minimum negative-case count to 52.

### Recurrence guard
- Every run of the canonical learning validator rejects symlinked authority files, and the existing negative suite exercises all five aliases after a canonical positive control.
- The suite remains bounded and source-isolated; a symlink test must never clobber a fixed shared scratch path or mutate the checked-out authority.

### Retry condition
- Revisit if the repository deliberately changes its canonical authority storage model or a new path substitution bypass is demonstrated. Do not accept symlinked production/learning authority merely to simplify fixtures.

### Outcome
- Exact-source `Operability Contracts` run `39939568631` completed SUCCESS on commit `0fa3c2d912fc249d9000296fac5b3c8a73293b8f`.

### Success evidence
- CI job `120367387387` logs show `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (52 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.

### Why safe
- The changes affect only source-identity validation and disposable negative fixtures. No production status, environment generation, recovery objective, drill request, typed evidence, credential, traffic, readiness or promotion authority was changed.

### Reusable mechanism
- Check canonical protected file paths for symlinks before `is_file()` or `read_text()`, and prove the rejection with isolated relative symlink aliases under temporary ownership. Bind the expanded suite to an exact-source CI caller.

### Protected-authority check
- Post-change re-read confirmed unchanged learning contract, production-status and strict OPS-P0-007 snapshot blobs, `productionDecision=NO_GO`, `PREREQUISITES_BLOCKED`, and zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, generation recovery evidence, complete typed eight-domain records and final candidates. Independent review and separate human promotion remain mandatory.
- This append-only learning record is operational history only; it cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Canonical learning path identity includes parent directories

### Symptom
- Leaf-file `is_symlink()` checks did not reject an ordinary file reached through a symlinked parent directory. A bound learning authority could therefore resolve to a different repository-relative path even though the final leaf was not a symlink.

### Evidence
- Before commit `63017df39cb9e1e90cf5f3667189364d9f0b05d0`, the validator rejected symlinked contract/learning/guard/entrypoint leaves but did not compare each strict resolved path to its declared repository-relative authority.
- Isolated negative fixtures can safely rename and alias `scripts`, `contracts/operations`, or `docs/operations` entirely inside disposable temporary roots.

### Root cause or unknown
- Verified: leaf identity alone is insufficient for exact-source path binding when a parent directory can be substituted. No actual malicious parent symlink or production evidence access was observed.

### Failed approach
- Treating `not path.is_symlink()` as proof that every component of the canonical path is unchanged.

### Correction
- Commit `63017df39cb9e1e90cf5f3667189364d9f0b05d0` requires each of the five learning authorities to resolve strictly to its exact declared path under the canonical repository root and rejects missing, escaping or parent-substituted paths.
- Commit `059566dd6aef5c9e03a704494f0afda3a5faece6` adds three isolated parent-directory symlink negatives, with no shared `/tmp` target or checkout mutation.
- Commit `1c79363a47e8fdb6ce676bbac729ff4288e669b8` raises the existing operability CI entrypoint's minimum negative-case count to 55.

### Recurrence guard
- The canonical learning validator now checks both leaf symlink rejection and strict resolved repository-relative path equality. The negative suite proves scripts, contract and learning-document parent substitution is rejected after a canonical positive control.
- Exact-source CI continues to require a controlled positive PASS and at least 55 negative cases.

### Retry condition
- Revisit only if the canonical repository layout changes legitimately or a new path substitution bypass is observed. Never allow a parent alias merely because the leaf appears to be a regular file.

### Outcome
- Exact-source `Operability Contracts` run `39939809179` completed SUCCESS on commit `1c79363a47e8fdb6ce676bbac729ff4288e669b8`.

### Success evidence
- CI job `120368171103` logs show `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (55 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.

### Why safe
- Only learning source-path validation and isolated negative fixtures changed. No production status, generation, objective, reviewed request, recovery evidence, typed non-resurrection, credential, traffic, readiness or promotion authority was modified.

### Reusable mechanism
- For canonical source authorities, compare the strictly resolved path relative to the repository root with the declared relative path; do not stop at leaf `is_symlink()`. Exercise parent-directory aliases inside owned temporary fixtures.

### Protected-authority check
- Post-change re-read confirmed unchanged autonomous-learning contract, production-status and strict OPS-P0-007 snapshot blobs, `productionDecision=NO_GO`, `PREREQUISITES_BLOCKED`, and zero registered/semantically eligible generations, approved objectives, executable reviewed drill requests, generation evidence, complete typed eight-domain records and final candidates. Independent review and separate human promotion remain mandatory.
- This append-only learning record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Learning negative proof must reject for the intended invariant and prove reachable execution

### Symptom
- The 55-case autonomous-learning negative suite accepted any canonical exit-1 diagnostic prefix, even when the fixture failed for an unrelated invariant. The positive validator also accepted a direct AST call in `main()` even if an unconditional top-level `return` or `raise` made that call unreachable.
- These were verified source-level false-positive risks; no observed production incident or actual CI bypass is claimed.

### Evidence
- Prior `require_failure` delegated only to `require_canonical_rejection`, which checked exit code, prefix and absence of a traceback, not the case-specific diagnostic.
- Prior `validate-autonomous-learning-system.py` counted a direct `validate_learning_guards(failures)` statement without checking earlier top-level termination.
- Commits `d4f21cf2dbddc1cc2f70779b98b0ae3dc9844dfd`, `4e2a989cf1c30a1f40801636961da84339f0183b`, `4979869261e7397e8c111d7c911d5b3d04d20db7`, `04fc818c0fac6ea36d062a4bfc6ed44e3db46075`, `7ed26afdd1cc31ddac6b4a62b5f1bfa647c73a23`, `7abd3c77f322532fd59b8b4842dd4c4e55fd34ae`, and `0d7c4e64376c6d56b0b6d6ee5cfd2c911f8128fa` committed the changes.
- Read-only source inspection confirmed 34 explicit plus 26 generated cases (60 total), expected-diagnostic binding, a synthetic wrong-reason classifier proof, two unreachable-call mutations, a 60-case CI floor, and unchanged learning-contract/production-status blobs.

### Root cause or unknown
- Verified: generic rejection classification conflated a guard's intended failure with unrelated validation failures. AST direct-child presence alone did not prove execution before an unconditional terminator.
- Exact-source GitHub Actions outcome remains **unobserved**, not PASS: the available commit-workflow-run connector only returns pull-request-triggered runs, and the combined commit-status endpoint returned no statuses for this push.

### Failed approach
- Treating a canonical rejection prefix alone as proof of a particular negative invariant, and treating a direct AST statement after an unconditional return/raise as live reachability.

### Correction
- Require each negative to match its intended canonical diagnostic; reject unknown negative names and prove an unrelated canonical failure is not accepted.
- Add missing authority-binding and duplicate-field negative fixtures, and reject direct learning guard calls after a top-level return/raise in `main()` with two dedicated negatives.
- Raise the existing CI caller's minimum negative-suite count from 55 to 60.

### Recurrence guard
- Canonical negative execution now requires both exit-1/prefix and a case-specific diagnostic. The validator rejects calls placed after a direct unconditional terminator. The CI caller rejects suites reporting fewer than 60 cases.
- This is bounded AST/static hardening, not a general proof of all possible Python control-flow paths.

### Retry condition
- Obtain an exact-source push-workflow run ID/log or a CI connector that can list push runs before claiming the new 60-case suite passed CI. If CI reveals a specific failure, diagnose it and correct only the verified cause; do not claim the static 60-case inspection is an executed test.
- Revisit reachability if a new executable bypass is demonstrated or the canonical entrypoint structure legitimately changes.

### Outcome
- Seven code commits were created on `so`; deterministic read-only source checks confirmed all targeted guard bindings and the 60-case floor. No new CI PASS was observed during this entry.

### Why safe
- Changes are limited to existing learning validators, isolated negative fixtures, and the existing CI entrypoint. No generation, recovery objective, reviewed drill request, production evidence, credential, traffic, readiness or promotion state was created.

### Reusable mechanism
- Bind negative outcomes to the specific guard reason they are intended to exercise, add a synthetic wrong-reason classifier control, and distinguish direct AST call presence from reachable placement before unconditional termination. Keep exact-source CI outcome separate from static inspection.

### Protected-authority check
- Re-read verified `contracts/operations/autonomous-learning-system.json` at blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` and `contracts/operations/production-operability-status.json` at blob `ce67e9353d6583e4eaf792470563cad25a7396b3`, with `productionDecision=NO_GO`. OPS-P0-007's semantic generation/objective gates, typed eight-domain non-resurrection, independent review and separate human promotion were not modified.
- This append-only learning entry is operational history only; it cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Learning CI main binding must not be shadowed

### Symptom
- The canonical learning validator required one synchronous `main()` definition and a live module-level `raise SystemExit(main())`, but a later `async def main()` or `main = lambda: 0` could shadow the checked function before invocation.

### Evidence
- Source inspection found the validator's AST check counted only `ast.FunctionDef` named `main` and did not reject a top-level async redefinition or assignment.
- Commits `7e6e2d82bd30f2d47b1346daaa91143c07e087c5`, `1de403bb889d26bb1a4d4ce046a30429ab8dd6a5`, and `cf3065d3ecbff131c04b6e25ea3cb0cd4192f967` added binding checks, two isolated shadowing negatives, and a 62-case CI floor.
- Read-only inspection confirmed both guard diagnostics, both case mappings, and 36 explicit plus 26 generated negative cases. This is static evidence; a new exact-source CI PASS has not been observed.

### Root cause or unknown
- Verified source-level issue: AST presence of a valid function definition does not prove that its name still resolves to that function at the module invocation point. No real CI bypass or production event was observed.

### Failed approach
- Treating a single synchronous `main` declaration as proof that a later module-level binding cannot replace it.

### Correction
- Reject top-level `async def main` and top-level assignments to `main`, including annotated assignments. Add positive-controlled negative fixtures for an async redefinition and lambda assignment.

### Recurrence guard
- The canonical positive validator fails closed on both shadowing patterns. The existing negative suite binds each case to its exact intended diagnostic, and the CI caller requires at least 62 cases.
- The guard covers the named static rebinding patterns, not arbitrary dynamic `globals()` mutation or all possible control-flow aliasing.

### Retry condition
- Claim CI success only after inspecting an exact-source push run executing all 62 cases. Revisit the binding guard if a distinct reachable shadowing mechanism is demonstrated or the canonical module structure changes legitimately.

### Outcome
- Three code commits landed on `so`, and deterministic read-only checks confirmed the intended source bindings and the unchanged protected snapshot/status.

### Why safe
- Only learning validation, disposable learning negative fixtures and the operability CI entrypoint were changed. No recovery generation, objective, request, evidence, traffic, credential, readiness or promotion authority was written.

### Reusable mechanism
- A static module entrypoint proof must bind not only a function definition and call but also the identity of the function name at the invocation boundary. Test each shadowing mechanism in an isolated positive-controlled fixture.

### Protected-authority check
- The strict OPS-P0-007 snapshot remained blob `dbaa36b082366737dca2461d15748103b9740ef6`, production status remained `ce67e9353d6583e4eaf792470563cad25a7396b3`, and the learning contract remained `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`. Both snapshot and status retain `productionDecision=NO_GO`; all generation/objective/request/evidence/candidate counts remain zero.
- Learning history is append-only operational context, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Exact-source 62-case CI proof and CI learning-guard function binding

### Symptom
- Earlier 62-case autonomous-learning negative coverage had no observed exact-source CI run in the learning history. A separate static source review found that the operability entrypoint could invoke a later shadowed `validate_learning_guards` binding instead of the checked synchronous function while still satisfying the canonical direct-call AST check.

### Evidence
- Operability Contracts run `39945311875` succeeded on exact source `cf3065d3ecbff131c04b6e25ea3cb0cd4192f967`; job `120386426833` logged both learning guards PASS and `Autonomous learning negative validation PASS (62 fail-closed cases)`.
- The positive learning validator previously checked one `main` binding and its direct guard call, but not the module-level binding identity of `validate_learning_guards` itself. No real shadowing incident was observed.

### Root cause or unknown
- Verified static reachability gap: a call-site AST name alone does not prove that the callee name still refers to the checked synchronous implementation. The earlier CI-visibility gap was resolved by reading the branch-scoped Actions runs endpoint and exact-source job logs.

### Failed approach
- Assuming a single direct call to `validate_learning_guards(failures)` guarantees the invoked function has not been replaced; treating a PR-filtered workflow-run lookup as exhaustive evidence for push-triggered CI.

### Correction
- Commit `f7face4d3594e35668d13ff445c2516aa7484cb8` requires one synchronous module-level `validate_learning_guards` definition and rejects async redefinitions and top-level assignments of the same name.
- Commit `48a56740495044a55b898c7239e41d28ec7f351f` adds two positive-controlled, case-specific-diagnostic negative fixtures for async and assignment shadowing.
- Commit `d94464848dabe173d5440606fc8e75af7ee070d4` raises the existing operability entrypoint's fail-closed negative floor from 62 to 64.

### Recurrence guard
- The canonical positive validator rejects the two shadowing patterns; the isolated negative suite exercises both and binds each to its own diagnostic. The CI caller refuses a suite reporting fewer than 64 cases. This is bounded static binding coverage, not a proof against arbitrary dynamic Python namespace mutation.

### Retry condition
- Revisit only if a distinct executable binding bypass is demonstrated or the canonical entrypoint structure legitimately changes. Continue using exact-source branch-scoped Actions runs and job logs to substantiate CI outcomes, not PR-only run listings.

### Outcome
- Three code commits landed on `so`, and exact-source Operability Contracts run `39952314681` completed SUCCESS on `d94464848dabe173d5440606fc8e75af7ee070d4`.

### Success evidence
- Job `120409512376` logged `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (64 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.
- Compare `4b730815ffb9cf71d3638df8ec3b73076fd10861...d94464848dabe173d5440606fc8e75af7ee070d4` changed only the two learning validator scripts and existing operability entrypoint.

### Why safe
- Only fail-closed learning CI checks and disposable negative fixtures changed. No production generation, objective, drill request, evidence, credential, traffic, readiness, or promotion authority was modified. CI PASS is guard execution evidence only.

### Reusable mechanism
- Validate both caller reachability and callee binding identity at the module invocation boundary. Exercise every newly rejected shadowing class in isolated positive-controlled fixtures, require the intended diagnostic, raise the existing CI case floor, and verify exact-source job logs.

### Protected-authority check
- Post-change reads confirmed learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` and production status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` unchanged, with `productionDecision=NO_GO`. OPS-P0-007 semantic generation/objective gates, typed eight-domain non-resurrection, independent review, and separate human promotion remain mandatory.
- This append-only learning record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion gates.

## 2026-10-23 — Destructuring and import aliasing must not shadow the CI learning guard

### Symptom
- After direct assignment and async-definition shadowing were guarded, a tuple-unpacking assignment or `from ... import ... as validate_learning_guards` could still replace the function invoked by `main()` without being rejected by the AST binding check.

### Evidence
- The previous AST check inspected only direct `ast.Name` assignment targets and async function definitions, not `ast.Store` names nested in destructured targets or import aliases. A top-level `from unittest.mock import Mock as validate_learning_guards` is a concrete syntactically valid bypass candidate; no actual production or malicious CI incident was observed.

### Root cause or unknown
- Verified static binding-coverage gap: Python binds names through nested assignment targets and import aliases in addition to direct assignments and function definitions.

### Failed approach
- Treating a direct `ast.Name` assignment check as comprehensive protection of a module-level callable binding.

### Correction
- Commit `3557d57a90d70bc39466e5baad77520fc2bbb8b7` checks `ast.Store` bindings in all assignment targets and rejects imports that bind `validate_learning_guards`.
- Commit `b79547caf4b324013a5aafacaf90ad32d527bd51` adds isolated positive-controlled negative cases for tuple destructuring and import aliasing, each requiring its intended canonical diagnostic.
- Commit `34e023a7c13bb4359a76c299dff3f5050637b78b` raises the existing operability CI floor to 66 negative cases.

### Recurrence guard
- The canonical learning validator rejects both rebinding classes before accepting the live main guard call. The negative suite exercises both mutations in temporary fixtures and the CI caller rejects fewer than 66 reported cases.

### Retry condition
- Revisit when a new reachable binding mechanism is demonstrated or the entrypoint intentionally changes its callable binding architecture; do not assume this bounded AST check covers arbitrary dynamic namespace mutation.

### Outcome
- Three code commits landed on `so`. Exact-source Operability Contracts run `39952790960` completed SUCCESS on `34e023a7c13bb4359a76c299dff3f5050637b78b`.

### Success evidence
- CI job `120411128017` logged `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (66 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.
- Git compare from `e38d8b4d7b759c639c4e726ff51690b077a19c7c` to `34e023a7c13bb4359a76c299dff3f5050637b78b` changed only the two existing learning validator scripts and operability entrypoint.

### Why safe
- All new rejection proofs mutate only disposable CI learning fixtures. No production-equivalent generations, objectives, reviewed drill requests, recovery evidence, credentials, traffic, readiness or promotion state was fabricated or modified.

### Reusable mechanism
- For static source-binding checks, inspect every `ast.Store` target within assignments and account for import aliases; a direct-name check is not sufficient. Keep positive-controlled mutation proof and exact-source CI logs separate from production evidence.

### Protected-authority check
- The learning contract remained blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status remained blob `ce67e9353d6583e4eaf792470563cad25a7396b3` with `productionDecision=NO_GO`, and the OPS-P0-007 snapshot remained blob `dbaa36b082366737dca2461d15748103b9740ef6` with zero registered/semantically eligible generations, approved objectives, executable requests, recovery evidence, complete typed eight-domain records, and final candidates. Independent review and separate human promotion remain mandatory.
- Learning history is append-only execution guidance and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Negative rejection proof must be a single intended diagnostic

### Symptom
- The learning negative classifier used substring membership for an expected diagnostic. A canonical exit-1 result containing an unrelated first error and the expected text on a later line could be misclassified as the intended negative rejection.

### Evidence
- The prior `require_expected_rejection` checked `expected in result.stderr`, without constraining the diagnostic to a single line. Two synthetic multi-error results can satisfy that old condition; this is a source-level false-positive risk, not an observed production failure.

### Root cause or unknown
- Verified: substring membership conflated the location of a diagnostic with its mere presence and did not exclude additional errors.

### Failed approach
- Accepting any stderr that starts with the generic canonical prefix and contains the expected diagnostic anywhere, regardless of additional failures.

### Correction
- Commit `b93a45d387d700da3812bf20c69becca0f6dad68` requires one canonical diagnostic line beginning with the case-specific expected message and adds two synthetic classifier controls rejecting an expected second-line diagnostic and a trailing unrelated error.
- The same commit adds a positive-controlled negative fixture for replacing the only synchronous learning guard with an async-only definition.
- Commit `e23867f18cb74a42cc532fa70de46573af1c505a` raises the existing operability CI minimum to 67 fail-closed cases.

### Recurrence guard
- The negative harness now rejects multiline and wrong-prefix diagnostics, tests its classifier with synthetic unrelated errors, and requires the async-only guard mutation to fail for the specific missing-synchronous-guard reason. The existing CI caller refuses fewer than 67 cases.

### Retry condition
- Revisit if canonical validator diagnostic formatting intentionally changes or a new ambiguous same-line diagnostic bypass is demonstrated. Do not loosen classification merely to make a failing negative fixture appear green.

### Outcome
- Two code commits landed on `so`; exact-source Operability Contracts run `39953028673` completed SUCCESS on `e23867f18cb74a42cc532fa70de46573af1c505a`.

### Success evidence
- CI job `120411933218` logged `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (67 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.
- Compare `4eb5db35f655d9cc35957fe566fe29b00798331e...e23867f18cb74a42cc532fa70de46573af1c505a` changed only the canonical learning negative suite and existing operability CI entrypoint.

### Why safe
- The new classifier controls are synthetic subprocess results and the async-only negative mutates an isolated fixture; no canonical production evidence, recovery generation, objective, drill, credential, traffic, readiness or promotion authority changed.

### Reusable mechanism
- For negative proof, bind both the specific intended diagnostic and its single-line position, and self-test rejection of extra/unrelated failures. Keep executed exact-source CI evidence distinct from production readiness.

### Protected-authority check
- The autonomous-learning contract remained blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status remained blob `ce67e9353d6583e4eaf792470563cad25a7396b3` with `productionDecision=NO_GO`, and the strict OPS-P0-007 snapshot remained blob `dbaa36b082366737dca2461d15748103b9740ef6` with zero registered/semantically eligible generations, approved objectives, executable requests, generation recovery evidence, complete typed eight-domain records and final candidates. Independent review and separate human promotion remain mandatory.
- This append-only learning entry cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Negative fixture mutations require observable state change

### Symptom
- The autonomous-learning negative harness previously seeded a temporary canonical fixture, invoked a mutation callback, and then tested for rejection without checking whether the mutation actually changed any authority file. A no-op mutation could produce misleading negative proof if a separate fixture fault caused the rejection.

### Evidence
- Before commit `aaba5672097836befe99d1ee32518f5be4c0e8a8`, `require_failure` had no before/after fixture-state comparison. The new self-test explicitly attempts a no-op callback and requires rejection before the canonical validator runs. This is a verified harness-design gap, not evidence of an actual malicious mutation or production failure.

### Root cause or unknown
- Verified: negative execution lacked an explicit mutation-reachability assertion; a canonical rejection alone cannot prove that the intended test input was changed.

### Failed approach
- Treating invocation of a mutation callback as sufficient evidence that it modified the isolated authority fixture.

### Correction
- Commit `aaba5672097836befe99d1ee32518f5be4c0e8a8` fingerprints fixture file bytes, file/directory modes, symlink targets and path components before and after each mutation, rejecting unchanged fixtures before running the canonical validator.
- The same commit adds a no-op mutation classifier self-test plus two positive-controlled contract parser negatives (invalid JSON and non-object root).
- Commit `fa14ba03dd09e4ac3dc64d7e058613787c1dcf54` raises the existing operability CI minimum to 69 negative cases.

### Recurrence guard
- Every learning negative now requires an observed state difference in the disposable fixture. The self-test proves no-op rejection, and the 69-case CI floor prevents silent removal of the new parser negatives. This verifies mutation occurred, while case-specific diagnostics separately verify that the intended invariant rejected it.

### Retry condition
- Revisit if a new fixture type or mutation mechanism is introduced that the fingerprint does not cover, or if the canonical authority path layout changes. Do not treat a no-op mutation as valid negative proof merely because the validator exits nonzero.

### Outcome
- Two code commits landed on `so`; exact-source Operability Contracts run `39953347781` completed SUCCESS on `fa14ba03dd09e4ac3dc64d7e058613787c1dcf54`.

### Success evidence
- CI job `120413000463` logged `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (69 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.
- Compare `3ed1a543fbe24b572086638c2f780f5f849732a4...fa14ba03dd09e4ac3dc64d7e058613787c1dcf54` changed only the existing learning negative suite and operability CI entrypoint.

### Why safe
- All fingerprinting, malformed-contract tests and no-op controls run in disposable fixtures; canonical production status, OPS-P0-007 admission snapshot, recovery evidence and promotion authority were not modified.

### Reusable mechanism
- Negative proof should require both a before/after mutation fingerprint and an intended canonical rejection. Include file modes and symlinked parent components in the fingerprint when the suite tests path identity, and self-test the no-op case before accepting negative counts.

### Protected-authority check
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` (`productionDecision=NO_GO`), and strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remained unchanged. The snapshot retains zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records, and final candidates. Independent review and separate human promotion remain mandatory.
- Learning history is append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Main entrypoint binding also needs import and tuple guards

### Symptom
- The learning validator guarded `main()` against direct assignments and async definitions, but top-level tuple destructuring or an import alias could still replace the checked synchronous `main` binding before the `__main__` invocation.

### Evidence
- The prior `main` assignment check matched only direct `ast.Name` targets, and did not inspect `ast.Import` or `ast.ImportFrom` aliases. The two isolated mutation fixtures demonstrate the exact syntax; no malicious CI or production incident was observed.

### Root cause or unknown
- Verified static binding-coverage gap: Python module-level names can be rebound through nested `ast.Store` targets and imports, not only direct assignments.

### Failed approach
- Assuming a direct-name assignment guard completely protects a checked `main` definition from later shadowing.

### Correction
- Commit `1ce2a878cd27efd88ad2b9f9d0e60c075a74dd93` extends the canonical learning validator to reject tuple-destructured `main` assignments and import aliases.
- Commit `caf31af8ec4ee624be508b91ba49709a7fc73654` adds two isolated positive-controlled negative cases with case-specific diagnostics.
- Commit `f9e622623624f455ed1c14f05cb860baea5e5438` raises the existing operability CI negative floor to 71.

### Recurrence guard
- The canonical positive validator rejects both rebinding classes and the negative suite proves each after a valid fixture positive control. The existing CI caller requires at least 71 fail-closed cases.

### Retry condition
- Revisit if a new reachable `main` shadowing mechanism is demonstrated or the canonical entrypoint changes legitimately. This bounded AST guard does not claim to prevent every possible dynamic Python namespace mutation.

### Outcome
- Three code commits landed on `so`; exact-source Operability Contracts run `39953640560` completed SUCCESS on `f9e622623624f455ed1c14f05cb860baea5e5438`.

### Success evidence
- CI job `120413982571` logged `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (71 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.
- Compare `3ed631690b236c533185d1cf97a417369817d217...f9e622623624f455ed1c14f05cb860baea5e5438` changed only the two learning validator scripts and existing operability entrypoint.

### Why safe
- All new negative mutations use disposable learning fixtures and no production-equivalent generation, recovery objective, drill request, recovery evidence, credential, traffic, readiness or promotion authority was created or changed.

### Reusable mechanism
- Apply consistent name-binding checks to both the executable caller and its callee; inspect nested assignment targets and import aliases, then bind the new rejection to an isolated negative and exact-source CI.

### Protected-authority check
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` (`productionDecision=NO_GO`), and OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remained unchanged. The snapshot retains zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final candidates. Independent review and separate human promotion remain mandatory.
- Learning history is append-only execution guidance and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Protected learning callables must not be rebound in module control flow

### Symptom
- Direct top-level assignment and import checks did not cover module-level loop targets or imports nested under a module-level `if`. Such code could replace the checked `main` or `validate_learning_guards` binding while leaving their original definitions and AST call sites present.

### Evidence
- The previous validator inspected direct top-level `Assign`, `AnnAssign`, `Import`, `ImportFrom` and async definitions, but did not recursively inspect module control-flow statements for binding operations. The new isolated fixtures demonstrate top-level `for` targets and a nested import alias; no actual malicious CI or production incident was observed.

### Root cause or unknown
- Verified static binding gap: a module-level compound statement can rebind a name without being a direct module-body assignment/import node.

### Failed approach
- Treating only direct module-body assignment/import statements as exhaustive protection of the executable entrypoint's callable identities.

### Correction
- Commit `b867656ddacbc216f84b240d595df490315fd2b0` adds a bounded module-scope AST walker that detects stored/deleted protected names, import aliases, exception/pattern captures and nested module control-flow bindings while excluding function/class/comprehension local scopes.
- Commit `ac14ca155dd9dbcb7fb30885049cb33e315a13e7` adds three positive-controlled negative fixtures for a `main` loop target, a learning-guard loop target and a nested import alias, each bound to the intended canonical diagnostic.
- Commit `69d80eb6cabfb3e3ac9ddb3a2090c240831c1a6b` raises the existing operability CI negative floor to 74.

### Recurrence guard
- The canonical learning validator now checks protected callable names across module control-flow bindings, and the negative suite exercises three independent bypass classes in disposable fixtures. The existing CI caller rejects fewer than 74 fail-closed cases.

### Retry condition
- Revisit if a new executable module-binding mechanism escapes the bounded AST walker or the canonical entrypoint's architecture legitimately changes. Do not infer that static AST checks prevent arbitrary runtime namespace manipulation.

### Outcome
- Three code commits landed on `so`; exact-source Operability Contracts run `39953973857` completed SUCCESS on `69d80eb6cabfb3e3ac9ddb3a2090c240831c1a6b`.

### Success evidence
- CI job `120415075695` logged `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (74 fail-closed cases)`, `Memory OS entrypoint document validation PASS`, and `production decision: NO_GO`.
- Compare `5c2314b2eeb47664556b08eecdb3f77f16227acc...69d80eb6cabfb3e3ac9ddb3a2090c240831c1a6b` changed only the two existing learning validator scripts and operability CI entrypoint.

### Why safe
- The new checks are source-only fail-closed validation; the negative mutations are temporary fixtures. No production-equivalent generation, objective, reviewed request, recovery evidence, credential, traffic, readiness or promotion authority was changed.

### Reusable mechanism
- For protected Python module callables, walk module-level compound statements for name-binding operations while excluding local scopes. Require isolated positive-controlled negatives and exact-source CI proof rather than accepting AST definition/call presence alone.

### Protected-authority check
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` (`productionDecision=NO_GO`), and strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remained unchanged. The snapshot retains zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records, and final candidates. Typed non-resurrection still requires all eight domains and two independent bundle/digest-bound reviews; separate human promotion remains mandatory.
- Learning history is append-only execution guidance and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Full admission validator proof must come from reachable workflow run blocks

### Symptom
- Static snapshot workflow admission-chain proof could count a line beginning with `python scripts/validate-...` even when it appeared in non-executable YAML data, a disabled step, a shell heredoc, or after an unconditional shell exit. This was a source-level false-positive risk, not an observed production or recovery failure.

### Evidence
- Before commit `07b69ce732e5b70e7b4f79b3d178a0fa026aa65b`, `require_full_admission_chain` searched the entire workflow text with a line-anchored regex and had only a comment-only control. The new positive-controlled fixtures explicitly cover a YAML `env` literal, `if: false` step, heredoc body and post-`exit 0` command; each is rejected for the intended missing executable validator diagnostic.

### Root cause or unknown
- Verified: source-text matching did not bind the mandatory recovery-objective, reviewed-drill-request, generation-evidence and typed non-resurrection validators to enabled GitHub Actions `run: |` steps or executable shell regions.

### Failed approach
- Treating any syntactically command-shaped line in the YAML source as proof that the full admission validator executes.

### Correction
- Commit `07b69ce732e5b70e7b4f79b3d178a0fa026aa65b` limits evidence to enabled `run: |` step bodies, excludes heredoc data and stops counting commands after a direct unconditional shell exit. The existing canonical workflow permission negative suite now includes one positive control and five rejection fixtures (including the original comment-only case).

### Recurrence guard
- The pre-existing CI-bound snapshot workflow permission negative suite executes the reachability controls on each relevant change. Exact-source `OPS P0 007 Snapshot Permission Boundary` run `39960522958` and `OPS P0 007 Admission Snapshot Readonly` run `39960522755` both completed SUCCESS on commit `07b69ce732e5b70e7b4f79b3d178a0fa026aa65b`; the readonly job logged canonical snapshot/negative/authority validation PASS and `production decision: NO_GO`.

### Retry condition
- Extend the bounded parser only when a concrete new workflow syntax or unreachable shell construct is demonstrated to bypass it, or if canonical workflow run-step structure legitimately changes. Do not treat static line presence or this learning entry as production, recovery or promotion evidence.

### Outcome
- One fail-closed executable guard commit landed on `so`, and two exact-source snapshot workflows succeeded. No production-equivalent environment generation, approved objective, executable reviewed request, recovery evidence, traffic, credential, readiness or promotion state was created.

### Success evidence
- Workflow run `39960522958`, job `120437071311`: `Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS`, full objective/request/evidence/eight-domain checks reported required, and `production decision: NO_GO`.
- Workflow run `39960522755`, job `120437070149`: strict admission snapshot, negative suite, validator authority, generator execution authority and workflow permission negative all logged PASS at the same source SHA.

### Why safe
- Only the existing negative guard was changed; all new fixtures are in-memory strings. The guard is read-only and fail-closed, and both CI jobs verified source binding and authority immutability.

### Reusable mechanism
- Bind workflow execution evidence to enabled run-step bodies, exclude inert YAML and shell heredoc text, require positive-controlled negative fixtures, and confirm exact-source CI execution rather than relying on textual command presence.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/semantically eligible generations, approved objectives, executable requests, generation recovery evidence, complete typed eight-domain records and final candidates; autonomous-learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate non-automatic human promotion remain mandatory.
- This append-only learning history is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Snapshot corruption negatives must identify their intended canonical rejection

### Symptom
- The strict OPS-P0-007 snapshot corruption negative harness accepted any canonical-prefixed exit-1 diagnostic for every validator mutation, even if an unrelated invariant caused the failure. This was a verified test-classification weakness, not an observed production failure.

### Evidence
- Before commit `a95f3149b75232c207cd1237345a60bdb8c4d1e7`, `run_validator(False, label)` checked only exit code 1, the generic `OPS-P0-007 ADMISSION SNAPSHOT FAILED:` substring and absence of a traceback. It did not distinguish the intended field-set, count, downstream projection, next-action or production-decision rejection from unrelated errors.

### Root cause or unknown
- Verified: the negative harness conflated any controlled canonical failure with case-specific proof.

### Failed approach
- Using a generic fail-closed prefix as sufficient evidence that a particular corruption mutation was detected for its intended reason.

### Correction
- Commit `a95f3149b75232c207cd1237345a60bdb8c4d1e7` binds six high-value snapshot/status mutations to an exact single-line canonical diagnostic. The classifier's synthetic positive control and three wrong/multiline controls reject unrelated errors; other existing negative cases remain governed by their prior checks pending separately verified case-specific mappings.

### Recurrence guard
- The existing `scripts/validate-memory-os-ops-p0-007-admission-snapshot-negative.py` suite now fails if one of the six mapped cases is rejected for the wrong reason. Exact-source `OPS P0 007 Admission Snapshot Readonly` run `39960839717`, job `120438124050`, completed SUCCESS and logged strict snapshot negative PASS, validator authority negative PASS, workflow permission negative PASS and `production decision: NO_GO`.

### Retry condition
- Expand exact mappings only after verifying the intended diagnostics for the remaining registry/blocker mutations; revisit if canonical validator messages legitimately change. Never loosen the classifier merely to convert an unrelated failure into a passing negative.

### Outcome
- A second executable guard commit landed on `so`, with exact-source readonly CI SUCCESS. No production-equivalent generations, objectives, executable reviewed requests, generation recovery evidence, typed non-resurrection records, credentials, traffic, readiness or promotion were created.

### Success evidence
- `a95f3149b75232c207cd1237345a60bdb8c4d1e7` changed only the existing snapshot negative suite. CI `39960839717` exercised the new classifier controls and all existing strict snapshot negative cases successfully at that SHA.

### Why safe
- The change strengthens only negative classification, uses synthetic diagnostics for classifier self-tests, and retains the existing canonical validator and disposable/restored mutation handling. No authority was weakened.

### Reusable mechanism
- For negative admission proof, pair material mutation and a clean positive control with an exact expected diagnostic; reject multiline or unrelated canonical failures and verify exact-source CI.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` still has zero registered/semantically eligible generations, approved objectives, executable requests, recovery evidence, complete typed eight-domain records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human production promotion remain mandatory.
- Learning is append-only operational guidance, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Nested canonical rejection is not an arbitrary multiline failure

### Symptom
- New generator corruption diagnostic guard initially rejected a legitimate fail-closed nested validator diagnostic, causing exact-source snapshot readonly CI to fail.

### Evidence
- Commit `d7726f870bea44cfd10a002097489b426026f230`, `OPS P0 007 Admission Snapshot Readonly` run `39961118870`, job `120439058803`: `generator canonical blocker replacement: generator rejection did not use one intended authority diagnostic`. Observed stderr contained the canonical typed admission prefix followed by `LOCAL APPLE REPLAY RESTORE VALIDATION FAILED: OPS-P0-007 missingEvidence must equal the ordered canonical six production blockers`.

### Root cause or unknown
- Verified: the new classifier assumed every valid generator rejection was one line. The canonical typed non-resurrection admission validator legitimately preserves a two-line nested local Apple restore diagnostic with an exact cause.

### Failed approach
- Requiring `len(stderr.splitlines()) == 1` for every generator corruption negative, without first inspecting the composed validator's real output contract.

### Correction
- Commit `0337f4f6d3e85435583dca2f9688768d2775619c` accepts either a one-line expected authority prefix or an exact two-line typed/local-restore diagnostic with the second line bound to the specific blocker/decision mutation. Unrelated, wrong-prefix, wrong-cause and extra-line outputs remain rejected by synthetic classifier controls.

### Recurrence guard
- The existing snapshot negative suite self-tests both accepted diagnostic shapes and rejects unrelated/multiline impostors. Exact-source `OPS P0 007 Admission Snapshot Readonly` run `39961336278` (job `120439791485`) and `OPS P0 007 Admission Snapshot` run `39961336289` (job `120439792152`) completed SUCCESS and logged strict snapshot negative PASS with `production decision: NO_GO`.

### Retry condition
- Revisit only if the canonical typed/local-restore validator changes its diagnostic shape or a new nested diagnostic is observed. Do not retry the rejected one-line-only classifier unchanged; preserve strict cause-binding rather than accepting arbitrary stderr.

### Outcome
- The fail-closed classifier now distinguishes intended nested authority rejection from unrelated failure without weakening production/recovery gates. One failing code commit was corrected by a second code commit, both retained in history.

### Success evidence
- Exact-source runs `39961336278` and `39961336289` succeeded at `0337f4f6d3e85435583dca2f9688768d2775619c`. The independent `Backup Restore Admission Chain Negative` run `39961336244` still failed at the pre-existing Source-binding Clean Worktree blocker; that known scoped blocker was not changed or retried manually.

### Why safe
- Only negative diagnostic classification and its synthetic controls changed. The canonical typed validator, eight-domain requirements, independent review, source authority, registries and human promotion were not weakened. Publisher diagnostic-file churn was not treated as readiness or production evidence.

### Reusable mechanism
- Before enforcing exact stderr shape across composed validators, inspect observed nested failure evidence. Whitelist only specific nested causes and test rejection of unrelated prefixes, wrong second lines and extra diagnostics.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/semantically eligible generations, approved objectives, executable requests, generation recovery evidence, complete typed eight-domain records and final candidates; autonomous-learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent reviews and separate human promotion remain mandatory.
- Learning is append-only execution guidance, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Publisher revalidation must be invoked, not merely defined

### Symptom
- The strict snapshot publisher permission negative accepted the presence of `revalidate_latest_snapshot` as a source substring. A retained shell function definition with its retry/finalization invocations removed could satisfy that check while weakening publication-time revalidation. This is a source-level guard gap, not an observed production incident.

### Evidence
- Prior to `32a95540242dec24edad9aa1252adb9bada41837`, the workflow guard used `"revalidate_latest_snapshot" in publish`. The canonical publisher contains one definition and three distinct shell call sites; the new negative fixtures replace one real call with a comment or echo while retaining the definition.

### Root cause or unknown
- Verified: string presence does not establish invocation reachability; a definition, comment or echo can preserve the marker without running the revalidation function.

### Failed approach
- Using an unscoped workflow-text substring as proof of bounded source revalidation before publication.

### Correction
- Commit `32a95540242dec24edad9aa1252adb9bada41837` binds the function definition and at least three existing call sites to enabled workflow `run: |` shell bodies. Positive control uses the canonical publisher, and two mutated negative fixtures prove comment-only and echo-only calls cannot satisfy the guard.

### Recurrence guard
- The pre-existing CI-bound workflow permission negative now enforces the call-site check. Exact-source `OPS P0 007 Snapshot Permission Boundary` run `39961657212` (job `120440891848`) and `OPS P0 007 Admission Snapshot Readonly` run `39961657127` (job `120440892139`) completed SUCCESS, logging workflow permission negative PASS and `production decision: NO_GO`.

### Retry condition
- Revisit if the canonical publisher legitimately changes its bounded revalidation architecture or a demonstrated unreachable shell branch evades this bounded static check. Do not restore substring-only proof.

### Outcome
- A fourth executable guard commit landed on `so` with two exact-source CI successes. No environment generation, approved objective, executable reviewed drill request, recovery evidence, credentials, traffic, readiness or promotion was created.

### Success evidence
- Both exact-source workflows completed successfully at `32a95540242dec24edad9aa1252adb9bada41837`. The readonly workflow also logged strict admission snapshot negative PASS and unchanged `NO_GO`.

### Why safe
- Only an existing read-only workflow negative validator changed; tests mutate in-memory workflow strings. The canonical publisher, production status, snapshot, registries, typed eight-domain gate, independent reviews and human promotion were not modified.

### Reusable mechanism
- For shell workflow authority, distinguish function definitions from executable invocation sites and prove that replacing a real call with inert text fails a positive-controlled negative suite.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/semantically eligible generations, approved objectives, executable requests, recovery evidence, complete typed eight-domain records and final candidates; autonomous-learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate non-automatic human promotion remain mandatory.
- Learning is append-only execution guidance and never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Objective registry corruption negatives must bind the exact rejection cause

### Outcome
- Commit `2fc45f6c67e47e084956cba824af388f88881195` binds five existing objective-registry corruption cases to the precise canonical snapshot validator rejection, rather than accepting an unrelated fail-closed error.
- Exact-source OPS-P0-007 Admission Snapshot Readonly run `39968202155` and publisher run `39968202122` completed SUCCESS at that SHA.

### Evidence
- Readonly job `120463542490` logged `Memory OS OPS-P0-007 strict admission snapshot negative validation PASS`, 22 controlled validator corruption cases rejected, three controlled generator corruption cases rejected, and `production decision: NO_GO`.
- Publisher job `120463541996` logged the same negative PASS and source SHA `2fc45f6c67e47e084956cba824af388f88881195`.
- Canonical objective writer `validate_registry_for_append` supplies the exact five failures for boolean aggregate count, append-only, schema, production evidence, and production readiness; the snapshot validator wraps them as `recovery objective canonical registry authority invalid: ...`.

### Why safe
- The change is limited to the existing fail-closed negative diagnostic map, does not alter any positive validator or production authority, and exercises existing byte/mode-restored registry mutations. No new objective, generation, drill request, recovery evidence, traffic, credential, readiness or promotion was created.

### Reusable mechanism
- For registry corruption negatives, bind each mutation label to the precise writer-side failure wrapped by the canonical snapshot validator. Keep the existing positive control, exact single-line diagnostic classifier, material mutation assertion, byte/mode restoration and exact-source CI checks.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human production promotion remain mandatory.
- Learning history is append-only operational guidance, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Reviewed drill-request corruption negatives require exact writer diagnostics

### Outcome
- Commit `9767fb9484b5ff99accf452b9c7dd7a8cacf3414` extends the existing strict snapshot negative classifier with three exact reviewed drill-request registry rejection causes (boolean count, append-only, and productionEvidence).

### Evidence
- The canonical request writer validates `registeredRequestCount` as a non-boolean integer, `appendOnly is True`, and `productionEvidence is False`; the snapshot validator wraps the writer's failure under `restore drill request canonical registry authority invalid: ...`.
- Exact-source Readonly run `39968494722` (job `120464578224`) and Snapshot publisher run `39968494732` (job `120464577887`) both completed SUCCESS on that code SHA. Both logged strict snapshot negative PASS, 22 controlled validator corruptions rejected, and `production decision: NO_GO`.

### Why safe
- Only the pre-existing negative diagnostic map changed. Registry mutations remain positive-controlled, material, and restored byte-for-byte/mode-for-mode. No reviewed request, recovery objective, generation, recovery evidence, credential, traffic, readiness or promotion was created.

### Reusable mechanism
- Derive an exact case-specific rejection from the canonical writer's validation order and the composing snapshot validator's wrapper, then require successful exact-source CI of the existing negative suite. Do not treat a generic canonical failure as proof of the intended mutation.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` still records zero registered/eligible generations, objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human promotion remain mandatory.
- Append-only learning history is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Generation and typed registry corruption negatives need cause-specific proof

### Outcome
- Commit `0d73d57d50b7bca93f1f68e8bdb2ad1ef36dac6d` binds six existing generation-recovery-evidence and typed non-resurrection registry negative mutations to their exact canonical rejection diagnostics, preserving the eight-domain independent-review gate.

### Evidence
- Canonical generation writer validates the non-boolean `registeredEvidenceCount`, append-only flag and production boundary. Canonical typed writer validates `completeRecordCount`, append-only flag and production boundary; the snapshot validator wraps each writer failure with the corresponding canonical registry label.
- Exact-source OPS-P0-007 Admission Snapshot Readonly run `39968796678` (job `120465635539`) and Snapshot publisher run `39968796659` (job `120465635636`) completed SUCCESS. Both logged strict snapshot negative PASS, 22 controlled validator corruption cases rejected, and `production decision: NO_GO`.

### Why safe
- Only the existing negative classifier's expected diagnostic map changed. Existing registry mutation, positive-control and byte/mode restoration mechanisms were retained. No production-equivalent generation, recovery objective, reviewed request, generation evidence, typed record, credential, traffic, readiness or promotion was created.

### Reusable mechanism
- Map generation and typed registry negatives to writer-side fail-closed diagnostics wrapped by the canonical validator; require exact-source CI and keep typed eight-domain coverage plus independent reviews as separate candidate prerequisites.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable reviewed requests, recovery evidence, complete typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human promotion remain mandatory.
- Append-only learning is operational guidance only, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Canonical six-blocker corruption must reject for the exact list invariant

### Outcome
- Commit `3e81adab33d71fdd78c4399508a6b6b3755f5a67` binds both canonical OPS-P0-007 blocker replacement and blocker ordering negative mutations to the exact six-blocker list rejection, not an arbitrary snapshot validation failure.

### Evidence
- `memory_os_backup_restore_blockers.require_canonical_gaps` requires equality with the ordered immutable six production blockers and raises `OPS-P0-007 missingEvidence must equal the ordered canonical six production blockers`; the snapshot validator propagates that `Fail` unchanged.
- Exact-source Readonly run `39969072879` (job `120466612199`) and Snapshot publisher run `39969072893` (job `120466612444`) both completed SUCCESS at the code SHA, logging strict snapshot negative PASS, 22 controlled validator corruptions rejected, and `production decision: NO_GO`.

### Why safe
- Only existing negative-case diagnostic binding changed. Canonical blocker text, ordering, production status, generation/objective/request registries, recovery evidence and promotion authorities were not modified.

### Reusable mechanism
- When a shared canonical helper directly raises a specific fail-closed cause, bind negative proof to that exact cause and verify both content replacement and ordering mutation. Preserve positive control, material mutation and byte/mode rollback, and require exact-source CI.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, objectives, executable requests, recovery evidence, typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Typed eight-domain coverage, independent review and separate human promotion remain mandatory.
- Append-only learning is operational guidance, not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Positive-control output proof and fixture newline escaping

### Symptom
- The new positive-control classifier rejected its own synthetic valid fixture and failed both strict snapshot workflows before the negative cases.

### Evidence
- Commit `9d7ad9de0a45c59c858acf4408a7314969b5af24`; Readonly run `39969357561` (job `120467591399`) and Snapshot run `39969357580` (job `120467591823`) both failed: `synthetic positive: canonical positive validator success output missing or duplicated`.
- Source inspection and a direct Python `splitlines()` check showed literal backslash-n strings, not real newlines. The publisher temporarily committed a failure diagnostic fixture at `32dda94aaafde010c610a1c28698b3e3aac4f27a`, later removed by the publisher's bounded success reconciliation at `5d46e81ba91f2ed83a6e06e43bf9816d2ef0cf48`. Neither is production evidence.

### Root cause or unknown
- Verified: JavaScript-to-Python source generation double-escaped newlines. The synthetic positive output was a single line with literal backslash-n sequences.

### Failed approach
- Adding synthetic positive-output controls without inspecting the generated Python string's actual newline semantics. This repeated a previously known fixture-escaping failure class; its recurrence guard was not applied during source generation.

### Correction
- Commit `a481e7ce810e6b4fd1df6f0ffb899b783dfc6a7c` converts ten double-escaped fixture sequences to actual Python newline escapes while retaining exactly-one-PASS and exactly-one-NO_GO output requirements.

### Recurrence guard
- The CI-bound negative suite now rejects a baseline validator that exits zero without its canonical PASS and `production decision: NO_GO` output. Its classifier has a synthetic positive and six missing, unrelated, wrong-decision, duplicate and embedded-marker controls.
- When generating Python fixture source through JavaScript, inspect serialized source and independently verify `splitlines()` before commit.

### Retry condition
- Revisit only if the canonical validator's positive output changes or a concrete new success-spoofing bypass is demonstrated. Never reuse double-escaped synthetic newlines unchanged.

### Outcome
- Corrected exact-source Readonly run `39969470365` (job `120467982921`) and Snapshot publisher run `39969470368` (job `120467982891`) both completed SUCCESS on `a481e7ce810e6b4fd1df6f0ffb899b783dfc6a7c`.

### Success evidence
- Both logs contain strict snapshot negative PASS, 22 controlled validator corruptions rejected, and `production decision: NO_GO`. The earlier CI failures remain historical failures.

### Why safe
- Only the existing negative harness was strengthened; synthetic fixtures and diagnostic files are not recovery or promotion evidence. No generation, objective, reviewed request, recovery evidence, credential, traffic, readiness or promotion was created.

### Reusable mechanism
- Require canonical positive PASS and NO_GO lines as well as zero exit; prove the classifier rejects missing or spoofed output and confirm the exact-source CI outcome.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable requests, generation recovery evidence, complete typed eight-domain records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human promotion remain mandatory.
- Append-only learning cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Snapshot symlink escape negatives must prove the exact path guard

### Outcome
- Commit `e6cfa860b8cce694d931408a455bc430c056f290` binds the existing objective-registry and objective-writer symlink escape negatives to the exact canonical snapshot validator path-drift rejection.

### Evidence
- The canonical validator's runtime authority loop checks both the recovery objectives registry and objective writer against their exact resolved repository paths, rejecting symlink substitution with a label-specific `strict snapshot validator ... authority path drift` diagnostic.
- Exact-source Readonly run `39969825472` (job `120469236039`) and Snapshot publisher run `39969825489` (job `120469236121`) completed SUCCESS at this code SHA. Both logged strict snapshot negative PASS, 22 controlled validator corruptions rejected, and `production decision: NO_GO`.

### Why safe
- Only two expected diagnostic bindings were added to the existing negative suite. Its temporary symlink targets, cleanup, byte/mode restoration and canonical generator rejection checks were retained; no production, recovery or promotion authority changed.

### Reusable mechanism
- When a negative case replaces a canonical file with a symlink, require the exact authority-path drift diagnostic, not any unrelated fail-closed exit. Preserve isolated temporary targets and cleanup plus exact-source CI proof.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Typed eight-domain coverage, independent review and separate human promotion remain mandatory.
- Append-only learning never counts as production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — Rejected snapshot generator attempts must preserve file mode as well as bytes

### Outcome
- Commit `7a577eb45f4e05ef15cd63d844a0b6db27b421ab` strengthens the existing generator-rejection negative helper to assert both canonical snapshot bytes and file mode are unchanged.

### Evidence
- Previously `run_generator_rejects` checked snapshot bytes only after fail-closed generator exit; a mode-only mutation could evade that local assertion.
- The new pure-state classifier has an unchanged positive control and separate synthetic bytes-change and mode-change rejections. Exact-source Readonly run `39970206346` (job `120470559817`) and Snapshot publisher run `39970206253` (job `120470559346`) completed SUCCESS, logging strict snapshot negative PASS, 22 validator corruptions rejected, and `production decision: NO_GO`.

### Why safe
- The guard compares a tuple of observed bytes and file mode after a rejected generator attempt. Synthetic classifier controls are in-memory; no new production or recovery authority was written. Existing canonical registry restoration and atomic replacement tests remain intact.

### Reusable mechanism
- A rejected publication must preserve not only content but permission metadata. Use a pure before/after state classifier with a synthetic mode-only negative to prevent false success, then exercise it through the existing CI-bound generator rejection cases.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Eight-domain coverage, independent review and separate human promotion remain mandatory.
- Append-only learning never counts as production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-23 — In-process snapshot authority substitutions must preserve mode and bytes

### Outcome
- Commit `045b78a1990faa6b8c2251be8725663e2c48d4f9` reuses the previously CI-proven before/after snapshot-state guard for post-write validator substitution, full admission helper substitution and generator authority-path substitutions.

### Evidence
- These three in-process rejection paths previously asserted snapshot byte preservation but not file-mode preservation.
- Exact-source Readonly run `39970502410` (job `120471592143`) and Snapshot publisher run `39970502471` (job `120471591521`) completed SUCCESS at the code SHA, logging strict snapshot negative PASS, 22 validator corruption cases rejected, and `production decision: NO_GO`.

### Why safe
- The change reuses a tested pure bytes/mode comparator and does not alter any generator, positive validator, production status, registry, recovery evidence or promotion authority. Synthetic substitutions remain in-process and restore their original function references.

### Reusable mechanism
- Apply a single independently tested bytes/mode state invariant across every rejection path, including in-process authority substitution—not only subprocess generator rejection. Avoid duplicating weaker byte-only assertions.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable reviewed requests, recovery evidence, complete typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Eight-domain coverage, independent review and separate human promotion remain mandatory.
- Append-only learning never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Symlink escape resolution fails before the later path-drift branch

### Symptom
- A new exact generator symlink diagnostic classifier rejected the actual canonical generator failure and caused both strict snapshot workflows to fail.

### Evidence
- Commit `2db54036d29c08ad73a7bb7dd5f1be11c4268eb5`; Readonly run `39970804689` (job `120472644031`) and Snapshot run `39970804685` (job `120472643803`) failed on `generator objective source symlink escape`. Actual stderr was `strict snapshot authority missing or escapes repository: recovery objective registry`, not the expected `strict snapshot authority drift: recovery objective registry`.
- A failure diagnostic fixture was temporarily committed at `529e5438d0e1ad61e32869b9fc36e273a8df2a51` and later removed by bounded success reconciliation at `3154c44b669254c6c139fadab25ebdf25ed3c025`; neither is production evidence.

### Root cause or unknown
- Verified: the symlink target resolves outside the repository. `path.resolve(strict=True).relative_to(ROOT.resolve())` raises `ValueError` inside the generator's `require_exact_repo_file` try block, which emits the earlier `missing or escapes repository` diagnostic. The later `authority drift` branch is not reached.

### Failed approach
- Predicting the exact failure from the final symlink predicate without checking which earlier path-resolution exception branch runs. This was an incorrect static diagnostic assumption.

### Correction
- Commit `8682b50fc4477786d002c891f061ab079fdf5b0b` maps both objective registry and objective writer symlink escapes to their actual canonical `missing or escapes repository` diagnostics.

### Recurrence guard
- The existing CI-bound generator negative classifier now requires exact single-line diagnostics for both symlink labels, with synthetic valid controls and unrelated-suffix, duplicate-line and wrong-prefix rejections. For exact error mapping, inspect exception order and actual CI stderr before generalizing from a later guard branch.

### Retry condition
- Revisit only if the generator's canonical path-resolution order or the isolated symlink target location changes, or a demonstrated new bypass appears. Do not retry the incorrect `authority drift` mapping unchanged.

### Outcome
- Corrected exact-source Readonly run `39970967714` (job `120473210879`) and Snapshot publisher run `39970967662` (job `120473211463`) completed SUCCESS at `8682b50fc4477786d002c891f061ab079fdf5b0b`.

### Success evidence
- Both logs contain strict snapshot negative PASS, 22 controlled validator corruption cases rejected, and `production decision: NO_GO`. The earlier failures remain failures in history.

### Why safe
- Only expected diagnostics in the existing negative harness changed. Symlink fixtures are temporary and restored, with no production or recovery authority weakened. Diagnostic fixture commits cannot satisfy readiness.

### Reusable mechanism
- Trace the actual first fail-closed branch for symlink resolution, then bind its exact observed diagnostic with positive-controlled negative fixtures and exact-source CI.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; strict snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Eight-domain coverage, independent review and separate human promotion remain mandatory.
- Append-only learning cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Nested generator negatives require their exact two-line cause

### Outcome
- Commit `0681b8b5168c51ff92a44480ea01d14460c062d1` requires all three nested generator corruption cases to emit the exact two-line local Apple replay restore diagnostic, rather than accepting any single-line typed-admission failure with a matching generic prefix.

### Evidence
- Before the change, `require_expected_generator_diagnostic` accepted `valid_single` for nested case labels, so a generic typed-admission error could satisfy the negative without reaching the intended blocker/decision mutation. The new classifier independently rejects a single-line prefix, a suffixed first line, a wrong second line and duplicate lines for each nested case.
- Exact-source Readonly run `39972153246` (job `120477348224`) and Snapshot publisher run `39972153486` (job `120477349705`) both completed SUCCESS on the code SHA. Both logged strict snapshot negative PASS, 22 controlled validator corruptions rejected, 3 generator corruptions rejected, and `production decision: NO_GO`.

### Why safe
- Only the existing CI-bound negative diagnostic classifier changed. No canonical generator, registry, recovery objective, production status, typed eight-domain evidence or promotion authority was modified.

### Reusable mechanism
- A negative case that is expected to fail through a nested validator must require its complete cause-specific multiline diagnostic. Do not permit a generic single-line prefix fallback; add positive and unrelated/partial/duplicate negative controls for every bound case.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered and semantically eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human promotion remain mandatory.
- Learning is append-only operational guidance and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Snapshot positive control must reject hidden stderr failures

### Outcome
- Commit `69bf5d6aa40eaab1477ae1df69023725d0cd30f0` strengthens the existing strict snapshot negative suite's positive control: zero exit and the two expected stdout markers are insufficient when the canonical validator also emits a failure on stderr.

### Evidence
- Before this change, `run_validator(expect_success=True)` passed only stdout to `require_positive_validator_output`; stderr was not inspected after a zero exit. The new classifier rejects nonempty stderr and includes an in-process synthetic positive-stdout/failed-stderr control.
- Exact-source Readonly run `39972500337` (job `120478545574`) and Snapshot publisher run `39972500121` (job `120478545519`) both completed SUCCESS. Each logged strict snapshot negative PASS, 22 controlled validator corruptions rejected, 3 generator corruptions rejected, and `production decision: NO_GO`.

### Why safe
- The change is confined to the CI-bound negative harness's clean positive-control classification. It does not relax the validator, create external evidence, or modify production, recovery, readiness or promotion authorities.

### Reusable mechanism
- A canonical positive control must require zero exit, exact success markers and no hidden error output. Include a synthetic test that combines valid stdout with a fail-closed stderr diagnostic to prove the positive classifier cannot be spoofed by mixed output.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; strict OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable requests, recovery evidence, complete typed eight-domain records and final candidates. Learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only guidance and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Interrupted atomic negative tests must restore snapshot mode

### Outcome
- Commit `8e9e7caccfabe373f235e64f5ae79a0f360eaffb` makes the strict snapshot atomic-replace negative restore the original canonical file mode through a `finally`-backed context manager, even if the injected failure or a subsequent assertion unexpectedly raises.

### Evidence
- Previously the test restored the mode only along its expected rejection/assertion branches; an unexpected exception before those branches could leave the canonical snapshot at temporary mode `0o640`. The new isolated temporary-file control deliberately raises mid-context and checks original mode and bytes were restored.
- Exact-source Readonly run `39972914029` (job `120479990351`) and Snapshot publisher run `39972914013` (job `120479990596`) both completed SUCCESS, logging strict snapshot negative PASS, 22 controlled validator corruptions rejected, 3 generator corruptions rejected and `production decision: NO_GO`.

### Why safe
- The new exception-path probe runs in an external temporary directory; the canonical atomic-replace negative still uses its original expected fail-closed replacement error, byte/mode assertions, cleanup checks and status immutability check. No production or recovery evidence was created.

### Reusable mechanism
- Tests that temporarily change canonical authority metadata must use unconditional restoration, not only success-path cleanup. Prove exceptional restoration using an isolated synthetic fixture before exercising the canonical test.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable requests, recovery evidence, complete typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human promotion remain mandatory.
- Learning is append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Rejected snapshot generators must preserve symlink identity

### Outcome
- Commit `810bc721a8c0e360f5981a425fb2e86a5bf0a5aa` extends the existing strict snapshot rejection-state guard from bytes/mode to bytes/mode/symlink identity and requires every canonical authority in the final negative-suite check to be a regular non-symlink file.

### Evidence
- Previously the state comparator read snapshot bytes and `stat` mode, both of which follow symlinks. Replacing a snapshot with a symlink to matching bytes/mode could escape those two assertions. The new pure-state classifier includes a synthetic symlink-status-only mutation and applies the same three-part comparator to all eight existing rejected-generator before/after call sites.
- Exact-source Readonly run `39973259217` (job `120481178591`) and Snapshot publisher run `39973259273` (job `120481180594`) completed SUCCESS. Both logged strict snapshot negative PASS, 22 controlled validator corruptions rejected, 3 generator corruptions rejected and `production decision: NO_GO`.

### Why safe
- Only the CI-bound negative suite changed; the synthetic symlink mutation is an in-memory tuple and creates no filesystem alias. Existing symlink escape fixtures remain temporary and restore canonical bytes/modes. No production, recovery or promotion authority was changed.

### Reusable mechanism
- For protected filesystem authorities, comparing bytes and permissions alone is insufficient: also assert path identity/type and absence of symlink substitution. Reuse the same tested state comparator across all rejected publication paths and add a symlink-only negative control.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable requests, recovery evidence, complete typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human promotion remain mandatory.
- Learning is append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-23 — Generator path-substitution negatives need exact authority labels

### Outcome
- Commit `9c50dc08fad705162d2b2cdf4f88f641aac17c97` binds all 17 existing generator runtime authority substitutions to the exact canonical `strict snapshot authority drift: <label>` rejection rather than accepting any error containing `strict snapshot authority`.

### Evidence
- Before the change, an unrelated failure containing the generic authority substring could satisfy a substitution test. The generator's `require_exact_repo_file` emits the exact drift diagnostic for a substituted valid in-repository path. The new classifier tests the intended label and rejects a wrong label, prefixed/suffixed unrelated text and a non-string exit code.
- Exact-source Readonly run `39973533882` (job `120482130094`) and Snapshot publisher run `39973533663` (job `120482129418`) both completed SUCCESS, logging strict snapshot negative PASS, 22 controlled validator corruptions rejected, 3 generator corruptions rejected and `production decision: NO_GO`.

### Why safe
- The change only tightens existing negative test diagnostics. All 17 original substitutions and restoration checks remain, and the production snapshot, generator, registries, recovery evidence and promotion authorities are untouched.

### Reusable mechanism
- For path-binding negatives, associate each mutation with the exact canonical authority label and compare the complete exit diagnostic, not a broad substring. Include an independently tested classifier rejecting unrelated text and wrong-target failures.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable requests, recovery evidence, complete typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human promotion remain mandatory.
- Learning is append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Atomic replacement negatives must prove the injected call reached the target

### Outcome
- Commit `d78d03b6f1fb4abbf66b61915629090298531244` requires the strict snapshot atomic-replace negative to observe exactly one injected `os.replace` call against the canonical snapshot, with the expected sibling temporary-file prefix/suffix and the exact injected failure diagnostic.

### Evidence
- Previously a matching broad `cannot atomically write` message could satisfy the test even if the injected replacement callback was never reached. The new pure classifier accepts one correctly targeted call and rejects missing, duplicate, wrong-destination and wrong-temporary-source calls.
- Exact-source Readonly run `39974686556` (job `120486083386`) and Snapshot publisher run `39974686580` (job `120486083549`) completed SUCCESS. Both logged strict snapshot negative PASS, 22 controlled validator corruptions rejected, 3 generator corruptions rejected and `production decision: NO_GO`.

### Why safe
- Only the existing negative test's call accounting and rejection classification changed. The actual atomic writer, snapshot content, Production Status, registry and promotion authorities remain unchanged; the injected replacement still fails closed and cleanup is verified.

### Reusable mechanism
- Failure injection is not proof of coverage unless the intended hook actually runs against the intended resource. Record invocation count and exact target, bind the failure to the injected diagnostic, and use synthetic controls for missing, duplicate and wrong-target calls.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; strict OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable requests, generation recovery evidence, complete typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning is append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Successful atomic snapshot rewrites must preserve adjacent authority and cleanup

### Outcome
- Commit `2fb6cc13c700972b3a3028b493cc5fed7605f297` extends the existing successful atomic snapshot rewrite negative proof to verify the snapshot's bytes/mode/symlink identity, Production Status bytes/mode/symlink identity, and unchanged temporary-file inventory.

### Evidence
- Previously the success-path test checked snapshot bytes and its temporary `0o640` mode but did not explicitly assert status preservation, symlink identity or absence of leftover temporary authority files. The change reuses the tested `temporary_mode` and `require_snapshot_state_unchanged` helpers.
- Exact-source Readonly run `39975100189` (job `120487510861`) and Snapshot publisher run `39975100132` (job `120487510244`) both completed SUCCESS, logging strict snapshot negative PASS, 22 controlled validator corruptions rejected, 3 generator corruptions rejected and `production decision: NO_GO`.

### Why safe
- The test still writes the canonical snapshot's exact original content through the existing atomic writer and unconditionally restores its temporary mode. No new evidence or production authority is written, and additional assertions only tighten the proof.

### Reusable mechanism
- A successful atomic authority rewrite should preserve unrelated protected authorities, file type and mode, and leave no new temporary files. Reuse tested state guards for both rejection and success paths; do not infer cleanup from a zero exit alone.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Publisher revalidation must not hide validators after an unconditional early return

### Outcome
- Commit `1d50b1c863d9b4617ae3506cf5b66779c61bab4e` extends the existing CI-bound publisher workflow permission negative guard to reject standalone `return` or `exit` before the required validators inside `revalidate_latest_snapshot()`.

### Evidence
- Prior static function-body binding required four canonical validator command lines, but did not reject an unconditional `return 0` or `exit 0` inserted at the beginning of that function, which would leave the command lines unreachable.
- The new in-suite mutation probes both early-return and early-exit substitutions and requires the cause-specific fail-closed diagnostic. An independent six-case classifier check passed: baseline, comment-only return, and echoed return accepted; early return, early exit, and missing validator rejected.
- At recording time, GitHub combined commit statuses and PR-scoped workflow-run lookup returned no runs for this commit. Exact-source CI success is not claimed.

### Why safe
- Only the existing negative harness was changed; the publisher workflow, source-binding logic, canonical snapshot, recovery registries, production status, and human-promotion authority were not changed. No synthetic test is production evidence.

### Reusable mechanism
- Command presence inside a called function is insufficient when an unconditional function terminator precedes it. Bind required commands to the live function body and prove an early-termination mutation fails for the intended reason, without rejecting comments or echo strings as control cases.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `productionDecision=NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains zero registered/eligible generations, approved objectives, executable requests, generation evidence, typed eight-domain records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Complete typed eight-domain coverage, independent review and separate human promotion remain mandatory.
- Learning remains append-only operational guidance, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Claim exact-source CI success only after a successful observed workflow run at the code commit or its descendant; revisit the guard if the publisher's legitimate function control flow changes.

## 2026-10-24 — Fail-closed publisher validators and safe source-text replacement

### Symptom
- Commit `70cc89f1ecd0685a1aa866266b399e30d98cc1f6` accidentally duplicated roughly 178 lines of Python after a generated regex, leaving the negative guard syntactically invalid. The write succeeded but the committed diff immediately exposed the corruption.

### Evidence
- The diff showed `fail_closed_command` ending in `2>&1(publish: str) -> None:` followed by a duplicated remainder of the module. The file expanded from 567 to 767 lines. This was a repository source defect, not a production incident or an observed CI failure.
- Corrective commit `67a2ee99640eff1b64fbf1a4d0801481df04c624` restored the source from the last known good commit and reapplied only the intended guard. The resulting file has 589 lines and one definition each of `main`, `prove_publisher_revalidation_call_binding` and `require_readonly_pr_permissions`.

### Root cause or unknown
- Verified: JavaScript `String.replace(pattern, replacementString)` interprets the `$'` sequence as the suffix of the input. The replacement text contained a Python raw-string regex ending in `$'`, so the remainder of the original module was inserted into the replacement.

### Failed approach
- Passing Python source text containing JavaScript replacement metacharacters directly as a string replacement, without checking the complete generated diff and module structure before writing.

### Correction
- Rebuild from the previous clean blob; use `replace(pattern, () => replacement)` and `String.raw` for literal Python regex text. Verify the expected line delta, exact regex terminator, absence of duplicate function definitions and absence of the corrupted splice marker before publishing.

### Recurrence guard
- The existing CI-bound Readonly workflow compiles this negative guard with `python -m py_compile`. Before connector writes involving generated source text, use a callback replacement and deterministic structural assertions; inspect the committed diff immediately. Do not count static checks as a completed canonical CI run.

### Retry condition
- Revisit this source-generation failure only if the source transformation mechanism changes or a fresh structural mismatch is observed; never reapply the corrupt `70cc89f` payload.

### Outcome
- Corrected commit `67a2ee9` adds an exact fail-closed invocation check for all four mandatory publisher revalidation commands, and 12 negative mutations (`|| true`, `|| :`, `; true`) in the existing CI-bound suite.
- An independent 15-case Python classifier test accepted the baseline and rejected two early terminators plus all 12 masked validator commands. This is isolated classifier proof, not an observed canonical workflow success.

### Why safe
- Only the existing negative harness was changed. The publisher, recovery registries, production status, strict snapshot and promotion authorities remain unchanged. The mutations are source-text fixtures, not production evidence.

### Reusable mechanism
- A present validator command is not a fail-closed gate if shell suffixes swallow its nonzero exit. Require exact command shape inside the bounded latest-source function, then prove masking mutations are rejected for the intended reason.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Independent review and separate human production-promotion authority remain mandatory.
- Append-only learning is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-24 — Snapshot corruption rejection must not simultaneously report success

### Outcome
- Commit `eca18bf85b97b728cea9d55a2fb815d717cb9b91` extends the canonical strict snapshot corruption negative suite to reject nonempty stdout whenever the canonical validator is expected to exit 1 with its case-specific failure diagnostic.

### Evidence
- Previously `run_validator(False, label)` checked exit 1 and cause-specific stderr but ignored stdout; a child reporting a positive PASS on stdout alongside a matching negative stderr could be misclassified as a clean negative proof.
- The positive canonical validator emits PASS lines only after all checks complete. The new synthetic in-suite control injects a positive marker into negative stdout and requires a cause-specific rejection.
- An independent five-case pure-classifier check accepted empty/whitespace stdout and rejected positive, unrelated, and copied-error stdout. GitHub commit status lookup returned no completed status entries at recording time; exact-source CI success is not claimed.

### Why safe
- Only the existing CI-reachable negative harness changed. No production status, strict snapshot, generator, registries, recovery evidence, credentials, traffic, readiness or promotion authority was modified.

### Reusable mechanism
- Pair exact negative stderr and exit-code assertions with a clean stdout requirement; use a mixed positive/negative synthetic control so a contradictory child result cannot masquerade as expected failure. Keep isolated classifier tests distinct from exact-source canonical CI proof.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains `PREREQUISITES_BLOCKED` and zero registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Eight-domain coverage, independent review and separate human promotion remain mandatory.
- Append-only learning never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Claim full suite success only after observed exact-source Readonly/Publisher workflow execution; revisit if the canonical validator intentionally adds documented diagnostic stdout on controlled failure.

## 2026-10-24 — Generator corruption negatives must reject mixed success stdout

### Outcome
- Commit `9868cc6c0a8d0daa0dc14e61bfb90522811b116f` extends the existing strict snapshot negative harness to require empty stdout when the generator exits 1 with an expected case-specific corruption diagnostic.

### Evidence
- Previously `run_generator_rejects` used `proc.stderr or proc.stdout`, so a matching stderr could conceal a contradictory success marker on stdout. The canonical generator prints its success markers only after all authority checks and atomic publication validation complete.
- The new in-suite synthetic control requires rejection of a generator success marker on negative stdout. An independent five-case classifier check accepted empty/whitespace output and rejected success, unrelated, and error-like stdout.
- No exact-source CI success is claimed until the Readonly/Publisher workflows are observed at a matching source revision.

### Why safe
- Only the CI-reachable negative harness changed. Generator implementation, production status, strict snapshot, objective/generation registries, recovery evidence and promotion authorities remain unchanged.

### Reusable mechanism
- Negative subprocess proof requires a consistent tuple: expected nonzero exit, case-specific stderr, no implementation traceback, no contradictory stdout, and unchanged protected output. Reuse this rule for both validator and generator rejection paths.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, recovery evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged; independent review and separate human promotion remain mandatory.
- Learning history is append-only and never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the canonical generator intentionally changes its controlled-failure stdout contract or a new mixed-output bypass is observed. Claim CI success only from observed exact-source runs.

## 2026-10-24 — Generator rejection stdout must distinguish upstream preflight PASS from publication success

### Symptom
- The strict snapshot negative suite rejected a legitimate generator failure at the `generator canonical blocker replacement` mutation, breaking the Readonly and Backup Restore admission workflows after commit `9868cc6`.

### Evidence
- Exact-source Readonly run `39977288828` and Backup Restore Admission Chain run `39977288872` failed with `generator canonical blocker replacement: canonical generator rejection emitted unexpected stdout`. The snapshot publisher run `39977288720` also failed; its diagnostic publication was separately refused after source HEAD advanced (exit 75).
- Source inspection verified that `generate-memory-os-ops-p0-007-admission-snapshot.py` calls four canonical admission validators before constructing/publishing the snapshot. Those validators legitimately print PASS diagnostics to stdout; a later typed non-resurrection admission failure can therefore coexist with upstream PASS output without generator publication success.

### Root cause or unknown
- Verified: the prior negative classifier required completely empty generator stdout, conflating valid upstream preflight diagnostics with the generator's own final publication-success marker.

### Failed approach
- Rejecting every non-whitespace stdout byte for any generator exit 1, without accounting for the canonical validator call chain.

### Correction
- Commit `f9f5323c71745981e66e0e6ab77f4649349211c9` captures the complete positive stdout of the four canonical preflight validators before mutating authorities. Rejected generator output may only be a complete-line prefix of that observed baseline. Unrelated output, reordered lines, incomplete lines, and the generator's final success marker remain forbidden.

### Recurrence guard
- The existing CI-bound negative suite exercises synthetic clean, partial, complete, unrelated, reordered, unterminated and mixed-success stdout controls, then runs the actual corruption cases. It continues to require exit 1, the case-specific stderr diagnostic, no traceback and an unchanged deterministic snapshot.

### Retry condition
- Revisit only if the canonical preflight validators intentionally change their output or ordering, or an exact-source CI run exposes a new mismatch. Do not reintroduce a blanket empty-stdout rule without changed preconditions.

### Outcome
- Exact-source Readonly workflow run `39986110192` at `f9f5323` completed SUCCESS; its job log records `Memory OS OPS-P0-007 strict admission snapshot negative validation PASS` and three controlled generator corruption cases rejected.

### Why safe
- Only the negative harness changed. The observed upstream stdout is not accepted as generator publication success, and no production evidence, registry entry, objective, drill, credential, traffic, readiness or promotion authority was created.

### Reusable mechanism
- For a composite executable with earlier read-only validators, bind failure stdout to an observed positive-control preflight prefix rather than requiring empty stdout or accepting arbitrary PASS text. Keep the failing stage's exact stderr and protected-output invariance as independent checks.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- This append-only lesson is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence; independent review and separate human promotion remain mandatory.

## 2026-10-24 — Latest-source publisher retry must execute the full ordered admission chain

### Symptom
- The workflow permission negative previously bound only four core validators inside `revalidate_latest_snapshot()`. A publisher retry could omit or reorder other review/snapshot guards after resetting to latest `so`, while their presence in the earlier initial validation step could conceal that omission.
- The first new negative fixture implementation at commit `06f5539` failed on its own `missing reset` case.

### Evidence
- Canonical publisher source contains a five-command source-refresh prefix followed by 14 ordered review, generator, snapshot and negative-suite commands inside the bounded function.
- Exact-source Snapshot Permission Boundary run `39986587121` at `06f5539` failed with `missing reset: bounded source fixture drift`; the test mistakenly required every refresh command to immediately follow the function declaration, even though only `git fetch` is adjacent.

### Root cause or unknown
- Verified guard gap: the prior function-body checker enforced only the four `FULL_ADMISSION_VALIDATORS` and did not bind the other ten commands or their order to the latest-source retry.
- Verified fixture defect: the mutation target concatenated the function declaration and each refresh command, so it could never locate later refresh lines.

### Failed approach
- Treating four present core commands as sufficient proof of the complete publisher retry chain; generating negative mutations with an incorrect adjacency assumption.

### Correction
- Commits `06f5539e618aa69ba098431c9c07144011d6da42` and `4daf8318fdb83301d29831449b018f2e31f75cf0` bind the exact five-step fetch/reset/SHA/export/log-refresh prefix and all 14 existing review/snapshot commands, once each, in their current fail-closed order. The fixture correction replaces each target only inside the actual function suffix and restores the intended whitespace regex.

### Recurrence guard
- The existing CI-bound permission negative mutates missing/stale refresh commands, reorders two review commands, and masks all 14 validators with `|| true`, `|| :` and `; true`. It rejects unbound decoy commands, early returns and commented call sites as before.

### Retry condition
- Revisit if the publisher intentionally changes its bounded source-refresh or review-chain architecture, or a new exact-source negative exposes an unguarded bypass. Do not retry the broken function-adjacent fixture.

### Outcome
- Exact-source Snapshot Permission Boundary run `39986658090` at `4daf8318` completed SUCCESS, logging `Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS` and `production decision: NO_GO`.

### Why safe
- Only the existing read-only workflow negative harness changed. The publisher workflow itself, production status, strict snapshot, registries, evidence and promotion authorities were not written.

### Reusable mechanism
- For bounded reconcile/retry workflows, validate the complete ordered source-refresh prefix and exact downstream fail-closed command sequence in the invoked function. Mutate only the intended function body, not an ambiguous earlier workflow step.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Append-only learning never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates. Eight-domain non-resurrection coverage, independent review and separate human production promotion remain mandatory.

## 2026-10-24 — Diagnostic publisher AST must reject unconditional early termination

### Outcome
- Commit `ab174641a2a28467416433e22f5bb2868faaf5b1` extends the existing CI-bound snapshot workflow permission negative to reject unconditional `raise`, `exit()`, `quit()`, `sys.exit()` and `os._exit()` in the executable diagnostic Python heredoc, including unconditional try/with bodies and constant-true branches.

### Evidence
- Before the change, `executable_diagnostic_calls` found required AST calls anywhere in a syntactically live heredoc, even after a preceding top-level `raise SystemExit(0)`. This was a source-level reachability gap, not an observed production incident.
- Five in-memory mutations now inject module-level or try-body termination while preserving the original atomic publication calls and require the exact `strict snapshot diagnostic unconditional early termination` rejection. Exact-source Snapshot Permission Boundary run `39987038616` completed SUCCESS at `ab174641`, logging workflow permission negative PASS.

### Why safe
- The canonical workflow and diagnostic publisher were not changed; only the existing read-only negative harness and in-memory AST fixtures changed. Legitimate conditional exception-handler cleanup is not classified as unconditional early termination.

### Reusable mechanism
- AST presence checks must also inspect reachable statement order. For crash-safe publication proof, reject unconditional terminators before accepting the presence of later `mkstemp`, `fsync`, `replace` and `unlink` calls, and require cause-specific mutation rejection.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains `PREREQUISITES_BLOCKED` and zero registered/eligible generations, approved objectives, executable requests, generation recovery evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- This append-only learning record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates. Eight-domain typed coverage, independent review and separate human production-promotion authority remain mandatory.

### Retry condition
- Revisit only if the canonical diagnostic heredoc legitimately adds an unconditional exit path, or an observed execution-path bypass evades the bounded AST guard. Do not weaken required atomic-publication call reachability to accommodate an unrelated failure.

## 2026-10-24 — Validator authority symlink-state hardening is a scoped connector-write blocker

### Symptom
- A proposed change to the existing snapshot validator authority negative suite could not be committed through the connected GitHub write action.

### Evidence
- The connector returned `The tool failed internally` after a bounded update attempt targeting `scripts/validate-memory-os-ops-p0-007-admission-snapshot-validator-authority-negative.py`. A fresh `so` read still showed HEAD `fa47ebd7f3b7b84273aefb29a84e8a5d9fbb638e` and unchanged target blob `9475062def8aa438d282d0e2b7cd61b1d9b4e5ff`; the proposed `protected_state` helper is absent.

### Root cause or unknown
- Unknown: the connector reported an internal tool error, not a verified repository-level validation, permission or content error.

### Failed approach
- Attempting one contents-API update to add bytes/mode/symlink-identity assertions and isolated symlink-only negative proof.

### Correction
- Do not claim the guard was implemented or tested. Preserve the existing suite and continue independent read-only inspection and previously CI-reachable safe work.

### Recurrence guard
- Re-read branch and target blob after an ambiguous connector failure; treat the write as uncommitted unless the exact source change is observed. Never infer a commit SHA or a validator PASS from the attempted payload.

### Retry condition
- Retry only after observable connector health/write capability changes, or a new independently supported safe edit path becomes available under the existing repository policy; do not repeat the same unchanged failed write blindly.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains blocked prerequisites and zero real recovery candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. This learning entry cannot become production or promotion evidence.

## 2026-10-24 — Snapshot diagnostic finally cleanup must be executable

### Outcome
- Commit `4c918753d6041e21a6cbaf4336c0fb5cdf7ccbbf` extends the existing snapshot workflow permission negative to reject unconditional termination in an atomic diagnostic publisher's `finally` body before its required `os.unlink(tmp_name)` cleanup.

### Evidence
- The existing AST guard inspected unconditional exits in a `try` body but not its `finally` body, although its call-presence checker counted cleanup calls that could appear after `raise SystemExit(0)` or `exit(0)` in `finally`.
- Three isolated source-text negative mutations now inject `raise SystemExit(0)`, `exit(0)`, and a constant-true raise immediately before the original cleanup call; all require the exact `strict snapshot diagnostic unconditional early termination` diagnostic.
- Exact-source Snapshot Permission Boundary run `39993385074` at commit `4c918753` completed SUCCESS. The job log confirms `Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS` and `production decision: NO_GO`.

### Why safe
- Only the pre-existing read-only negative harness changed. The publisher workflow, production status, strict snapshot, registries, credentials, traffic, recovery evidence, readiness and promotion authorities were not modified. Mutations are in-memory workflow fixtures.

### Reusable mechanism
- For AST-based atomic-publication proof, check mandatory cleanup reachability inside `finally`, not merely call presence or termination in the main `try` body. Pair each bypass with an exact-cause negative mutation and an observed exact-source CI run.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human production promotion remain mandatory.
- This append-only lesson is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the diagnostic publisher intentionally changes its cleanup architecture or a new observed bypass survives the existing exact-source negative suite.

## 2026-10-24 — Generator negative must protect source, file and parent identity

### Outcome
- Commit `ed72200dce3163bd87ce01d1a4486f975505dd98` strengthens the canonical strict snapshot generator execution-authority negative: all 11 substituted helper probes must leave snapshot, Production Status and generator source bytes, mode, device/inode, parent-directory identity and resolved path unchanged.

### Evidence
- The previous harness compared snapshot/status bytes and permission bits but could not distinguish an identical-content symlink or replaced parent directory from the original canonical authority.
- A temporary-directory-only positive/negative identity fixture now replaces a file with an equal-content symlink and separately replaces its parent directory with a symlink. Both must change `protected_state`; the original file identity must be recoverable after the first fixture.
- Exact-source OPS-P0-007 Admission Snapshot publisher run `39993256887` at `ed72200d` completed SUCCESS. The later exact-source Readonly run `39993384036` at `4c918753` also completed SUCCESS; its log confirms `strict snapshot generator execution authority negative PASS`, `execution helper substitutions rejected: 11`, `isolated file and parent symlink identity bypass accepted: false`, and `production decision: NO_GO`.

### Why safe
- Only the existing CI-invoked negative harness changed. Symlink mutations are confined to an isolated temporary directory, and the canonical production status, snapshot, generator, registries, evidence, credentials, traffic, readiness and promotion authorities remain untouched.

### Reusable mechanism
- A negative test asserting canonical immutability must compare identity as well as content and mode: `lstat` of file and parent, device/inode and resolved path. Prove that equal-content file/parent symlink substitution is detectable without mutating the checkout. Do not confuse successful CI execution of these synthetic probes with production evidence.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` retains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` retains `PREREQUISITES_BLOCKED` and zero registered/eligible generations, approved objectives, executable drill requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human production promotion remain mandatory.
- Append-only learning never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if a fresh observed source-path identity bypass or an intentional canonical path architecture change alters this negative's assumptions; the separately blocked validator-authority negative path retains its own unchanged retry condition.

## 2026-10-24 — Shell exit reachability must distinguish function definitions from live execution

### Symptom
- Snapshot Permission Boundary exact-source CI failed after the new indented-shell-exit guard, even though the canonical publisher itself had not changed.

### Evidence
- Commit `21d7672e57f4f1274dc0021de74bc1d004d3e9f0` switched exit detection from raw indentation-sensitive `command` to `stripped` and added two negative fixtures for indented unconditional exits.
- Exact-source Permission Boundary run `39993764642` failed: `early exit 0 rejected outside intended reachability guard: strict snapshot publisher missing executable bounded revalidation call sites`. This is a harness-classification failure, not production evidence or a production incident.
- The existing `prove_publisher_revalidation_call_binding` deliberately injects `exit 0` inside the definition of `revalidate_latest_snapshot()`, expecting its dedicated `revalidation contains unconditional early return/exit` diagnostic. The generic run-step parser had stopped parsing at the injected function-body exit and therefore discarded later call sites.

### Root cause or unknown
- Verified: trimming indentation fixed top-level exit detection but also misclassified an exit inside an uncalled shell function definition as an immediately executed top-level exit.

### Failed approach
- Treating every indented `exit` in a run-step block as unconditional outer-shell termination without tracking whether the line belongs to the bounded function definition.

### Correction
- Commit `e2d31caaea796f8442a41ce6883719c0b8b2cdc5` tracks the exact `revalidate_latest_snapshot() {` / `}` definition boundary. Function-body exits remain visible to the dedicated function reachability guard; only unconditional outer-shell exits terminate the generic run-step command scan.

### Recurrence guard
- The existing CI-bound suite now includes both negative fixtures for indented top-level `exit 0` (including a trailing comment), plus positive controls for an unknown conditional exit and an uncalled function-body exit. The existing function-level early-exit fixture still requires its exact intended rejection.
- Exact-source Permission Boundary run `39993853357` at `e2d31caa` completed SUCCESS, logging `Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS` and `production decision: NO_GO`.

### Retry condition
- Revisit only if a new shell-function architecture, nested brace form, or observed CI failure invalidates the bounded function-definition model. Do not repeat the unscoped `stripped`-only exit classifier from `21d7672`.

### Outcome
- The corrected parser now rejects indented live shell exits without hiding later commands behind an inert function definition or losing the dedicated function-level rejection diagnostic.

### Why safe
- Only the existing CI-bound read-only negative harness and its synthetic YAML fixtures changed. The publisher workflow, production status, OPS-P0-007 snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were not changed.

### Reusable mechanism
- Distinguish command presence, command reachability and definition-time shell parsing. Track a bounded function scope separately from top-level run-step termination, and require both positive and cause-specific negative fixtures before accepting a parser hardening change.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Independent review and separate human production promotion remain mandatory.
- Append-only learning is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-24 — Atomic replacement failure must preserve protected path identity

### Outcome
- Commit `ebaec2571dd1f99a03057e05a49dbff9aa57c51d` extends the existing OPS-P0-007 strict snapshot atomic replacement negative with source-path verification and protected file/parent identity checks for snapshot, Production Status and generator.

### Evidence
- Previously the failure-injection test proved one exact rejected `os.replace` call, unchanged snapshot/status bytes and modes, and no temporary-file residue, but did not assert that equal-content file or parent symlink replacement could not escape its postcondition.
- The new isolated temporary-directory classifier rejects equal-content file and parent symlink aliases and confirms restoration of the original file inode. The canonical failure-injection probe now also compares `lstat` mode, device/inode, parent identity and resolved path for all three protected files.
- Exact-source OPS-P0-007 Admission Snapshot Atomic Write Negative run `39994043466` at `ebaec257` completed its atomic proof and canonical authority check successfully. The job log confirms `strict snapshot atomic replacement negative proof: PASS`, `snapshot/status/generator source and parent identity unchanged: true`, and `isolated file/parent symlink identity bypass accepted: false`.

### Why safe
- Only the pre-existing read-only atomic-write negative harness changed. The injected `os.replace` failure remains confined to the canonical snapshot target, while symlink mutations occur only in an isolated temporary directory. No production status, recovery registry, objective, evidence, credential, traffic, readiness or promotion authority was modified.

### Reusable mechanism
- An atomic failure test must verify both failure-injection reachability and protected-authority identity, not only bytes/mode and temporary cleanup. Combine exact injected-error and attempt-count assertions with `lstat`/resolved-path checks and a separate equal-content symlink negative control.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Independent review and separate human production promotion remain mandatory.
- Append-only learning cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the canonical atomic writer's target/source path architecture changes or a new observed failure bypasses the identity and cleanup postconditions.

## 2026-10-24 — Exact checkout binding must reject alternate-version duplicate steps

### Outcome
- Commit `95a677ad6cc2811aed8e5c45047b4b56b538c0e0` extends the existing OPS-P0-007 snapshot workflow permission negative so the expected SHA-bound `actions/checkout@v4` step must also be the only checkout step, regardless of a second checkout's action version.

### Evidence
- The prior anchored matcher counted only `- uses: actions/checkout@v4` followed by `with.ref`; an additional `actions/checkout@v3`, `@v4.2.0`, or `@main` step could evade the duplicate-step count while changing the checked-out source later.
- The updated guard enumerates all executable `actions/checkout@...` steps and requires exactly one canonical `@v4` step. Both PR and publisher workflow negative fixtures now inject each of four duplicate versions and require the intended checkout-source diagnostic.
- Exact-source Snapshot Permission Boundary run `39994202431` at `95a677ad` completed SUCCESS; the job log records `Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS` and `production decision: NO_GO`.

### Why safe
- Only the existing CI-bound read-only workflow negative harness and its synthetic text fixtures changed. Neither checkout workflow, production status, strict snapshot, registry, evidence, credential, traffic, readiness nor promotion authority was modified.

### Reusable mechanism
- For exact-source CI, validate both the expected step's pinned source ref and the absence of alternative-version duplicate source-mutating steps. A regex restricted to the expected version alone cannot prove uniqueness.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning entry cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if a legitimate workflow checkout architecture changes or a new observed checkout-step bypass evades the canonical single-checkout matcher.

## 2026-10-24 — PR admission validator commands must be fail-closed, not merely reachable

### Outcome
- Commit `b0ea8905730dc5fabf1400a9ab61eecb7d685d3b` strengthens the existing OPS-P0-007 workflow permission negative so each of the four mandatory recovery-objective, reviewed-drill-request, generation-evidence and typed non-resurrection validators must run with an exact fail-closed command shape in executable workflow steps.

### Evidence
- The prior `require_full_admission_chain` accepted any reachable line beginning with `python <validator>`, including `python <validator> || true`, `|| :`, and `; true`. This could allow the PR admission gate to conceal a validator failure even while its command appeared in the workflow.
- The new guard allows the observed plain PR invocation and exact publisher log-redirection invocation, rejecting any other candidate command shape. Twelve synthetic masked-PR cases require the intended fail-closed rejection; positive controls preserve both legitimate forms.
- Exact-source Snapshot Permission Boundary run `39994390592` at `b0ea8905` completed SUCCESS, logging `Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS` and `production decision: NO_GO`.

### Why safe
- Only the existing read-only negative harness and isolated workflow text fixtures changed. The PR/publisher workflows, production status, strict snapshot, registries, recovery evidence, credentials, traffic, readiness and promotion authorities were not modified.

### Reusable mechanism
- Workflow validator reachability and fail-closed execution are separate requirements. A line-prefix matcher proves neither failure propagation nor allowed redirection; enumerate exact supported command forms, reject masked alternatives, and prove both positive controls and cause-specific negative cases.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Independent review and separate human production promotion remain mandatory.
- Append-only learning cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the canonical PR/publisher validator invocation architecture intentionally changes or a new observed masking bypass escapes the exact fail-closed classifier.

## 2026-10-24 — Constant-false assertions cannot stand before diagnostic atomic publication

### Outcome
- Commit `ee62ac6aecbebc04ec09d9758077af9839286ceb` extends the existing OPS-P0-007 snapshot diagnostic AST negative so constant-false `assert` statements before required publication or cleanup calls are rejected as unconditional early termination.

### Evidence
- The prior reachability guard rejected explicit `raise`, `exit()` and constant-true branches containing them, but an `assert False` or `assert 0` could still terminate the canonical Python diagnostic before `os.replace` or `os.unlink`, while an AST call-presence scan saw the later calls.
- Three isolated source-text negative fixtures now insert false assertions at module level, before atomic replacement inside `try`, and before cleanup inside `finally`; each requires the exact `strict snapshot diagnostic unconditional early termination` rejection.
- Exact-source Snapshot Permission Boundary run `39994559293` at `ee62ac6a` completed SUCCESS, logging `Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS` and `production decision: NO_GO`.

### Why safe
- Only the pre-existing CI-bound read-only negative harness and in-memory diagnostic fixtures changed. The publisher workflow, production status, strict snapshot, recovery registries, evidence, credentials, traffic, readiness and promotion authorities were not changed.

### Reusable mechanism
- AST call presence is insufficient for publication proof: account for deterministic exception-producing statements as well as explicit exits, and test module, `try` and `finally` reachability separately. Preserve exact diagnostic binding.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable reviewed requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Independent review and separate human promotion remain mandatory.
- Append-only learning never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the canonical diagnostic changes its exception/optimization semantics or an observed deterministic termination bypass escapes the current AST negative suite.


## 2026-10-24 — Snapshot PR shell admission requires executable fail-closed options

### Outcome
- Commit fbe505fce6d768d9291b36c5a3fd73f789ec1314 added a canonical CI-bound negative guard requiring every one of the three strict OPS-P0-007 PR workflow run steps to begin with executable set -euo pipefail, with no later shell-option override.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40002039699 completed SUCCESS at that commit, including Prove strict snapshot permission boundary and read-only worktree verification.

### Evidence
- Previously, the workflow permission negative verified required validator command presence and exact command shape but did not bind PR shell startup or guard against later set +e, set +u, or set +o pipefail.
- The new fixture first proves the canonical PR shell shape, then tests 21 synthetic weakening mutations across all three run steps: incomplete startup, comment-only startup, quoted/echoed startup, and four shell-option overrides per step. Each mutation must receive its intended exact diagnostic.

### Why safe
- Only the existing read-only, CI-reachable negative harness changed. The PR workflow, publisher workflow, production status, strict snapshot, registries, real recovery evidence, credentials, traffic, readiness and promotion authorities were not modified.

### Reusable mechanism
- Treat a validator command as fail-closed only when its containing executable shell starts with effective error, unset-variable and pipeline failure propagation and does not disable those options before running admission gates. Distinguish shell configuration proof from validator command presence and from CI success.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning entry is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the legitimate PR workflow run-step architecture changes or a newly observed executable shell-option bypass evades the exact negative suite.


## 2026-10-24 — Publisher source refresh and diagnostic steps must retain fail-closed shell options

### Outcome
- Commit 3fe0cebcc1757fc90022b53d4349b9ffb3d9fe3d added a CI-bound executable guard requiring the three protected publisher steps (exact-source capture, bounded revalidation/publication, and privacy-safe failure diagnostic) to start with set -euo pipefail and never override shell options later in the step.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40002199216 completed SUCCESS at this commit. The existing generator step deliberately uses set +e to capture and propagate validator exit codes through the separate output-gated publication path and was not reclassified as a protected fail-closed step.

### Evidence
- Previously the negative harness proved source-refresh and fourteen-validator ordering inside the bounded revalidation function but did not verify the enclosing publisher shell's error-propagation options. A validator failure could otherwise be ignored if errexit were disabled.
- The new canonical positive control and 21 synthetic negative mutations across three protected run steps require exact startup and override rejection diagnostics. Startup replacement by comments or echo statements does not count as execution.

### Why safe
- Only the existing read-only permission-boundary negative harness changed; the publisher workflow, PR workflow, production status, OPS-P0-007 snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Bind source refresh and all publication gates to the enclosing shell failure-propagation mode, not only to command text. Scope fail-closed requirements to the protected steps; preserve a separate explicit status-capture contract for steps that intentionally disable errexit.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Append-only learning never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only when protected publisher run-step architecture changes, when the status-capture gate changes, or when a new observed shell-option bypass escapes the bounded negative proof.


## 2026-10-24 — PR validator presence inside a conditional or uncalled function is not admission

### Outcome
- Commit 8cf02028e3d33068d0d48ed181a736e659d61b71 adds a canonical CI-bound negative guard that rejects shell conditional/loop/function wrappers around the strict snapshot PR admission step's four mandatory validators.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40002337873 completed SUCCESS at this commit.

### Evidence
- The existing executable run-line parser intentionally treats commands in unknown shell conditions as potentially executable and also scans shell function bodies. That permissive classification is appropriate for general text discovery but is insufficient to prove that a PR admission validator always runs.
- The PR workflow's canonical admission run step is linear and executes each of four required validators as an exact top-level command. Eight new synthetic negatives wrap each validator in an unknown runtime condition or uncalled function, requiring the exact unconditional-admission rejection. A positive control permits comments and quoted text mentioning shell control flow.

### Why safe
- Only the existing CI-bound read-only workflow permission negative harness changed. The PR workflow, publisher workflow, production status, strict OPS-P0-007 snapshot, registries, real recovery evidence, credentials, traffic, readiness and promotion authorities were unchanged.

### Reusable mechanism
- Distinguish potentially reachable shell commands from mandatory unconditional admission gates. For a deliberately linear CI admission step, fail closed on control-flow wrappers rather than treating an unknown condition or uncalled function as sufficient runtime proof.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Append-only learning is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the reviewed PR admission step intentionally introduces conditional execution, or if a newly observed shell wrapper bypasses the bounded negative classifier.


## 2026-10-24 — Constant-true comparisons cannot hide diagnostic early termination

### Outcome
- Commit ea8e7e7e4012387fe935b0eb1aed20c9464266b8 strengthens the existing strict OPS-P0-007 diagnostic Python AST negative with literal-only static truth evaluation of comparisons, negation and boolean conjunction/disjunction.
- Exact-source OPS P0 007 Snapshot Permission Boundary job 120581830451 in run 40002469879 completed SUCCESS, including the canonical negative proof and clean-worktree verification.

### Evidence
- The previous early-termination classifier recognized literal if True and if False but not equivalent deterministic conditions such as if 1 == 1 or if not False. An unconditional raise or exit under those conditions could precede atomic replacement or cleanup while required calls remained present later in the AST.
- Four new synthetic negatives insert deterministic true branches containing raise, exit or assert before atomic replacement. They require the exact unconditional-termination diagnostic. A constant-false comparison branch containing a raise is the positive control, proving that unreachable code is not mistaken for executed termination.

### Why safe
- Only the pre-existing read-only CI-bound workflow negative harness and synthetic Python heredoc mutations changed. Publisher workflow, Production Status, OPS-P0-007 snapshot, registries, real recovery evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- For executable AST proof, evaluate only a bounded whitelist of literal operations and inspect the branch whose truth value is deterministically known. Never use eval on source code; unknown runtime conditions must remain unknown. Pair true-branch negative controls with false-branch positive controls.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if diagnostic source changes the supported expression grammar or an observed deterministic termination form bypasses this bounded classifier.


## 2026-10-24 — Snapshot PR must execute the complete canonical admission chain in order

### Outcome
- Commit 6226052c76dc42b49eeeca724f2a3d80a56fdc7a strengthens the existing CI-bound workflow negative guard: the strict OPS-P0-007 PR validation step must run the full ordered canonical admission and snapshot chain, including its own workflow-permission negative, without an early exit or shell control-flow wrapper.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40002608279 completed SUCCESS at this commit.

### Evidence
- Prior checks proved four mandatory recovery gates and fail-closed shell options, but a successful exit after those four gates could still skip downstream snapshot generation, snapshot negative validation or authority-negative checks without violating the four-gate presence predicate.
- The new classifier requires the exact observed fifteen-command PR chain (fourteen bounded publisher revalidation commands plus the workflow permission negative). Isolated negatives reorder adjacent commands, remove the snapshot negative, insert an unreviewed extra validator, and inject early exits before both an early and a late gate. Each must produce its cause-specific diagnostic.

### Why safe
- Only the existing read-only CI-reachable negative harness and synthetic source-text mutations changed. Neither workflow nor Production Status, OPS-P0-007 snapshot, registries, real evidence, credentials, traffic, readiness or promotion authority was modified.

### Reusable mechanism
- Four critical admission gates are necessary but not sufficient for complete CI execution proof. Bind the entire ordered validator chain, its negative suites and its final permission boundary to the same unconditional run step. A successful exit before a later gate is a failure, not a successful admission.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed PR validation chain intentionally changes, or an observed command-order or early-termination bypass escapes the bounded negative suite.


## 2026-10-24 — Named duplicate checkout steps must not evade exact-source binding

### Outcome
- Commit 532c2beb391584c88f6a66fa40252ffb6508ec6f extends the existing OPS-P0-007 snapshot workflow permission negative so a second checkout step declared with name first and uses on the following YAML line cannot evade the single-checkout source binding.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40002756551 completed SUCCESS at this commit.

### Evidence
- The prior matcher enumerated only step list items beginning with - uses: actions/checkout@v4. GitHub Actions also permits a step to begin with - name: followed by uses: actions/checkout@..., so a later named checkout could change source authority while escaping the duplicate count.
- Both PR and publisher fixture suites now inject named second checkout steps using v4, v3, v4.2.0 and main. All eight new mutations must receive the exact checkout source-binding rejection; the canonical single-checkout positive controls remain required.

### Why safe
- Only the existing read-only, CI-reachable workflow negative harness and isolated YAML text fixtures changed. Neither workflow, Production Status, strict snapshot, recovery registries, evidence, credentials, traffic, readiness nor promotion authority was modified.

### Reusable mechanism
- For GitHub Actions source-binding checks, count executable uses declarations in both legal step-key orders. A regex that recognizes only - uses on the list-item line is insufficient to establish checkout uniqueness. Retain version-agnostic duplicate detection and exact source-SHA binding as separate assertions.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed checkout-step YAML architecture changes or a new observed duplicate checkout representation bypasses the bounded matcher.


## 2026-10-24 — Deterministically infinite diagnostic loops are early termination

### Outcome
- Commit b1d62aef872154d6a77be12ed117c4187bb50609 extends the strict OPS-P0-007 diagnostic Python AST negative to reject deterministic true while loops before atomic publication or cleanup.
- Exact-source OPS P0 007 Snapshot Permission Boundary job 120583422598 in run 40002927507 completed SUCCESS.

### Evidence
- Earlier AST guards rejected explicit raise, exit, false assertions and deterministic true conditional branches but did not reject a while True: pass loop before the required os.replace or os.unlink. Required calls could still appear later in the AST while being unreachable.
- New negative fixtures insert while True before atomic replacement and while 1 == 1 before cleanup. Both require the exact unconditional early-termination rejection. A while False branch containing a raise is the positive control and must not be treated as executable early termination.

### Why safe
- Only the existing CI-bound read-only workflow negative harness and isolated in-memory diagnostic mutations changed. Publisher workflow, Production Status, OPS-P0-007 snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- For a diagnostic that must complete an atomic write and cleanup, an unbounded deterministic loop is a fail-closed reachability violation even without an explicit exit. Use bounded literal-only truth evaluation and positive controls for dead loops, without executing mutated diagnostic code.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the canonical diagnostic intentionally introduces bounded loop semantics or a newly observed deterministic loop bypass escapes this classifier.


## 2026-10-24 — Atomic snapshot diagnostics must remain privacy-safe non-production metadata

### Outcome
- Commit d518991badc1f8c1665139faad5ec00f3d97a950 binds the strict OPS-P0-007 snapshot diagnostic publisher's executable Python payload to an exact non-production schema, current source SHA, bounded output, failure result and diagnostic-only file path.
- Exact-source OPS P0 007 Snapshot Permission Boundary job 120584081039 in run 40003116777 completed SUCCESS.

### Evidence
- Earlier workflow negative proof required an atomic, mode-preserving diagnostic write and cleanup, but did not inspect the actual diagnostic record's production-evidence/readiness flags, source SHA binding, result, log-length bound or output path. An atomic write alone cannot prove the payload is safe or non-promotional.
- The new AST guard requires all expected literal fields with exact types, productionEvidence=false, productionReady=false, containsSecrets=false, generation/objective/request/restore flags false, result=FAIL, the observed source and exit-code environment bindings, output limited to the last 12000 characters, and the canonical diagnostic fixture path.
- Twelve isolated negative mutations change each protected field, replace source/exit bindings, remove the log bound, or redirect the output path to a production-evidence location. Each must fail with the exact non-production evidence-boundary diagnostic.

### Why safe
- Only the existing read-only, CI-reachable workflow negative harness and synthetic in-memory publisher mutations changed. The publisher workflow itself, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Distinguish crash-safe atomic publication from semantic publication authority. Validate the actual executable AST record and target path, including boolean types and bounded privacy-safe output; never infer non-production status merely from successful atomic write or a filename.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Append-only learning is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the reviewed diagnostic schema, privacy-redaction contract, source binding or publication path changes, or if a new observed payload bypass evades the exact AST guard.


## 2026-10-24 — Diagnostic payload safety must survive post-initialization mutations

### Outcome
- Commit 6f6f8552e42a766593d26b03e405a67da9b3fba6 extends the existing OPS-P0-007 snapshot diagnostic AST negative so its safe initial record cannot be overwritten, mutated or replaced with forged serialized bytes before atomic publication.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40003271633 completed SUCCESS at this commit.

### Evidence
- A diagnostic record could initially satisfy the exact non-production schema and source binding but then be changed by value item assignment, update, deletion or by reassigning/augmenting the serialized payload before handle.write(payload). The prior initial-field check did not prove that the emitted bytes retained those fields.
- The new guard binds the single executable payload assignment to the exact canonical JSON serialization expression and rejects subsequent writes, deletions, augmentations and known mutating record methods. Five synthetic negatives mutate productionEvidence, productionReady, containsSecrets or payload after safe initialization, requiring the exact non-production evidence-boundary diagnostic.

### Why safe
- Only the existing read-only CI-bound workflow permission negative harness and in-memory diagnostic fixtures changed. Publisher workflow, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were not changed.

### Reusable mechanism
- Validate the complete dataflow from authorized literal record to serialized bytes and atomic write, not only the record's initial assignment. Fail closed on mutable aliases or reassignment that can invalidate a previously verified safety invariant.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the diagnostic serialization/dataflow architecture changes or an observed aliasing mutation bypass escapes the bounded AST guard.


## 2026-10-24 — Generator execution-authority rejection cannot emit success output

### Outcome
- Commit cd2bb4da2378d0acbfab17f297b5957deaa203be extends the existing OPS-P0-007 strict snapshot generator execution-authority negative to capture stdout during each substituted-helper rejection and require it to be empty.
- Exact-source OPS P0 007 Admission Snapshot Readonly run 40003468551 completed SUCCESS at this commit, including the generator execution-authority negative.

### Evidence
- The previous helper substitution negative required the exact SystemExit rejection and protected snapshot/status/generator identity, but did not verify that a rejected generator had not already printed a misleading successful snapshot publication or readiness marker.
- The new classifier first accepts empty stdout, then rejects synthetic snapshot-generated, production GO and recovery-objective PASS output. All eleven canonical helper substitutions must fail at the intended authority guard without emitting success output, and must preserve protected file and parent identity.

### Why safe
- Only the existing read-only, CI-reachable generator execution-authority negative harness changed. The canonical generator, publisher workflow, Production Status, OPS-P0-007 snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Exact failure code and diagnostic alone are insufficient for negative proof: also reject contradictory success output before failure. Capture output around the tested canonical execution boundary, retain exact cause binding, and verify protected authorities after every rejected mutation.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the canonical generator intentionally changes its pre-rejection output contract or a newly observed contradictory output bypass escapes the negative suite.


## 2026-10-24 — Atomic replacement negative must bind the entire injected failure diagnostic

### Outcome
- Commit 029420ed9f692efa26910b8d50263287c901505e strengthens the existing OPS-P0-007 strict snapshot atomic-write negative: the injected canonical os.replace failure must produce exactly the expected target-bound atomic-write error, not merely two substrings.
- Exact-source OPS P0 007 Admission Snapshot Atomic Write Negative run 40003924228 completed SUCCESS at this commit.

### Evidence
- The prior test required the failure string to contain both cannot atomically write and injected atomic replacement failure. An unrelated target or prefixed/suffixed diagnostic containing both fragments could satisfy that predicate.
- The new exact classifier requires the full canonical snapshot path and injected failure sentinel, and independently rejects unrelated prefix/suffix, wrong target path and sentinel-only synthetic diagnostics. The existing exactly-one canonical replacement attempt, protected bytes/mode/identity and temporary cleanup checks remain in place.

### Why safe
- Only the existing CI-bound read-only atomic-write negative harness changed. The generator, publisher workflow, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- An injected error must prove both the intended failure source and its exact protected target. Use a single canonical diagnostic with negative controls for prefix/suffix and wrong-target masquerading, alongside exact attempt count and protected-authority postconditions.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the canonical atomic writer changes its error contract or an observed failure injection bypasses exact target/diagnostic binding.


## 2026-10-24 — Post-write rollback must reject symlinked canonical authorities before mutation

### Outcome
- Commit f80d201fd0ff87f2faa50534ddf918a7444e6bce adds fail-closed source-path checks to the existing strict OPS-P0-007 snapshot post-write rollback negative before either canonical mutation scenario and after each cleanup.
- Exact-source OPS P0 007 Snapshot Post Write Rollback Negative run 40004096132 completed SUCCESS at this commit.

### Evidence
- The rollback harness intentionally writes and restores the canonical strict snapshot. Its previous bytes/mode checks did not explicitly prevent a same-content symlinked snapshot, Production Status or generator path from becoming the target of that test's mutation.
- The new precondition requires the exact expected repository-relative file, resolved path, regular-file identity and non-symlinked parent for all three authorities. Isolated temporary fixtures prove acceptance of a canonical file, exact rejection of a same-content file symlink, restoration, and exact rejection of a parent-directory symlink. No fixture symlink is created in the canonical checkout.

### Why safe
- The added checks execute before existing rollback mutation and again after each cleanup. Only the CI-bound rollback negative harness changed; the canonical generator, publisher workflow, Production Status, snapshot content, registries, evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Before an intentionally mutating negative test, prove canonical source path identity independently of content and mode. Use disposable file/parent symlink fixtures for negative proof, then recheck canonical path authority before each destructive phase.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if canonical rollback source-path architecture changes or a newly observed symlink/path alias bypasses the pre-mutation guard.


## 2026-10-24 — Publisher initial status capture must gate every admission validator

### Outcome
- Commit d57fbbbda094042ff8d8bf324ea7021b3923c5c7 extends the existing OPS-P0-007 snapshot workflow permission negative to bind the initial publisher generation step's intentionally non-errexit shell to exact fail-closed exit-status capture and all fourteen canonical admission/snapshot validators.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40004281996 completed SUCCESS at this commit.

### Evidence
- The publisher's initial generation step deliberately uses set +e so it can capture a failing validator's code, publish a diagnostic instead of a snapshot, and gate subsequent publication on steps.snapshot.outputs.exit_code. Earlier guards proved the bounded revalidation function and protected publication steps, but did not bind all initial capture commands and their status propagation.
- The new positive control requires set +e, log reset, code=0, compile failure capture, all fourteen validators in canonical order with an exact if-code-zero guard and failure propagation, and the final exact exit_code output binding.
- Fourteen synthetic negatives remove the status assignment from one validator at a time; additional negatives reorder validators, forge exit_code=0, alter the initial status, or mask compile failure. Each requires its intended exact rejection diagnostic.

### Why safe
- Only the existing CI-bound read-only workflow permission negative harness changed. The publisher and PR workflows, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- When a workflow intentionally disables errexit to preserve diagnostics, its explicit status-capture chain becomes the fail-closed authority. Bind every validator's execution condition, failure assignment, command order and output gate; a plain command-presence scan cannot establish this safety property.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed publisher initial status-capture architecture changes or a newly observed skipped/masked validator bypass escapes the bounded negative suite.


## 2026-10-24 — Snapshot publisher staging allowlist and overlapping command fixtures

### Symptom
- Initial commit da808f6e2ca7f435babdf4cc3c005259a62af373 caused exact-source Snapshot Permission Boundary run 40004477561 to FAIL during its new force-push negative fixture, before proving the staging allowlist.

### Evidence
- CI job 120588765126 reported OPS-P0-007 SNAPSHOT WORKFLOW PERMISSION NEGATIVE FAILED: force push publisher staging fixture drift, exit 1.
- The source contained two valid lines beginning with if git push origin HEAD:so; then: one normal multiline if and one inline if with exit 0. The fixture incorrectly required the shared prefix to occur once.

### Root cause or unknown
- Verified: the negative mutation anchor was a non-unique substring of two legitimate publisher push commands. The production publisher behavior itself was not the cause.

### Failed approach
- Using substring count on an overlapping shell command prefix as a uniqueness proof for one negative mutation.

### Correction
- Commit 6b027ac20b9cf796f2d17d1f2223c9156ffbab03 anchors the force-push mutation to the complete, indentation-preserving command line including its newline. The corrected exact-source Snapshot Permission Boundary run 40004506159 completed SUCCESS.

### Recurrence guard
- For negative fixtures against commands with shared prefixes, require a unique full-line mutation anchor, not a shared prefix. The canonical positive staging/push allowlist now also rejects broad git add -A, Production Status staging, forced push, commit-all, diagnostic redirection and extra staging, with cause-specific rejection.

### Retry condition
- Do not rerun the known-broken da808f6 fixture. Revisit only if the publisher staging architecture changes or a new observed staging/push bypass evades the exact allowlist.

### Outcome
- The CI-bound negative now restricts snapshot publisher git add/rm/commit/push commands to the eight observed safe command forms, preserving only the strict snapshot and non-production diagnostic publication paths.

### Why safe
- Only the existing read-only workflow permission negative harness and synthetic publisher text fixtures changed. Neither publisher workflow nor Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness or promotion authorities were modified.

### Reusable mechanism
- Exact-source and exact-stage allowlists prevent a write-capable workflow from widening its commit scope to protected production authorities. Couple allowlisted staging/push forms with exact full-line negative fixtures and a successful canonical positive control.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.


## 2026-10-24 — Publisher captured status cannot be bypassed by an early exit

### Outcome
- Commit f105f7eceedbe357184d24c61b0110562105561e extends the existing OPS-P0-007 publisher initial status-capture guard to reject an early exit, return, exec or later shell-option override before the final status publication.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40004640714 completed SUCCESS at this commit.

### Evidence
- The prior initial status-capture guard required all fourteen validator lines and exact exit_code output at the end, but a successful exit before those lines could leave them present yet unexecuted. It also did not explicitly reject later set overrides inside the intentionally non-errexit step.
- Three synthetic negatives insert exit 0 before the first or last validator and set -euo pipefail after the initial code=0; each must produce the exact unconditional early-termination or shell-override rejection. The canonical final exit 0 remains allowed only after the captured status is written.

### Why safe
- Only the CI-bound read-only workflow permission negative harness and synthetic publisher text fixtures changed. The publisher workflow, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- A status-capture step must execute all intended checks before its intentional final success exit. Verify not just command presence and output binding but also absence of earlier shell termination or option reconfiguration that would bypass the status gate.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the publisher capture step's reviewed shell-control architecture changes or a newly observed early-termination bypass escapes the bounded guard.


## 2026-10-24 — Atomic failure injection must originate from canonical sibling temporary file

### Outcome
- Commit 40dc893ac6e75eeb5bf18bb592afc047b7e0068f strengthens the existing strict OPS-P0-007 snapshot atomic-write negative by requiring the intercepted os.replace source to be a canonical sibling temporary file of the snapshot target.
- Exact-source OPS P0 007 Admission Snapshot Atomic Write Negative run 40004775994 completed SUCCESS at this commit.

### Evidence
- The prior atomic negative proved exactly one intercepted canonical destination, the exact injected error and protected rollback state, but did not validate the source path of the attempted replacement. An unexpected source could still satisfy destination-only injection.
- The new classifier requires the source parent to equal the canonical snapshot parent, the filename to begin with the target-specific hidden temporary prefix and end in .tmp. Synthetic negatives reject unrelated names, wrong suffixes and wrong parent paths before the canonical failure injection runs.

### Why safe
- Only the existing read-only atomic-write negative harness and isolated synthetic source-path classifier changed. The canonical generator, publisher workflow, Production Status, snapshot, registries, evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Atomic failure-injection proof should bind the source and destination of the attempted replace, not just the destination and error message. Verify canonical sibling temporary naming alongside exact injected diagnostic, attempt count, cleanup and protected-authority identity.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the canonical atomic writer's temporary-file naming or directory architecture changes, or an observed source alias bypasses the bounded source/destination guard.


## 2026-10-24 — Atomic replacement source must be a materialized regular file

### Outcome
- Commit 8a4d225ba84703556600d358b674410f022d7cde extends the strict OPS-P0-007 atomic-write failure negative so the intercepted canonical sibling temporary source must actually exist as a regular non-symlink file before the injected replacement failure.
- Exact-source OPS P0 007 Admission Snapshot Atomic Write Negative run 40004915665 completed SUCCESS at this commit.

### Evidence
- The earlier source-path classifier verified the temporary filename and directory but did not prove that the source was materialized. A nonexistent file, directory or symlink with the correct name could satisfy the naming predicate even though no valid atomic replacement would be possible.
- The new classifier first proves acceptance of an isolated regular temporary file, then requires exact rejection for an equal-content symlink alias, directory and missing file. The actual intercepted canonical replacement now requires both target-specific sibling naming and a materialized regular source.

### Why safe
- Only the existing read-only atomic-write negative harness and temporary-directory fixtures changed. The canonical generator, publisher workflow, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Failure-injection reachability must prove a real attempted operation, not merely a matching source/destination string. For atomic replacement, require source existence, regular-file identity, canonical sibling naming, exact destination, exact injected diagnostic and cleanup.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the canonical atomic writer changes its temporary-file materialization architecture or an observed alias/non-regular source bypass escapes this guard.


## 2026-10-24 — Short-circuit literal truth is sufficient to reject diagnostic early termination

### Outcome
- Commit ed61c88fa4827d8782e45e6eb3dc5dbb10305929 extends the strict OPS-P0-007 diagnostic Python AST negative to evaluate deterministically true or false short-circuit boolean expressions even when another operand depends on unknown runtime state.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40005061554 completed SUCCESS at this commit.

### Evidence
- The prior bounded static truth evaluator required all operands of and/or to be known. An if True or runtime_unknown branch was actually always true, but its unknown operand prevented classification, so an early raise before atomic replacement could evade the unconditional-termination proof.
- New negative fixtures insert if True or runtime_unknown and if not (False and runtime_unknown) before atomic replacement; both require the exact early-termination rejection. A positive control with if False and runtime_unknown must not be misclassified as executable termination.

### Why safe
- Only the existing read-only CI-bound workflow permission negative harness and in-memory Python AST fixtures changed. The publisher workflow, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- For static reachability, logical AND is false when any operand is deterministically false, and logical OR is true when any operand is deterministically true, regardless of other unknown operands. Retain unknown for all other cases; never evaluate arbitrary runtime code.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- Learning remains append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if diagnostic condition syntax expands beyond the bounded literal evaluator or a newly observed deterministic branch bypass escapes the AST negative.

## 2026-10-24 — PR admission must reject shell traps and command indirection

### Outcome
- Commit 213624c1fc43f7b3c6dafbe62ce1ba752e456ab7 extends the CI-bound strict OPS-P0-007 PR admission negative to reject executable trap, alias, unalias, shopt, enable, source, and dot-source commands in the deliberately linear validator step.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40005770113 completed SUCCESS at that commit.

### Evidence
- The prior linear admission classifier rejected conditional wrappers, shell functions, early exit, and reordered validators but did not reject shell traps or source/alias commands inserted before a validator. A trap on ERR could turn a validator failure into exit 0; shell sourcing or enabled aliases could alter command resolution or errexit while leaving all required validator lines present.
- Eight synthetic mutations now insert those shell commands before the first required validator and require the exact unconditional-admission rejection diagnostic. Existing comment/quoted-shell positive controls remain accepted.

### Why safe
- Only the existing CI-bound read-only workflow permission negative harness and isolated in-memory PR workflow mutations changed. The PR and publisher workflows, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness, and promotion authorities were untouched.

### Reusable mechanism
- For a linear fail-closed CI admission step, prove not just required validator presence and order but also absence of shell constructs that can redefine commands or intercept failure. Keep exact-diagnostic negative fixtures and positive controls to avoid accepting unrelated failures.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records, and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, or promotion evidence.

### Retry condition
- Revisit only if the reviewed linear PR shell architecture changes or a new observed shell-command indirection bypasses the bounded negative guard.


## 2026-10-24 — PR source-verification authority and repeated fixture-anchor collision

### Symptom
- Initial exact-source Snapshot Permission Boundary run 40005920442 at cbc18a67b54e5b466ff73990f374dbc94e879c9d failed with strict snapshot PR source verification fixture drift.
- The first correction at 7ccfc01d71dd21f688653a6bbe92cd7b71e0e59c still failed in run 40005999096 with the same diagnostic.

### Evidence
- The canonical PR workflow has two legitimate clean-worktree assertions: one in Verify exact pull request source and one after the deterministic snapshot diff check.
- Both the missing-clean-check and extra-command negative fixtures originally used the shared test -z git status line as a global uniqueness anchor. The first correction scoped only the missing-clean-check fixture; the extra-command fixture still counted the shared line twice.

### Root cause or unknown
- Verified: the synthetic mutation harness required a globally unique substring that was not unique in the reviewed workflow. This was a fixture-boundary failure, not a failure of the production or PR validator execution.

### Failed approach
- Replacing one repeated shell line by globally counting it, and then correcting only one of two fixtures that shared the same ambiguous anchor.

### Correction
- Commits 7ccfc01 and 7fad5de scope both mutations to the unique pair of checked-out HEAD verification and clean-worktree assertion in the named PR source step.
- Exact-source Snapshot Permission Boundary run 40006081169 at 7fad5de81c4473393b37ca414e5c3fc838403c4a completed SUCCESS.

### Recurrence guard
- The CI-bound negative now requires an exact named source-verification step: fail-closed shell startup, nonempty PR-head SHA, checked-out HEAD equality, clean worktree, no conditional or continue-on-error override, no extra command, and no duplicate step. Nine isolated mutations must produce its exact authority-drift diagnostic.
- Mutation anchors for repeated workflow commands must be unique within the intended step, not globally matched by a shared command suffix. Before adding fixtures, count every occurrence in the actual canonical workflow.

### Outcome and evidence
- The repaired negative suite passed exact-source CI run 40006081169; it rejects weakening of the source-binding precondition without changing the reviewed workflow.

### Why safe and reusable mechanism
- Only the existing CI-bound read-only negative harness changed; its fixture mutations operate on in-memory workflow text. Bind source verification to a reviewed step-shaped allowlist and exercise exact-diagnostic negatives for each required assertion. No production evidence or readiness was generated.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Do not retry the ambiguous cbc18a67 or partially fixed 7ccfc01 fixture. Revisit only if the reviewed source-verification step changes or an observed source-binding bypass escapes the bounded exact-step guard.


## 2026-10-24 — Publisher status capture must reject EXIT-trap status forgery

### Outcome
- Commit 7c2997e4a2a57914a155a8d4d7200710ea40adeb strengthens the existing OPS-P0-007 publisher status-capture guard to reject shell traps, sourced scripts, alias manipulation and shell-option indirection before captured status publication.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40006209895 completed SUCCESS at this commit.

### Evidence
- The reviewed publisher intentionally uses set +e and an explicit code variable, then writes exit_code=$code to GITHUB_OUTPUT. The previous guard rejected early exit and later set overrides but did not reject an EXIT trap that appends exit_code=0 after the real status, potentially causing downstream success gating to read a forged final output.
- Six synthetic mutations now insert a forged EXIT trap, ERR trap, source, dot-source, shopt, or alias after code=0. Every mutation must trigger the exact capture early-termination/shell-override rejection; the canonical positive workflow still passes.

### Why safe
- Only the existing read-only CI-bound workflow permission negative harness and in-memory publisher fixtures changed. The publisher workflow, Production Status, strict snapshot, registries, evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- A captured status gate is not safe merely because every validator line propagates failure. Forbid shell hooks or command-resolution indirection that can overwrite the published result after the validated chain completes. Exercise exact-diagnostic negative fixtures for status-forging EXIT traps.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the reviewed publisher status-capture architecture changes or a new observed status-forging shell hook escapes this bounded guard.


## 2026-10-24 — Publisher protected steps must not mask failures with shell hooks

### Outcome
- Commit 4652d54009e578f14d42c3d0e00cf6e51fe50535 extends the strict OPS-P0-007 publisher protected-step fail-closed shell guard to reject traps, sourced scripts, shell alias manipulation and option indirection after the mandatory set -euo pipefail prefix.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40006331321 completed SUCCESS at this commit.

### Evidence
- The prior protected-step guard rejected a later set override but not an ERR/EXIT trap that could exit 0 on a failed source refresh, publication or diagnostic command. Those commands could remain textually present without retaining fail-closed behavior.
- Each of the three reviewed protected steps now has synthetic negative fixtures for ERR/EXIT traps, source/dot-source, alias, shopt and the original four shell-option overrides. All must produce the exact protected-shell-options rejection.

### Why safe
- Only the CI-bound read-only workflow permission negative harness and synthetic workflow fixtures changed. The actual publisher and PR workflows, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- A fail-closed shell prefix is not sufficient if later traps or sourced code can replace its failure semantics. Bind every protected publication step to an uninterrupted shell control surface and prove each forbidden override through exact-diagnostic negatives.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the protected publisher step architecture changes or a newly observed shell failure-masking hook evades the bounded guard.


## 2026-10-24 — Publisher initial SOURCE_SHA must be captured by an exact checked-out HEAD assertion

### Outcome
- Commit 89462e400cc20d438f64d8ef405a0e93a957ce09 adds an exact-step authority guard for the publisher's initial source capture and nine cause-specific synthetic negative mutations.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40006483570 completed SUCCESS at this commit.

### Evidence
- The existing publisher guard checked exact checkout ref, protected shell startup and later stale-source comparisons, but only searched for SOURCE_SHA text and did not require the initial source capture step to execute its clean-worktree assertion, checked-out HEAD equality, and actual GITHUB_ENV publication in the reviewed order.
- New fixtures remove or replace each source check, forge SOURCE_SHA, disable/continue-on-error the step, add early exit, reorder checks or duplicate the step. All require the exact publisher source-capture authority-drift rejection.
- Fixtures mutate the complete unique named step block, not a shared shell command substring, avoiding the earlier PR fixture-anchor collision.

### Why safe
- Only the existing read-only CI-bound workflow permission negative harness and synthetic workflow text changed. The actual publisher and PR workflows, Production Status, strict snapshot, registries, evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Exact-source publication must prove the original checkout SHA is verified and exported by a live fail-closed step, not merely that the expected variable name occurs in workflow text. Bind the named step to its complete reviewed command sequence and mutate only a unique step-scoped fixture.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the reviewed publisher source-capture architecture changes or a new observed stale/forged source-binding bypass escapes this exact-step guard.


## 2026-10-24 — Generator runtime authority paths must reject same-type aliases

### Outcome
- Commit 34ead77d026ed698e757d4d841d5dcd4779b5378 extends the strict OPS-P0-007 snapshot generator execution negative to test seventeen runtime path constant substitutions against existing but incorrect canonical files.
- Exact-source OPS P0 007 Admission Snapshot Readonly run 40006679895 and OPS P0 007 Admission Snapshot run 40006679736 both completed SUCCESS at this commit.

### Evidence
- The existing generator negative tested callable helper substitutions and protected path identity but did not directly exercise whether the generator rejected in-memory substitution of OUTPUT, STATUS, registry, helper, validator or writer paths with other real repository files.
- Both exact-source CI logs reported Memory OS OPS-P0-007 strict snapshot generator execution authority negative PASS and canonical runtime path substitutions rejected: 17, while retaining production decision: NO_GO.
- Each synthetic substitution now requires the exact strict snapshot authority drift diagnostic naming its expected path role. A same-type but wrong path must not be accepted as a valid authority.

### Why safe
- Only the existing CI-bound read-only generator execution negative changed. The generator itself, snapshot, Production Status, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched. In-memory path substitutions are restored after each rejection, and protected snapshot/status/generator bytes and file/parent identity are checked.

### Reusable mechanism
- A generator's helper identity guard and canonical file existence checks need a paired negative that swaps authority path bindings to other real files. Exact role-specific diagnostics prevent unrelated failures from being mistaken for the intended path-drift rejection.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the generator's reviewed runtime path bindings change or a newly observed authority alias bypass escapes the seventeen negative probes.


## 2026-10-24 — PR validator body cannot establish admission in a disabled or non-fatal step

### Outcome
- Commit 81654568de7a3d0bc564a82f4dc7d4f5a2a582ed binds the strict OPS-P0-007 PR admission validator chain to the reviewed enabled step header, not just the executable-looking run block.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40007020689 completed SUCCESS at this commit.

### Evidence
- The prior PR admission guard required all validators in linear order but did not inspect the enclosing step's if, continue-on-error, or shell settings. A disabled step could skip all validators; a continue-on-error step could report a successful workflow despite a failed validator.
- Four synthetic mutations insert if: false, an expression-level false condition, continue-on-error: true or an unreviewed shell override before the run block. Each requires the exact PR admission step execution-policy drift diagnostic.

### Why safe
- Only the existing read-only CI-bound workflow permission negative harness and in-memory PR workflow fixtures changed. The actual PR/publisher workflows, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- A mandatory CI gate requires both live command reachability and an enabled, failure-propagating workflow step. Validate the complete reviewed step header before treating command order as proof of admission.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the reviewed PR admission step header changes or an observed step-level skip/error-mask bypass escapes the bounded negative guard.


## 2026-10-24 — PR deterministic snapshot drift rejection must remain an executable fatal gate

### Outcome
- Commit d55e46c9757f0a7d73384ddfb82d7bca4e42ee16 binds the strict OPS-P0-007 PR deterministic snapshot drift rejection to its reviewed enabled, fail-closed step rather than a textual occurrence of git diff.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40007135504 completed SUCCESS at this commit.

### Evidence
- The prior PR permission negative checked for the drift command's substring but did not prove that the final drift-rejection step actually executed it and propagated failure. A comment or echo containing the command, a disabled step, or continue-on-error could leave the workflow apparently green despite a changed deterministic snapshot.
- Eight step-scoped synthetic mutations now replace the diff with echo, remove the clean-worktree check, disable/mask the step, alter its shell, insert an early exit or broad staging, or duplicate the named step. Every mutation must produce the exact PR drift-rejection step authority-drift diagnostic.

### Why safe
- Only the existing CI-bound read-only workflow permission negative harness and in-memory PR workflow fixtures changed. The PR and publisher workflows, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- A deterministic drift gate must be proven as an enabled, fatal, reviewed step with an exact command sequence. Mutate a unique named-step block rather than globally matching shell commands repeated elsewhere in the workflow.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the reviewed PR deterministic drift step changes or a newly observed step-level skip/error-mask bypass escapes this exact-step guard.


## 2026-10-24 — PR admission cannot rely on a disabled or non-fatal validation job

### Outcome
- Commit 2255e4d37e8f57cbe30d10b1053df1205703d422 binds the strict OPS-P0-007 PR validation to its reviewed enabled job header and rejects job-level skip, failure-masking or runner drift.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40007333281 completed SUCCESS at this commit.

### Evidence
- Earlier guards required a live source-verification step, validator step and deterministic drift-rejection step, but did not require the enclosing validate job to remain enabled and fatal. A job-level if: false or continue-on-error could defeat all three step-local guards without changing their text.
- Seven synthetic mutations now insert job-level if: false, continue-on-error, unreviewed needs, runner change, invalid timeout, removed steps or duplicate validate job. Each must produce the exact PR job execution-policy drift diagnostic.

### Why safe
- Only the existing CI-bound read-only workflow permission negative harness and in-memory workflow fixtures changed. The PR and publisher workflows, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- CI gate reachability is hierarchical: validate the job-level execution/failure policy in addition to each required step and command. A correctly written validator is not authoritative when its enclosing job is skipped or non-fatal.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the reviewed PR job execution architecture changes or a newly observed job-level skip/failure-mask bypass escapes the bounded guard.


## 2026-10-24 — PR admission must have a real event trigger and complete critical path coverage

### Outcome
- Commit 403a641caf76a95138d5da72753633fd22a6030a binds the strict OPS-P0-007 PR admission to a real pull_request event and path-filter coverage for the reviewed workflow files, snapshot/status authorities, backup/restore evidence scope and all publisher revalidation-chain validators.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40007499012 completed SUCCESS at this commit.

### Evidence
- The prior PR guard searched for pull_request: anywhere in the workflow but did not prove that it was the actual event trigger, or that the path filter included all critical validator and authority inputs. A comment-only trigger or removed validator path could silently prevent PR checks from running on relevant changes.
- Eight synthetic mutations replace the trigger with workflow_dispatch or pull_request_target, add an unreviewed push event, remove the paths key or critical status/generator/negative-guard paths, or duplicate a path. Every mutation requires the exact PR trigger/path authority-drift rejection.

### Why safe
- Only the existing CI-bound read-only workflow permission negative harness and in-memory workflow fixtures changed. The PR/publisher workflows, Production Status, strict snapshot, registries, evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- CI reachability is an authority chain from event trigger and path filters through enabled job, enabled steps and executable validators. Validate each link; command presence cannot prove that the workflow will run for a changed authority.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the reviewed PR trigger/path architecture changes or a newly observed missing-path event bypass escapes this bounded guard.


## 2026-10-24 — PR path filters must cover every typed recovery authority contract

### Outcome
- Commit d50f7e4b8aca12aedd1291fd59f6eab94458b38f extends the strict OPS-P0-007 PR trigger guard to require thirteen reviewed environment-generation, eligibility, recovery-objective, drill-request, generation-evidence and typed non-resurrection contracts, registries and schemas.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40007628427 completed SUCCESS at this commit.

### Evidence
- The initial event/path guard protected the core snapshot/status, workflows, evidence directory and executable validator chain, but did not explicitly require each typed recovery authority contract or registry in the PR path filter. Removing a registry path could suppress the PR admission workflow for a change to that authority alone.
- Thirteen new negative fixtures each remove one distinct required contract/registry/schema path and demand the exact PR trigger/path authority-drift rejection. The canonical path filter remains a positive control.

### Why safe
- Only the existing read-only CI-bound workflow permission negative harness and in-memory path-filter fixtures changed. The actual PR/publisher workflows, Production Status, strict snapshot, registries, evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Trigger coverage must include every authority that feeds eligibility, approved objectives, reviewed requests, generation evidence and eight-domain non-resurrection review. Enumerate required inputs in a bounded constant and prove each omission is rejected individually.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the reviewed typed recovery authority set changes or a newly observed path-filter omission escapes the bounded contract negative suite.


## 2026-10-24 — Snapshot publisher job must be enabled and fatal

### Outcome
- Commit 0583431ea419cb564fe11f2beaa79a43af627d50 extends the strict OPS-P0-007 publisher workflow negative to require its reviewed enabled, failure-propagating validate job header.
- Exact-source OPS P0 007 Snapshot Permission Boundary run 40007739191 completed SUCCESS at this commit.

### Evidence
- The publisher guard previously verified the initial SOURCE_SHA capture, status propagation, bounded latest-source reconcile, diagnostic publication and protected shell steps but did not reject a job-level if: false or continue-on-error. A skipped or non-fatal job could leave all executable-looking step text intact without proving the publication checks ran.
- Seven synthetic mutations disable the job, mask its failure, add an unreviewed needs dependency, change the runner or timeout, remove steps, or duplicate validate. Each must produce the exact publisher job execution-policy drift diagnostic.

### Why safe
- Only the existing CI-bound read-only workflow permission negative harness and in-memory publisher fixtures changed. The actual publisher and PR workflows, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Verify publisher gate reachability from enabled fatal job to protected steps, executable validators, captured failure status, bounded reconcile and CAS publication. Job-level skip/masking cannot be ignored merely because the step bodies remain present.

### Protected-authority check
- Production Status blob ce67e9353d6583e4eaf792470563cad25a7396b3 remains NO_GO; strict OPS-P0-007 snapshot blob dbaa36b082366737dca2461d15748103b9740ef6 remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob 87712ea9c0e1d25dea1565f34b1c21a2b2d276db remains unchanged. Independent review and separate human promotion remain mandatory.
- This append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Retry condition
- Revisit only if the reviewed publisher job architecture changes or a newly observed job-level skip/error-mask bypass escapes this bounded guard.

## 2026-10-24 — PR py_compile stage requires executable exact-file binding and indentation-aware negatives

### Symptom
- The first compile-stage hardening commit `32a12df6b3fd9da7d16e5bed3cdff1801879b1e4` failed OPS P0 007 Snapshot Permission Boundary run `40010496516`.

### Evidence
- The exact-source CI log reported `OPS-P0-007 SNAPSHOT WORKFLOW PERMISSION NEGATIVE FAILED: reordered arguments compile fixture mutation was a no-op`.
- The reviewed PR workflow indents compile arguments by twelve spaces, while the synthetic reorder fixture used ten. Individual substring mutations matched from within the longer indentation, but concatenated adjacent-argument replacement could not match.
- The corrected commit `572fe4d4f98cad2f24fcd6cbd41961c23b249f4a` completed exact-source Snapshot Permission Boundary run `40010578092` with SUCCESS.

### Root cause or unknown
- Verified: fixture anchors omitted the additional two YAML continuation spaces. This was a test-harness mutation-construction failure, not observed recovery evidence or a production validator failure.

### Failed approach
- Constructing adjacent argument replacement from stripped YAML indentation and assuming it would match the reviewed workflow's physical command lines.

### Correction
- Match the canonical twelve-space continuation indentation in first/second/last compile argument fixtures, and preflight the adjacent-argument replacement against the actual step body before writing.
- Preserve the compile guard in the existing CI-reachable workflow permission negative harness; do not modify the reviewed PR workflow.

### Recurrence guard
- The existing executable negative harness now binds the complete PR admission run body: fail-closed shell startup, one exact `python -m py_compile` invocation, all 23 reviewed files in order with physical continuation syntax, and the exact subsequent validator chain.
- Eleven isolated mutations cover omitted, comment-only, aliased, reordered, masked, extra, interrupted, moved, duplicated or early-exited compilation. Each must produce the exact compile-stage authority-drift diagnostic.
- Fixture anchors must match actual YAML indentation and be proven to produce a non-no-op mutation before accepting the negative as proof.

### Retry condition
- Do not rerun the broken `32a12df` fixture or reuse stripped-indentation adjacent anchors. Revisit only if the reviewed compile command shape or required script list changes, or a new observed compile bypass escapes this bounded guard.

### Outcome
- Exact-source Snapshot Permission Boundary run `40010578092` passed at `572fe4d4`. The separately triggered Snapshot Readonly run is not counted as successful unless its own completed result is observed.

### Why safe
- Only the existing read-only, CI-invoked permission negative script and its in-memory PR workflow fixtures changed. No production evidence, recovery generation, objective, drill request, credential, traffic, readiness or promotion authority was created or altered.

### Reusable mechanism
- Treat compile checks as a separate live execution boundary, not as proof that validators ran. Bind exact arguments and continuation lines to a named enabled step, and independently bind runtime validator execution. Scope multi-line mutation anchors to physical YAML indentation and exact step boundaries.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable requests, generation recovery evidence, complete typed eight-domain non-resurrection records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Distinct eligible environments, explicitly human-approved current recovery objective, executable reviewed request binding, independent review and separate human promotion remain mandatory.
- This append-only lesson is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-24 — Publisher compile stage must retain exact files and captured nonzero status

### Outcome
- Commit `97a0d8df03ae83f840f346389d4dbeaa3df05881` adds an exact publisher compile-stage authority guard and twelve focused synthetic negatives to the existing read-only permission negative harness.
- Exact-source OPS P0 007 Snapshot Permission Boundary run `40010748076` completed SUCCESS. The separate Snapshot Readonly run is not counted as successful without its own completed result.

### Evidence
- The reviewed publisher intentionally uses `set +e` for bounded status capture: compile failure must flow through `>> "$log" 2>&1 || code=$?` before any subsequent conditional validator.
- The earlier capture guard required only textual presence of `python -m py_compile` and the redirect, not the exact twenty-two compile files, continuation lines, adjacency, or status-reset absence.
- The new guard checks the complete named capture run body against the reviewed startup, exact compile arguments, failure capture, fourteen conditional validators and final status publication.
- Twelve isolated mutations remove, comment, replace, reorder, duplicate or interrupt compile arguments, remove/mask capture, add unreviewed files or reset status. Each must produce the exact compile-stage authority-drift diagnostic.

### Why safe
- Only the existing CI-reachable read-only workflow permission negative script and in-memory workflow fixtures changed. The publisher workflow, Production Status, OPS-P0-007 snapshot, registries, recovery evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- For intentional `set +e` capture steps, prove the compile command's exact physical arguments and failure propagation together; checking only the presence of a compile command and a separate `code=$?` fragment is insufficient.
- Reuse the reviewed PR compile file tuple for the publisher's common twenty-two files, with the PR-only permission negative excluded from the publisher's own compile stage. Keep compile checks distinct from executed recovery admission validators.
- Scope every mutation to the unique named publisher step and its physical twelve-space YAML argument indentation; require non-no-op mutations and exact diagnostic binding.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct semantically eligible environments, explicit human-approved current recovery objective, executable reviewed request, independent review and separate non-automatic human production promotion remain mandatory.
- Learning and CI outcomes do not satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed publisher capture command sequence or compile input list changes, or an observed status/compile bypass escapes the bounded negative proof.

## 2026-10-24 — PR admission must reject unreviewed Actions steps and setup drift

### Outcome
- Commit `c0b540fe02ec9e94d8fe335b0e5186a439b9c7c7` adds a five-step allowlist for the strict OPS-P0-007 PR admission workflow, with eleven synthetic step-boundary negatives.
- Exact-source OPS P0 007 Snapshot Permission Boundary run `40010930195` completed SUCCESS. A separate Snapshot Readonly run is not treated as successful without its own completed result.

### Evidence
- Existing guards verified the checkout ref, enabled validator job and individual run steps, but did not reject an additional `uses:` step or changes to the Python setup action/version before admission.
- The new guard requires exactly the reviewed checkout@v4 with exact PR-head ref and full fetch depth, setup-python@v5 with Python 3.12, and the three named run steps in the reviewed order.
- Eleven negative mutations add unreviewed action/run steps, alter setup or checkout inputs, disable/mask setup, duplicate or reorder steps, or rename source verification. Each requires the exact step-allowlist drift diagnostic.

### Why safe
- Only the existing CI-bound read-only workflow permission negative harness and in-memory workflow fixtures changed. The actual PR/publisher workflows, Production Status, strict snapshot, registries, evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- CI reachability is hierarchical: the event and job may be valid while an extra unreviewed `uses:` action executes outside the protected run-step set. Bind the complete reviewed step inventory and action inputs as well as validator command bodies.
- Keep step mutations in-memory and require exact guard-specific rejection; do not weaken protected workflow permissions or promote CI outcomes into production evidence.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Independent review and separate human promotion are mandatory; this learning entry cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed PR step/action architecture changes or an observed unreviewed step bypass escapes the bounded allowlist.

## 2026-10-24 — Publisher must reject unreviewed Actions steps and altered failure branches

### Outcome
- Commit `b5980a3cd766cfc10d64e4bff5e5a616542e0962` adds an exact seven-step allowlist and fourteen focused negative mutations to the existing strict OPS-P0-007 publisher permission harness.
- Exact-source OPS P0 007 Snapshot Permission Boundary run `40011062682` completed SUCCESS. The separately triggered Snapshot Readonly run is not counted as successful until completed.

### Evidence
- Existing publisher guards verified the enabled job, checkout ref, source capture, validator chain, conditional commit, diagnostics and final status fragments, but did not reject an extra `uses:` action or changes to setup-python action/version outside those protected bodies.
- The new guard binds the exact checkout and Python setup steps, source capture, generation/captured status step, mutually exclusive successful snapshot commit and failed-run diagnostic branches, and the final strict status enforcement.
- Fourteen in-memory mutations add unreviewed action/run steps, weaken setup or checkout, duplicate/reorder steps, disable capture/generation, mask commit/diagnostic failures, invert diagnostic branching or remove/forge final enforcement. Each must emit the exact publisher step-allowlist drift diagnostic.

### Why safe
- Only the existing read-only CI-bound workflow permission negative harness and synthetic publisher workflow text changed. The actual publisher/PR workflows, Production Status, strict snapshot, registries, evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- A publisher may have correct status-capture commands but still execute unreviewed actions or skip the required terminal failure gate. Bind the entire reviewed step inventory and exact conditional branch headers in addition to the executable commands.
- Keep production promotion separate from snapshot publication. Exact-source CI checks are guard execution evidence only, never recovery or production readiness evidence.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain non-resurrection records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Distinct semantically eligible environments, explicit human-approved current recovery objective, executable reviewed request binding, independent review and separate human promotion remain mandatory.
- Learning records and CI guard successes do not satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed publisher step inventory, action inputs, conditional publication branches or final enforcement change, or a new observed bypass escapes the bounded allowlist.

## 2026-10-24 — Publisher push trigger must cover every reviewed recovery authority path

### Outcome
- Commit `b7f360ae50d6f94799c51653959b0045362a1159` adds a publisher event/path authority guard with forty required path-removal negatives and eight event/selector mutation negatives.
- Exact-source OPS P0 007 Snapshot Permission Boundary run `40011230172` completed SUCCESS. The separate Snapshot Readonly run is not counted as successful until completed.

### Evidence
- The previous publisher guard rejected pull-request events textually but did not prove that the actual `on.push.branches` selected `so` or that every typed generation/objective/request/evidence contract, registry, schema and executable validator path triggered publication.
- The reviewed publisher has one `so` push event with forty required paths and an explicit manual dispatch event. The new guard binds the complete header through the reviewed `contents: write` scope, preserving the existing publication authority.
- Forty synthetic fixtures remove one required path each; eight additional fixtures weaken the push event, branch/path selectors, manual dispatch or introduce an unreviewed schedule/duplicate path. Every fixture requires the exact publisher trigger/path drift diagnostic.

### Why safe
- Only the existing CI-bound read-only permission negative harness and in-memory publisher trigger fixtures changed. The actual publisher/PR workflows, Production Status, strict snapshot, registries, recovery evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Trigger reachability is distinct from command execution: a perfectly guarded validator cannot publish a deterministic projection when its workflow never runs for a relevant changed authority.
- Reuse the reviewed typed recovery contract set and shared compile-script list to bind path filters, and require each omission to fail closed. The workflow itself retains its existing write scope; negative checks never grant production readiness.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct semantically eligible environments, explicit human-approved current recovery objective, executable reviewed request, independent review and separate human promotion remain mandatory.
- Learning and CI guard successes do not satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed publisher trigger architecture or typed recovery authority path set changes, or a new observed trigger-coverage bypass escapes this bounded guard.

## 2026-10-24 — PR trigger coverage must include all twenty-three compiled admission scripts

### Outcome
- Commit `94da8e6b8a06d712081fcefe594e181576542578` extends the existing strict OPS-P0-007 PR trigger/path guard to require every one of the twenty-three reviewed `py_compile` inputs.
- Exact-source OPS P0 007 Snapshot Permission Boundary run `40011380488` completed SUCCESS. The separately triggered Snapshot Readonly run is not counted as successful until completed.

### Evidence
- The prior PR trigger guard covered the four core admission validators, fourteen publisher revalidation-chain validators, typed recovery contracts and core status/negative paths, but did not require every compiled support script to trigger PR admission when changed.
- The reviewed PR workflow includes all twenty-three compile inputs in its path filter. The extended guard reuses the exact compile-file tuple and adds one cause-specific missing-path negative for each script, requiring the canonical trigger/path drift diagnostic.

### Why safe
- Only the existing CI-reachable read-only workflow permission negative harness and in-memory path-filter fixtures changed. The actual PR/publisher workflows, Production Status, strict snapshot, registries, evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Bind CI trigger coverage to every compiled source input, not only to executable validator entrypoints; a support-script change must not bypass the PR admission gate.
- Reuse the single reviewed compile-file tuple rather than maintaining a second divergent script list. Negative fixtures must remove exactly one path and prove exact-diagnostic rejection.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain non-resurrection records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Independent review and separate human production promotion remain mandatory. Learning/CI records never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed compiled input set or PR path-filter architecture changes, or a new observed missing-script trigger bypass escapes the bounded negative proof.

## 2026-10-24 — Independent readonly workflow must retain source-bound immutable validation

### Symptom
- First implementation commit `d26504c5afe34b725718ffc081fc0a5d5ba33bdd` failed both exact-source Snapshot Permission Boundary run `40011653431` and Snapshot Readonly run `40011653410` during Python compilation.

### Evidence
- Permission Boundary job log reported `SyntaxError: invalid syntax` at the generated `expected="` literal containing `github.event_name == 'pull_request'`.
- The new guard was generated by replacing a placeholder inside a single-quoted Python string. The replacement introduced an unescaped inner `'pull_request'`, terminating that string.
- Correction commit `113f99c4bc0093c9d16a2e5135f15466a1c5727c` completed exact-source Snapshot Readonly run `40011754630` with SUCCESS; its job log confirms workflow permission negative PASS and `production decision: NO_GO`.
- The separate Permission Boundary run `40011754620` was not yet complete when this entry was written; do not count it as SUCCESS without a completed result.

### Root cause or unknown
- Verified: cross-language string generation inserted a single-quoted GitHub expression into a Python single-quoted string literal. The repository had no production evidence or runtime authority failure; this was generated source syntax corruption.

### Failed approach
- Blindly substituting a GitHub Actions expression containing quote characters into a Python literal without preserving the literal's quoting boundary.

### Correction
- Capture the GitHub Actions source expression once in the double-quoted `READONLY_SOURCE_REF` constant and concatenate it into the expected shell command, avoiding nested Python single-quote parsing.
- The corrected canonical source compiled and the independent readonly workflow executed the full negative suite successfully.

### Recurrence guard
- The existing CI-reachable permission negative harness now validates the separate readonly workflow's read-only token, enabled fatal job, exact checkout/source ref and Python setup, three reviewed steps, source cleanliness, paired authority snapshots, six compiled/runtime validators and final diff/worktree checks.
- Eleven isolated mutations cover write permissions, disabled/nonfatal job, extra action, disabled run step, setup drift, compile echo, missing negative, missing/masked diff and early exit. Each must trigger the exact readonly-workflow authority-drift diagnostic.
- For future generated Python source containing GitHub `'pull_request'` expressions, bind the expression through a separately quoted constant rather than interpolating it inside a single-quoted literal. Confirm `py_compile` in exact-source CI before claiming executable proof.

### Retry condition
- Do not rerun the broken `d26504c` generated literal. Revisit only if the readonly workflow's reviewed execution shape changes or a newly observed bypass escapes the bounded guard.

### Outcome
- Exact-source Snapshot Readonly run `40011754630` completed SUCCESS with canonical workflow permission negative PASS and `NO_GO`. Permission Boundary run status remains separately attributable.

### Why safe
- Only the existing CI-invoked read-only negative script and in-memory readonly workflow fixtures changed. The actual readonly/PR/publisher workflows, Production Status, strict snapshot, registries, real evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- A second independent readonly workflow is a useful cross-check only if its own job, steps, compile/runtime validators and authority-drift checks remain executable and fatal. Validate that workflow explicitly rather than assuming a previous CI run proves future wiring.
- Keep all negative mutations in memory, distinguish compile from runtime invocation, and preserve independent exact-source CI attribution.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct semantically eligible environments, explicitly human-approved current recovery objective, executable reviewed request, complete typed eight-domain coverage, independent review and separate human promotion remain mandatory.
- Learning and CI guard successes are not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-24 — Independent readonly snapshot gate needs PR and so-push trigger coverage

### Outcome
- Commit `77ac84e209f323be17f3682cc76c3bc7ffa9cb55` binds the independent readonly workflow's PR, `so` push and manual-dispatch event header to its fourteen reviewed trigger paths on both automatic events.
- Exact-source OPS P0 007 Snapshot Permission Boundary run `40012059629` completed SUCCESS. The separate Snapshot Readonly run is not counted as successful without its own completed result.

### Evidence
- The prior readonly execution guard proved the job, checkout, immutable authority snapshots and validators, but did not prove that changing an input would actually trigger that workflow.
- The new guard requires all fourteen reviewed paths in each of the PR and push filters, the exact `so` push branch selector, and the reviewed manual dispatch event.
- Twenty-eight isolated path-removal mutations and eight event/selector mutations must emit the exact readonly trigger/path drift diagnostic.

### Why safe
- Only the existing CI-bound read-only workflow permission negative harness and in-memory readonly workflow fixtures changed. The actual readonly/PR/publisher workflows, Production Status, strict snapshot, registries, recovery evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Independent CI is only meaningful when both its executable gate and its trigger coverage remain intact. Bind both PR and push path filters to the same reviewed fourteen-input set, then prove each missing path fails closed without creating a parallel production authority.
- Trigger validation and runtime validator invocation are separate requirements; neither can substitute for the other or for real recovery evidence.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct semantically eligible environments, explicit human-approved current recovery objective, executable reviewed request, independent review and separate human production promotion remain mandatory.
- Learning/CI successes cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed readonly workflow trigger architecture or required input set changes, or an observed missing-trigger bypass escapes the bounded negative suite.

## 2026-10-24 — Every snapshot corruption negative must have an exact diagnostic mapping

### Outcome
- Commit `37f81767fed1f50ab19c09c122f67ecc7d06080b` removes the fallback that allowed a new snapshot corruption case to count as successful negative proof merely because any canonical rejection occurred.
- Exact-source OPS P0 007 Admission Snapshot Readonly run `40012220075` completed SUCCESS. Its job log reports strict snapshot negative validation PASS, twenty-two controlled validator corruption cases rejected, workflow permission negative PASS and `production decision: NO_GO`.

### Evidence
- The existing snapshot negative runner used `CASE_SPECIFIC_VALIDATOR_REJECTIONS.get(label)` and skipped exact diagnostic verification for an unmapped label. A newly added case could therefore be rejected for an unrelated canonical error and still count as a passing negative.
- The current mapping has twenty-four unique labels: twenty-two registry/snapshot/status corruption cases and two source/module symlink escape cases. The new guard requires exact set equality and fails closed on unknown labels before treating a validator rejection as expected.
- Two synthetic unknown-label classifier controls require the precise missing-mapping diagnostic. Existing exact-diagnostic and output/exit controls remain intact.

### Why safe
- Only the existing CI-reachable strict snapshot corruption negative suite changed. It exercises isolated/restored canonical authority mutations but does not create production evidence, recovery generations, objectives, executable drills, credentials, traffic, readiness or promotion authority.
- Production Status, strict snapshot, typed registries and actual workflows were not changed by this commit.

### Reusable mechanism
- Negative test registration must be closed over its expected diagnostic map. Require both complete coverage and absence of stale labels; never silently fall back to generic fail-closed prefixes for new cases.
- Keep positive baseline, exact exit status, empty contradictory stdout, no traceback, exact stderr and protected bytes/modes checks separate from the case-map completeness proof.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct eligible environments, explicitly human-approved current recovery objective, current executable reviewed request, complete typed eight-domain coverage, independent review and separate human production promotion remain mandatory.
- This learning and CI evidence cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only when a new reviewed corruption case is added, an existing expected canonical diagnostic changes, or an observed unrelated failure escapes the strict mapping.

## 2026-10-24 — Generator corruption cases require complete exact diagnostic bindings

### Outcome
- Commit `114819dbd33140669445993ad03d67a56eeefbc8` requires every real generator corruption negative to have an explicit exact or nested canonical diagnostic mapping.
- Exact-source OPS P0 007 Admission Snapshot publisher run `40012416362` completed SUCCESS; its job log reports strict snapshot negative validation PASS, three controlled generator corruption cases rejected and `production decision: NO_GO`.
- The separate Snapshot Readonly run was not yet complete at this entry and is not counted as successful without a completed result.

### Evidence
- The existing generator rejection classifier intentionally supports exact one-line source/module path diagnostics and exact two-line typed-admission nested diagnostics, but `run_generator_rejects` previously allowed a new unknown label to use generic allowed-prefix matching.
- The new guard closes that fallback for actual generator negative execution: the three nested corruption labels and two exact symlink labels must form the complete disjoint five-label set.
- Two synthetic unknown-label controls demand the precise missing-binding rejection. Existing baseline, output, timeout, unchanged-snapshot and canonical diagnostic classifiers remain intact.

### Why safe
- Only the existing CI-invoked snapshot corruption negative harness changed. It does not modify production evidence, recovery generations, objectives, executable drill requests, credentials, traffic, readiness or promotion authority.
- The real publisher workflow, Production Status, strict snapshot, registries and typed eight-domain review requirements were not changed.

### Reusable mechanism
- Treat diagnostic classification as a closed registry for actual negative execution: no new generator case may silently fall back to generic prefix matching. Keep separate exact and nested maps disjoint, and assert the set equals the reviewed cases plus explicit symlink tests.
- Synthetic classifier probes may exercise generic parser behavior, but actual corruption tests must always bind to a known exact diagnostic label.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain non-resurrection records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct semantically eligible environments, explicitly human-approved current recovery objective, current executable reviewed request, independent review and separate human production promotion remain mandatory.
- Learning and CI success never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Existing scoped blocker observed
- Backup Restore Admission Chain Negative run `40012416291` failed with the already-recorded `source-binding negative requires clean canonical source worktree` diagnostic. The retry condition has not changed; do not repeat the same blocked fix. Independent snapshot guard work remains safe.

### Retry condition
- Revisit generator diagnostic bindings only when a reviewed corruption case or canonical exact/nested diagnostic changes, or an observed unrelated failure escapes the mapping. Revisit the separate clean-worktree blocker only after its recorded precondition changes.

## 2026-10-24 — Readonly authority digest coverage must include all nine protected files

### Outcome
- Commit `5d99460e6dc3f74899fa000869151f383baa41c9` binds the independent OPS-P0-007 readonly workflow's before/after byte-digest and mode snapshot to the exact nine reviewed protected authority files.
- Exact-source OPS P0 007 Snapshot Permission Boundary run `40012850471` completed SUCCESS. The separately triggered Snapshot Readonly run is not counted as successful without its own completed result.

### Evidence
- The prior readonly workflow guard verified two authority-snapshot loops and final diff checks but did not validate the contents of the `authorities=(...)` list. Removing Production Status, the typed non-resurrection registry or the human promotion-review registry could silently narrow the immutable-authority proof while leaving both loops intact.
- The new guard requires exactly the reviewed nine-file list, including snapshot, admission inventory, Production Status, generation/objective/drill/evidence/non-resurrection registries and the separate promotion-review registry.
- Nine isolated missing-authority mutations each require the exact readonly-workflow authority-drift diagnostic.

### Why safe
- Only the existing read-only CI-bound workflow permission negative harness and in-memory readonly workflow fixtures changed. The actual readonly workflow, Production Status, strict snapshot, registries, recovery evidence, credentials, traffic, readiness and promotion authority were untouched.

### Reusable mechanism
- A before/after digest-and-mode comparison is only as strong as its protected input list. Bind the complete list to reviewed authority paths and reject each omission independently, especially the separate human promotion authority.
- Keep authority integrity evidence distinct from production recovery or promotion evidence; a clean CI digest comparison never satisfies recovery gates.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct semantically eligible environments, explicit human-approved current recovery objective, executable reviewed request, independent review and separate human production promotion remain mandatory.
- Learning and CI success cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed protected authority list changes or an observed missing-file integrity bypass escapes this bounded guard.

## 2026-10-24 — Readonly before/after snapshots must hash actual bytes and file modes

### Outcome
- Commit `4192db1e9545860d27cf06c0c3ed0914f15694a8` binds both readonly authority-snapshot loops to the reviewed file-existence check, SHA-256 content digest, filesystem mode extraction and distinct before/after output files.
- Exact-source OPS P0 007 Snapshot Permission Boundary run `40013017011` completed SUCCESS. The separate Snapshot Readonly run is not counted as successful without its own completed result.

### Evidence
- The previous readonly guard required two `for authority` loops and `done > "$snapshot"`/`done > "$current"` but did not prove that each loop actually hashed bytes and modes. Replacing `sha256sum` or `stat` with a constant could make a drift comparison pass falsely.
- The new guard checks exact reviewed loop command sequences: the first loop checks file existence and records content hash/mode; the second independently records the same hash/mode fields for comparison.
- Five synthetic mutations forge content digests, forge modes, comment/mask hash commands or remove the existence check. Each must produce the exact readonly-workflow authority-drift diagnostic.

### Why safe
- Only the existing read-only CI-bound workflow permission negative harness and in-memory readonly workflow fixtures changed. The real readonly/PR/publisher workflows, Production Status, strict snapshot, registries, recovery evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- A protected-file list and two output files are not enough: bind the actual hashing, mode extraction, existence check and output redirection commands before treating a diff as integrity evidence.
- Use exact command-shape negatives rather than assuming the presence of `sha256sum` text proves execution. Preserve separation between CI integrity proof and production recovery/promotion authority.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct semantically eligible environments, explicit human-approved current recovery objective, executable reviewed request, independent review and separate human production promotion remain mandatory.
- Learning/CI outcomes do not satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed readonly hash/mode comparison architecture changes or an observed forged integrity comparison escapes the bounded guard.

## 2026-10-24 — Readonly integrity gate must reject shell hooks and error masking

### Outcome
- Commit `334f776f4b0d2393b66cb596e82252ef2361e4da` strengthens the existing readonly workflow authority guard to reject shell traps, aliases, sourced scripts, option overrides and unconditional/conditional control-flow substitutions before validator execution.
- Exact-source OPS P0 007 Snapshot Permission Boundary run `40013158519` completed SUCCESS. The separate Snapshot Readonly run is not counted as successful without its own completed result.

### Evidence
- A readonly workflow can contain the correct compile, validator, digest and diff commands while an added ERR/EXIT trap, alias or sourced script changes their actual failure semantics. A `set -euo pipefail` prefix alone does not prove uninterrupted fail-closed execution.
- The new guard permits only the reviewed initial shell option line and the exact EXIT trap that removes the two temporary digest files; it rejects unreviewed command-resolution hooks and control-flow overrides.
- Ten isolated in-memory shell mutations, including forged-success traps, `source`, dot-source, Python alias, `shopt`, `set +e`, early exit, `eval` and a dead conditional, require the exact readonly authority-drift diagnostic.

### Why safe
- Only the existing CI-bound read-only workflow permission negative harness and synthetic readonly workflow text changed. The actual readonly/PR/publisher workflows, Production Status, strict snapshot, registries, recovery evidence, credentials, traffic, readiness and promotion authorities were untouched.

### Reusable mechanism
- Treat fail-closed shell behavior as a whole-step property. Require exact startup options and only explicitly reviewed cleanup traps, then prove that later shell hooks and conditional wrappers cannot silently replace validator execution or failure propagation.
- CI integrity checks are not production recovery evidence or promotion approval.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct eligible environments, explicit human-approved current recovery objective, executable reviewed request, independent review and separate human production promotion remain mandatory.
- Learning/CI successes never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Revisit only if the reviewed readonly shell execution architecture changes or an observed failure-masking shell hook escapes this bounded guard.

## 2026-10-24 — Post-write rollback rejection must bind the exact observed atomic-write diagnostic

### Symptom
- Initial exact-diagnostic hardening commit `48271b98d467113cbf6384f21c1b408afb679220` failed exact-source Snapshot Post Write Rollback Negative run `40013364654`.

### Evidence
- The job log reported `post-write rollback rejected outside exact canonical diagnostic` with the actual complete message:
  `generated strict snapshot invalid: snapshot field set drift; rollback incomplete: cannot atomically write contracts/operations/ops-p0-007-admission-snapshot.v1.json: synthetic strict snapshot rollback replace rejection`.
- The first guard expected the primary validation message and injected rollback exception but omitted the generator's canonical `cannot atomically write <relative path>:` wrapper.
- Correction commit `5d15181cfa476c3e0faa0f0206525429d0e3227e` completed exact-source Snapshot Post Write Rollback Negative run `40013510857` with SUCCESS.

### Root cause or unknown
- Verified: the negative fixture assumed the raw injected `OSError` text would be the rollback diagnostic. The generator's atomic-write helper wraps the error with the canonical destination path before the outer rollback-incomplete message is constructed.

### Failed approach
- Inferring the final rollback diagnostic from the outer exception formatter without observing the inner atomic-write helper's exception wrapper.

### Correction
- Bind the failed-rollback expectation to the exact full diagnostic observed in run `40013364654`, including the canonical snapshot path and `cannot atomically write` wrapper.
- Preserve the successful-rollback primary diagnostic `generated strict snapshot invalid: snapshot field set drift` as a separate exact expectation.

### Recurrence guard
- The existing CI-reachable post-write rollback negative now requires exact primary and failed-rollback diagnostics, rather than accepting three unrelated substrings anywhere in the exception.
- Synthetic classifier controls reject unrelated prefixes/suffixes, incorrect primary causes and multiline impostors for both cases.
- The existing two atomic-replace scenarios, invalid published candidate proof, canonical bytes/modes restoration, temporary-file cleanup and Production Status immutability remain enforced.

### Retry condition
- Do not reuse the raw-OSError-only expectation. Revisit only if the reviewed generator's atomic-write diagnostic changes or a newly observed unrelated rollback failure escapes the exact classifier.

### Outcome
- Exact-source Snapshot Post Write Rollback Negative run `40013510857` completed SUCCESS at `5d15181c`. The negative's real post-write failure/rollback scenarios executed; this is CI guard evidence, not a production restore drill.

### Why safe
- Only the existing CI-bound post-write rollback negative script and its controlled in-memory/temporary failure injections changed. The actual generator, Production Status, strict snapshot, recovery registries, credentials, traffic, readiness and promotion authorities were not committed or promoted.

### Reusable mechanism
- For layered error handling, capture the final observed canonical diagnostic at the exact-source CI boundary. An injected inner exception may be wrapped by atomic-write, validator or rollback layers before reaching the caller.
- Bind full messages only after observation; keep primary validation failure and rollback failure separately visible and require exact output shape.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final recovery candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct semantically eligible environments, explicitly human-approved current recovery objective, executable reviewed request, complete typed eight-domain non-resurrection coverage, independent review and separate human production promotion remain mandatory.
- Learning/CI evidence does not satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Readonly step and job trailing YAML metadata must not bypass integrity gate

### Symptom and evidence
- The readonly workflow authority checker previously extracted only indented shell lines after the reviewed `run: |` header. It ignored later YAML step/job keys, so `continue-on-error: true` or `if: false` placed after the run scalar could make the workflow appear successful without a fatal integrity check.
- Initial commit `e88d54f7844e5dcbc66fd0a21e1383c7ecf2c023` added the structural guard but emitted doubled newline escapes in the synthetic YAML fixtures. The fixture did not model real newline-separated YAML metadata. Correction `d72cf5807b5367e842bbd8833cb61d3c26e182d9` replaced these with actual Python newline escapes.
- Independent, source-read structural control after correction: legitimate readonly shell body accepted (1/1); five trailing step/job metadata mutations rejected (5/5). The GitHub combined-status endpoint returned no statuses for `d72cf580`; exact-source GitHub Actions success has **not** been observed and is not claimed.

### Verified root cause or unknown
- Verified: the previous checker discarded non-shell YAML lines after the final run step, leaving an unguarded step/job metadata override. The first test fixture used an incorrect double-escaped newline representation. Canonical GitHub Actions execution of the correction remains unverified.

### Failed approach
- Treating shell-command presence alone as proof of fatal step/job execution; generating YAML mutation text with doubly escaped newlines instead of checking the resulting Python string and YAML line boundaries.

### Correction and recurrence guard
- The existing CI-reachable readonly workflow permission negative checker now rejects any nonblank line after the reviewed run header that is not within the ten-space shell block indentation.
- Five bounded negative fixtures append valid trailing YAML keys: step-level `continue-on-error`, `if`, `shell`, and job-level `continue-on-error`, `if`. Each must fail with the exact readonly authority-drift diagnostic; the unmodified workflow remains the positive control.
- Preserve canonical runtime checks and distinct negative proof. Do not treat independent structural tests as completed exact-source CI.

### Outcome, why safe and reusable mechanism
- Commits `e88d54f` and `d72cf58` modify only the existing CI-bound negative harness, not the actual workflow, snapshot, Production Status, registries, evidence or promotion authority.
- Reusable rule: after extracting a YAML block scalar, reject any trailing unreviewed step/job metadata; executable shell text alone does not guarantee a non-skipped, fatal CI gate. Use valid newline-separated mutation fixtures and exact diagnostic binding.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked, with no registered/eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain non-resurrection records or final candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Human-approved current recovery objective, unsuperseded semantically eligible generations from distinct environments, current executable reviewed request, complete typed eight-domain coverage, independent review and separate non-automatic human promotion remain mandatory.
- Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Retry condition
- Do not repeat the double-escaped YAML fixture. Revisit only after observing the exact-source CI outcome or a new bypass of the reviewed readonly step/job boundary. The separate known clean-worktree blocker remains unchanged and must not be retried on the same precondition.

## 2026-10-24 — Readonly validator commands must not be shadowed by shell functions or hash pins

### Outcome and observed evidence
- Commit `87e446ea9143284aef69ef298b631517574f159a` extends the existing readonly workflow permission negative guard to reject unreviewed POSIX/Bash function declarations and the shell `hash` builtin before validator execution.
- Source-read independent positive control: the current readonly workflow has no rejected function/hash override. Four bounded synthetic commands (`python() { :; }`, `git () { :; }`, `sha256sum() { echo forged; }`, `hash -p /bin/true python`) are rejected by the classifier (4/4). Exact-source GitHub Actions completion has not been observed; the commit's combined-status endpoint returned no statuses.

### Why safe and reusable mechanism
- Only the existing CI-bound negative harness changed. The actual workflows, canonical snapshot, Production Status, generation/objective/drill/evidence/non-resurrection registries, credential/traffic/readiness and promotion authorities remain untouched.
- Shell text containing `python script.py`, `git diff` or `sha256sum` is not execution proof if a prior function or hash pin changes command resolution. Require fail-closed command-resolution integrity as well as the reviewed command sequence, with independent negative fixtures bound to the exact readonly authority-drift diagnostic.

### Failure-class record
- Symptom: a syntactically intact readonly shell block could shadow Python, Git or hashing commands while preserving all reviewed command text.
- Evidence: the previous shell control regex rejected aliases, sourced files and option overrides but not `name() { ... }` function declarations or `hash -p`.
- Verified root cause: the control matcher covered only named shell builtins and did not cover function declarations or executable hash pinning. No actual production failure is claimed.
- Failed approach: assuming literal validator command strings imply execution of their intended executable without checking command-resolution overrides.
- Correction: reject shell function declarations and `hash` in the existing readonly shell execution policy.
- Recurrence guard: four bounded in-memory negative mutations, positive unmodified workflow, and exact diagnostic binding in the existing CI-reachable suite.
- Retry condition: revisit only after an observed unhandled command-resolution bypass or reviewed workflow command architecture change. Do not retry the unchanged separate clean-worktree blocker.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED`, with zero registered/eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Distinct semantically eligible environments, human-approved current recovery objective, current executable reviewed request, independent review, typed eight-domain coverage and separate human promotion remain mandatory.
- Learning and CI outcomes never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — PR and publisher run blocks must reject trailing step-level execution overrides

### Outcome and evidence
- Commit `4809dbfcfdbcba3444850b8b9fdaab8e48562aa0` extends the existing PR/publisher step allowlist to reject YAML metadata dedented after the reviewed `run: |` scalar, even when all required shell commands remain unchanged.
- Independent source-read positive controls accepted the canonical PR and publisher workflows (2/2). Six bounded trailing `if: false`, `continue-on-error: true` and custom `shell` mutations were rejected (6/6). These are structural classifier checks, **not** completed exact-source GitHub Actions CI; the combined-status endpoint returned no statuses.

### Symptom, root cause and failed approach
- Symptom: the previous PR and publisher allowlists checked step headers and filtered shell lines but could ignore a later YAML step property that disables or makes a critical step nonfatal.
- Evidence: both reviewed workflow source files have run blocks with no trailing step metadata; their previous validators did not constrain dedented lines after `run: |`. In-memory fixtures demonstrate the omitted boundary.
- Verified root cause: shell body extraction discarded valid YAML step-level overrides appearing after a run block. No actual production failure is claimed.
- Failed approach: treating a reviewed step header and exact shell command list as sufficient proof of fatal Actions step execution.

### Correction, recurrence guard and retry condition
- For each of the three PR run steps and four publisher run-block steps, require every subsequent nonblank line to remain within the ten-space shell scalar indentation. Keep the publisher's final inline enforcement step separately bound by its existing exact-step equality check.
- Add six CI-reachable negative fixtures requiring the exact PR/publisher step allowlist authority-drift diagnostic. Preserve both canonical positive controls.
- Revisit only when the reviewed workflow step architecture changes or a new valid YAML override escapes this guard. Do not repeat the known clean-worktree blocker without changed preconditions.

### Why safe and reusable mechanism
- Only the existing negative harness changed; neither actual workflow, snapshot, Production Status, recovery registry, evidence nor human promotion authority was written.
- Reusable principle: validate both executable shell commands and the surrounding GitHub Actions YAML step boundary; ordering of YAML mapping keys is not an execution guarantee.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`. OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. Distinct eligible environments, human-approved current recovery objective, current executable reviewed request, typed eight-domain non-resurrection coverage, independent review and separate human promotion remain mandatory.
- Learning/CI outcomes never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Publisher command-resolution guard must allow only the reviewed helper function

### Outcome and evidence
- Commit `94437c446b14009cffe4851df01bbb1214c2a464` extends the existing publisher protected-shell guard to reject `hash` executable pinning and shadow functions named `python`, `git`, `sha256sum` or `stat`.
- Independent source-read positive control accepted the reviewed `revalidate_latest_snapshot() {` helper and canonical publisher shell (PASS); four injected command-resolution overrides were rejected (4/4). The commit's GitHub combined-status endpoint returned no statuses, so no exact-source CI success is claimed.

### Failure-class record
- Symptom: a shell step may retain the exact reviewed validator/atomic-publish command text while invoking a shadow function or hash-pinned executable.
- Evidence: the previous publisher shell override guard covered `set`, `trap`, aliases and sourced scripts, but did not reject shadow function declarations or `hash -p`.
- Verified root cause: incomplete command-resolution policy for the protected publisher shell; no actual production incident is asserted.
- Failed approach: checking literal command lines without constraining the executable resolution that Bash applies to them.
- Correction: reject shadow declarations for the four protected executable names and the hash builtin, while explicitly retaining the existing reviewed revalidation helper.
- Recurrence guard: four bounded in-memory negative fixtures with exact publisher protected-shell diagnostic binding, plus the canonical positive control.
- Retry condition: revisit only if the reviewed publisher helper architecture changes or an observed command-resolution bypass escapes this bounded matcher. Do not retry the unchanged clean-worktree blocker.

### Why safe and reusable mechanism
- Only the existing CI-bound workflow permission negative harness changed. Actual publisher workflow, canonical snapshot, Production Status, recovery registries, evidence and separate human promotion authority were not modified.
- Reusable rule: when a reviewed shell function is necessary, prohibit shadowing of protected executables by name instead of banning all shell functions indiscriminately.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED`, with zero registered/semantically eligible generations, approved objectives, executable reviewed requests, generation recovery evidence, complete typed eight-domain records and final candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Distinct eligible environments, explicitly human-approved current recovery objective, current executable reviewed request, complete typed eight-domain coverage, independent review and separate human promotion remain mandatory.
- Learning/CI outcomes cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Generator rejection probes must preserve recovery registry identity

### Outcome and evidence
- Commit `bea92e9626daf1bd2b50c6594eda3596dccc1a32` extends the existing CI-bound generator execution-authority negative to protect six canonical recovery registries in addition to the strict snapshot, Production Status and generator.
- Source-read post-write verification found nine protected paths, three uses of the shared protected set (preflight, each rejected substitution and final comparison), and unchanged canonical snapshot/Production Status blobs. Exact-source Actions runs `40018062428` (readonly) and `40018062742` (publisher) were in progress at this observation; **CI success is not claimed**.

### Why safe
- Only the existing generator negative harness changed. In-memory helper/path substitutions are restored, while byte content, file inode/mode, parent identity and resolved path are compared. No registry, actual generator, production status, snapshot, evidence, credential, traffic, readiness or promotion authority was written.

### Reusable mechanism
- A negative proof must verify non-mutation of *all* recovery authority inputs it could conceivably affect, not only its immediate output. Centralize the protected-path set and require canonical non-symlink paths before executing failure injections; compare complete identity and bytes after each rejected probe and at suite completion.
- This is CI/test evidence only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Registered and semantically eligible generations remain distinct; unsuperseded eligible generations from distinct environments, explicit human-approved current objective, current executable reviewed request for new evidence, complete typed eight-domain non-resurrection coverage, independent review and separate human promotion authority remain mandatory.

### Retry condition
- Revisit this guard if an observed exact-source CI failure identifies a new required path/precondition, or a newly discovered mutation escapes the expanded protected-state comparison. Do not retry the unrelated unchanged source-binding clean-worktree blocker.

## 2026-10-24 — Atomic replacement failure must preserve all recovery registries and detect same-inode writes

### Outcome and evidence
- Commit `7ae3e6b411a984a20d2a4073fe49a339cea7a75b` extends the existing CI-bound atomic-write negative to protect the bytes, file/parent identity and resolved path of six recovery registries plus the snapshot, Production Status and generator.
- Commit `d17c82051b03ebb06e04ebc5e3211b878d2c7fb4` corrects the synthetic byte-drift fixture's newline escaping. Exact-source Atomic Write Negative run `40018252589` completed SUCCESS; job log shows `OPS-P0-007 strict snapshot atomic replacement negative proof: PASS` and `snapshot/status/generator/recovery registries bytes and identity unchanged: true`. Prior run `40018218456` also completed SUCCESS at the pre-correction source; it does not replace the corrected-source result.

### Failure: fixture newline escaping
- **Symptom:** The first new registry-byte fixture wrote literal backslash-n instead of the intended newline-terminated JSON sample. This was detected by post-write source inspection, not a CI failure.
- **Evidence:** Source at `7ae3e6b` contained two `\\\\n` escape sequences in Python byte literals; the first exact-source run succeeded because the test still mutated bytes, but its fixture representation was not faithful.
- **Root cause:** JavaScript-to-Python string serialization double-escaped the newline, repeating a previously documented fixture-generation failure class.
- **Failed approach:** Writing generated Python fixture literals without inspecting their final source representation before committing.
- **Correction:** Replace the two doubled escapes with canonical single `\\n` Python byte-literal escapes, preserving the byte-mutation assertion.
- **Recurrence guard:** Re-read the written source and assert that the intended two fixture lines have single escapes and no doubled escapes; require corrected-source CI success. Future generated fixtures must check serialized source before writing.
- **Retry condition:** Do not reuse the double-escape construction. Revisit only if a source-read fixture audit or exact-source CI identifies a new serialization mismatch.

### Why safe and reusable mechanism
- Only the existing atomic-failure negative harness changed. The failure injection remains scoped to one attempted atomic replacement; the source-read and CI postconditions prove canonical snapshot, Production Status, generator and six registry identities/bytes were unchanged.
- Compare both bytes and inode/parent/resolved-path identity: inode checks alone cannot detect an in-place rewrite. Use an isolated temporary same-inode content mutation as negative proof; do not mutate canonical registries.
- This test evidence is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Registered and semantically preflight-eligible generations are separate. Preflight still needs distinct unsuperseded eligible environments and human-approved current objective; new generation evidence requires current executable reviewed request; final candidates still need complete typed eight-domain non-resurrection coverage and independent review; human promotion remains separate and non-automatic.

## 2026-10-24 — Post-write rollback must not mutate recovery registry authority

### Outcome and observed evidence
- Commit `bc4db77243bc16f999e382c0a1fba41c1271186c` extends the existing post-write rollback negative to require canonical non-symlink paths and compare bytes, file/parent inode/mode and resolved path for six recovery registries, the generator and Production Status after both successful and deliberately failed rollback.
- Exact-source Snapshot Post Write Rollback Negative run `40018393318` completed SUCCESS. Its job log confirms `Memory OS OPS-P0-007 strict snapshot post-write rollback negative PASS`, `canonical production status and six recovery registries bytes/identity remain unchanged: true`, `negative cleanup restores canonical strict snapshot bytes/mode: true` and `production evidence/readiness/promotion created: false`.
- Previously pending generator change `bea92e9` also reached exact-source Readonly run `40018062428` SUCCESS and Snapshot Publisher run `40018062742` SUCCESS. Readonly job log explicitly reports generator execution authority negative PASS and `production decision: NO_GO`.

### Why safe
- Only the existing CI-bound rollback negative changed. The synthetic invalid snapshot candidate and explicit cleanup remain the only intentional canonical-file mutation, confined to the Actions checkout. Recovery registries, production status, generator, credentials, traffic, readiness and promotion authorities were not modified.
- The tested generator and snapshot validators still enforce real registered-versus-semantically-eligible generation separation, explicit human-approved current objective, current executable reviewed request for new recovery evidence, typed eight-domain non-resurrection coverage, independent review and separate human promotion.

### Reusable mechanism
- A rollback test must prove both restoration of the intentionally mutated output and non-mutation of *all* independent recovery authority inputs across success and failure paths. Snapshot bytes/mode alone are insufficient; compare registry bytes and file/parent identity in each branch and require canonical path identity before and after.
- CI guard success is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; strict snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.

### Retry condition
- Revisit only if a changed rollback implementation, a new protected recovery authority or an observed exact-source failure reveals an unguarded mutation. The unrelated source-binding clean-worktree blocker remains scoped and is not retried.

## 2026-10-24 — Every typed non-resurrection domain needs its own missing-domain negative proof

### Outcome
- Commit `40b9f38ecd735677c7301b9689ca3fabe41fe594` extends the existing contract-bound, CI-transitively-invoked non-resurrection negative suite from a single missing-domain deletion probe to one isolated probe per required domain.
- Exact-source Backup Restore Non-Resurrection Admission run `40028749299` completed SUCCESS on that commit. The admission validator's canonical `run_validator(NEGATIVE, ...)` invokes the suite with fatal nonzero-exit handling; the workflow log does not separately print the individual negative-case outputs.

### Evidence
- The eight unique `requiredDomains` values are read from the unchanged typed admission contract. For each, the harness deletes only that domain from a deep-copied valid record and requires the exact `domain coverage drift` writer diagnostic; an unrelated writer exception cannot satisfy the case.
- Exact-source Readonly run `40028749333` and Reconcile Negative run `40028749302` also completed SUCCESS. Operability Admission Inventory run `40028749270` failed its separate production inventory gate and wrote a diagnostic; that failure is not a typed-evidence success or a reason to weaken the gate.

### Why safe
- Only the existing negative harness changed. Each fixture is synthetic and restores its state; no production-equivalent generation, objective, executable drill, typed evidence, credentials, traffic, readiness or promotion authority was created or altered.

### Reusable mechanism
- For a mandatory typed set, prove omission of *each* independently named member rather than only one representative. Derive negative labels from the reviewed contract and bind every rejection to the exact canonical diagnostic; preserve the positive control and fatal CI invocation.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `productionDecision=NO_GO`; strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation recovery evidence, complete typed eight-domain records and final candidates.
- Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates; human review and promotion remain separate.

### Retry condition
- Revisit only if required domains, canonical coverage diagnostics, the bound negative suite's executable call chain or exact-source CI behavior changes. Do not retry the unrelated unchanged clean-worktree blocker.

## 2026-10-24 — OPERABILITY review failures must be independently rejected even when SECURITY passes

### Outcome and observed evidence
- Commit `4609a94d14c82a0a43cf997cfaf4215c457b55ba` adds seven independently scoped OPERABILITY-only negative probes: exact typed-domain bundle omission, typed-domain evidence digest mismatch, review result not APPROVED, and each of four prohibited production-boundary booleans.
- Exact-source Backup Restore Non-Resurrection Admission run `40029036142` completed SUCCESS; Readonly `40029036194`, Reconcile Negative `40029036146`, and Drill Request Admission `40029036154` also completed SUCCESS. The canonical admission validator invokes this negative suite transitively with nonzero exit treated as failure; individual negative-case output is not surfaced separately in the workflow log.

### Why safe and reusable guard
- Existing shared review-failure fixtures exercised SECURITY first and could not independently prove OPERABILITY rejection. The synthetic fixture now selects a target review: SECURITY stays independently valid while only OPERABILITY is mutated, and each case requires its own exact `OPERABILITY review ...` diagnostic. A final positive validation proves state restoration after the probes.
- The suite mutates no production evidence, registered generations, human-approved recovery objectives, executable drill requests, typed registry, production credentials, traffic, readiness or promotion. The original positive control and existing SECURITY negatives remain intact.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED`, with zero registered/eligible generations, approved objectives, executable requests, recovery evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- The separate Operability Admission Inventory run `40029036053` failed its production inventory gate; it is not an OPERABILITY-review success or promotion evidence. Keep fail-closed inventory and human promotion authority unchanged.

### Retry condition
- Revisit the isolated review negative mechanism only if reviewed schema, canonical writer diagnostics, review validation ordering or exact-source CI invocation changes. Do not repeat the unchanged source-binding clean-worktree blocker.

## 2026-10-24 — OPERABILITY provenance and review-type rejection must be isolated from SECURITY

### Outcome and evidence
- Commit `7dd1a4e834b965ab13bc6120c207a65275536082` adds four isolated OPERABILITY review negatives for generation ID, source commit, typed record ID and review type, each bound to the exact canonical `OPERABILITY review ...` diagnostic.
- Post-write source re-read confirms all four cases and the existing final positive-control invocation. Commit comparison shows only the canonical negative suite changed (18 added, 1 removed line). The commit's combined-status endpoint returned no statuses and the commit workflow-run lookup returned no runs; **exact-source CI success is not yet observed**.

### Symptom, root cause or unknown, and failed approach
- Symptom: the existing provenance cases mutated both reviews, so SECURITY failed first and the suite could not prove that OPERABILITY independently rejects mismatched provenance. The typed contract explicitly names OPERABILITY source-commit rejection.
- Evidence: the prior fixture used the same mutable generation/source/record state for both review payloads, and only the SECURITY diagnostic was expected for those three cases.
- Verified root cause: the synthetic review loader applied provenance overrides unconditionally to both review types, making the OPERABILITY rejection unreachable in those probes. No production incident is asserted.
- Failed approach: treating a SECURITY-first failure as proof that both independent reviewers enforce their own provenance bindings.

### Correction, recurrence guard, and retry condition
- Scope the synthetic review payload's generation/source/record/type overrides to the selected review target. With `reviewTarget=OPERABILITY`, SECURITY stays canonical while four OPERABILITY-only mutations each require the intended diagnostic. Restore every mutated state field and execute the existing positive control after the negative probes.
- Reusable guard: independent reviewers must each have isolated negative proofs for provenance and review-type authority; one review failing first cannot count for the other.
- Retry condition: if exact-source CI reports a fixture or diagnostic mismatch, inspect that run's actual output before correction. Otherwise revisit only after the reviewed schema, validator ordering or review provenance binding changes. Do not retry the unchanged source-binding clean-worktree blocker.

### Why safe and protected-authority check
- The commit changes only a CI-bound synthetic negative harness. No generation, recovery objective, drill request, typed evidence registry, production credential, traffic, readiness, snapshot or promotion authority was written.
- The branch diff from pre-change HEAD contains only the negative harness; Production Status and strict OPS-P0-007 snapshot were not changed. `productionDecision=NO_GO` remains required, and typed eight-domain coverage, independent review and separate explicit human production promotion remain mandatory.
- This learning record and any future CI pass are never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-24 — Typed domain provenance must be independently rejected for all eight domains

### Outcome and observed evidence
- Commit `9aa667c58757dfd4ac86ce9f662edf721d89c77c` extends the existing CI-bound typed non-resurrection negative suite with 28 new isolated cases: generation, source commit, domain name and result drift for each of the seven previously unproven domains. The first domain retains its four original cases, for 32 total provenance-binding probes.
- Source re-read confirms the eight-domain contract remains unchanged, the fixture scopes each mutation to one named domain, restores the altered field in `finally`, and executes a positive control after the loop. Post-write commit comparison shows only the existing negative harness changed (29 additions, 2 deletions).
- GitHub combined status returned no statuses for this commit. The structural checks above are not canonical validator execution or exact-source CI success.

### Symptom, verified root cause, and failed approach
- Symptom: all eight domains had missing-domain, path-type and result-path negatives, but generation/source/domain/result evidence-payload provenance rejection was only exercised for the first domain.
- Evidence: the earlier synthetic loader applied provenance overrides to every domain payload, so an error in the first domain masked whether any later domain independently enforced its provenance.
- Verified root cause: the test harness lacked per-domain targeting for the four payload-provenance overrides. No actual production recovery or non-resurrection failure is asserted.
- Failed approach: using one representative domain's rejection as executable proof for every independently required typed domain.

### Correction, recurrence guard, and retry condition
- Introduce a fixture-only `domainTarget` selector: all non-target domain evidence remains canonical while exactly one domain is mutated. For every remaining required domain, require its exact writer diagnostic for generation, source commit, domain name and result mismatch. Restore state and revalidate the complete positive fixture.
- Reusable mechanism: derive independently scoped negative cases from the contract's reviewed `requiredDomains`, and bind each rejection to the domain-specific canonical diagnostic. Do not allow an earlier domain to satisfy a later domain's negative proof.
- Retry only if exact-source CI identifies a concrete failing diagnostic/fixture or if domain schema, required set, writer validation order or CI invocation changes. The separate known source-binding clean-worktree blocker has no changed precondition.

### Why safe and protected-authority check
- Only the existing synthetic negative validator changed; neither the typed contract/registry nor any production, generation, objective, drill, credential, traffic, readiness, snapshot or promotion authority was written. The post-write diff contains only the negative harness.
- `productionDecision=NO_GO` and strict OPS-P0-007 gates remain mandatory: unsuperseded eligible generations from distinct environments, current human-approved objective, current executable reviewed request for new evidence, complete typed eight-domain coverage, independent review and separate explicit human promotion.
- Learning records, static checks and CI results cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Production-boundary flags need independent rejection in every typed domain

### Outcome and evidence
- Commit `65cb1f513174d13f62e26b5dc48172b258fa175b` adds 28 isolated domain-evidence negative probes: each of the seven previously unproven typed domains independently rejects `productionTraffic`, `productionCredentials`, `productionEvidence` and `productionReady` relabeling. The first domain retains its four original flag probes, yielding 32 domain/flag combinations.
- Post-write source read confirms each probe targets one domain, requires the exact domain/field-specific canonical writer diagnostic, restores the flag in `finally`, resets domain targeting and revalidates the positive fixture. The commit comparison contains only 14 added lines in the existing negative suite. GitHub combined status returned no statuses, so **canonical CI success is unverified**.

### Symptom, verified root cause and failed approach
- Symptom: the negative suite exercised four domain-level production flags only for its first typed domain; later domains could theoretically lose their own checks without a case-specific negative failure.
- Evidence: the previous domain flag loop used a shared unscoped synthetic loader and expected only the first-domain diagnostic.
- Verified root cause: per-domain fixture selection was missing until the preceding provenance hardening introduced `domainTarget`. No real production evidence bypass is asserted.
- Failed approach: assuming one domain's production-boundary rejection demonstrates independent enforcement for the other seven.

### Correction, recurrence guard and retry condition
- Reuse the existing domain-target selector to inject exactly one prohibited flag into one domain payload at a time, leaving every other domain canonical. Require the exact diagnostic, restore fixture state and run a final positive control.
- Reusable mechanism: derive the Cartesian product of contract-required domains and forbidden production-boundary flags for negative proof, not just a representative domain. Keep the proof isolated and diagnostic-specific.
- Retry only if a concrete exact-source CI result identifies a failure, or reviewed domain schema, production-boundary rules or writer ordering changes. Do not retry the unchanged clean-worktree source-binding blocker.

### Why safe and protected-authority check
- Only the existing CI-bound synthetic negative harness changed. No production-equivalent generations, human-approved objectives, drill requests, typed evidence/registries, credentials, traffic, readiness, snapshots or promotion authority were created or changed.
- The code commit diff contains no protected authority. `productionDecision=NO_GO`, distinct semantically eligible environments, current human-approved objective, executable reviewed drill request for new evidence, complete eight-domain coverage, independent review and separate human promotion remain required.
- Neither this learning record nor any CI outcome can satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — A negative symlink fixture must never unlink an occupied evidence path

### Outcome and observed evidence
- Commit `3068db9e1696de08e212d078e0cb65e4388a12de` adds a fail-closed vacant-path precondition to the existing typed non-resurrection symlink escape negative. It removes the previous unconditional `unlink(missing_ok=True)` before fixture creation and permits cleanup only after this invocation actually created the symlink and its target identity remains unchanged.
- Two temporary-directory controls require exact rejection and byte preservation for an occupied regular file and exact rejection/preservation for a dangling symlink. Source re-read confirms the precondition, created-only cleanup and both controls; commit comparison shows only the existing negative harness changed (35 added, 2 deleted lines). The commit's combined status returned no statuses; exact-source CI success is not observed.

### Symptom, verified root cause and failed approach
- Symptom: the earlier negative suite unconditionally deleted a canonical repository-relative evidence path before creating its synthetic symlink, and unconditionally deleted the path again in `finally`. If the fixture name became occupied, the suite could destroy an unrelated real artifact.
- Evidence: the prior code called `symlink_path.unlink(missing_ok=True)` both before `symlink_to` and in unconditional cleanup, with no vacancy assertion.
- Verified root cause: fixture setup assumed exclusive ownership of a hard-coded evidence filename without proving it. No actual deletion of a real evidence file is claimed.
- Failed approach: using destructive cleanup as an implicit collision-resolution mechanism in a negative proof.

### Correction, recurrence guard and retry condition
- Require that the canonical fixture target neither exists nor is a dangling symlink. Create it only after the precondition passes; delete it only if this invocation created it and it still points at the expected isolated temporary artifact. Keep occupied-file and dangling-symlink negative controls outside the repository authority tree.
- Reusable mechanism: test fixtures must fail closed on name collisions, never overwrite/delete unknown artifacts, and bind cleanup to ownership and identity rather than pathname alone.
- Retry only if an observed exact-source CI failure reveals an incompatible fixture prerequisite, or a new source-path/parent identity bypass is demonstrated. Do not retry the unchanged source-binding clean-worktree blocker.

### Why safe and protected-authority check
- Only the synthetic CI-bound negative harness changed. Neither the typed registry, generation/objective/drill authority, Production Status, strict snapshot, credentials, traffic, readiness nor promotion was written. The post-write code diff contains no protected authority.
- `productionDecision=NO_GO` remains mandatory; semantically eligible unsuperseded generations from distinct environments, current human-approved objective, current executable reviewed drill request, complete typed eight-domain non-resurrection coverage, independent review and separate human promotion are unchanged.
- This learning history and CI/test results cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed negative evidence fixture parents must be canonical and identity-stable

### Outcome and observed evidence
- Commit `a05de8023e9f4200426da6d046041f01fe22f741` extends the existing CI-bound typed non-resurrection negative harness. It requires a real, non-symlinked canonical parent before creating a synthetic evidence symlink; refuses to create missing repository directories; and binds cleanup to the original parent device/inode plus the created symlink's own device/inode and expected external target.
- Three isolated temporary-directory controls reject a missing parent, a parent outside the test root and a symlinked parent; an isolated canonical parent remains accepted. Exact-source Admission run `40033049310`, Readonly run `40033049248`, and Reconcile Negative run `40033049278` completed SUCCESS. The Admission job's negative admission suite reported PASS and `production decision: NO_GO`.
- The code commit comparison from `b7fe0b7` to `a05de802` changed only the synthetic negative harness (59 additions, 1 deletion). Production Status, strict OPS-P0-007 snapshot and autonomous-learning contract blob identities remained unchanged. A separate automated inventory-diagnostic commit `e7785a64` followed; it is not evidence of production readiness.

### Symptom, evidence, root cause, and failed approach
- Symptom: the negative fixture previously called `parent.mkdir(parents=True, exist_ok=True)` and checked only that its leaf was vacant, then cleaned up by matching symlink target path. A symlinked parent could redirect creation/cleanup to a different directory; same-target replacement of the leaf was not inode-detected.
- Evidence: the prior source had no parent canonicality or parent/leaf inode check around the symlink negative. This is a discovered fixture authority gap, **not** observed production corruption or a demonstrated exploit.
- Verified root cause: leaf vacancy and target resolution do not establish parent-path authority or ownership of the created symlink inode.
- Failed approach: implicitly creating parent directories and assuming an equal-target symlink is necessarily the fixture-created object.

### Correction, recurrence guard, and retry condition
- Require each parent component to be an existing directory without symlink aliases, bind the resolved parent to the canonical root, snapshot parent device/inode before creation, and require identical parent and created-leaf device/inode before deletion. Keep missing/outside/symlinked-parent negative controls entirely inside an isolated temporary root.
- Reusable mechanism: a destructive test fixture must prove **both** canonical parent authority and created-leaf ownership, not merely a vacant filename or equal target.
- Retry only after an observed exact-source Admission CI failure with a concrete diagnostic, a changed reviewed fixture parent layout, or a newly demonstrated identity bypass. Do not retry the unchanged source-binding clean-worktree blocker.

### Why safe and protected-authority check
- Only the existing synthetic CI negative harness changed. No actual evidence, recovery generation, objective, drill, registry, credentials, traffic, readiness, promotion, snapshot or Production Status authority was written.
- `productionDecision=NO_GO` remains mandatory. Distinct unsuperseded semantically eligible environments, explicitly human-approved current objective, current executable reviewed request for new generation evidence, complete typed eight-domain coverage, independent review and separate human production-promotion authority remain unchanged.
- Learning and CI outcomes are never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-24 — Execute typed writer CLI authority negatives from canonical admission and bind lock cleanup to inode ownership

### Outcome and observed evidence
- Commit `d16aa227293f9a284ca8fe0483b619199004b594` wires the pre-existing typed writer CLI authority negative script into the canonical typed non-resurrection admission validator. Exact-source Admission run `40033293331` completed SUCCESS; the existing Readonly workflow has a wildcard trigger for `scripts/validate-memory-os-backup-restore-non-resurrection-*.py` and executes that canonical admission validator.
- Commit `cadb8f2740575f9c98bf3264899364771723f6fc` replaces unconditional canonical lock fixture unlink with a parent/leaf device-and-inode ownership guard, plus an isolated same-target replacement test. Exact-source Readonly run `40033403750` FAILED with `TYPED NON-RESURRECTION WRITER AUTHORITY NEGATIVE FAILED: typed lock replacement diagnostic drift`.
- Commit `ec9cc4be377e503b0311d4641e88e6731a6c271c` corrects the isolated test's parent identity. Exact-source Readonly run `40033431139` completed SUCCESS. Protected Production Status, strict OPS-P0-007 snapshot and autonomous-learning contract blobs remained unchanged; only validator/test code and a separately generated non-production inventory diagnostic changed.

### Symptom, observed evidence, verified root cause, and failed approach
- Symptom: the isolated same-target symlink replacement negative unexpectedly reported the wrong diagnostic in `40033403750`.
- Evidence: the test passed the **repository lock parent** identity to the helper while checking a symlink in a **temporary-directory parent**. Thus the helper rejected the parent first, masking the intended replaced-leaf inode rejection.
- Verified root cause: a copied parent-identity variable crossed fixture-root boundaries. No production evidence corruption or production decision change occurred.
- Failed approach: assuming the canonical lock's parent identity also describes an isolated temporary test parent.

### Correction, recurrence guard, and retry condition
- Record the isolated link's own parent `st_dev/st_ino` and pass that identity to the isolated replacement probe. Require the exact `typed negative lock symlink identity drift` diagnostic so an unrelated parent rejection cannot count as proof. Retain the canonical lock fixture's independent parent/leaf inode checks before cleanup.
- Reusable mechanism: every synthetic identity test must derive its expected parent identity from the **same fixture root**; exact diagnostics must prevent an earlier, unrelated rejection from satisfying a negative.
- Retry only if exact-source CI reveals another concrete failure, a reviewed lock/validator invocation changes, or an observed parent/leaf identity bypass is demonstrated. Do not retry the unchanged source-binding clean-worktree blocker.

### Why safe and protected-authority check
- These changes only extend existing CI-bound validators and their synthetic lock fixture. No actual recovery generation, objective, drill request, typed evidence registry, production credentials, traffic, readiness, snapshot or promotion authority was written.
- The new canonical invocation provides executable regression coverage, while the Readonly wildcard trigger reaches changes to the writer-authority script. This does not turn a synthetic test into production recovery evidence.
- `productionDecision=NO_GO`, unsuperseded semantically eligible generations from distinct environments, explicit human-approved current recovery objective, executable reviewed request for new generation evidence, eight-domain typed coverage, independent review and separate human promotion remain required. Learning/CI are never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-24 — Reject ancestor symlink aliases in typed lock negative fixtures

### Outcome and observed evidence
- Commit `4edc5419ef61770e82a50e0ff7c3787c2060937a` extends the CI-reachable typed writer CLI authority negative with a canonical-ancestor guard for the materialized lock fixture. It rejects missing or symlinked components between the approved fixture root and lock parent, verifies exact canonical resolution and retains parent/leaf inode ownership checks before cleanup.
- An isolated temporary-directory negative creates a symlinked parent alias and requires its exact rejection diagnostic while preserving the alias; the pre-existing same-target replacement control now explicitly passes its isolated root. Exact-source Readonly run `40033544834` and Backup and Restore Contracts run `40033544777` completed SUCCESS.
- Post-write comparison from `8fcaedae` to `4edc5419` changed only the existing negative validator (44 additions, 10 deletions). Production Status, strict OPS-P0-007 snapshot and learning contract blobs were unchanged.

### Symptom, observed evidence, verified root cause, and failed approach
- Symptom: the prior helper checked only `lock.parent.is_symlink()`, which cannot detect a non-symlink leaf directory reached through a symlinked ancestor. No actual malicious substitution or production corruption is asserted.
- Evidence: the prior helper used `lock.parent.stat()` and `lock.parent.is_symlink()` but did not walk ancestor components or compare canonical parent resolution.
- Verified root cause: leaf-parent identity does not prove canonical ancestor-chain identity.
- Failed approach: relying on a final directory's `is_symlink()` to exclude all symlink aliases above it.

### Correction, recurrence guard, and retry condition
- Walk each component from the selected fixture root to the lock parent; reject missing, symlinked or non-directory components and resolution drift. Bind the isolated negative to its own root so a different precondition cannot mask the intended parent-alias rejection.
- Reusable mechanism: the same canonical ancestor-chain proof now protects both typed evidence symlink fixtures and the writer's materialized lock fixture, with exact negative diagnostics.
- Retry only after a concrete exact-source failure, reviewed authority path changes or a newly observed ancestor-chain bypass. Do not retry the unchanged source-binding clean-worktree blocker.

### Why safe and protected-authority check
- The modification affects only an executable synthetic negative test, not any production or recovery evidence, generation, objective, drill, registry, credential, traffic, readiness, snapshot or promotion authority.
- `productionDecision=NO_GO` and strict OPS-P0-007 preflight/typed eight-domain/independent-review/current executable request/separate human-promotion gates remain mandatory. Learning records and CI are not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-24 — Typed writer CLI guard must be a live first AST statement

### Outcome and observed evidence
- Commit `ae07cf86d19d220c6d72d2692de2fa4ab813f386` introduces a CI-reachable AST classifier that requires the writer's synchronous `main()` to begin with a direct, argument-free `require_cli_authorities()` call. Synthetic comment, string, dead-branch, early-return and async substitutes must each fail with the intended diagnostic. This closes the earlier `inspect.getsource(...).find(...)` text-only proof gap.
- Exact-source Readonly run `40033649503` FAILED at `writer main source syntax invalid` in the synthetic positive control. Commit `d52da15e3b23e185c0d6f7da14dff6fbb3e94885` corrected the fixture. Exact-source Readonly run `40033671563` and Backup and Restore Contracts run `40033671622` then completed SUCCESS.
- Post-write comparison from `58df0753` to `d52da15e` changed only the existing CI-bound writer-authority negative script (42 added lines). Production Status, strict OPS-P0-007 snapshot and autonomous-learning contract blobs remained unchanged.

### Symptom, evidence, root cause, and failed approach
- Symptom: the first AST fixture emitted literal double-escaped `\\n` sequences instead of real line separators, so the synthetic positive-control Python text failed parsing before testing the intended classifier.
- Evidence: Readonly `40033649503` reported `TYPED NON-RESURRECTION WRITER AUTHORITY NEGATIVE FAILED: writer main source syntax invalid`. Source inspection counted 18 double-escaped newline sequences inside the fixture block.
- Verified root cause: the JavaScript edit generated Python string literals with two backslashes before `n`, a previously recorded class of fixture-escaping failure. This repeated known failure was not an authority bypass; the positive-control syntax guard correctly rejected it.
- Failed approach: writing escaped fixture source without checking the final Python string-literal escape depth before committing.

### Correction, recurrence guard, and retry condition
- Replace double-escaped fixture newline sequences with one source-level backslash and `n`; re-read the exact committed source and assert zero double-escaped sequences in the classifier fixture block. Keep the AST positive control as an executable precondition, plus five exact-diagnostic negative controls.
- Reusable mechanism: prefer source-level AST parse of a canonical positive control and diagnostic-specific negative mutations over substring checks; verify literal escaping **before** committing generated source, particularly across JavaScript-to-Python boundaries.
- Retry only if exact-source CI shows a new concrete diagnostic failure, the reviewed writer entrypoint legitimately changes, or a new dead-code/comment/shadowing bypass is observed. Do not repeat the unchanged source-binding clean-worktree blocker or the known double-escaped fixture construction.

### Why safe and protected-authority check
- Only the existing synthetic CI negative changed. The production writer, typed registry, recovery generation/objective/drill/evidence authorities, credentials, traffic, readiness, strict snapshot and promotion authority were not written.
- `productionDecision=NO_GO` remains mandatory; strict semantically eligible distinct environments, human-approved current objective, executable reviewed request for new generation evidence, complete typed eight-domain coverage, independent review and separate human promotion are unchanged.
- Learning and CI are never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## 2026-10-24 — Typed writer authority negative admission must remain AST-reachable

### Outcome and observed evidence
- Commit `3e15b05899e9810682b86a8587bfd1b5ed976a0a` adds an executable CI-bound source-binding proof to the canonical typed non-resurrection negative suite. It parses the canonical admission validator and requires exactly one direct, unconditional top-level `run_validator(WRITER_AUTHORITY_NEGATIVE, ...)` statement in its synchronous `main`, with the exact reviewed writer-authority negative path binding.
- Five isolated AST mutations independently remove, dead-branch, string-substitute, duplicate or path-substitute the call. Every case must fail with its own expected diagnostic; the canonical source is the positive control. Mutations occur only in memory, never in the production validator file.
- Exact-source Readonly run `40033865867`, Reconcile Negative run `40033865365`, and Admission run `40033865433` completed SUCCESS. Post-write comparison from `ed7c00ac` to `3e15b058` changed only the existing synthetic negative harness (88 added lines). Production Status, strict OPS-P0-007 snapshot and learning contract blobs were unchanged.

### Symptom, observed evidence, verified root cause, and failed approach
- Symptom: after adding the writer-authority negative to canonical admission, a future edit could remove or bury its call without the writer-authority test itself running. A file's existence or a commented invocation is not CI reachability proof.
- Evidence: the prior negative suite did not independently assert the admission validator's direct writer-authority call or its canonical source-path binding.
- Verified root cause: the new execution edge lacked a separate executable regression check. No actual CI bypass or production evidence bypass was observed.
- Failed approach: relying on the newly wired validator to prove its own continued invocation.

### Correction, recurrence guard, and retry condition
- Require the exact AST binding and a single direct call in canonical admission; mutate the AST in memory to prove missing, dead, string, duplicate and path-substitution cases are rejected for the intended reason.
- Reusable mechanism: an independently invoked negative suite must verify the **reachability edge** of newly introduced security/authority checks; AST mutations avoid string-escape fixture mistakes and unrelated diagnostic masking.
- Retry only if exact-source CI reports a concrete regression, the reviewed admission function architecture legitimately changes, or a new call shadowing/dead-code bypass is demonstrated. Do not retry the unchanged source-binding clean-worktree blocker.

### Why safe and protected-authority check
- The modification affects only the existing synthetic negative harness. No actual generation, approved objective, drill request, typed evidence registry, credential, traffic, readiness, snapshot, Production Status or promotion authority was written.
- `productionDecision=NO_GO` and strict OPS-P0-007 requirements remain mandatory: unsuperseded semantically eligible distinct environments, current human-approved objective, executable reviewed request for new evidence, complete typed eight-domain coverage, independent review and separate human promotion.
- Learning and CI results cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed writer main module binding must remain unique and undecorated

### Outcome and observed evidence
- Commit `1d58cae6d84d4ca6965d7f50e1ccd82593483384` extends the existing CI-bound typed writer CLI authority negative with a module-level AST guard for exactly one synchronous, undecorated, argument-free `main` definition and no module-scope rebinding.
- Ten synthetic mutations test duplicate definitions, assignment, tuple assignment, import alias, dead-branch assignment, loop binding, `globals()['main']`, `setattr(..., 'main', ...)`, a decorator, and async substitution. Each requires its expected diagnostic. A canonical positive control precedes the negative cases.
- Exact-source Backup Restore Non-Resurrection Readonly run `40038583508` completed SUCCESS; its log includes typed non-resurrection admission validation PASS and `production decision: NO_GO`. Backup and Restore Contracts run `40038583307` also completed SUCCESS. Admission Chain was still in progress at the time of this record and is not claimed successful.
- GitHub compare from `86e663fbc4dd710ce880888620e225bc5e568d5f` to `1d58cae6d84d4ca6965d7f50e1ccd82593483384` showed one modified file, the existing writer-authority negative harness (78 additions, zero deletions).

### Symptom, evidence, verified root cause or unknown, and failed approach
- Symptom/risk: inspecting `inspect.getsource(writer.main)` and checking the first guarded statement does not independently prove the module has only one unshadowed CLI entrypoint. A later module-scope assignment or decorated definition could change which callable is invoked.
- Evidence: the prior harness verified the source of the currently resolved `writer.main` but did not parse the complete writer module for duplicate/rebound `main` names.
- Verified gap cause: function-local source inspection omits module-level name binding. No actual production bypass or malicious replacement was observed.
- Failed approach to avoid: treating an AST-verified first statement in one function body as proof that the module-level executable binding cannot be replaced.

### Correction, recurrence guard, and retry condition
- Parse the complete canonical writer source with AST and reject module-level rebinding, including bindings inside top-level branches, loops, imports, tuples, and direct dynamic `globals`/`setattr` substitutes. Reject decorators and signature drift. Preserve the existing first-statement guard and its independent negative suite.
- Reusable mechanism: distinguish the function-body execution proof from the module-level symbol-identity proof; require both and exercise each with exact-diagnostic synthetic negatives. Build fixture line breaks with `"\\n".join(...)` to avoid the previously observed double-escaped Python fixture failure.
- Retry only if exact-source CI shows a concrete failure, the reviewed writer module legitimately changes, or a newly observed binding bypass exists. Do not repeat the unchanged source-binding clean-worktree blocker or a target-specific write blocker without changed preconditions.

### Why safe and protected-authority check
- Only an existing synthetic negative harness was changed; no production writer, registry, generation, recovery objective, drill request, typed evidence, credential, traffic, readiness, snapshot or promotion authority was written.
- The source diff contained no protected authority files. `productionDecision=NO_GO` remains required, with unsuperseded semantically eligible distinct environments, a human-approved current recovery objective, a current executable reviewed request for new evidence, typed eight-domain coverage, independent review, and separate non-automatic human promotion.
- This learning entry and the CI results are operational history only; they cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed writer parser and exclusive lock require AST execution reachability

### Outcome and observed evidence
- Commit `8c86c511058e8133d6a08940518669b35841cade` replaces substring/offset-only checks of the typed writer's parser and lock with an AST classifier in the existing writer-authority negative harness.
- The classifier requires a direct second-statement `argparse.ArgumentParser()`, direct `validate_record(record)` before lock, one top-level lock acquisition `try`, exact `os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)`, and a `FileExistsError` rejection handler. Direct early exit before lock is forbidden.
- Eleven isolated in-memory mutations exercise parser comments, strings and dead branches, early return, missing/dead lock, substituted path/flags/mode, changed exception handler and record-validation ordering. Each requires the expected diagnostic.
- Exact-source Non-Resurrection Readonly run `40038734608` completed SUCCESS after this code change. Backup and Restore Contracts and Admission Chain were in progress at the time of this entry; their success is not claimed here. The preceding module-binding change's Admission Chain run `40038583319` completed SUCCESS.
- Post-write compare from `9dc2353d7bd2093787482e66423f8555cd232fee` to `8c86c511058e8133d6a08940518669b35841cade` changed only the existing synthetic negative harness (120 additions, 9 deletions).

### Symptom, observed evidence, verified root cause or unknown, and failed approach
- Symptom/risk: `main_source.find(...)` can accept a comment, string or unreachable branch as apparent proof that parsing precedes lock acquisition and the lock uses exclusive-create flags.
- Evidence: the prior harness used textual offsets for `argparse.ArgumentParser` and `os.O_CREAT | os.O_EXCL` without checking executable AST statements or the `LOCK` argument and mode.
- Verified gap cause: text location is not execution reachability. No actual production writer substitution or evidence corruption was observed.
- Failed approach to avoid: treating substring order as a sufficient security boundary for parser and lock semantics.

### Correction, recurrence guard, and retry condition
- Require direct AST statement shape, exact canonical lock arguments, fail-closed exception handling and record-validation ordering; preserve a positive control and eleven diagnostic-bound negatives.
- Reusable mechanism: bind critical CLI operations to both statement reachability and exact call arguments, rather than strings. Build test fixtures with explicit newline joins, and require exact diagnostics so unrelated parser errors cannot count as rejection.
- Retry only on an observed exact-source CI regression, legitimate reviewed writer control-flow change or a demonstrated new parser/lock bypass. Do not repeat the unchanged source-binding clean-worktree or target-specific permission blockers.

### Why safe and protected-authority check
- The canonical production writer and all recovery registries, generations, objectives, drill requests, typed evidence, credentials, traffic, readiness, Production Status, snapshot and promotion authority were not written.
- `productionDecision=NO_GO` remains mandatory. Distinct unsuperseded semantically eligible environments, explicitly human-approved current objective, current executable reviewed drill request for new evidence, complete typed eight-domain coverage, independent review and separate human promotion remain intact.
- This operational learning and CI result cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed writer CLI dispatch and Fail exit must be AST-reachable

### Outcome and observed evidence
- Commit `32fba9088a27e704639f451450226e3093e5181a` adds an executable AST guard to the existing typed writer authority negative harness for the module's final `if __name__ == "__main__"` dispatch.
- The guard requires exactly one final canonical dispatch block, a direct `try: raise SystemExit(main())`, a single `except Fail` handler, and a nonzero `SystemExit` on that failure path.
- Ten synthetic mutations independently test missing/renamed/duplicate guards, call-only dispatch, hard-coded successful exit, string/dead-branch substitutes, wrong exception type, swallowed exception, and zero exit. Each requires its exact expected diagnostic.
- Exact-source Non-Resurrection Readonly run `40038850946` and Backup and Restore Contracts run `40038850990` completed SUCCESS. Admission Chain `40038850979` was pending at the time of this record and is not claimed successful.
- Post-write comparison from `8caef09d6e9260d64fa401e181dcae31b27f1e4f` to `32fba9088a27e704639f451450226e3093e5181a` modified only the existing synthetic negative harness (101 additions, 1 deletion).

### Symptom, observed evidence, verified root cause or unknown, and failed approach
- Symptom/risk: a module can contain a correctly guarded `main` function while its `__main__` dispatch is disabled, string-substituted or changed to return success after `Fail`.
- Evidence: previous checks inspected the `writer.main` function and module-level binding but did not validate the script's actual CLI dispatch and exception-to-exit mapping.
- Verified gap cause: callable identity and function-body reachability do not prove the `python script.py` entrypoint executes the callable or propagates failure. No actual malicious bypass or production incident was observed.
- Failed approach to avoid: treating a guarded function as sufficient proof of CLI execution without inspecting its module dispatch.

### Correction, recurrence guard, and retry condition
- Require AST reachability for the final canonical dispatch and nonzero Fail handling, alongside the existing first-guard, module-binding, parser and lock checks. Prove each rejection with a canonical positive control and diagnostic-bound synthetic mutation.
- Reusable mechanism: audit the entire CLI authority chain separately—module binding, guarded function body, parser/lock operations, and script dispatch. Neither source presence nor function importability alone proves CLI enforcement.
- Retry only on a concrete exact-source CI failure, a reviewed change to the writer's CLI dispatch structure, or a demonstrated dispatch bypass. Do not repeat unchanged clean-worktree or permission blockers.

### Why safe and protected-authority check
- Only the CI-bound synthetic negative harness was changed; no actual production writer, environment generation, recovery objective, drill request, typed evidence, registry, credential, traffic, readiness or promotion authority was written.
- Canonical Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`, strict OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, approved objectives, executable requests, generation recovery evidence, complete typed records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Distinct unsuperseded semantically eligible environments, explicitly human-approved current objective, executable reviewed request for new evidence, complete eight-domain typed coverage, independent review and separate human promotion remain mandatory. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Pre-dispatch module exits cannot masquerade as live writer CLI authority

### Outcome and observed evidence
- Commit `cdec3337f0cd192b43647ea62654370d69150090` extends the existing CI-reachable typed writer authority negative harness with a module-scope AST guard against explicit termination before the final canonical CLI dispatch.
- Nine synthetic negative cases reject module-level `raise SystemExit`, `sys.exit`, `os._exit`, `exit`, `quit`, nested branch/try termination, and dynamic `exec`/`eval` calls. The canonical positive control is required before any mutation.
- Exact-source Non-Resurrection Readonly run `40039026581` completed SUCCESS. Contracts and Admission Chain were still running when this entry was written and are not claimed successful.
- Compare from `e80cd46e922bc7be350d2d5d430fa89fd6d2df6a` to `cdec3337f0cd192b43647ea62654370d69150090` changed only the existing negative harness (63 additions, zero deletions).

### Symptom, observed evidence, verified root cause or unknown, and failed approach
- Symptom/risk: even an AST-verified final `if __name__ == "__main__"` dispatch may never execute if earlier module-scope code explicitly terminates the interpreter.
- Evidence: the preceding dispatch guard proved the shape of the final block but did not inspect preceding module-scope statements for direct early exits. No actual malicious early exit or production incident was observed.
- Verified gap cause: existence of a final dispatch is not the same as reachability through preceding module initialization.
- Failed approach to avoid: assuming a valid final dispatch statement is sufficient proof of execution while ignoring earlier unconditional or branch-contained interpreter exits.

### Correction, recurrence guard, and retry condition
- Traverse module-scope AST before the final dispatch, excluding deferred function/class/lambda bodies, and reject explicit early-exit calls or raises. Require nine exact-diagnostic negatives and a positive control; preserve the previously added module-binding, function-guard, parser/lock and dispatch checks.
- Reusable mechanism: for CLI entrypoint assurance, prove not only that the target call exists, but also that obvious module-scope termination cannot prevent reaching it. Static checks do not establish absence of all dynamic import-time side effects.
- Retry only after a concrete exact-source failure, a reviewed change in writer module initialization, or a demonstrated new pre-dispatch bypass. Do not repeat unchanged source-binding clean-worktree or target-specific write blockers.

### Why safe and protected-authority check
- The production writer, recovery generation/objective/request/evidence registries, typed coverage, credentials, traffic, readiness, Production Status, snapshot and promotion authority were not written.
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Distinct unsuperseded semantically eligible environments, explicit human-approved current recovery objective, current executable reviewed request for new evidence, typed eight-domain non-resurrection coverage, independent review and separate human production promotion remain mandatory. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Dynamic writer module namespace rebinding needs explicit AST proof

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check
- Outcome: commit `5821ee79060d3c02fd435c31c7d61252c999107f` adds nine diagnostic-bound negative mutations for module namespace changes through `globals()`, `vars()`, `locals()` and module `__dict__`; commit `2c5a50443240e3a80085d1850227d5c4268e378c` corrects the fixture source escaping before claiming any CI success.
- Evidence: a local independent Python AST positive control and nine mutation probes rejected all nine with `writer module main binding drift`. The repository comparison from start HEAD `c14ae1c5` to corrected HEAD `2c5a504` changed only `scripts/validate-memory-os-backup-restore-non-resurrection-writer-authority.py` (38 additions, 6 deletions). GitHub commit workflow-run discovery returned no exact-source runs for `2c5a504`; canonical CI remains unverified at recording time.
- Why safe: changes are confined to the existing CI-bound synthetic negative harness. The canonical writer, evidence registries, objectives, drill requests, production state and promotion authority were not modified.
- Reusable mechanism: separately prove direct `main` symbol binding and module-level dynamic namespace mutation, including dead-branch substitutes, with a positive AST control and diagnostic-specific negatives. Treat unresolvable namespace-mutating calls as fail-closed rather than attempting to infer their runtime values.
- Protected-authority check: no protected authority path changed in the observed compare. `productionDecision=NO_GO` remains mandatory; OPS-P0-007 still requires distinct unsuperseded semantically eligible environments, explicitly approved current recovery objective, current executable reviewed drill request for new evidence, complete typed eight-domain coverage, independent review and separate human promotion. This learning and CI are not production/backup/restore/RPO/RTO/skew/drill/credential/traffic/readiness/promotion evidence.

### Material failure: symptom, evidence, root cause or unknown, failed approach
- Symptom: the first commit emitted literal double-escaped `\\n` into nine Python fixture strings, which would create invalid synthetic source and mask the intended namespace-binding diagnostic.
- Evidence: immediately after commit `5821ee7`, re-reading the exact GitHub blob counted ten double-backslash-newline escape sequences and zero valid single-backslash newline escapes in the new fixture block.
- Verified root cause: JavaScript template-string escaping produced two Python-source backslashes before `n`, repeating the previously recorded cross-language fixture escaping failure class. No canonical CI failure or production incident is claimed.
- Failed approach: writing JavaScript-generated Python fixtures without inspecting the committed literal escape depth before the first write.

### Correction, recurrence guard, retry condition
- Correction: commit `2c5a504` replaces all ten double-escaped sequences with single source-level newline escapes. The post-write preflight verified ten correct escapes and zero doubled escapes.
- Recurrence guard: inspect the final generated Python source and require both zero doubled newline escapes and a parseable positive fixture before committing. The existing exact-diagnostic negative assertions additionally reject syntax-error masking instead of counting it as a valid security rejection.
- Retry condition: revisit only on a concrete exact-source CI regression, a reviewed legitimate writer module-binding change or a demonstrated new namespace rebinding bypass. Do not retry unchanged source-binding clean-worktree or external permission blockers.

## 2026-10-24 — Eager class and definition expressions are import-time execution

### Outcome
- Commit `25934ba15776a46459227e63edffa8af9a05fd79` extends the existing typed writer CLI negative with six AST-bound rejection probes for class-body exit/raise, decorator execution, function default evaluation, class base evaluation and lambda default evaluation before final CLI dispatch.
- Deferred function/method bodies remain exempt from this import-time check; class bodies and eager definition expressions are inspected instead.

### Evidence
- Independent local Python AST controls accepted a canonical guarded dispatch and deferred function/method bodies, while rejecting all six eager-execution substitutions. The committed source contains twelve correct fixture newline escapes and zero double-escaped newline sequences.
- Exact-source GitHub workflow-run discovery for `25934ba` returned no runs at recording time. The result is local AST proof plus repository structural inspection, **not** a claimed Canonical CI success.
- GitHub compare from run-start `c14ae1c5` to `25934ba` changed only the existing synthetic negative validator and append-only learning log; no protected authority paths were changed.

### Why safe
- No actual typed writer, generation/objective/drill/evidence registry, production status, recovery snapshot, credential, traffic, readiness or promotion authority was written.
- `productionDecision=NO_GO` remains mandatory. OPS-P0-007 still requires unsuperseded semantically eligible generations from distinct environments, a current human-approved recovery objective, a current executable reviewed drill request for new generation evidence, complete typed eight-domain non-resurrection coverage, independent review and separate human promotion.

### Reusable mechanism
- Static CLI reachability checks must distinguish deferred function bodies from eagerly executed decorators, default arguments, class bases and class bodies. A final valid `__main__` block alone cannot prove those earlier expressions will not terminate the process.
- Maintain a positive AST control, precise negative diagnostics and source-level fixture-escape preflight before committing. Do not treat a synthetic guard or learning history as production evidence or readiness.

### Protected-authority check and retry condition
- Protected authorities did not drift in the observed compare; the autonomous-learning contract blob remains `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`. Learning remains append-only and separate from production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness and promotion gates.
- Retry only on observed exact-source CI failure, reviewed legitimate import-time architecture change or demonstrated new eager-execution bypass. Do not retry the unchanged source-binding clean-worktree or scoped external permission blockers.

## 2026-10-24 — Writer negative admission must not return success before its validator call

### Outcome
- Commit `0b80efea9c9646d4604c008f27702deea008bb40` extends the existing CI-bound typed non-resurrection negative suite. It now rejects five AST mutations that retain the required direct `run_validator(WRITER_AUTHORITY_NEGATIVE, ...)` call but insert a preceding return, conditional return, `sys.exit(0)`, `raise SystemExit(0)` or `finally` return.
- The original source-path and single direct-call guards remain intact. The negative suite uses in-memory AST mutation rather than modifying canonical admission source.

### Evidence
- A local Python AST positive control accepted an unconditional direct writer-authority call and rejected all five early-success substitutions. The committed source was re-read and the five cases and exact-diagnostic guard were observed.
- GitHub compare from `c14ae1c5` to `0b80efe` changed only the existing writer-authority negative, typed non-resurrection negative and append-only learning authority. GitHub commit workflow-run discovery for `0b80efe` returned no exact-source runs, so CI success remains unverified.
- Workflow source audit found that the dedicated non-resurrection readonly workflow triggers on `scripts/validate-memory-os-backup-restore-non-resurrection-*.py` and calls the canonical admission validator; Backup and Restore Contracts explicitly includes the writer-authority negative path in PR/push triggers. The dedicated admission workflow's own path filter does not include the writer-authority negative, but this is not evidence of a global CI reachability gap.

### Why safe
- Only synthetic AST-based negative tests were changed. No actual writer, typed evidence, environment generation, objective, reviewed drill request, recovery evidence, registry, production status, snapshot, credential, traffic, readiness or promotion authority was written.
- `productionDecision=NO_GO` remains mandatory; strict OPS-P0-007 semantic eligibility, distinct environments, current human-approved objective, current executable reviewed request, typed eight-domain coverage, independent review and separate human promotion remain enforced.

### Reusable mechanism
- A direct AST call in an admission function does not prove reachability when an earlier successful return or interpreter exit can bypass it. Require both unique direct-call binding and fail-closed prefix control flow, with a positive control and diagnostic-specific negative mutations.
- Verify all relevant workflow triggers and transitive invocation edges before claiming CI reachability is absent; a single workflow missing a path can be covered by another canonical workflow. Static reachability and observed exact-source CI success remain separate proof layers.

### Protected-authority check and retry condition
- The autonomous-learning contract blob remains `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`. No protected authority path changed in the observed compare. Learning history remains append-only and cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
- Retry only after observed exact-source CI regression, legitimate reviewed admission control-flow changes or a newly demonstrated early-success bypass. Do not repeat unchanged source-binding clean-worktree or scoped workflow-write blockers.

## 2026-10-24 — Typed admission child failures cannot be overridden by PASS-looking stdout

### Material success: outcome and observed evidence
- Commit `85db0bd4d1ee8b5e8eff79269f5b82556ea24edd` extends the existing CI-invoked `scripts/validate-memory-os-backup-restore-non-resurrection-transport-negative.py` with an executable child-exit propagation guard.
- The isolated subprocess stub checks three cases against the actual canonical admission `run_validator`: exit 0 succeeds, exit 7 with contradictory PASS-looking stdout rejects with the exact combined diagnostic, and signal-style exit -9 rejects. It also checks exact interpreter, script, cwd, capture, text and `check=False` invocation arguments and restores the original subprocess function after each case.
- Exact-source Non-Resurrection Readonly run `40048927528` completed SUCCESS at code HEAD `85db0bd4`. Job `120736951051` explicitly logged `PASS boundary: typed child nonzero/signal exits reject even with PASS stdout` and `Typed non-resurrection execution/registry/reconcile transport negative suite PASS`. This is synthetic validator/CI proof, not production recovery evidence.
- GitHub compare `0ccad4e6..85db0bd4` showed only the existing transport-negative suite changed (45 additions, zero deletions).

### Symptom/risk, cause, and failed approach to avoid
- Risk: a future admission runner could accept a child validator that prints a PASS marker but exits nonzero, or could silently stop checking the child return code. No actual production incident or observed bypass occurred.
- Verified coverage gap: existing transport negatives tested monkeypatch rejection at `main` entry but did not exercise the child `run_validator` success/failure result boundary directly.
- Failed approach to avoid: inferring child failure propagation solely from a successful parent CI run or from static presence of `subprocess.run` without injecting a contradictory child result.

### Correction, recurrence guard, and retry condition
- Reusable mechanism: execute the real canonical child-runner function with bounded synthetic `CompletedProcess` results, require diagnostic-specific nonzero rejection even when stdout resembles success, and assert exact subprocess invocation and cleanup/restoration. Reuse the existing CI-reachable transport negative instead of introducing a parallel authority.
- Retry only after an exact-source CI regression, a reviewed legitimate change to the canonical subprocess invocation contract, or a demonstrated new child-result bypass. Do not repeat unchanged source-binding clean-worktree or workflow-write blockers.

### Why safe and protected-authority check
- The change touches only a synthetic negative validator. No production writer, environment generation, human-approved objective, reviewed drill request, generation recovery evidence, typed domain record, credential, traffic, readiness or promotion authority was written.
- Post-change canonical blobs were unchanged: Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` (prerequisites blocked, zero registered/eligible generations and final candidates), and learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`.
- Strict semantic eligibility across distinct unsuperseded environments, an explicitly human-approved current objective, a current executable reviewed request for new generation evidence, typed eight-domain coverage, independent review, and separate non-automatic human promotion remain mandatory. This learning and its CI result cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Canonical typed child runner must not be rebound after source validation

### Material success: outcome and observed evidence
- Commit `c428b65448bf3729647425085ebe8e8a8f577628` extends the existing CI-invoked typed non-resurrection transport-negative suite with AST source-binding proof for the canonical admission `run_validator` function.
- A canonical positive source control is followed by eleven exact-diagnostic mutations: duplicate definition, decorator, assignment, import alias, dead-branch assignment, `globals()` subscript/update/pop, module `__dict__` mutation, `setattr`, and dynamic `exec`. The guard also rejects signature drift and other namespace mutators.
- Exact-source Non-Resurrection Readonly run `40049054856` completed SUCCESS. Job `120737344136` explicitly logged `PASS reject: eleven typed admission child runner binding/decorator substitutions` and `Typed non-resurrection execution/registry/reconcile transport negative suite PASS`.
- GitHub compare `8359ae36..c428b654` changed only the existing transport-negative validator (109 additions, zero deletions).

### Symptom/risk, verified gap, and failed approach to avoid
- Risk: the admission source can retain a correct-looking `run_validator` function and its direct calls while a later module assignment or dynamic namespace mutation replaces that callable with a no-op. No production incident or actual bypass was observed.
- Verified coverage gap: the previous child-exit propagation probe executed the canonical function in isolation but did not prove the imported module's `run_validator` name could not be rebound before the admission `main` calls it.
- Failed approach to avoid: treating source presence or direct-call text as sufficient runtime authority without checking definition uniqueness, callable binding, decorators and module namespace mutation.

### Correction, recurrence guard, and retry condition
- Reusable mechanism: parse the actual canonical admission module, require a unique undecorated synchronous `run_validator(path, label)` definition, reject direct/dynamic rebinding, then run exact-diagnostic AST mutation negatives before transport tests. Reuse the existing CI path; do not add a competing validator authority.
- Retry only after a reviewed change to the admission module's legitimate function architecture, an exact-source CI regression, or a demonstrated new binding bypass. Do not repeat unchanged external workflow-write or source-binding clean-worktree blockers.

### Why safe and protected-authority check
- Only a synthetic, CI-bound negative suite changed. No production writer, environment generation, recovery objective, reviewed drill request, recovery evidence, typed eight-domain record, credential, traffic, readiness or promotion authority was modified.
- Post-change Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`, strict OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisites blocked, and learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight still requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current objective; new generation evidence requires a current executable reviewed request; final candidates require complete typed eight-domain coverage and independent review; human production promotion is separate and non-automatic. Learning and CI do not satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Concurrent bot publication must not turn stale source into evidence

### Material failure: symptom and observed evidence
- Two exact-source runs at `0b80efea9c9646d4604c008f27702deea008bb40` failed during concurrent branch advancement: Drill Request Admission `40044180746` (job `120721963481`) and Operability Admission Inventory `40044180615` (job `120721962518`).
- Both logs show `origin/so` advancing from `0b80efea` to `87792aac` during execution. The drill job explicitly emitted `Drill planning source HEAD changed during reconciliation; refusing stale derived authority.` and exited 75. Inventory first encountered the previously known `source-binding negative requires clean canonical source worktree`, then refused to publish a stale failure diagnostic after the same source advance and exited 75.
- The concurrent commit `87792aacc2b413de77208e925359bfa4f98f5879` was the source parent of a scheduled automated incident-control exercise, not a new production-equivalent generation, recovery objective, or promotion. Neither failed run produced valid new recovery evidence.

### Root cause or explicit unknown, failed approach, and correction
- Verified immediate cause of the exit-75 reconciliation failures: source HEAD changed while the jobs were running, violating their exact-source freshness precondition. The separate clean-worktree negative's underlying interference remains the already-recorded scoped blocker; do not invent a new cause for it.
- Failed approach to avoid: classifying these as failed recovery validation or treating stale diagnostics as current evidence; rerunning an unchanged clean-worktree path without a changed precondition.
- Correction: preserve the existing executable bounded source-SHA refresh/reconcile rejection and classify both as stale-source/concurrent-write failures. No workflow mutation or bypass is warranted from this evidence.

### Recurrence guard and retry condition
- Reusable mechanism: compare the captured validation source to the refreshed branch head immediately before any derived-authority or diagnostic publication; abort on mismatch rather than rebase/force-push or relabeling stale results. Distinguish CI status from valid exact-source proof.
- Retry only after a stable source window or a reviewed bounded-reconcile design change; the known clean-worktree blocker requires its separate recorded retry precondition to change. Independent synthetic guards may continue in parallel without promoting the failed runs.

### Protected-authority check
- This is append-only learning history, not readiness or evidence. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, approved objectives, executable requests, generation recovery evidence, typed records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Human-approved current objectives, distinct unsuperseded semantically eligible environments, current executable reviewed drill request for new evidence, typed eight-domain coverage, independent review and separate human promotion remain mandatory. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Full admission-chain child failures must propagate; synthetic helpers must be smoke-tested

### Material success: outcome, observed evidence, and why safe
- Commit `094d245e6722e7ce06935e7f75aa1eec220601f3` added three synthetic child exit cases to the existing full-chain runner negative proof: exit 0 yields a parent PASS; exit 7 with contradictory PASS-looking child stdout and signal-style exit -9 must raise the exact parent `Fail` diagnostic and must not print `PASS chain step`. The fixture asserts canonical interpreter/path/cwd/capture arguments and restores patched subprocess and transport guard objects.
- After correction commit `7708f7dd282d091f9a2d6aed9ff01ccccce6a719`, exact-source Backup Restore Admission Chain run `40049384222` completed SUCCESS. Job `120738382250` explicitly logged `PASS boundary: full-chain child nonzero/signal exits cannot become parent PASS`, `Admission-chain full runner negative validation PASS`, and `Backup/restore admission-chain workflow permission negative PASS`.
- The negative suite is actually invoked transitively by the canonical workflow-permission negative step, as verified from the exact-source job log; its absence from the top-level `STEPS` list is not a CI reachability gap. Only the existing synthetic negative harness was changed, not the canonical runner or any production/recovery authority.

### Material failure: symptom, evidence, verified root cause, failed approach
- Initial exact-source run `40049331341` at `094d245e` failed in the workflow-permission negative step. Job `120738218771` showed `NameError: name 'require' is not defined` inside the new `prove_full_step_exit_propagation` fixture.
- Verified root cause: the new helper called `require(...)` while the existing full-negative script had no `require` definition. Source-shape inspection before commit checked insertion anchors but did not check referenced local helpers; the error was not a production validator rejection.
- Failed approach: adding a cross-file adapted synthetic guard without verifying all imported/helper names against the target harness, then relying on CI to catch a basic fixture NameError.

### Correction, recurrence guard, reusable mechanism, retry condition
- Correction: `7708f7dd` defines the missing local `require(condition, message)` fail-closed assertion helper; the exact-source CI subsequently passed. A concurrent automated diagnostic-only commit `e109ee4b` changed the branch head between read and correction, so the correction was written only after re-reading latest `so` and confirming the target blob remained unchanged.
- Recurrence guard: for adapted negative probes, perform source-level dependency/undefined-helper checks and a bounded positive fixture smoke test before committing; keep diagnostic-specific failure assertions so an unexpected Python exception cannot count as a security rejection. Do not weaken the canonical guard to make a fixture pass.
- Reusable mechanism: isolate a canonical runner's child execution by temporarily replacing only the in-memory transport and its identity guard, verify both positive and contradictory-negative outcomes, and restore every mutation. Confirm transitive CI invocation from actual job logs before adding duplicate workflow wiring.
- Retry only after an observed exact-source regression, reviewed legitimate runner transport change, or demonstrated new child-result bypass. Unchanged source-binding clean-worktree and workflow-write blockers retain their separate retry conditions.

### Protected-authority check
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; strict OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/semantically eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Distinct unsuperseded semantically eligible environments, explicit human-approved current recovery objective, current executable reviewed drill request for new evidence, complete eight-domain typed non-resurrection coverage, independent review and separate non-automatic human promotion remain mandatory. This learning and CI do not satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Full-chain run_step binding must be proven before main captures its default

### Material success: outcome, observed evidence, why safe
- Commit `68be4b241d6d3ae7fd6a70c18464411065f2d4f8` extends the existing CI-invoked full admission-chain negative harness with AST binding proof for `run_step`. It rejects eleven exact-diagnostic substitutions inserted before `main` captures its default callable: assignment, import alias, dead-branch assignment, `globals()` subscript/update/pop, module `__dict__`, `setattr`, `exec`, duplicate definition and decorator.
- Exact-source Backup Restore Admission Chain run `40049559862` completed SUCCESS. Job `120738938096` explicitly logged `PASS reject: eleven full-chain pre-main step rebinding/decorator substitutions`, `PASS boundary: full-chain child nonzero/signal exits cannot become parent PASS`, and `Admission-chain full runner negative validation PASS`.
- GitHub compare `fc7a6745..68be4b24` changed only the existing synthetic full-negative suite (109 additions, zero deletions). No production runner, registry, workflow, recovery objective or evidence authority was changed.

### Symptom/risk, verified gap, and failed approach to avoid
- Risk: the canonical runner's `main(canonical_run_step=run_step)` captures whatever `run_step` is bound to at function definition. A pre-main reassignment to a no-op could therefore defeat a later `run_step is canonical_run_step` runtime identity comparison. No actual malicious bypass or production incident was observed.
- Verified coverage gap: previous runtime negative tests mutated `run_step` after importing the canonical module, but did not prove the source could not rebind it before `main` captured its default.
- Failed approach to avoid: assuming a runtime identity check against a default parameter is independent authority when the default itself can capture an earlier source-level replacement.

### Correction, recurrence guard, reusable mechanism, retry condition
- Reusable mechanism: parse the actual canonical runner source, require one undecorated synchronous step with the canonical signature, reject direct and dynamic symbol rebinding (including dead branches), then prove exact diagnostics for pre-main AST mutations. Keep the existing CI-reachable negative suite and its positive source control rather than adding a parallel contract or workflow.
- Retry only after a reviewed legitimate change to the full-runner step architecture, exact-source CI regression, or demonstrated binding bypass. Unchanged external workflow-write and source-binding clean-worktree blockers retain their recorded retry conditions.

### Protected-authority check
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates, and learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Preflight still requires distinct unsuperseded semantically eligible environments and a human-approved current objective; new generation evidence still requires a current executable reviewed drill request; final candidates still require complete typed eight-domain non-resurrection coverage and independent review; human production promotion remains separate and non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Full-chain CLI main binding rejects module-level shadowing

### Material success: outcome and observed evidence
- Code commit `d19096069e9042ecf2ed048db2dfadf94b653b57` extends the existing CI-reachable `scripts/validate-memory-os-backup-restore-admission-chain-full-negative.py` with a canonical AST positive control and fourteen diagnostic-specific main replacement/decorator negatives.
- Exact-source Backup Restore Admission Chain run `40053728104` (job `120751915026`) completed SUCCESS at that code SHA. Its log explicitly reports `PASS reject: fourteen full-chain main rebinding/decorator substitutions`, `Admission-chain full runner negative validation PASS`, and `production decision: NO_GO`.
- Only the existing synthetic negative harness was modified. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO, OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains PREREQUISITES_BLOCKED with zero eligible generations, approved objectives and final candidates, and learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.

### Symptom/risk, verified coverage gap and failed approach to avoid
- Risk: a later module-level `main` assignment, import alias, decorator or namespace mutation could replace the guarded CLI entrypoint while leaving the original function text intact. No production incident or actual bypass was observed.
- Verified gap: the existing full-chain negative harness protected `run_step` pre-main binding and tested runtime `main` guard substitution, but did not verify that the module-level `main` symbol remained uniquely bound and undecorated.
- Failed approach to avoid: treating `main(canonical_authority_guard=...)` runtime identity defaults or presence of a guarded function as sufficient proof of the CLI symbol's module-level binding.

### Correction, executable recurrence guard and retry condition
- Parse the canonical full runner, require one synchronous undecorated `main` with the expected two default-bound authority arguments, and reject static/dynamic rebinding, dead-branch assignments, import aliases, duplicate/async/class definitions, `globals()` mutation, module `__dict__`, `setattr` and `exec`. Require exact rejection diagnostics for each synthetic mutation.
- Reuse the existing transitive CI execution path rather than adding a competing workflow or production authority.
- Retry only on exact-source CI regression, a reviewed legitimate main architecture change, or a newly demonstrated main-binding bypass. Do not retry unchanged clean-worktree, external dependency or workflow-write blockers.

### Why safe, reusable mechanism and protected-authority check
- All mutation cases operate on in-memory AST copies. No production writer, generation, recovery objective, reviewed drill request, evidence, typed domain record, credential, traffic, readiness or promotion authority was changed.
- Strict OPS-P0-007 preflight still requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current objective. New generation evidence requires a current executable reviewed request; final candidates require all existing gates, complete typed eight-domain non-resurrection coverage and independent review. Human production promotion remains separate and non-automatic.
- This learning and CI proof cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Full-chain script dispatch must invoke main and propagate Fail

### Material success: outcome and evidence
- Commit `f968b525f3e6afc95d86d3c3b9eb07f615774952` adds a canonical AST positive control and thirteen negative probes to the existing CI-reachable full-chain negative suite. The probes reject removed/duplicated/nonterminal CLI guards, dead or direct-call-only dispatch, zero exit, unexpected arguments, alternate exception handlers, swallowed failures and handler finally branches.
- Exact-source Backup Restore Admission Chain run `40053836317` (job `120752260957`) completed SUCCESS. Its log explicitly shows `PASS reject: thirteen full-chain CLI dispatch/failure-exit substitutions`, `Admission-chain full runner negative validation PASS` and `production decision: NO_GO`.
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, objectives, evidence and candidates, and learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.

### Symptom/risk, root cause or explicit unknown, failed approach
- Risk: the module can define a correctly guarded `main` yet never execute it under `python script.py`, or can swallow `Fail` and exit 0. No production incident or successful bypass was observed.
- Verified coverage gap: prior negative checks covered `main` symbol binding and runtime identity, not the executable module's `__main__` dispatch AST or its exception-to-nonzero-exit boundary.
- Failed approach to avoid: equating function presence or a passing import-time test with proof that the actual CLI entrypoint reaches the guard and preserves failure status.

### Correction, executable recurrence guard and retry condition
- Require exactly one terminal `if __name__ == "__main__"` guard, a direct try with `raise SystemExit(main())`, and one `except Fail` whose last statement raises nonzero `SystemExit`. Verify exact rejection diagnostics on thirteen isolated AST mutations.
- Reuse the canonical transitive CI route; no parallel authority, workflow write or production registry mutation is necessary.
- Retry only after a reviewed CLI architecture change, an exact-source CI regression or a demonstrated new dispatch bypass. Do not retry unchanged source-binding clean-worktree, external dependency or workflow-write blockers.

### Why safe, reusable mechanism and protected-authority check
- The validator changes only in-memory AST copies of the canonical full runner; no production generation, objective, reviewed request, recovery evidence, typed eight-domain record, credential, traffic, readiness or promotion was written.
- Distinct unsuperseded semantically eligible environments, a human-approved current objective, an executable reviewed request for new generation evidence, complete eight-domain typed non-resurrection coverage, independent review and separate non-automatic human promotion remain mandatory.
- Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Full-chain pre-dispatch eager exits reject; fixture escapes require a syntax preflight

### Material success: outcome and observed evidence
- Commit `7ea976a9657b6b78dc58271ae1860a567d369696` introduced fifteen synthetic AST negatives for module-level `raise`, `sys.exit`, `os._exit`, `exit`, `quit`, conditional/try exits, dynamic execution, eager class bodies, decorators, function defaults, class bases and lambda defaults before the full-chain CLI dispatch.
- Correction commit `a3acbdc77a1bea41e651edcb1a4c55ab97393957` fixed the fixture strings. Exact-source Backup Restore Admission Chain run `40053988293` (job `120752746393`) completed SUCCESS and explicitly logged `PASS reject: fifteen full-chain pre-dispatch eager termination substitutions` and `Admission-chain full runner negative validation PASS`. The successful bounded reconcile removed the prior failure diagnostic in bot commit `aa85facea342f12ef3c3b8e75a845f2b98e58e04`.
- The executable proof is in the existing CI-reachable full-runner negative suite; it does not modify the canonical runner or production authorities.

### Material failure: symptom, evidence, verified root cause, failed approach
- Initial exact-source run `40053956572` at `7ea976a9` failed. Job `120752645755` logged `SyntaxError: unexpected character after line continuation character` for the synthetic `if True:\\n    raise SystemExit(0)` source, before the new negative cases could complete. This was a fixture error, not a recovery-gate failure.
- Verified root cause: JavaScript-generated source text double-escaped newline characters inside Python mutation strings. Python received a literal backslash-plus-n instead of an actual newline when `ast.parse` evaluated the fixture.
- Failed approach to avoid: adapting cross-file AST fixtures without preflighting the resulting Python string escape depth, especially where the same fixture defect has already been recorded in learning.

### Correction, recurrence guard and retry condition
- Replace all ten double-escaped newline sequences in the inserted mutation fixture block with single-escaped Python newline literals; inspect the generated file content before updating. The correction CI passed.
- Reusable executable guard: canonical positive AST control plus fifteen exact-diagnostic negative probes, with deferred function bodies excluded and eager decorators/defaults/class bodies included. Add a deterministic fixture-literal syntax preflight before any future multi-line mutation batch; never count an unexpected `SyntaxError` as the intended security rejection.
- Retry only on exact-source CI regression, a reviewed change to import-time/CLI initialization semantics, or a demonstrated new early-exit bypass. Unchanged external dependencies, workflow-write and clean-worktree blockers retain their own retry conditions.

### Why safe and protected-authority check
- Only a synthetic negative validator, append-only learning and the CI-owned privacy-safe failure diagnostic lifecycle changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, approved objectives, executable requests, recovery evidence, typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Distinct unsuperseded semantically eligible environments, an explicitly human-approved current objective, a current executable reviewed request for new generation evidence, complete typed eight-domain coverage, independent review and separate human promotion remain mandatory. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Full-chain main must execute authority guards before canonical steps

### Material success: outcome and observed evidence
- Code commit `2bf96461ce64ca0b2689fb2be6d291090dc633ff` adds a canonical AST positive control and fifteen negative probes to the existing full-chain negative suite. The probes reject skipped, inverted, dead, swallowed or reordered authority checks, missing step identity checks, no-op/dead/empty/wrapped loops, swapped step arguments and early success returns.
- Exact-source Backup Restore Admission Chain run `40054122931` (job `120753176207`) completed SUCCESS. The job explicitly logged `PASS reject: fifteen full-chain main guard/step reachability substitutions`, `Admission-chain full runner negative validation PASS` and `production decision: NO_GO`.
- This is executable synthetic control-flow proof through an existing CI-reachable path, not a production restore or readiness result.

### Symptom/risk, verified coverage gap, failed approach to avoid
- Risk: a correctly named, undecorated `main` can still return success before enforcing runtime authority, or can skip or reorder the `STEPS` validation loop. No actual production incident or successful bypass was observed.
- Verified coverage gap: earlier full-chain guards checked the callable's binding, CLI dispatch and child exit propagation, but not the direct first statements of `main` and their ordered execution path.
- Failed approach to avoid: relying on function signature, text presence or successful import without checking that runtime authority and step identity checks precede direct canonical step execution.

### Correction, recurrence guard and retry condition
- Require the canonical `main` AST to begin with a direct authority identity rejection, a direct `enforce_runtime_authority()` call, a direct step-function identity rejection, and a direct `for relative, label in STEPS: run_step(relative, label)` loop. Require exact rejection diagnostics for fifteen isolated AST mutations.
- Retry only on exact-source CI regression, reviewed legitimate control-flow refactoring, or a demonstrated new execution-order bypass. Preserve known clean-worktree, workflow-write and external-evidence blocker retry conditions.

### Why safe, reusable mechanism and protected-authority check
- Only the existing synthetic negative harness changed; no production writer, generation, human-approved objective, reviewed request, recovery evidence, typed eight-domain record, credential, traffic, readiness or promotion authority changed.
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains PREREQUISITES_BLOCKED with zero registered/semantically eligible generations, objectives, requests, evidence, typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Strict preflight still requires unsuperseded semantically eligible generations from distinct environments plus an explicitly human-approved current objective; new evidence requires a current executable reviewed request; final candidates require typed eight-domain non-resurrection coverage and independent review; human promotion is separate and non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Full-chain default-captured helpers require symbol-specific binding proof

### Material success: outcome and observed evidence
- Initial code commit `5f0de794207d38838563d80e387b291495d876bf` added AST binding checks for `enforce_execution_transport`, `enforce_runtime_authority` and `canonical_script` plus thirty synthetic negative mutations across assignment, import alias, dead branch, namespace dictionary, dynamic execution, duplicate definition and decorator.
- Corrected code commit `aeebbe8006db8f7be4bb22c953dca48d61dc2cad` passed exact-source Backup Restore Admission Chain run `40054328459` (job `120753834003`). Logs explicitly show `PASS reject: thirty full-chain guard/resolver helper binding substitutions`, `Admission-chain full runner negative validation PASS` and `production decision: NO_GO`.
- The changes are confined to the existing CI-reachable synthetic negative harness. The CI-owned stale failure diagnostic was subsequently cleaned up by bounded reconcile commit `ab1bda3cef4a53f90a86b3c05e7b12222266a6b1`.

### Material failure: symptom, evidence, verified root cause, failed approach
- Exact-source run `40054229866` (job `120753515734`) failed at `5f0de794` with `full-chain helper enforce_runtime_authority/globals-update diagnostic drift`. The probe intended to mutate only `enforce_runtime_authority`.
- Verified root cause: the first version of the generic AST classifier rejected every `globals().update(...)` and `exec(...)` call while scanning each protected helper, so the earlier `enforce_execution_transport` check incorrectly classified a mutation to a different helper. This was an overbroad synthetic diagnostic, not a production bypass.
- Failed approach to avoid: reusing a generic dynamic-namespace mutation detector across multiple symbols without checking which symbol the concrete mutation affects, then expecting symbol-specific diagnostics.

### Correction, executable recurrence guard and retry condition
- Scope literal `exec`/`eval` and dictionary update/pop/setitem detection to the targeted helper name; retain conservative rejection for dynamic/unknown keys, `clear` and `popitem`. Preserve exact diagnostic assertions for all thirty probes.
- Reusable mechanism: verify each default-captured authority helper has one synchronous undecorated canonical signature and no static/dynamic rebinding before the full runner can capture it; test every protected symbol independently.
- Retry only on exact-source CI regression, a reviewed helper architecture change or a demonstrated binding bypass. Do not retry unchanged source-binding clean-worktree, external-evidence or workflow-write blockers.

### Why safe and protected-authority check
- No canonical runner, environment generation, human-approved objective, executable reviewed request, generation recovery evidence, typed eight-domain record, credential, traffic, readiness or promotion authority was changed.
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains PREREQUISITES_BLOCKED with zero registered/eligible generations, objectives, requests, evidence, typed records and candidates, and learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Distinct unsuperseded semantically eligible environments, an explicitly human-approved current objective, current executable reviewed drill request for new evidence, complete typed eight-domain non-resurrection coverage, independent review and separate human production promotion remain mandatory. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Dynamic learning CI guard rebinding must be rejected by executable negatives

### Material success: outcome and observed evidence
- Commits `2e9cce93ca763e4a6292080ac5f270d00224e3e4` and `12982ac53f29dafc86cf8018a42d72d1a21009dd` extend the existing autonomous-learning positive and negative validators to reject module-level dynamic replacement of `main` and `validate_learning_guards` through `globals()` subscript/update, module `setattr` and literal `exec`. The ten isolated mutations have symbol-specific canonical diagnostics.
- Commit `23fd243fb37674ed602a3b272b0607f919d5dd08` raises the existing entry-docs CI minimum from 74 to 84 negative cases. Exact-source Operability Contracts run `40054584618` (job `120754611691`) completed SUCCESS and logged `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (84 fail-closed cases)`, and `Memory OS entrypoint document validation PASS`.
- The first two code commits alone did not trigger this path-filtered CI. The legitimate entry-docs minimum-case binding supplied the CI-reachable execution proof; a mere source-shape inspection was not counted as CI success.

### Symptom/risk, verified gap and failed approach to avoid
- Risk: a module-level `globals().update`, `globals()['main']`, `setattr` or `exec` can replace a correctly defined CI learning guard after static definition checks, allowing an apparent entrypoint to skip real learning validation. No production incident or observed successful bypass occurred.
- Verified gap: the existing learning validator's module-scope rebinding analysis covered direct assignments, imports and loop/exception aliases but not dynamic namespace writes.
- Failed approach to avoid: treating the presence of one synchronous `main` or `validate_learning_guards` definition and a direct call as sufficient binding authority without checking module-level dynamic writes; treating non-triggered code commits as exact-source CI proof.

### Correction, recurrence guard and retry condition
- Extend the canonical AST binding detector with symbol-scoped subscript, update/pop, `setattr` and `exec` checks, conservatively rejecting unknown dynamic keys. Add ten isolated negative cases and bind the expanded case count to the existing CI classifier's minimum.
- Retry only after exact-source regression, reviewed legitimate learning-entrypoint architecture changes, or a demonstrated new dynamic rebinding bypass. Do not repeat unchanged workflow-write or source-binding clean-worktree blockers.

### Why safe, reusable mechanism and protected-authority check
- Only learning/entry-docs validators and append-only learning changed; no production writer, recovery generation, approved objective, reviewed request, generation evidence, typed eight-domain record, credential, traffic, readiness or promotion authority was modified.
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains PREREQUISITES_BLOCKED with zero registered/eligible generations, approved objectives, executable requests, evidence, typed records and final candidates, and learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Strict preflight requires unsuperseded semantically eligible generations from distinct environments plus explicit human-approved current objectives; new generation evidence requires a current executable reviewed request; final candidates require complete typed eight-domain coverage and independent review; promotion remains a separate non-automatic human decision. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Full-chain synthetic fixture syntax is a separate fail-closed boundary

### Material success: outcome and observed evidence
- Commit `4413653e90342921b1245646682e09f56faec32f` adds `parse_checked_negative_fixture` and two diagnostic-specific synthetic controls to the existing full-chain negative suite. Multi-line pre-dispatch AST mutations now pass through an explicit literal-backslash-n check and a caught syntax preflight before any security rejection is evaluated.
- Exact-source Backup Restore Admission Chain run `40054725078` (job `120755057943`) completed SUCCESS. The job explicitly logged `PASS reject: two malformed full-chain negative fixture syntax controls`, `PASS reject: fifteen full-chain pre-dispatch eager termination substitutions`, and `Admission-chain full runner negative validation PASS`.
- The change closes a recorded fixture-generation recurrence gap; it is not production recovery evidence.

### Symptom/risk, prior verified cause and failed approach
- Previously recorded run `40053956572` failed when a multi-line negative source was double-escaped, producing `SyntaxError: unexpected character after line continuation character` instead of the intended guard rejection. The corrected suite passed in `40053988293`.
- Failed approach to avoid: introducing or adapting multi-line synthetic AST strings without checking literal escape depth and syntax before interpreting a negative result.

### Correction, executable recurrence guard and retry condition
- Use `chr(92) + "n"` to detect a literal backslash-n and `ast.parse` with an explicit `Fail` diagnostic for malformed Python. A positive multiline fixture and two negative controls verify both failure classes; real security negatives still require their own exact rejection diagnostics.
- Retry only after a new fixture parsing regression, reviewed fixture representation change or a demonstrated case where malformed test input is misclassified as a valid security rejection.

### Why safe, reusable mechanism and protected-authority check
- Only the existing synthetic negative harness and append-only learning were changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, objectives, executable requests, generation evidence, typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Distinct unsuperseded semantically eligible environments, explicitly human-approved current objectives, current executable reviewed requests for new evidence, typed eight-domain non-resurrection coverage, independent review and separate non-automatic human promotion remain mandatory. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Learning CI guard calls cannot be hidden behind nested early exits

### Material success: outcome and observed evidence
- Commits `f566e10b6d387515fd0bca65eb2646d1aa4b86d0` and `33eb238cb46a6f5ebbc140a7fa5e311eeafd2a47` extend the canonical learning validator and existing negative suite to reject eleven early-termination mutations before `validate_learning_guards(failures)`: nested return/raise, direct process exit, dead branch, try/finally, dynamic exec, eager function default and eager class body.
- Commit `d18ed4a5f212b549bccf343f22f97f5ccf7bbff8` raises the entry-docs CI minimum from 84 to 95 fail-closed cases. Exact-source Operability Contracts run `40054920766` (job `120755680392`) completed SUCCESS and logged `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (95 fail-closed cases)` and `Memory OS entrypoint document validation PASS`.
- This is synthetic CI reachability proof, not a production readiness or recovery result.

### Symptom/risk, verified gap and failed approach to avoid
- Risk: a learning CI entrypoint can retain a direct AST call to the bound guard but return/exit from a preceding nested statement or eager definition before that call. No actual production incident or successful bypass was observed.
- Verified gap: the prior learning validator rejected only direct `Return` and `Raise` statements before the call, not nested control flow or explicit process exits.
- Failed approach to avoid: treating a direct call's textual or AST presence as proof of execution without inspecting preceding reachable termination paths.

### Correction, executable recurrence guard and retry condition
- Traverse statements before the bound learning guard call, checking nested returns/raises, explicit process termination, dynamic execution and eager class/default evaluation while excluding deferred function bodies. Require exact canonical rejection diagnostics for eleven independent synthetic mutations.
- The CI entrypoint minimum is bound to the expanded suite count; use `chr(10)` for multi-line mutation fixtures to avoid the previously recorded double-escape failure.
- Retry only on exact-source CI regression, reviewed legitimate control-flow refactoring or a demonstrated new early-termination bypass. Do not retry unchanged external evidence, workflow-write or source-binding clean-worktree blockers.

### Why safe, reusable mechanism and protected-authority check
- Only learning and entry-docs validators plus append-only learning were modified. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, approved objectives, executable requests, recovery evidence, typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight still requires unsuperseded semantically eligible generations from distinct environments plus a human-approved current objective; new evidence requires a current executable reviewed request; final candidates require complete typed eight-domain non-resurrection coverage and independent review; human promotion remains separate and non-automatic. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed non-resurrection admission CLI main binding is independently guarded

### Material success: outcome and observed evidence
- Commit `9be561a986b7eda82630aa760f3d132d7030c94c` extends the existing typed non-resurrection transport-negative suite with a canonical AST positive control and thirteen diagnostic-specific negatives for `main` assignment, tuple rebinding, import alias, dead branch, dynamic namespace mutation, `exec`, class/async/duplicate definitions and decorators.
- Exact-source Backup Restore Non-Resurrection Readonly run `40055052695` (job `120756095481`) completed SUCCESS. Logs explicitly show `PASS reject: thirteen typed admission main rebinding/decorator substitutions`, `Typed non-resurrection execution/registry/reconcile transport negative suite PASS` and `production decision: NO_GO`.
- The existing canonical CI path executes the suite; no separate production authority was created.

### Symptom/risk, verified coverage gap and failed approach
- Risk: the typed admission module can retain a correct-looking `main(canonical_execution_guard=...)` while a later module-level assignment or dynamic write replaces the callable invoked by `python script.py`. No production incident or observed successful bypass occurred.
- Verified gap: previous typed transport negatives protected the child `run_validator` binding and exercised runtime transport substitution but did not verify the module-level `main` binding.
- Failed approach to avoid: treating runtime guard identity or the original main function text as sufficient proof that the actual CLI symbol cannot be replaced.

### Correction, executable recurrence guard and retry condition
- Require exactly one synchronous undecorated typed admission `main` with the canonical default-bound execution guard argument, reject static/dynamic symbol rebinding and require exact diagnostics for thirteen AST mutations.
- Retry only after exact-source CI regression, reviewed legitimate typed admission architecture changes or a demonstrated new main-binding bypass. Unchanged clean-worktree, external evidence and workflow-write blockers retain their recorded retry conditions.

### Why safe, reusable mechanism and protected-authority check
- Only an existing synthetic negative harness and append-only learning were modified. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, objectives, executable requests, generation evidence, typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Distinct unsuperseded semantically eligible environments, a human-approved current objective, current executable reviewed request for new evidence, complete typed eight-domain non-resurrection coverage, independent review and separate non-automatic human promotion remain mandatory. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed non-resurrection CLI dispatch must preserve failure exit

### Material success: outcome and observed evidence
- Commit `2a38dfc120fc0f28dfe17695906be505a48a55b5` adds an AST positive control and thirteen negative probes to the existing typed admission transport-negative suite. The probes reject removed/duplicated/nonterminal `__main__` guards, dead/no-op dispatch, zero exit, unexpected main arguments, alternate exception handlers, swallowed failures and finally branches.
- Exact-source Backup Restore Non-Resurrection Readonly run `40055157780` (job `120756418636`) completed SUCCESS. Logs explicitly show `PASS reject: thirteen typed admission CLI dispatch/failure-exit substitutions`, `Typed non-resurrection execution/registry/reconcile transport negative suite PASS` and `production decision: NO_GO`.
- The synthetic proof is CI-reachable through the existing typed admission validation path; it does not create operational recovery evidence.

### Symptom/risk, verified gap and failed approach
- Risk: a valid typed admission `main` function may exist but not be invoked by the executable script, or its `Fail` exception may be converted to a successful exit. No production incident or observed successful bypass occurred.
- Verified gap: prior typed transport negatives protected child runner and main symbol bindings but did not inspect the live `if __name__ == "__main__"` dispatch or nonzero Fail exit mapping.
- Failed approach to avoid: inferring CLI execution and error propagation from function presence or import-time validation alone.

### Correction, executable recurrence guard and retry condition
- Require one terminal canonical `__main__` guard with direct `try: raise SystemExit(main())` and `except Fail` ending in nonzero `SystemExit`; prove thirteen exact-diagnostic AST mutation rejections.
- Retry only after exact-source CI regression, reviewed CLI architecture changes or a demonstrated new dispatch bypass. Do not retry unchanged clean-worktree, workflow-write or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only the existing synthetic negative validator and append-only learning were modified. Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, objectives, executable requests, evidence, typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Distinct unsuperseded semantically eligible environments, human-approved current recovery objective, current executable reviewed request for new evidence, complete typed eight-domain non-resurrection coverage, independent review and separate non-automatic human promotion remain mandatory. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed admission cannot terminate before guarded CLI dispatch

### Material success: outcome and observed evidence
- Commit `6a37224012b4ad5584567ea76d7852ce9a847bc9` extends the existing typed transport-negative suite with a canonical AST positive control and fifteen negative probes for module-level `raise`, process exit, conditional/try exits, dynamic execution, eager class bodies, decorators, function defaults, class bases and lambda defaults before the typed admission CLI dispatch.
- Exact-source Backup Restore Non-Resurrection Readonly run `40055248661` (job `120756702256`) completed SUCCESS. Logs explicitly show `PASS reject: fifteen typed admission pre-dispatch eager termination substitutions`, `Typed non-resurrection execution/registry/reconcile transport negative suite PASS` and `production decision: NO_GO`.
- The fixture batch uses `chr(10)` for actual newlines, explicitly rejects literal backslash-n and wraps fixture parsing errors so malformed tests cannot be counted as expected guard rejections.

### Symptom/risk, verified gap and failed approach to avoid
- Risk: the typed admission module may define a correct `main` and dispatch guard but terminate successfully during module initialization before reaching it. No production incident or observed successful bypass occurred.
- Verified gap: the previous typed admission main-binding and CLI-dispatch checks did not inspect eager statements and definition expressions preceding the final CLI guard.
- Failed approach to avoid: assuming a terminal canonical `__main__` block is reachable merely because it is present in the source; repeating known double-escaped multiline fixture generation.

### Correction, executable recurrence guard and retry condition
- Reject explicit import-time termination through nested AST traversal while excluding deferred function bodies and including eager defaults/decorators/class bodies. Require exact diagnostics for fifteen isolated mutations.
- Retry only on exact-source CI regression, reviewed legitimate module initialization changes or a demonstrated new early-exit bypass. Do not retry unchanged clean-worktree, workflow-write or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only a synthetic negative suite and append-only learning changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains NO_GO; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, approved objectives, executable requests, recovery evidence, typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Distinct unsuperseded semantically eligible environments, a human-approved current objective, current executable reviewed request for new generation evidence, typed eight-domain non-resurrection coverage, independent review and separate non-automatic human promotion remain mandatory. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed admission main guard and registry load order have executable reachability proof

### Material success: outcome and observed evidence
- Code commit `f905fef40cd06cf9c91bc404df6f4f559a1b5f76` extended the existing CI-reachable typed non-resurrection transport-negative suite with a canonical AST positive control and fourteen diagnostic-specific mutations. The new guard requires the execution-transport identity check, execution transport validation, runtime authority validation, and exact ordered loads of the typed and generation contracts/registries at the start of `main`.
- Exact-source Backup Restore Non-Resurrection Readonly run `40055360132` at that SHA completed SUCCESS. Job `120757043568` explicitly logged `PASS reject: fourteen typed admission main guard/registry reachability substitutions`, `Typed non-resurrection execution/registry/reconcile transport negative suite PASS`, and `production decision: NO_GO`.
- The code commit changed only `scripts/validate-memory-os-backup-restore-non-resurrection-transport-negative.py`; it did not modify the canonical validator or production/recovery authorities.

### Symptom/risk, root cause or explicit unknown, failed approach
- Risk: the typed admission validator could retain correctly named guards while bypassing them through an early success return, dead/inverted condition, or reordered/missing registry load. No production incident or actual bypass was observed.
- Verified coverage gap: prior main-binding, CLI-dispatch and import-time early-exit checks did not establish the order and direct reachability of the first live `main` statements.
- Failed approach to avoid: assuming source-level presence of named guards and registry references proves their execution before admission.

### Correction, executable recurrence guard and retry condition
- Parse the canonical validator's AST, enforce the exact first seven statements, and require precise failure diagnostics for fourteen isolated AST mutations; reuse the existing CI-transitive negative suite instead of creating a parallel authority.
- Retry only after an exact-source CI regression, reviewed legitimate typed admission entrypoint refactor, or demonstrated new reachability bypass. Do not retry unchanged clean-worktree, workflow-write or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only synthetic AST mutations are exercised; no generation, approved objective, executable reviewed request, recovery evidence, typed eight-domain record, credential, traffic, readiness or promotion authority is created or changed.
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. The previously verified strict OPS-P0-007 snapshot remains blocked; this run did not use learning or CI as evidence for any operational gate.
- Preflight requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current objective; new evidence requires a current executable reviewed drill request; final candidates require complete typed eight-domain coverage and independent review; human promotion remains separate and non-automatic.

## 2026-10-24 — Typed child validation gate-order fixture must match the canonical runner

### Material failure: symptom, evidence, root cause, failed approach
- Initial code commit `55c18b6fa5f6c3c951fda8b4952c5d47f6dbaf81` added twenty child-reachability mutations, but exact-source Readonly run `40055771731` and Unreadable Authority Negatives run `40055771756` failed. Both logs showed `TYPED TRANSPORT NEGATIVE FAILED: typed admission child validation must follow canonical gate order` immediately after the existing fourteen main-guard probes passed.
- Verified root cause: the new AST positive control incorrectly expected `writer.validate_registry_for_append(registry)` to follow the two local foundation validators. The canonical typed admission `main` performs writer append validation first, then local Apple/coherent checks, then candidate-boundary checks, then three negative suites.
- Failed approach: relying on a simplified local `main` fixture whose statement order differed from the canonical source. A separate incorrect early-negative mutation in that local fixture was detected and corrected before repository publication.

### Correction, recurrence guard, retry condition
- Correction commit `dd6a36800b648f8652a4d8c497abaab6be1b88bc` enforces `registry append check < local Apple < local coherent < candidate boundary < negative < writer negative < path negative` while retaining twenty exact-diagnostic AST mutations.
- Executable guard: parse the actual canonical admission source as the positive control, then independently mutate child presence, labels, order, dead calls, duplicate calls, early returns, process exits and final return. Preflight any simplified fixture against actual source order; do not count failed positive controls as intended security rejections.
- Retry only on reviewed legitimate gate-order refactor, exact-source CI regression, or demonstrated new child-validation bypass. Do not retry unchanged clean-worktree, workflow-write or external-evidence blockers.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check
- Exact-source Readonly run `40055827388` (job `120758476410`) completed SUCCESS and explicitly logged `PASS reject: twenty typed admission child validation reachability substitutions`, the existing fourteen-case PASS, `Typed non-resurrection execution/registry/reconcile transport negative suite PASS`, and `production decision: NO_GO`. Unreadable Authority Negatives `40055827420` and Reconcile Negative `40055827450` also completed SUCCESS.
- The mechanism operates on in-memory AST copies inside the existing CI-reachable negative harness. No generation, approved objective, reviewed drill request, recovery evidence, typed domain record, credential, traffic, readiness or promotion authority was created or changed.
- Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/semantically eligible generations, approved objectives, executable requests, evidence, typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Strict preflight still requires distinct unsuperseded semantically eligible environments and explicit human-approved current objectives; new evidence requires a current executable reviewed request; final candidates require all gates, complete typed eight-domain coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Final recovery candidate derivation is bound to typed eight-domain coverage

### Material success: outcome and observed evidence
- Commit `31214a33ba70808c2cff59db9aa66392894ad966` adds fourteen exact-diagnostic AST negatives to the existing typed transport-negative suite. It binds the canonical typed admission validator's `base_candidate_ids` and `final_candidate_ids` to distinct upstream predicates, requires `complete_typed_ids` to derive only from complete typed records, and enforces intersection, pending coverage, final equality and registry aggregate-count checks in canonical order.
- Exact-source Non-Resurrection Readonly run `40055994754` (job `120758992920`) completed SUCCESS and explicitly logged `PASS reject: fourteen typed candidate derivation and coverage-gate substitutions`, `PASS reject: twenty typed admission child validation reachability substitutions`, `Typed non-resurrection execution/registry/reconcile transport negative suite PASS` and `production decision: NO_GO`. Exact-source Unreadable Authority Negatives `40055994647` and Reconcile Negative `40055994651` also completed SUCCESS.

### Symptom/risk, root cause or explicit unknown, failed approach
- Risk: a future source edit could derive final candidates directly from base eligibility, replace typed intersection with a union, bypass a final-candidate equality check, or weaken count consistency while the empty current registries still happen to pass. No production incident or observed actual bypass occurred.
- Verified gap: the existing transport negative suite bound entrypoint/child execution but did not independently protect the canonical source expression for candidate derivation and its final typed-coverage gates.
- Failed approach to avoid: inferring full non-resurrection candidate integrity from an empty-registry baseline or from an unexecuted contract declaration without checking the executable derivation.

### Correction, executable recurrence guard and retry condition
- Parse the actual canonical typed admission AST as a positive control. Compare six exact derivation expressions and three final coverage/count gates, require their order, then independently mutate assignments, missing/weakened/duplicated gates and late validation with fourteen exact diagnostics. A source-shaped local fixture was syntax/negative preflighted before publication; no production validator was altered.
- Retry only after an exact-source CI regression, reviewed legitimate candidate-derivation refactor, or demonstrated new typed coverage bypass. Do not retry unchanged clean-worktree, workflow-write or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- All mutations are isolated in-memory AST copies within the existing CI-reachable negative suite; no production-equivalent generation, objective, reviewed request, recovery evidence, typed record, credential, traffic, readiness or promotion authority was changed.
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/semantically eligible generations, approved objectives, executable requests, evidence, complete typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current objective; new evidence requires a current executable reviewed request; final candidates require all generation/objective gates, complete typed eight-domain coverage and independent review; human promotion remains separate and non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed writer append validation and historical row counts remain executable gates

### Material success: outcome and observed evidence
- Code commit `5cfbb2f718d1d91fc1c580c2209ad65319bc14c3` adds fifteen exact-diagnostic AST mutations to the existing typed non-resurrection transport-negative suite. The canonical positive control binds the writer's `validate_registry_for_append(registry)` call, its domain-error conversion and rethrow, the validated-row projection equality, every historical row's `writer.validate_record(row)`, the derived complete count and its fail-closed aggregate gate in execution order.
- Exact-source Non-Resurrection Readonly run `40056107718` (job `120759332838`) completed SUCCESS, logging `PASS reject: fifteen typed writer registry validation and count substitutions`, the earlier twenty child and fourteen candidate probes, `Typed non-resurrection execution/registry/reconcile transport negative suite PASS` and `production decision: NO_GO`. Unreadable Authority Negatives run `40056107722` and Reconcile Negative run `40056107752` also completed SUCCESS.

### Symptom/risk, root cause or explicit unknown, failed approach
- Risk: a later source edit could bypass the canonical writer append authority, swallow its domain failure, skip historical typed row validation, or turn complete-record counts into unverified claims. No actual bypass or production incident was observed.
- Verified coverage gap: existing source-binding and transport probes did not independently check the typed admission `main`'s exact writer-append call, exception path, row projection and complete-count derivation.
- Failed approach to avoid: treating an empty registry or the mere existence of `validate_registry_for_append` as proof that `main` actually invokes it and propagates errors.

### Correction, executable recurrence guard and retry condition
- Parse the actual canonical validator as a positive AST control; require exact writer-append try/except structure, historical row loop and count gates, then exercise fifteen isolated missing, substituted, dead, swallowed, duplicated and reordered mutations with exact diagnostics. The local source-shaped syntax and negative fixture passed before publication; the canonical production validator remains unchanged.
- Retry only after a reviewed legitimate append-validation refactor, exact-source CI regression or demonstrated new validation bypass. Unchanged source-binding clean-worktree, workflow-write and external-evidence blockers retain their recorded retry conditions.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable synthetic negative suite changed; mutations use in-memory AST copies, never production or recovery registries. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, recovery evidence, complete typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight still requires distinct unsuperseded semantically eligible environments and explicit human-approved current objectives; new evidence requires a current executable reviewed request; final candidates require all generation/objective gates, complete typed eight-domain coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — External negative harness binds execution of typed transport guards

### Material success: outcome and observed evidence
- Code commit `c10e592cc35008d32eb8dc0708ff1174c7a4df8f` extends the existing CI-reachable typed load/unreadable-authority negative suite with independent AST verification of the transport-negative suite's `main` entrypoint. It requires the canonical validator source check, eight guard calls in order (including the newly added child, candidate and registry checks), canonical module load, child-exit propagation, registry and reconcile transaction probes, and a terminal success return.
- Exact-source Non-Resurrection Readonly run `40056292188` (job `120759896092`) completed SUCCESS, explicitly logging `PASS reject: fourteen external typed transport guard reachability substitutions`, `Typed unreadable/escaped-authority negative suite PASS`, `Typed non-resurrection execution/registry/reconcile transport negative suite PASS` and `production decision: NO_GO`. Unreadable Authority Readonly `40056292230`, Unreadable Authority Negatives `40056292174` and Reconcile Negative `40056292165` also completed SUCCESS.

### Symptom/risk, root cause or explicit unknown, failed approach
- Risk: a transport negative suite can retain correct-looking guard functions while a later edit removes or dead-branches their `main` invocations, allowing CI to print PASS without exercising those proofs. No actual bypass or production incident was observed.
- Verified gap: the canonical workflow invoked the transport-negative executable, but a separate executable did not independently bind its newly added internal guard calls.
- Failed approach to avoid: equating the presence of a negative function in a source file or the top-level workflow's invocation of that file with proof that the function itself is executed.

### Correction, executable recurrence guard and retry condition
- Reuse the existing load-negative suite as an independent source-level harness. Parse the canonical transport-negative source, enforce exact call order and non-skippable return boundaries, then run fourteen diagnostic-specific in-memory mutations for missing, dead, reordered, duplicated/altered execution boundaries and early returns. The local source-shaped positive/negative fixture and syntax preflight passed before publication.
- Retry only after a reviewed legitimate transport-negative main refactor, exact-source CI regression or demonstrated new guard-invocation bypass. Do not retry unchanged clean-worktree, workflow-write or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only a synthetic negative validator changed. Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, evidence, complete typed records and final candidates; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Distinct unsuperseded semantically eligible environments, explicit human-approved current objectives, current executable reviewed requests for new evidence, complete typed eight-domain coverage, independent review and separate non-automatic human promotion remain mandatory. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Independent eight-domain review omissions and digest drift are negative-tested

### Material success: observed outcome and evidence
- Code commit `2543daf809132b34f600bba0ed8e4228727f8644` extends the existing CI-reachable typed non-resurrection negative admission suite with 32 isolated cases. For each of eight required domains, each SECURITY and OPERABILITY review independently rejects both a missing exact bundle member and a mismatched canonical evidence digest. Each mutation has a specific expected writer-domain rejection diagnostic, and the synthetic state is restored in `finally`.
- Exact-source Backup Restore Non-Resurrection Readonly run `40057960623`, Reconcile Negative run `40057960588` and Non-Resurrection Admission run `40057960628` completed SUCCESS at the code SHA. The Readonly job logged typed admission validation PASS and `production decision: NO_GO`; child-validator stdout is suppressed on success, so individual new case messages were not visible in that job log. The canonical admission invokes the existing negative suite via its fail-closed `run_validator` path.
- Positive controls retain the valid complete eight-domain synthetic record before and after reviewer-specific mutations. These are synthetic tests, never production-equivalent recovery evidence.

### Symptom/risk, verified gap, failed approach
- Risk: one representative review-domain digest or missing bundle member can miss a regression limited to another domain or reviewer. No actual production bypass or incident was observed.
- Verified gap: prior negative probes tested both review roles but bundle omission always removed the last member and digest corruption always targeted the first member; the other domain positions lacked isolated review-specific proof.
- Failed approach to avoid: treating one representative review mutation or any unrelated `writer.Fail` as proof of eight-domain independent reviewer coverage.

### Correction, executable recurrence guard and retry condition
- Reuse the canonical CI-transitive negative suite, its exact-diagnostic `expect_rejected`, targeted per-review state and post-batch positive controls; do not add a parallel contract or change production validators.
- Retry only on exact-source CI regression, reviewed legitimate review-bundle refactor or a demonstrated new per-domain bypass. Do not retry unchanged clean-worktree, workflow-write or external-evidence blockers.

### Orchestration failure: symptom, evidence, root cause or unknown, correction
- A first pre-write patch orchestration failed locally with `SyntaxError: Invalid or unexpected token` and made no repository change. The precise parser location/root cause was not observed; the failed approach mixed quoted multiline replacement literals.
- Correction: use template literals, require each replacement anchor exactly once, bound the delta, and re-read branch head and target blob before writing. A subsequent learning append initially aborted safely when a concurrent diagnostic commit advanced `so` from `2543daf` to `451309e`; no stale write was attempted. Recurrence guard: bounded re-read/compare before each write; retry only when the branch/target precondition is refreshed.

### Why safe, reusable mechanism and protected-authority check
- The code commit changed only the synthetic negative suite. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. No generation, human-approved objective, executable reviewed request, recovery evidence, typed production record, credentials, traffic, readiness or promotion authority was created.
- Preflight still requires distinct unsuperseded semantically eligible environments and an explicit human-approved current objective; new generation recovery evidence requires a current executable reviewed drill request; final candidates require all upstream gates, typed eight-domain coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Independent typed review digest-key coverage is negatively proven

### Material success: observed outcome and evidence
- Code commit `3e3b1e883f609354731bea3c03cf857fcb748b90` adds eighteen exact-diagnostic synthetic negative cases to the existing CI-reachable typed admission suite. Each of eight domain-digest keys is removed separately from SECURITY and OPERABILITY review payloads, and each reviewer independently rejects an extra unreviewed digest key.
- Exact-source Backup Restore Non-Resurrection Readonly run `40058078790` (job `120765395401`) and Reconcile Negative run `40058078976` completed SUCCESS. The Readonly job logged typed admission validation PASS and `production decision: NO_GO`; child-validator stdout is suppressed on success, so individual new case lines are not claimed as independently visible in that log.
- The existing canonical writer checks `set(reviewed_digests) == set(domain_digests)` before comparing digest values. Synthetic positive controls restore valid state after each reviewer batch; no real evidence is admitted.

### Symptom/risk, verified gap, failed approach
- Risk: a future refactor could accept a missing or extra review digest key despite rejecting altered digest values. No actual bypass or production incident was observed.
- Verified coverage gap: prior per-domain tests mutated digest *values* and bundle member references, but did not independently mutate the review digest-map key set for every required domain and each reviewer.
- Failed approach to avoid: inferring digest-key coverage from value-mismatch tests or from empty-registry success; a distinct coverage gate requires distinct negative proof.

### Correction, executable recurrence guard and retry condition
- Reuse the existing synthetic `fake_load` review payload seam and `expect_rejected` exact-diagnostic classifier. Add `MISSING` and `EXTRA` digest-key mutations, isolate each reviewer and domain, restore state in `finally`, and revalidate the unchanged complete record.
- Retry only on exact-source CI regression, reviewed legitimate digest-map refactor or demonstrated new review coverage bypass. Unchanged clean-worktree, workflow-write and external-evidence blockers are not retried.

### Why safe, reusable mechanism and protected-authority check
- The code commit changes only the negative validator. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` still states `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, evidence, complete typed records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight requires distinct unsuperseded semantically eligible environments plus explicit human-approved current objectives; new recovery evidence requires a current executable reviewed request; final candidates require all upstream gates plus complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed reviewer pseudonym format and role identity remain fail-closed

### Material success: observed outcome and evidence
- Code commit `21dbf9ac08113834dccc654fc5e06763db81ca95` adds thirteen isolated exact-diagnostic negative probes to the canonical typed admission negative suite. SECURITY and OPERABILITY reviewers each reject six malformed pseudonym variants (empty, too short, uppercase, whitespace, boolean and overlong), and a SECURITY review cannot claim the OPERABILITY role.
- Exact-source Non-Resurrection Readonly run `40058155785`, Reconcile Negative run `40058155784`, and Generation Binding run `40058155767` completed SUCCESS at that SHA. The Readonly workflow's canonical admission path returned PASS and preserved `production decision: NO_GO`; individual child-negative stdout is suppressed on success, so those case messages were not independently visible in the workflow log.
- The existing writer validates reviewer pseudonyms against its canonical strict pattern and enforces exact reviewType before accepting the review digest; the synthetic valid eight-domain record is revalidated after each reviewer batch.

### Symptom/risk, verified gap, failed approach
- Risk: a future review payload refactor could accept malformed reviewer identities or role substitution while two different-looking pseudonyms still pass a superficial independence check. No actual production bypass or incident was observed.
- Verified gap: prior tests checked identical reviewer pseudonyms and OPERABILITY role substitution, but not reviewer pseudonym syntax for both roles or SECURITY role substitution independently.
- Failed approach to avoid: treating `security != operability` alone as proof that both reviewer identities are well-formed and both review types are bound.

### Correction, executable recurrence guard and retry condition
- Use the existing `fake_load` review payload seam, exact `expect_rejected` diagnostic classifier and `finally` state restoration. Exercise both reviewers without creating a new authority; validate the unchanged complete record between batches.
- Retry only after exact-source CI regression, reviewed legitimate reviewer schema change or demonstrated new identity/role bypass. Do not retry unchanged source-binding clean-worktree, workflow-write or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only synthetic negative tests changed. Production Status `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED`; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. No production-equivalent generation, approved objective, executable reviewed request, recovery evidence, typed production record, credential, traffic, readiness or promotion authority was created.
- Preflight remains restricted to unsuperseded semantically eligible generations from distinct environments plus a human-approved current objective; new generation recovery evidence requires a current executable reviewed request; final candidates require all upstream gates, typed eight-domain coverage and independent review. Human promotion remains separate and non-automatic. Learning/CI never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — All typed domain and review payloads have exact-schema negative coverage

### Material success: observed outcome and evidence
- Code commit `ed4996c7807b407958d887fa90f422fcbc7c6f5d` adds twenty isolated, exact-diagnostic synthetic negatives to the existing CI-reachable typed non-resurrection admission suite: each of eight domain evidence payloads and both review payloads independently reject a missing required `schemaVersion` and an unexpected `unexpectedField`.
- Exact-source Non-Resurrection Readonly run `40058233269` and Reconcile Negative run `40058233407` completed SUCCESS. The canonical Readonly path validated the typed admission and retained `production decision: NO_GO`; child-negative stdout is suppressed on success, so individual case diagnostics are not claimed to have been visible in its job log.
- The canonical writer already checks exact `DOMAIN_EVIDENCE_FIELDS` and `REVIEW_EVIDENCE_FIELDS`. New probes cover those existing guards per domain and reviewer; positive controls restore the valid synthetic record after each mutation batch.

### Symptom/risk, verified gap, failed approach
- Risk: a future payload schema refactor might ignore unknown keys or accept a missing required key for a particular domain or review role while provenance and digest checks still pass. No actual bypass or production incident was observed.
- Verified gap: the existing negative suite covered per-domain provenance, production flags, review bundle and digest bindings but did not exercise each payload's exact field-set rejection independently.
- Failed approach to avoid: assuming matching provenance, eight-domain PASS, or an empty-registry validator result proves exact payload schemas without explicit missing/extra-field negatives.

### Correction, executable recurrence guard and retry condition
- Extend only the existing `fake_load` synthetic payload seam with per-domain and per-review `MISSING`/`EXTRA` mutations, require exact writer diagnostics, restore each state in `finally`, and revalidate the canonical synthetic positive control. No new production contract or authority is created.
- Retry only after an exact-source CI regression, reviewed legitimate typed evidence schema change, or demonstrated field-set bypass. Do not retry unchanged clean-worktree, workflow-write or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only the existing synthetic negative suite changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Registered and semantically eligible generations remain distinct; preflight needs distinct unsuperseded eligible environments and an explicitly human-approved current recovery objective. New generation evidence requires a current executable reviewed drill request; final candidates require all upstream gates, typed eight-domain coverage and independent review; human promotion remains separate and non-automatic. No evidence, credential, traffic, readiness or promotion authority was manufactured. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed review bundle references and digest values reject malformed types

### Material success: observed outcome and evidence
- Code commit `bca2de113efbef53eac65edbf495594f2368f900` extends the existing CI-reachable typed admission negative suite with eight exact-diagnostic cases: both SECURITY and OPERABILITY review payloads independently reject duplicate or non-list reviewed domain references, and invalid-hex or boolean digest values.
- Exact-source Non-Resurrection Readonly run `40058316805` and Reconcile Negative run `40058316813` completed SUCCESS. The Readonly path runs canonical typed admission and preserves `production decision: NO_GO`; individual child-negative output is suppressed on success, so the case-by-case diagnostics are not claimed as separately visible in the job log.
- The existing writer already checks list uniqueness and digest SHA-256 shape before review approval; synthetic positive controls restore a valid eight-domain record after each review-specific mutation.

### Symptom/risk, verified gap, failed approach
- Risk: a later review parser refactor could accept duplicate/non-list reviewed refs or malformed digest types while nominally retaining complete review coverage. No actual production bypass or incident was observed.
- Verified gap: prior negatives exercised missing/extra digest keys and mismatched valid-length digests but did not independently exercise reviewed-reference type/uniqueness or digest type/hex-shape for each review role.
- Failed approach to avoid: equating digest value inequality or set equality alone with complete input-type and uniqueness validation.

### Correction, executable recurrence guard and retry condition
- Extend the existing `fake_load` synthetic seam with `DUPLICATE`, `NON_LIST`, `BAD_HEX` and `BOOLEAN` review-only mutations; require exact domain-specific rejection diagnostics, restore mutation state in `finally`, and validate the unchanged positive control.
- Retry only on exact-source CI regression, reviewed legitimate review payload schema change or demonstrated malformed review input bypass. Do not retry unchanged source-binding clean-worktree, workflow-write or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only a synthetic negative validator changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, approved objectives, executable drill requests, generation evidence, typed records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Preflight still requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current recovery objective; new generation recovery evidence requires a current executable reviewed drill request; final candidates require all upstream gates, complete typed eight-domain coverage and independent review; human promotion remains separate/non-automatic. No production evidence, credentials, traffic, readiness or promotion was created. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Unresolved noncritical findings cannot be relabeled complete typed evidence

### Material success: observed outcome and evidence
- Code commit `174a0faf133d09c56b81fdc073a7719f674f9774` adds two exact-diagnostic negative cases and two positive controls to the existing CI-reachable typed admission suite. LOW/OPEN and MEDIUM/ACCEPTED_WITH_OWNER unresolved findings are accepted only with `evidenceComplete=false`; changing that flag to true is rejected with `evidenceComplete derivation drift` despite eight PASS domains and approved independent reviews.
- Exact-source Non-Resurrection Readonly run `40058388404` completed SUCCESS and retained the canonical typed admission PASS and `production decision: NO_GO`. Child-negative stdout is suppressed on success; the individual new case lines are not claimed as visible in the job log.
- The existing writer derives completeness from eight PASS domain results **and no unresolved findings**. Synthetic controls verify both the legitimate incomplete state and the forbidden complete relabel.

### Symptom/risk, verified gap, failed approach
- Risk: a future completeness refactor could ignore unresolved LOW/MEDIUM findings, admitting a complete typed record even though findings remain. No actual production bypass or incident was observed.
- Verified gap: previous tests rejected HIGH unresolved findings and false completeness with all PASS domains, but did not prove LOW/MEDIUM findings prevent a true completeness claim.
- Failed approach to avoid: inferring the no-findings completeness gate from HIGH/CRITICAL rejection alone or from empty-registry success.

### Correction, executable recurrence guard and retry condition
- Reuse the canonical synthetic record and exact `expect_rejected` classifier; positively validate LOW/OPEN and MEDIUM/ACCEPTED_WITH_OWNER incomplete records, then negatively mutate only `evidenceComplete` while preserving the finding and review bindings.
- Retry only after exact-source CI regression, reviewed legitimate findings policy change or demonstrated completeness bypass. Do not retry unchanged clean-worktree, workflow-write or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only synthetic negative tests changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains blocked with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight still requires unsuperseded semantically eligible generations from distinct environments plus a human-approved current recovery objective; new evidence requires a current executable reviewed drill request; final candidates require all upstream gates, typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed evidence schema versions are bound independently for every domain and reviewer

### Material success: observed outcome and evidence
- Code commit `cc22eca3ebba3ed06ca4145cb0fb7130a0e94c1b` adds ten isolated exact-diagnostic synthetic negative cases to the canonical typed admission suite. Each of the eight domain payloads and each SECURITY/OPERABILITY review payload rejects an obsolete `schemaVersion` even when its field set and provenance bindings otherwise remain valid.
- Exact-source Non-Resurrection Readonly run `40058474714` and Reconcile Negative run `40058474755` completed SUCCESS. The Readonly path validated canonical typed admission and preserved `production decision: NO_GO`; child-negative stdout is suppressed on success, so individual new case lines are not claimed as independently visible in the job log.
- The existing writer already enforces exact domain/review schema versions; the new tests target those guards separately from missing/extra-field tests and restore valid synthetic state after each batch.

### Symptom/risk, verified gap, failed approach
- Risk: a future parser refactor could accept an obsolete schema version while the field set and review digests still match. No actual production bypass or incident was observed.
- Verified gap: prior synthetic negatives checked payload field-set omissions/additions but not the canonical `schemaVersion` value for every domain and each review role.
- Failed approach to avoid: inferring schema-version compatibility from exact field sets or empty-registry success without version-specific rejection probes.

### Correction, executable recurrence guard and retry condition
- Extend only the existing `fake_load` synthetic seam with per-domain and per-review obsolete-version substitutions; require exact canonical writer diagnostics, restore state in `finally`, and revalidate the complete synthetic positive record.
- Retry only after exact-source CI regression, reviewed legitimate evidence schema migration or demonstrated version-bypass. Do not retry unchanged clean-worktree, workflow-write or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only a synthetic negative validator changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable drill requests, recovery evidence, complete typed records and final candidates; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current recovery objective; new generation evidence requires a current executable reviewed request; final candidates require all upstream gates, typed eight-domain non-resurrection coverage and independent review. Human production promotion remains separate/non-automatic. No production evidence, credentials, traffic, readiness or promotion authority was created. Learning/CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Generation independent-review negative diagnostics cover both roles

### Material success: observed outcome and evidence
- Code commit `67f950c7823b84507a6cdabab4ffa84c9099b5a7` extends the existing generation independent-review negative suite. Both SECURITY and OPERABILITY roles now have synthetic positive controls before and after their negative batches; each negative requires the exact canonical review-field diagnostic instead of accepting any `module.Fail`.
- For each role, the suite exercises five provenance bindings, three production boundaries, wrong role, rejected review, four malformed timestamps, six invalid reviewer pseudonyms, missing/extra typed payload fields and obsolete schema version. These are isolated synthetic payloads, not submitted recovery evidence.
- Exact-source GitHub Actions run `40061383655` (job `120775446695`) completed SUCCESS for commit `67f950c`; checkout source verification and final-candidate independent-review readonly validation both succeeded. The job log confirms the generation candidate review negative suite PASS, canonical authority mutation false and human promotion remaining separate. Individual case diagnostics are not printed on success, so per-case log visibility is not claimed.

### Symptom/risk, verified gap, failed approach
- Risk: a future parser change could reject every synthetic review for an unrelated reason while a negative harness that catches any `Fail` still reports PASS. No production bypass or incident was observed.
- Verified coverage gap: the previous `expect_review_payload_fail` accepted any `module.Fail` and exercised payload mutations only for SECURITY; there was no matching synthetic positive control for either role.
- Failed approach to avoid: treating arbitrary rejection of an invalid fixture as proof that the intended role-specific provenance/schema/production guard executed.

### Correction, executable recurrence guard and retry condition
- Reuse the canonical `validate_review` entrypoint and existing in-memory payload seam; require an exact field-specific rejection string, verify the same fixture accepts a valid SECURITY or OPERABILITY review, and restore all monkeypatched functions in `finally`.
- Retry only after an exact-source CI regression, a reviewed legitimate independent-review schema change, or a demonstrated role-specific diagnostic bypass. Do not retry unchanged workflow-write, clean-worktree or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- The code change touched only the CI-reachable synthetic negative suite; it did not change the production validator, recovery contracts/registries, source-order or material-delta authority. The production status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` still says `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight remains limited to unsuperseded semantically eligible generations from distinct environments and a human-approved current recovery objective. New recovery evidence requires a current executable reviewed drill request. Final candidates still require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review; human promotion remains separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Source-order chronology self-test and three review branches are CI-reachable

### Material success: observed outcome and evidence
- Code commit `a2f0bf253c8183f493f25cd8d5fdb1bb1839d91a` extends the existing CI-invoked generation independent-review negative suite to execute the canonical review source-order validator's `self_test()` explicitly. It also uses an in-memory read-only synthetic fixture to prove `validate_row` visits SECURITY, OPERABILITY and cross-generation material-delta review refs and their chronology guards in order.
- The same fixture positively accepts the two-review same-generation case, rejects a same-generation material-delta reference, rejects missing cross-generation material-delta review, and injects one fail-closed chronology rejection for each of the three review branches with exact diagnostics. All source-order functions are restored in `finally`.
- Exact-source GitHub Actions `40061470306` (job `120775706112`) completed SUCCESS for `a2f0bf2`. The job log explicitly includes `PASS: review source-order negative rejects same-commit/stale/non-descendant commits`, the generation candidate review negative suite PASS and canonical authority mutation false.

### Symptom/risk, verified gap, failed approach
- Risk: empty-registry validation could report PASS even if the existing synthetic chronology self-test were never invoked or `validate_row` ceased checking one of the three review branches. No production bypass or incident was observed.
- Verified reachability gap: the owning workflow executed `validate-memory-os-backup-restore-review-source-order.py` without `--self-test`, and the existing CI-bound generation independent-review negative suite did not call `self_test`. The source-order function had self-test code, but its execution was not established by that workflow.
- Failed approach to avoid: treating the existence of a negative self-test or empty-registry success as proof of source-order execution for all candidate review branches.

### Correction, executable recurrence guard and retry condition
- Reuse the existing CI-reachable independent-review negative suite rather than changing the known workflow-write blocker or creating parallel production authority. Invoke the canonical `self_test` and exercise `validate_row` with explicit positive controls, per-branch chronology failure injection and exact rejection diagnostics.
- Retry only after exact-source CI regression, reviewed legitimate source-order/branching refactor, or a demonstrated chronology bypass. Unchanged workflow-write, source-binding clean-worktree and external-evidence blockers are not retried.

### Why safe, reusable mechanism and protected-authority check
- The code change touched only synthetic negative tests. The source-order validator, recovery contract/registry and production evidence remain unchanged. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` still says `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Preflight requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current recovery objective. New generation recovery evidence remains bound to a current executable reviewed request; final candidates require all upstream generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human production promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Source-order main must execute canonical row validation, not merely exist

### Material success: observed outcome and evidence
- Code commit `81f75e6c484c98015df43753c73e7d244d0bfb53` extends the existing CI-reachable generation independent-review execution negative suite with a source-level AST guard for the canonical review source-order validator's `main`. It binds the exact `--self-test` branch, direct contract validation, canonical registry row source, direct `enumerate(rows)` loop and `validate_row(row, index)` call, and absence of an early top-level success exit before row validation.
- Eleven isolated AST mutations independently reject removed/dead review loops, empty iteration, swapped row target, skipped row validation, early success return, unbound row source, omitted contract validation, unconditional self-test exit, shadowed main and duplicated main. The actual canonical source is the positive control; mutants are in-memory AST copies.
- Exact-source GitHub Actions run `40061561746` (job `120775987434`) completed SUCCESS for `81f75e6`. Its log explicitly reports `PASS: source-order main AST execution binding rejects 11 review bypass mutations` and `Memory OS generation independent-review execution authority negative PASS`.

### Symptom/risk, verified gap, failed approach
- Risk: the source-order validator can retain correct helper implementations while `main` skips all registry rows or returns success early; an empty-registry run and direct helper self-test alone would not detect that main-path bypass. No production incident or bypass was observed.
- Verified coverage gap: prior source-order self-test covered helper chronology semantics, and the independent-review negative suite exercised `validate_row` directly, but neither bound the canonical `main` entrypoint to direct per-row execution.
- Failed approach to avoid: inferring canonical main execution reachability from helper existence, empty-registry PASS, or independent helper-only negative tests.

### Correction, executable recurrence guard and retry condition
- Parse the actual source-order file as the positive AST control and require direct canonical row-validation and contract-gate structure. Test representative bypasses with in-memory AST mutations and exact guard diagnostics; never modify the production validator or review evidence.
- Retry only after exact-source CI regression, reviewed legitimate main-path refactor or demonstrated new source-order execution bypass. Do not retry unchanged workflow-write, clean-worktree or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- The code change is confined to an existing CI-invoked negative validator; source-order production validator, recovery contracts, registries, objective/review/evidence authorities and human promotion boundary are unchanged. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable drill requests, generation evidence, complete typed eight-domain records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight still uses only unsuperseded semantically eligible generations from distinct environments plus an explicitly human-approved current recovery objective. New generation recovery evidence requires a current executable reviewed request; final candidates require all existing generation/objective gates plus complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Every independent-review contract rule has an exact-diagnostic negative

### Material success: observed outcome and evidence
- Code commit `86b31c868ab56510b1341042b99bf647aa5a0129` strengthens the existing generation independent-review negative suite. The contract mutation harness now requires a valid canonical positive control before and after each isolated mutation and compares the exact canonical `module.Fail` diagnostic rather than accepting any failure.
- Synthetic negatives independently disable all eleven mandatory independent-review `recordRules`, each of five provenance-binding rules, and the separate independent-review promotion boundary. Additional cases reject removed/duplicate/extra required payload fields, obsolete review schema, widened review namespace, substituted material-delta/source-order validators and a substituted reviewer role map.
- Exact-source GitHub Actions `40061636237` (job `120776206495`) completed SUCCESS for `86b31c8`. Its log confirms the canonical generation candidate review negative suite PASS, the source-order main AST eleven-mutation PASS and canonical generation evidence authority mutation false.

### Symptom/risk, verified gap, failed approach
- Risk: a synthetic contract mutation might be rejected for an unrelated reason, while a harness that catches any `module.Fail` still reports PASS. No actual production bypass or incident was observed.
- Verified gap: previous `expect_contract_fail` accepted any `module.Fail`, exercised only a subset of mandatory review rules, and lacked an explicit positive control around each mutation.
- Failed approach to avoid: treating generic failure or one representative rule mutation as proof that all independent-review contract gates are independently enforced.

### Correction, executable recurrence guard and retry condition
- Reuse the existing CI-bound contract mutation seam. Require canonical positive validation before/after each mutation; require exact rule-specific failure text and restore the original `load_json` in `finally`. Exercise every mandatory rule and provenance binding separately without creating another authority.
- Retry only after an exact-source CI regression, reviewed legitimate independent-review contract change or demonstrated guard bypass. Do not retry unchanged workflow-write, clean-worktree or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- The code change modifies only synthetic negative tests. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Preflight still requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current recovery objective; new recovery evidence requires a current executable reviewed request. Final candidates require all existing generation/objective gates plus complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Generation recovery negative symlink fixtures cannot delete occupied evidence

### Material success: observed outcome and evidence
- Code commit `f7568ca0c0ae7947991a7390a37b172d6be37a8f` hardens the existing generation evidence negative suite's symlink escape fixture. It removes unconditional `unlink(missing_ok=True)`, refuses occupied regular files and dangling symlinks, validates canonical non-symlinked ancestor directories, and binds created-only cleanup to the original parent device/inode and the symlink's device/inode and external target.
- Isolated temporary-directory controls verify occupied-file bytes, dangling-symlink preservation, missing/outside/symlinked-parent rejection, and a valid canonical parent. Exact-source Generation Evidence Reconcile Negative run `40061719092` (job `120776466630`) completed SUCCESS, logging `Memory OS drill-request-bound generation negative admission suite PASS`, `generation review refs escape repository: false`, `unexpected exception accepted as a valid rejection: false` and `production decision: NO_GO`.
- During the learning append, `so` advanced from `f7568ca` to bot diagnostic commit `81f2946`; the stale-head write was aborted before mutation. A fresh comparison showed only the operability inventory diagnostic fixture changed; this append uses the current head and target blob.

### Symptom/risk, verified root cause and failed approach
- Risk: the prior negative fixture unconditionally unlinked `docs/fixtures/memory-os-operability/.generation-evidence-review-escape` before creating a synthetic symlink and again in `finally`, potentially deleting a newly occupied real artifact. No deletion incident was observed.
- Verified cause: the fixture lacked vacant-leaf, canonical-parent and created-object ownership checks. The same failure class had already been fixed in the typed non-resurrection sibling.
- Failed approach to avoid: assuming a fixed hidden fixture path is vacant or that unconditional cleanup is safe simply because the test expects ownership.

### Correction, executable recurrence guard and retry condition
- Reuse the existing typed non-resurrection fixture ownership pattern with explicit collision/alias controls and inode-bound cleanup. Never replace occupied repository paths or create missing repository directories to make a negative fixture pass.
- Retry only on exact-source CI regression, reviewed fixture-location change or demonstrated ownership bypass. Unchanged workflow-write, clean-worktree and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable generation evidence negative harness changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current recovery objective. New generation evidence requires a current executable reviewed drill request; final candidates require all existing generation/objective gates plus complete typed eight-domain non-resurrection coverage and independent review. Human promotion is separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — External harness binds source-order AST guard execution

### Material success: observed outcome and evidence
- Code commit `cef108e2d0b7e86885f501f7972f2fd41f0853ce` extends the existing CI-reachable generation independent-review negative suite with an external AST harness. It requires the separate independent-review execution-negative executable to define its source-order AST guard, retain its positive/negative mutation loop and call that guard as the first direct step of its canonical `main`.
- Seven in-memory AST negatives reject omission, reordering, dead-branching, duplicate invocation, missing guard definition, missing mutation loop and shadowing of the execution-negative `main`.
- Exact-source GitHub Actions run `40061872914` (job `120776941112`) completed SUCCESS for `cef108e`; the log explicitly reports `PASS: source-order main AST execution binding rejects 11 review bypass mutations`, `PASS: external source-order AST guard reachability rejects 7 mutations`, generation candidate review negative suite PASS and canonical generation evidence authority mutation false.

### Symptom/risk, verified gap and failed approach
- Risk: the eleven-mutation source-order AST guard could remain in a source file but be removed or dead-branched from its own negative suite's `main`, allowing a superficial workflow success without executing the proof. No production bypass or incident was observed.
- Verified gap: the previous workflow executed the independent-review execution-negative file, but no separate executable bound the newly introduced internal source-order AST guard to that file's direct main path.
- Failed approach to avoid: equating function presence or workflow-level invocation of a negative suite with proof that its internal guard is executed.

### Correction, executable recurrence guard and retry condition
- Reuse the existing sibling generation independent-review negative suite as an immutable external source-level harness; parse the actual execution-negative source as positive control and mutate in-memory AST copies with exact rejection diagnostics. No workflow mutation or parallel authority was introduced.
- Retry only after exact-source CI regression, reviewed legitimate execution-negative refactor or demonstrated guard-reachability bypass. Unchanged workflow-write, clean-worktree and external-evidence blockers are not retried.

### Why safe, reusable mechanism and protected-authority check
- Only a synthetic CI-reachable negative validator changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight requires distinct unsuperseded semantically eligible environments and a human-approved current recovery objective; new recovery evidence requires a current executable reviewed request. Final candidates require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion is separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Full-chain external self-symlink fixture uses exclusive ownership

### Material success: observed outcome and evidence
- Code commit `06449ef2f13d594693b8a4a687897c49c2fe8a69` replaces the full admission-chain negative suite's derived sibling `/tmp` path and unconditional `unlink(missing_ok=True)` with an exclusively created `NamedTemporaryFile` external symlink target. Cleanup is conditional on this invocation owning the file, and checks regular-file type plus the original device/inode before unlinking.
- Exact-source Backup Restore Admission Chain run `40061966819` (job `120777313102`) completed SUCCESS. Its log explicitly reports `PASS negative: self symlink substitution`, `PASS negative: broken self symlink`, `PASS negative: escaping self symlink`, `Admission-chain full runner negative validation PASS` and `production decision: NO_GO`.
- A separate local temporary-directory control verified that the new relative link target resolves to the exclusively created external file.

### Symptom/risk, verified root cause and failed approach
- Risk: the previous self-symlink negative computed an outside path from the temporary directory name, wrote to it without exclusive creation, and unconditionally unlinked that path even for non-escaping cases. A collision could overwrite/delete an unrelated file. No collision or deletion incident was observed.
- Verified root cause: the sibling path was not acquired through exclusive creation, and cleanup was not bound to the file's identity.
- Failed approach to avoid: treating a path derived from a random temporary directory name as equivalent to an exclusively owned artifact or using unconditional cleanup on an unowned path.

### Correction, executable recurrence guard and retry condition
- Use `NamedTemporaryFile(delete=False)` to acquire a unique outside target, retain its original inode identity and refuse cleanup after substitution. The existing negative suite still verifies the three canonical self-symlink failure modes, now without unowned path deletion.
- Retry only after exact-source CI regression, reviewed legitimate fixture topology change or demonstrated external-fixture ownership bypass. Unchanged workflow-write, source-binding clean-worktree and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the synthetic full-chain negative suite changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Preflight still requires unsuperseded semantically eligible generations from distinct environments and a human-approved current recovery objective; new recovery evidence requires a current executable reviewed request. Final candidates require all existing generation/objective gates plus complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Generation-binding symlink cleanup requires original inode identity

### Material success: observed outcome and evidence
- Code commit `69ef9e05d6a4906650804fc09fd38593173da540` hardens the existing generation-binding negative suite's fixed repository-root symlink fixture. The fixture still refuses occupied leaves; cleanup now requires the original non-symlinked repository parent device/inode, the symlink's original device/inode and its expected external target before unlinking.
- Exact-source Backup Restore Generation Binding run `40062120867` (job `120777689247`) completed SUCCESS, explicitly logging `PASS reject: local foundation evidence symlink escapes repository root`, `Memory OS backup/restore generation binding negative suite PASS` and `production decision: NO_GO`. Generation Binding Readonly run `40062120922` also completed SUCCESS.
- During learning persistence, `so` advanced to bot diagnostic commit `351e33c`; the stale-head write was aborted. A fresh comparison showed only the operability inventory diagnostic fixture changed, and this append uses the current target blob.

### Symptom/risk, verified root cause and failed approach
- Risk: the previous fixture checked vacancy before creating the symlink but unconditionally called `unlink(missing_ok=True)` during cleanup; if the path or parent were substituted, cleanup could delete an object it did not create. No replacement or deletion incident was observed.
- Verified gap: cleanup was not bound to the created symlink or its parent, unlike the existing hardened typed non-resurrection fixture pattern.
- Failed approach to avoid: treating a one-time vacancy check as permanent ownership throughout a negative test.

### Correction, executable recurrence guard and retry condition
- Reuse the existing parent/leaf identity-bound cleanup mechanism. Refuse to unlink if the root becomes a symlink, its inode changes, the leaf inode changes or the leaf no longer resolves to the expected temporary target.
- Retry only after exact-source CI regression, reviewed fixture-path change or demonstrated ownership bypass. Unchanged workflow-write, clean-worktree and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable synthetic generation-binding negative validator changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight still requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current recovery objective. New recovery evidence requires a current executable reviewed request; final candidates require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Generation-evidence contract-ref symlink cleanup is inode-bound

### Material success: observed outcome and evidence
- Code commit `1b1c0fb08106731842451dfd92d0726295baa255` hardens the existing generation-evidence contract-path negative suite's fixed repository-root symlink fixture. The fixture retains its occupied-path rejection and now requires the original non-symlinked root device/inode, created symlink device/inode and expected external target before cleanup.
- Exact-source Backup Restore Generation Evidence run `40062230682` (job `120778013900`) completed SUCCESS. Its log explicitly reports `PASS reject: repository-local symlink escaping generation-evidence authority root`, `Memory OS generation evidence contract path negative suite PASS` and `production decision: NO_GO`. Backup Restore Admission Chain `40062230684` also completed SUCCESS.

### Symptom/risk, verified root cause and failed approach
- Risk: the previous negative fixture refused occupied leaves before creation but unconditionally called `unlink(missing_ok=True)` in cleanup; a substituted leaf or parent could cause the test to delete an object it did not create. No substitution or deletion incident was observed.
- Verified gap: cleanup did not bind the original parent and leaf identity. The sibling generation-binding and typed non-resurrection suites already demonstrate a reusable inode-bound cleanup pattern.
- Failed approach to avoid: treating a one-time vacant-path assertion as permanent ownership of a repository-relative fixture path.

### Correction, executable recurrence guard and retry condition
- Reuse the established parent/leaf identity-bound cleanup. If the root is substituted, its inode changes, the leaf inode changes or the symlink no longer targets the intended temporary artifact, fail closed without unlinking it.
- Retry only after exact-source CI regression, reviewed fixture-path change or demonstrated ownership bypass. Unchanged workflow-write, clean-worktree and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable synthetic contract-path negative suite changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight still requires distinct unsuperseded semantically eligible environments and a human-approved current recovery objective; new recovery evidence requires a current executable reviewed request. Final candidates require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Generation writer authority negative modules use held exclusive file descriptors

### Material success: observed outcome and evidence
- Code commit `69d47645fd3bdd885cefac464a0064038f22edd8` hardens the existing generation-evidence writer authority negative suite. Temporary executable modules are now written through the original `mkstemp` file descriptor with `os.fdopen`, rather than closing it and reopening the path by name. The fixture parent is required to be a canonical non-symlinked repository directory; cleanup requires the original parent and leaf device/inode and refuses substituted files.
- Exact-source Backup Restore Unreadable Authority Negatives run `40062350757` (job `120778373346`) completed SUCCESS, explicitly logging `PASS: complete generation-evidence executable/data/lock/review authority substitution matrix is rejected`, `generation-evidence writer CLI authority substitutions accepted: false`, and `generation-evidence substitution modules isolated under operability fixtures: true`. Unreadable Authority Readonly `40062350695` also completed SUCCESS. Generation Evidence and Admission Chain workflows were still in progress at the time of this record.

### Symptom/risk, verified root cause and failed approach
- Risk: the previous negative harness created a repository-local temp module with `mkstemp`, immediately closed the descriptor, then reopened the path with `Path.write_text`. A substituted path could redirect the write; unconditional `unlink(missing_ok=True)` could delete a replacement. No actual race or deletion was observed.
- Verified gap: exclusive creation was not retained through publication and cleanup lacked parent/leaf identity checks.
- Failed approach to avoid: assuming a unique `mkstemp` pathname remains exclusively owned after closing its descriptor, or unconditionally unlinking it after arbitrary test execution.

### Correction, executable recurrence guard and retry condition
- Keep the exclusive descriptor open through writing, capture `os.fstat` identity, check the canonical fixture parent and require the original file identity before cleanup. On a write failure, only clean up a leaf that still matches the created inode.
- Retry only after exact-source CI regression, reviewed fixture-path change or demonstrated temp-module substitution. Unchanged workflow-write, clean-worktree and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable synthetic writer-authority negative suite changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current recovery objective; new generation evidence requires a current executable reviewed drill request. Final candidates require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Typed source-binding negative fixture must never unlink production evidence

### Material success: observed outcome and evidence
- Code commit `e852c91c01071baa5e49427a0aa429053280601b` replaces destructive fixture creation in the existing typed non-resurrection source-binding negative suite. The canonical evidence parent must already exist, be non-symlinked at every ancestor and retain its inode; the fixed negative leaf must be vacant, including dangling symlinks. The file is created exclusively with `os.open(O_CREAT|O_EXCL)`, written through the held descriptor and cleaned up only if the parent and created leaf still match their original identities.
- Isolated temporary-directory controls reject occupied regular files, dangling symlinks, missing parents and parents outside the test root without changing the occupants. The post-source negative also requires the exact `evidence missing from sourceCommitSha` diagnostic rather than accepting any `writer.Fail`.
- Exact-source Backup Restore Non-Resurrection Reconcile Negative run `40062452646` (job `120778682734`) completed SUCCESS, logging `PASS reject: post-source typed evidence`, `Memory OS backup/restore non-resurrection source-binding negative suite PASS`, `post-source typed evidence accepted: false` and `production decision: NO_GO`. Non-Resurrection Readonly run `40062452681` also completed SUCCESS.

### Symptom/risk, verified root cause and failed approach
- Risk: the previous negative harness called `POST_SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)`, unconditionally unlinked the fixed `docs/evidence/backup-restore/non-resurrection/source-binding-negative.json` path, then used `Path.write_text` and unconditionally unlinked it again. A real occupied evidence path or symlinked parent could be destroyed or overwritten. No actual deletion was observed.
- Verified root cause: no canonical-parent/vacancy precondition, no exclusive creation and no cleanup ownership binding.
- Failed approach to avoid: deleting a fixed evidence path to make a negative fixture available, or interpreting any rejection as proof of the intended source-commit binding.

### Correction, executable recurrence guard and retry condition
- Reuse the existing typed fixture collision and parent/leaf identity pattern, with exclusive descriptor-held publication and exact diagnostic proof. Never create missing repository evidence directories or overwrite occupied leaves to satisfy a test.
- Retry only after exact-source CI regression, reviewed legitimate fixture path change or demonstrated source-binding/fixture ownership bypass. The known Operability Inventory clean-worktree interference remains a separate scoped blocker; this change does not claim to resolve it.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable synthetic source-binding negative suite changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Preflight still requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current recovery objective; new recovery evidence requires a current executable reviewed request. Final candidates require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Drill-request writer negative temp modules retain exclusive descriptor ownership

### Material success: observed outcome and evidence
- Code commit `dc3883a64a918ee0d142b040c2e0b8877b08b150` hardens the existing drill-request writer authority negative suite. Its `mkstemp` module fixtures are now written through the original held descriptor, with canonical non-symlinked repository parent checks and original parent/leaf device-inode binding. Cleanup tracks only files exclusively created in the current negative case, including files created before a fixture registration error, and refuses substituted files.
- Exact-source Backup Restore Unreadable Authority Negatives run `40062543011` (job `120778958179`) completed SUCCESS, explicitly logging `PASS: drill request executable/data/lock authority substitutions are rejected`. Unreadable Authority Readonly run `40062543041` also completed SUCCESS. Admission Chain was still running at the time of this record.

### Symptom/risk, verified root cause and failed approach
- Risk: the previous negative harness called `mkstemp`, immediately closed the exclusive descriptor, reopened the pathname via `Path.write_text`, then unconditionally `unlink(missing_ok=True)` for cleanup. A substituted path could redirect the write or cause cleanup to delete an unrelated file. No actual race or deletion was observed.
- Verified gap: exclusive ownership was not retained through publication and cleanup lacked inode checks and coverage of files created before `cleanup.append`.
- Failed approach to avoid: assuming a temporary pathname remains exclusively owned after closing its descriptor, or using an unverified cleanup list to delete repository-local fixture files.

### Correction, executable recurrence guard and retry condition
- Reuse the generation writer's descriptor-held publication mechanism; track created path identities, compare them with expected cleanup registrations, and require unchanged canonical parent and file inode before unlinking. A write failure can clean up only a file matching the created inode.
- Retry only after exact-source CI regression, reviewed legitimate fixture parent change or demonstrated substitution bypass. Unchanged workflow-write, clean-worktree and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable synthetic drill-request writer authority negative suite changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Preflight requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current recovery objective; new generation evidence requires a current executable reviewed request. Final candidates require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Material-delta review negatives bind exact provenance and all contract rules

### Material success: observed outcome and evidence
- Code commit `98a8166eb38995252032c3db44fd37d6f37239c2` strengthens the existing generation material-delta review negative suite. Every synthetic payload mutation requires the exact canonical `records[0].materialDeltaReviewRef` diagnostic, with a passing canonical payload before and after mutation. It covers five provenance fields, approval, three production boundaries, timestamp/reviewer validity, missing/extra typed fields and obsolete schema.
- Contract mutations require exact diagnostics and positive controls before/after each case. They cover schema/root/validator/negative-validator authority, removed/duplicate/extra required fields, all thirteen mandatory material-delta `recordRules`, and the separate typed material-delta promotion boundary.
- Exact-source Generation Independent Review Negative run `40062636037` (job `120779220154`) completed SUCCESS, logging `PASS: material-delta review negatives reject runtime authority substitution, generic refs, semantic binding drift, candidate/promotion drift, unsafe claims, contract drift, and post-commit edits`. Review Source Order `40062635977`, Readonly `40062635952` and Generation Binding `40062635966` also completed SUCCESS.
- Before the learning append, `so` advanced to bot diagnostic commit `662acc1`. The stale-head write was aborted, the latest branch/target/protected blobs re-read, and the comparison confirmed only the operability inventory diagnostic fixture changed.

### Symptom/risk, verified gap and failed approach
- Risk: a negative payload/contract mutation could be rejected by an unrelated parser error while a harness catching any `module.Fail` reports PASS; representative contract mutations cannot prove every cross-generation gate. No production bypass or incident was observed.
- Verified gap: prior payload/contract negative helpers accepted any `module.Fail`, lacked paired canonical positive controls and exercised only some mandatory material-delta rules.
- Failed approach to avoid: treating generic failure or one representative rule as proof of intended provenance, schema, production or promotion boundaries.

### Correction, executable recurrence guard and retry condition
- Reuse canonical payload/contract validator entrypoints, restore monkeypatches in `finally`, require exact failure diagnostics and independently mutate every mandatory rule. Keep source-order, typed eight-domain and human-promotion authorities separate.
- Retry only after exact-source CI regression, reviewed legitimate material-delta contract/schema change or demonstrated guard bypass. Unchanged workflow-write, clean-worktree and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable synthetic material-delta negative suite changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current recovery objective; new generation evidence requires a current executable reviewed request. Final candidates require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Material-delta registry negatives must reach the row validator

### Material failure/risk: symptom, evidence, verified cause and failed approach
- Symptom/risk: three synthetic material-delta registry negatives could report PASS without exercising the intended generic-ref, same-generation or path-traversal rejection. No production bypass or incident was observed.
- Verified source evidence: the previous `expect_registry_fail` replaced `module.enforce_runtime_authorities` with a lambda, called `module.main()` and accepted any `module.Fail`. Canonical `main` invokes `enforce_execution_authority()` before row validation; that guard captures the original helper identity and rejects the lambda substitution. The negative harness could therefore pass at execution-helper drift rather than `validate_row`.
- Verified root cause: the fixture bypassed a canonical execution helper while relying on `main` to execute downstream semantics. Failed approach: using an authority-violating monkeypatch as setup for a downstream negative and accepting any failure as proof of that guard.

### Correction, executable recurrence guard and retry condition
- Code commit `887a32baff48c877b9c821d2e959bad08227609e` removes the vacuous monkeypatch and temporary registry file. Each negative now calls the actual `module.validate_row`, requires the exact intended diagnostic, and positively validates a canonical same-generation/null-review row before and after mutation.
- Exact-source Generation Independent Review Negative run `40062743178` (job `120779537307`) completed SUCCESS, logging `PASS: material-delta review negatives reject runtime authority substitution, generic refs, semantic binding drift, candidate/promotion drift, unsafe claims, contract drift, and post-commit edits`. Review Source Order `40062743218`, Readonly `40062743159` and Non-Resurrection Reconcile Negative `40062743279` also completed SUCCESS.
- During learning persistence, `so` advanced to bot diagnostic commit `7340ecc`; the stale-head write was aborted, and a fresh comparison confirmed only the operability inventory diagnostic fixture changed.
- Retry only after exact-source CI regression, reviewed row-validation refactor or demonstrated bypass. Helper-only negatives do not prove end-to-end main execution; that remains separately guarded. Unchanged workflow-write, clean-worktree and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable synthetic material-delta negative suite changed; canonical validator, contracts, registries and evidence remain unchanged. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED` with zero registered/eligible generations, approved objectives, executable requests, generation evidence, complete typed records and final candidates. Learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preflight requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current recovery objective; new generation evidence requires a current executable reviewed request. Final candidates require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Candidate review-pair negative proof must reach both distinctness guards

### Material success: observed outcome and evidence
- Code commit `8ac4a57c9bad958bc04e7b5a80bacd607fa55143` extends the canonical independent-review negative suite with a direct AST binding to the actual `candidate_reviews_approved` source. Ten negative mutations remove, weaken, hide or reorder Security/Operability typed review validation, distinct review references, distinct reviewer identities, and the positive return.
- Exact-source Backup Restore Generation Independent Review Negative run `40065447437` (job `120787616882`) completed SUCCESS. Its log explicitly reports `PASS: candidate pair direct source binding rejects 10 validation/distinctness bypasses` and the canonical generation candidate review negative suite PASS. Backup and Restore Contracts on the same code HEAD also completed SUCCESS.
- The generic-ref negative now requires the actual source-order namespace rejection; a previously mislabeled same-ref case was corrected to the missing in-namespace review evidence it actually exercises, with an exact source-order rejection diagnostic.

### Symptom, evidence, verified root cause, failed approach
- Verified coverage weakness, not a production incident: the previous generic and reused-review negative cases accepted any `Fail`. The supposed reused review path `docs/evidence/backup-restore/README.md` does not exist in the inspected repository tree, so that case could not reach the candidate's distinct-ref check. A failing test was not observed before this correction.
- Root cause: early source-order/file-presence rejection was treated as proof of a later candidate-level distinctness boundary.
- Failed approach to avoid: labeling a missing evidence-file rejection as proof of review reuse, or accepting any exception without checking which canonical authority rejected it.

### Correction, executable recurrence guard, retry condition
- The existing CI-reachable negative suite now checks the exact early rejection diagnostic and independently proves that the actual candidate function directly executes both typed review validations and both distinctness checks in the correct order. Ten source mutations must be rejected with exact guard diagnostics.
- This is source-level execution-binding proof, not a fabricated passing production review pair or a claim that a real reviewed candidate exists. A future isolated runtime pair test must satisfy source-order and material-delta positive controls before it can claim end-to-end pair-level rejection.
- Retry this guard only after exact-source CI regression, a reviewed change to the canonical candidate function, or demonstrated AST binding bypass. Do not retry unchanged clean-worktree, workflow-permission or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only a synthetic negative validator changed; no production registry, reviewed evidence, objective, generation or promotion authority was written. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisite-blocked; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Reuse the pattern: identify the actual earliest rejection boundary, require its exact diagnostic, and use canonical positive controls plus direct source-binding negative mutations for later guards when real evidence cannot safely be manufactured.
- Registered generations are not semantic preflight eligibility. Preflight still requires unsuperseded semantically eligible generations from distinct environments and a human-approved current objective; new recovery evidence needs a current executable reviewed drill request. Final candidates still require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion is separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Review append-only negative needs both history and creation-byte controls

### Material success: outcome and observed evidence
- Code commit `52e169b3b7e51c8fcec20b545e3dcf84b27113a6` extends the independent-review negative suite with an isolated temporary review file, one-commit synthetic history, an exact `git show` response, and positive/negative/positive creation-byte immutability checks. Multiple committed versions now require the precise append-only diagnostic instead of any `Fail`.
- Exact-source Backup Restore Generation Independent Review Negative runs `40065533990` (job `120787871898`) and `40065548828` completed SUCCESS. The first log explicitly reports `PASS: review append-only history and initial-blob immutability positive/negative controls`; Backup and Restore Contracts runs `40065534254` and `40065548861` also completed SUCCESS.
- Follow-up code commit `7e1521b942aa38821cb5ef8afa9945c4303b6a0a` simplifies synthetic payload bytes to canonical Python newline literals and has its own exact-source Independent Review Negative and Contracts CI SUCCESS.

### Symptom, evidence, verified root cause and failed approach
- Verified coverage weakness, not a production incident: the previous negative changed synthetic Git history to two commits and accepted any `Fail`; it did not prove that a one-commit review with unchanged bytes passed or that a changed creation blob was rejected.
- Root cause: history-count rejection was treated as proof of both history immutability and creation-byte binding. The initial new fixture also used an unnecessary escaped-newline replacement expression, an avoidable recurrence risk for earlier fixture escaping mistakes.
- Failed approach to avoid: relying on any exception or a multi-commit-only test as proof of exact creation-byte immutability; building synthetic bytes through ambiguous escape replacement.

### Correction, executable recurrence guard and retry condition
- Exercise the actual canonical `require_append_only_review` function in a disposable directory with exact mocked `git show` arguments and creation bytes. Require positive unchanged bytes, exact rejection of changed bytes, and recovery of the positive control. Restore all patched transport/history functions in `finally`.
- Keep newline bytes as explicit canonical literals. Retry only after exact-source CI regression, reviewed change to the canonical append-only implementation, or demonstrated mutation bypass. Existing unrelated external dependency and clean-worktree blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the synthetic negative validator changed. No registry, recovery evidence, production status, objective, credential, traffic or promotion authority was written. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisite-blocked; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Preserve the separation between registered and semantically eligible generations, distinct eligible environments, current human-approved objective, executable reviewed request for new recovery evidence, complete typed eight-domain non-resurrection coverage, independent review and separate non-automatic human promotion. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Material-delta review immutability needs creation-blob positive/negative controls

### Material success: outcome and observed evidence
- Code commit `3fb4253aff54178c3f373d89cbf9cd3512f1b19c` extends the existing material-delta review negative suite with an isolated synthetic review file, exact mocked creation-commit `git show`, one-commit unchanged-byte positive control, changed-byte negative control and restored positive control.
- Exact-source Backup Restore Generation Independent Review Negative run `40065616811` (job `120788120064`) completed SUCCESS. Its log explicitly reports `PASS: material-delta append-only history and creation-blob immutability positive/negative controls`, followed by the material-delta review negative suite PASS. The same job also confirms the independent-review candidate pair source-binding and creation-byte controls.

### Symptom, evidence, verified root cause and failed approach
- Verified coverage gap, not an observed production incident: the prior material-delta negative injected two synthetic history commits and accepted any `Fail`. It did not prove unchanged first-commit bytes are accepted or post-creation byte changes rejected at the correct canonical boundary.
- Root cause: the multi-commit history failure was used as a proxy for byte-level append-only immutability.
- Failed approach to avoid: accepting an arbitrary exception from a history-count-only fixture as proof of both history and content immutability.

### Correction, executable recurrence guard and retry condition
- Reuse the independently validated Security/Operability review fixture mechanism, with canonical newline bytes from the start, exact expected diagnostics, and a disposable path that never touches repository evidence. Restore `git_history` and `subprocess.run` in `finally`.
- Retry only after exact-source CI regression, reviewed canonical material-delta validator change, or demonstrated bypass. Do not retry unchanged external evidence, workflow-permission or clean-worktree blockers.

### Why safe, reusable mechanism and protected-authority check
- Only the synthetic material-delta negative validator changed; no recovery evidence, production registry, objectives, credentials, traffic, readiness or promotion authority was written. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisite-blocked; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Registered and semantically preflight-eligible generations remain distinct; preflight needs distinct unsuperseded eligible environments and a current human-approved objective; new recovery evidence needs a current executable reviewed request. Final candidates require all generation/objective gates plus typed eight-domain non-resurrection coverage and independent review. Human production promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Material-delta runtime substitution negatives require exact authority diagnostics

### Material success: outcome and observed evidence
- Code commit `ce1bcffee610b6f06cecf9cb56195478dea09548` strengthens four material-delta runtime authority substitution cases (contract, registry, validator, negative validator). The unchanged canonical execution/runtime authority is a positive control before and after each substitution; the mutated `main()` must reject at the exact intended path authority.
- Exact-source Backup Restore Generation Independent Review Negative run `40065668501` (job `120788275084`) completed SUCCESS, including the canonical material-delta review negative suite PASS and creation-blob controls.

### Symptom, evidence, verified root cause and failed approach
- Verified test weakness, not a production incident: prior substitutions accepted any `module.Fail` from `main()`, so unrelated early rejection could masquerade as protection of the target contract/registry/validator path.
- Root cause: runtime substitution checks asserted only rejection class, not the intended canonical authority diagnostic.
- Failed approach to avoid: accepting arbitrary fail-closed exceptions as evidence that the targeted authority guard actually executed.

### Correction, executable recurrence guard and retry condition
- Assert exact contract, registry, validator and negative-validator path drift diagnostics while verifying unchanged canonical bytes and successful pre/post authority checks. Reuse this pattern for other negative suites after searching existing source/CI reachability.
- Retry only on exact-source CI regression, reviewed canonical runtime authority changes, or demonstrated misclassification. Do not retry unchanged external-evidence, workflow-permission or clean-worktree blockers.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable synthetic material-delta negative validator changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisite-blocked; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- No production-equivalent generations, objectives, drill/recovery evidence, credentials, traffic, readiness or promotion were created. Distinct unsuperseded semantic eligibility, current human-approved objective, current executable reviewed request, typed eight-domain non-resurrection coverage, independent review and separate non-automatic human promotion remain mandatory. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Independent-review runtime substitution diagnostics must identify the actual authority

### Material success: outcome and observed evidence
- Code commit `b439c7e225ceb31f3ea3638b4cb45c2c43ee2cc1` requires exact rejection diagnostics for five independent-review runtime substitutions: contract, registry, material-delta validator, review source-order validator and independent-review validator. The unchanged canonical execution/runtime authorities must pass both before and after each negative mutation.
- Exact-source Backup Restore Generation Independent Review Negative run `40065727361` (job `120788455456`) completed SUCCESS and logged the generation candidate review negative suite PASS, the ten candidate pair source mutations PASS, and append-only creation-blob controls PASS.

### Symptom, evidence, verified root cause and failed approach
- Verified test weakness, not a production incident: the previous five substitution cases accepted any `module.Fail` and therefore could not distinguish the intended runtime path rejection from unrelated earlier failure.
- Root cause: rejection-class-only assertions did not bind test outcomes to the protected authority actually under mutation.
- Failed approach to avoid: counting any fail-closed exception as a proof that a specific substituted validator/registry/contract was rejected at its intended guard.

### Correction, executable recurrence guard and retry condition
- Map each substituted authority to its exact canonical path-drift diagnostic. Require unmodified execution/runtime positive controls before and after mutation, preserve original contract/registry bytes and restore the substituted module attribute in `finally`.
- Retry only on exact-source CI regression, reviewed canonical authority changes or demonstrated diagnostic bypass. Unchanged clean-worktree, external-evidence and workflow-permission blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the synthetic independent-review negative suite changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisite-blocked; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- No production-equivalent generations, objectives, drill/recovery evidence, credentials, traffic, readiness or promotion were created. Preflight still requires distinct unsuperseded semantically eligible environments and a current human-approved objective. New recovery evidence requires a current executable reviewed request; final candidates require all existing gates, complete typed eight-domain non-resurrection coverage and independent review. Human production promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — External CI harness must prove candidate pair negative execution reachability

### Material success: outcome and observed evidence
- Code commit `d7b5aede161f1becd9743c2498f1808bac03b7cc` extends the existing independent-review execution-negative suite to inspect the separate CI-invoked independent-review negative harness. It requires exactly one candidate-pair proof definition, its second direct `main()` step before validator loading, and no top-level reassignment.
- Six negative mutations remove, move, hide, duplicate or shadow the proof call/definition and must fail with exact diagnostics.
- Exact-source Backup Restore Generation Independent Review Negative run `40065799032` (job `120788672371`) completed SUCCESS, explicitly logging `PASS: external candidate pair negative harness reachability rejects 6 bypasses`, `Memory OS generation independent-review execution authority negative PASS`, and `PASS: candidate pair direct source binding rejects 10 validation/distinctness bypasses`.

### Symptom, evidence, verified root cause and failed approach
- Verified coverage risk, not a production incident: the previously added candidate-pair mutation helper could be present in the repository yet become ineffective if the independent-review negative harness stopped invoking it. Its own function-level negative tests cannot prove that their caller still runs.
- Root cause: a helper's existence and passing internal mutations are distinct from external CI entrypoint reachability.
- Failed approach to avoid: treating a standalone test helper's source or self-report as sufficient proof that the workflow actually executes it.

### Correction, executable recurrence guard and retry condition
- Use the existing external execution-negative harness as the immutable caller for a direct AST reachability check, then mutate the harness's invocation and definition in memory. Keep the canonical workflow's current execution path; no new parallel authority is introduced.
- Retry only after exact-source CI regression, reviewed change to the negative harness call graph or demonstrated source-binding bypass. Unchanged workflow-write, clean-worktree and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the CI-reachable synthetic execution-negative validator changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisite-blocked; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- No production-equivalent generations, objectives, drill/recovery evidence, credentials, traffic, readiness or promotion were created. Registered generations remain distinct from unsuperseded semantically eligible generations; preflight requires distinct eligible environments and a human-approved current objective. New recovery evidence requires a current executable reviewed request. Final candidates require all generation/objective gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion is separate/non-automatic. Learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Real review-pair rejection needs an isolated Git chronology positive control

### Material success: outcome and observed evidence
- Code commit `3f291e850bacfffda397d9b3dc9eccd16ddbf208` adds a disposable, self-contained Git repository to the CI-reachable independent-review negative suite. It copies the canonical validators and contract, commits a synthetic source authority, then commits typed Security and Operability reviews strictly after that source with fixed UTC creation/review times.
- The real canonical `candidate_reviews_approved` function accepts the valid synthetic Security/Operability pair. A different Operability review using the Security reviewer is rejected specifically at `Security and Operability reviewers must remain distinct`; reusing the Security review file as Operability evidence is rejected specifically at `operabilityReviewRef reviewRole mismatch`. The original valid pair remains accepted afterward.
- Exact-source Backup Restore Generation Independent Review Negative run `40065889641` (job `120788938015`) completed SUCCESS and explicitly logged `PASS: isolated Git source-order positive pair and exact reviewer/ref reuse runtime negatives`, along with the six external harness reachability mutations and ten direct candidate source-binding mutations.

### Symptom, evidence, verified root cause and failed approach
- Verified coverage weakness, not a production incident: the previous reused-ref negative pointed to a missing repository file and failed during source-order/path resolution. The AST source guard proved the candidate distinctness checks existed but did not exercise a real, valid reviewed pair or reach reviewer reuse rejection at runtime.
- Root cause: missing prerequisite-positive source chronology, committed typed payloads and reviewer-role evidence allowed early failures to masquerade as candidate-level reuse coverage.
- Failed approach to avoid: treating a generic or missing review path, or static source checks alone, as runtime proof of independent reviewer identity and role binding.

### Correction, executable recurrence guard and retry condition
- Use an exclusively owned temporary Git repository with deterministic source/review commit times, canonical validator files, typed payloads and exact review source-order binding. Establish a passing positive pair, mutate one semantic dimension through separately committed synthetic review files, require exact rejection diagnostics, then reconfirm the positive pair.
- This is synthetic negative evidence only. It never creates a real reviewed drill request, recovery objective, production-equivalent generation, production evidence or promotion authority.
- Retry only on exact-source CI regression, reviewed canonical candidate/source-order semantics changes or demonstrated runtime bypass. Unchanged external-evidence, workflow-permission and clean-worktree blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- All synthetic Git commits and review files exist only inside a temporary directory and are destroyed afterward. The production repository's canonical evidence/registries and promotion authorities were not modified.
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisite-blocked; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Registered and semantically eligible generations are distinct. Preflight still requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current objective; new generation evidence requires a current executable reviewed request. Final candidates require all generation/objective gates plus typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — External CI harness binds real review-pair runtime proof, not just its AST helper

### Material success: outcome and observed evidence
- Code commit `1a61071d64fcbb8c3bcdc0a32de52c5b2a93ae84` extends the existing independent-review execution-negative harness to require exactly one `prove_runtime_review_pair_controls` definition and a fourth direct `main()` step after canonical validator loading. It rejects five additional mutations that remove, hide, duplicate, shadow or delete the runtime proof.
- Exact-source Backup Restore Generation Independent Review Negative run `40065952831` (job `120789135859`) completed SUCCESS. Its log explicitly reports `PASS: external candidate pair negative harness reachability rejects 11 bypasses` and `PASS: isolated Git source-order positive pair and exact reviewer/ref reuse runtime negatives`.

### Symptom, evidence, verified root cause and failed approach
- Verified CI-reachability risk, not a production incident: the new isolated Git positive/negative runtime test could have been skipped by a future harness change even while the older AST-only pair proof continued to pass.
- Root cause: the external harness originally bound only the source-level proof invocation, not the later real Git runtime proof.
- Failed approach to avoid: inferring runtime execution from a test helper's presence or from a different static guard's success.

### Correction, executable recurrence guard and retry condition
- Extend the existing external AST execution boundary to bind both source-level and runtime pair proof calls. In-memory negative mutations must fail at exact invocation/definition/shadowing diagnostics. Keep the workflow and production validators unchanged.
- Retry only after exact-source CI regression, reviewed harness call-graph changes or demonstrated bypass. Unchanged clean-worktree, workflow-permission and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Only the synthetic CI execution-negative validator changed. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisite-blocked; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- No production-equivalent generations, objectives, drill/recovery evidence, credentials, traffic, readiness or promotion were created. Registered and unsuperseded semantically eligible generations remain distinct. Preflight requires distinct eligible environments and a current human-approved objective; new evidence requires a current executable reviewed request; final candidates require all existing gates, complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Real Git review source-order negatives must distinguish same-commit and timestamp violations

### Material success: outcome and observed evidence
- Code commit `3e2b3515fe4401dade8a1140cf835a5d7ce554e3` expands the existing disposable Git independent-review pair fixture with two additional immutable typed Operability reviews: one timestamped before the source commit, one after the review creation commit.
- The real canonical candidate validator now proves exact rejection of three independently mutated cases: sourceCommitSha equal to review creation commit, reviewedAt before source commit, and reviewedAt after review creation commit. The original valid review pair remains accepted afterward.
- Exact-source Backup Restore Generation Independent Review Negative run `40066020828` (job `120789338343`) completed SUCCESS and explicitly logged `PASS: isolated Git positive pair and exact reviewer/ref reuse plus three source-order runtime negatives`.

### Symptom, evidence, verified root cause and failed approach
- Verified test coverage gap, not an observed production incident: source-order chronology previously had isolated unit/AST negative proof, but the new end-to-end Git review pair fixture exercised only a valid post-source pair and reviewer/reference reuse.
- Root cause: runtime pair tests did not independently mutate source commit identity and review timestamps while preserving committed, canonical typed review files.
- Failed approach to avoid: inferring that unit chronology checks alone prove the full candidate admission path rejects stale/same-commit reviews at the intended authority.

### Correction, executable recurrence guard and retry condition
- Extend the same isolated Git fixture, commit all typed reviews once with deterministic UTC commit times, and mutate only the candidate's source SHA or selected review ref. Require exact canonical source-order diagnostics and a restored positive control.
- Retry only after exact-source CI regression, reviewed chronology semantics changes or demonstrated bypass. Unchanged clean-worktree, workflow-permission and external-evidence blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- Synthetic Git commits, review files and candidate rows remain entirely within a disposable directory; they are not production or recovery evidence. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisite-blocked; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- No production-equivalent generations, objectives, drill/recovery evidence, credentials, traffic, readiness or promotion were created. Preflight still requires distinct unsuperseded semantically eligible environments and a current human-approved objective; new generation evidence needs a current executable reviewed request; final candidates require all generation/objective gates, typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Cross-generation material-delta review must pass real Git positive control before negatives

### Material success: outcome and observed evidence
- Code commit `6686fd53f06a46cab4c25e334f054de5f8be965b` extends the disposable Git candidate-review fixture with a genuinely typed, post-source synthetic cross-generation material-delta review and matching independent Security/Operability reviews. The real canonical `candidate_reviews_approved` accepts both same-generation and cross-generation synthetic positive controls.
- Three cross-generation/same-generation negative mutations must fail at exact authorities: missing cross-generation material-delta reference, forbidden same-generation material-delta reference, and cross-generation material-delta payload bound to an unrelated restore target generation. Both positive controls remain accepted after negative cases.
- Exact-source Backup Restore Generation Independent Review Negative run `40066090816` (job `120789546736`) completed SUCCESS and explicitly logged `PASS: isolated Git same/cross-generation positive pairs and exact reviewer/ref, chronology and material-delta runtime negatives`.

### Symptom, evidence, verified root cause and failed approach
- Verified coverage gap, not a production incident: previous end-to-end Git candidate review tests exercised the same-generation branch only; separate material-delta unit/negative tests did not prove a valid cross-generation reviewed candidate reaches all three canonical review authorities together.
- Root cause: lack of a complete synthetic positive cross-generation evidence/reference set in the isolated runtime fixture.
- Failed approach to avoid: treating material-delta payload unit tests or early missing-ref rejection as equivalent to real source-order, typed material-delta and independent review integration.

### Correction, executable recurrence guard and retry condition
- In the same disposable Git repository, commit all synthetic typed review files once after the source commit with deterministic UTC times. Exercise positive same/cross-generation paths, mutate one material-delta authority dimension per negative, require exact rejection and recheck both positive paths.
- Retry only after exact-source CI regression, reviewed canonical cross-generation semantics changes or demonstrated bypass. Unchanged external-evidence, workflow-permission and clean-worktree blockers remain scoped.

### Why safe, reusable mechanism and protected-authority check
- All synthetic records, commits and review payloads remain inside a temporary test repository and cannot satisfy actual production evidence or promotion gates. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains prerequisite-blocked; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Registered generations remain distinct from unsuperseded semantically eligible generations. Preflight requires distinct eligible environments and an explicitly human-approved current objective; new recovery evidence requires a current executable reviewed request. Final candidates require all generation/objective gates plus complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate/non-automatic. Learning and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Cross-generation candidate predicate must reject each incomplete typed overlay independently

### Material success: outcome and observed evidence
- Code commit `a85cc0f6e2f9e2e141620650c5306b269ed81075` extends the existing generation-evidence negative suite's disposable cross-generation candidate positive control. It adds 24 candidate-level negative mutations: missing and failed evidence for each of the eight required typed domains, absent/reused typed review references, incomplete coverage, production-evidence relabeling, duplicate typed overlays, and an overlay bound to a different generation.
- The fixture first confirms `writer.candidate(valid) is True`; each mutation separately requires `base_candidate(valid) is True` while the final `writer.candidate(valid)` is false. It restores the original temporary overlay bytes in `finally`, requires the valid candidate to recover after every mutation, and checks final byte-for-byte restoration.
- Post-write GitHub reads confirmed the new code is present at source blob `1133959a2fde908975e83b15fc9d5c285ea7eb2c`. The commit-associated workflow query returned no runs and combined commit statuses were empty; exact-source CI execution and runtime PASS are **not yet observed**.

### Symptom, observed evidence, root cause and failed approach
- Verified coverage gap (not a production failure): the previous cross-generation positive fixture checked only that a complete synthetic typed overlay unlocked the candidate. The separate typed negative suite tested domain/review admission, but the generation candidate fixture did not independently show that each typed-domain or typed-review failure revoked final candidacy while all pre-overlay gates remained satisfied.
- Root cause: the positive cross-layer fixture did not include per-domain and review/binding negative transitions.
- Failed approach to avoid: inferring cross-layer candidate revocation solely from an isolated typed row rejection, or accepting a negative when the base generation/objective/request predicate already failed.

### Correction, executable recurrence guard and retry condition
- Reuse the existing temporary cross-generation fixture and real candidate predicate; mutate only the temporary typed registry, assert the base predicate remains true, assert final candidacy becomes false, restore bytes and re-establish the positive control after every case.
- This is a structural synthetic candidate-boundary test. The temporary noncanonical overlay does not substitute for full canonical typed payload/digest validation or real independent Git review evidence; those remain separate canonical validators.
- Retry exact-source runtime/CI validation when a suitable workflow run for this code SHA becomes observable or a supported executable checkout is available. Do not claim CI success from source inspection. Do not retry unchanged clean-worktree, workflow-permission or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only the existing CI-reachable synthetic negative suite changed. The new fixture writes solely to an exclusively owned temporary registry and restores it; no canonical evidence/registry or production authority is modified.
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` still declares `NO_GO`, OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED`, and learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Registered generations remain distinct from unsuperseded semantically eligible environments. Preflight requires two distinct eligible environments and a current explicitly human-approved objective. New generation evidence requires a current executable reviewed request. Final candidates require all generation/objective gates plus complete typed eight-domain non-resurrection coverage and independent review. Human production promotion remains separate and non-automatic. Learning, synthetic tests and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Candidate negative-case inventory must match its recorded count

### Material success: outcome and evidence
- Code commit `732e4a1d229a28025d13f08a7abb916a96fa576b` adds two independent synthetic final-candidate negatives to the same disposable cross-generation fixture: missing Operability review and an undeclared ninth typed domain.
- The complete case inventory is now exactly 24: 16 per-domain missing/FAIL probes (eight domains each), plus eight distinct overlay review/completeness/provenance/production-boundary probes. GitHub source blob `0925ec67f7d9f62ac017011ce2e022644c4d71df` contains both additional cases. No exact-source CI result has yet been observed.

### Symptom, evidence, verified root cause and failed approach
- The preceding learning entry described 24 probes although the initial commit contained only 22 (16 domain probes plus six overlay probes).
- Root cause: the narrative case count was not reconciled against the actual test-call inventory before recording it.
- Failed approach: trusting a manually estimated probe count without a deterministic source inventory.

### Correction, recurrence guard and retry condition
- Two independently useful cases close the count gap while strengthening the cross-generation candidate boundary. The helper continues to assert base eligibility remains true, final candidacy becomes false, temporary bytes restore, and the positive candidate recovers after every mutation.
- Future claims of negative-probe totals must be calculated from the source's actual loop cardinality plus explicit calls, not from a planned count. Retry runtime validation only after an executable exact-source checkout or corresponding workflow run becomes available; no CI success is inferred.

### Why safe, reusable mechanism and protected-authority check
- Only the synthetic negative fixture changed. Production Status remains `NO_GO` at blob `ce67e9353d6583e4eaf792470563cad25a7396b3`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` at blob `dbaa36b082366737dca2461d15748103b9740ef6`; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Synthetic fixtures and learning cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates. Distinct semantically eligible unsuperseded environments, a current human-approved objective, a current executable reviewed drill request, complete typed eight-domain non-resurrection coverage, independent review and separate non-automatic human promotion remain mandatory.

## 2026-10-24 — Candidate fixture cleanup must be bound to exclusive file identity

### Material success: outcome and observed evidence
- Code commit `34077ac49193ab322b413bd85e5fe8158029b44c` adds descriptor/inode ownership tracking to transient typed domain and review files created by the existing generation-candidate mutation harness. Before writing an owned leaf, it verifies canonical non-symlinked ancestors and the original parent/leaf identity, then opens without following a leaf symlink when supported and checks the descriptor inode before truncation.
- Code commit `88e636936d9c94bfa3f44666c0037919026be5a3` makes the separate registry-row mutation harness call the same ownership-bound cleanup function instead of independently unlinking paths. GitHub post-write source reads confirm both bindings. Exact-source CI/validator execution is not yet observed; these are static source/authority checks only.

### Symptom, evidence, verified root cause and failed approach
- Verified negative-fixture safety risk, not a reported deletion incident: both candidate suites formerly called unconditional `path.unlink()` on transient repository-local typed evidence files after closing their creation descriptors. A path or parent substitution before cleanup could delete an object not created by the harness; ordinary `Path.write_text` could follow a replaced leaf symlink.
- Root cause: creation ownership was not persisted across subsequent writes and cleanup, and the registry-row harness duplicated unsafe cleanup logic.
- Failed approach to avoid: trusting a random temporary filename or cleanup list as proof of continuing ownership after the file descriptor closes.
- A first read-only post-write check incorrectly required the literal `os.O_NOFOLLOW` while the implementation uses `getattr(os, "O_NOFOLLOW", 0)` for portability; the precondition check aborted without a write. Root cause was a mismatch between the checker string and the actual implementation. Corrected check verifies the real expression. Recurrence guard: inspect the actual source syntax before creating literal source-presence assertions; retry only if the source or expected expression changes.

### Correction, executable recurrence guard and retry condition
- Register original parent and leaf device/inode immediately after exclusive `NamedTemporaryFile` creation. Require unchanged canonical ancestors and parent/leaf identities before cleanup; require the opened descriptor's inode to match before truncating an owned file. Reuse the shared helper in both harnesses, including when a build fails before a path reaches the explicit cleanup list.
- Retry runtime validation when exact-source CI or a supported executable checkout is available. Revisit the fixture only if CI fails, canonical typed evidence paths change, or a demonstrated identity/substitution bypass remains. Do not retry unchanged workflow-permission, clean-worktree or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Changes are confined to two synthetic CI negative harnesses; they do not create canonical generation evidence, production traffic, credentials, recovery objectives, reviewed requests, readiness or promotion.
- Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged. Registered and semantically preflight-eligible generations remain distinct; distinct unsuperseded eligible environments and a current human-approved objective remain mandatory. New evidence needs a current executable reviewed drill request, and final candidates need complete typed eight-domain non-resurrection coverage plus independent review. Human promotion remains separate/non-automatic; learning and CI never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Fixture ownership checks need their own non-destructive negative proof

### Material success: outcome and observed evidence
- Code commit `8f4d84604942627532e2a507718d6539c1c470a4` extends the existing candidate-mutation negative harness with three fail-closed probes for the newly introduced ownership helper. Two probes alter only the recorded parent/leaf inode values in memory, demand exact rejection diagnostics from the actual descriptor-bound write path, and verify the original evidence bytes remain unchanged. A third passes an unowned cleanup path and requires rejection before any unlink.
- The harness restores the recorded identities in `finally` and rechecks the positive candidate predicate. Post-write GitHub source inspection confirms these executable assertions exist at blob `eb3ccd18a67f52b4024f76d9a897d227d6498dac`; runtime/CI PASS is not yet observed.

### Symptom, evidence, root cause and failed approach
- Coverage gap, not an observed filesystem incident: the initial ownership guard was present in source but had no negative case proving its parent/leaf identity checks actually rejected mismatches without touching evidence bytes.
- Root cause: safety implementation and negative proof were introduced separately.
- Failed approach to avoid: treating the mere presence of an inode comparison as executed fail-closed evidence.

### Correction, recurrence guard and retry condition
- Use the already-owned synthetic typed-domain file as positive control; mutate only the in-memory ownership tuple (never replace real paths), require exact rejection, byte preservation and positive candidate recovery. Test unowned cleanup rejection before deletion.
- Retry exact-source runtime/CI validation when a workflow run or supported executable checkout is available; do not infer success from static source inspection. Revisit on a demonstrated bypass or reviewed ownership/fixture semantics change, not unchanged external or permission blockers.

### Why safe, reusable mechanism and protected-authority check
- All negative mutations are confined to the synthetic harness's in-memory identity registry. Production Status blob `ce67e9353d6583e4eaf792470563cad25a7396b3` remains `NO_GO`; OPS-P0-007 snapshot blob `dbaa36b082366737dca2461d15748103b9740ef6` remains `PREREQUISITES_BLOCKED`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remains unchanged.
- Registered and semantically eligible environments remain distinct, preflight needs two distinct unsuperseded eligible environments and a current human-approved objective, new evidence needs a current executable reviewed request, and final candidates need complete typed eight-domain coverage and independent review. Human production promotion remains separate/non-automatic. Learning, synthetic tests and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## 2026-10-24 — Validate fixture parent before exclusive leaf publication

### Material success: outcome and evidence
- Code commit `33f884170f11114affcaa29072c5e63f96ba76c9` adds a canonical non-symlinked parent/ancestor check before `NamedTemporaryFile` creates any typed evidence leaf in the candidate mutation harness. The same parent is checked again and bound to the created file identity after exclusive creation.
- GitHub source read confirms the pre-publication guard at blob `093ca012eb2d87b8733594bcb9e6c642b85095e5`. No exact-source CI/validator execution has yet been observed.

### Symptom, evidence, root cause and failed approach
- Verified code-order risk, not a reported filesystem incident: the initial ownership hardening checked parent identity after the temporary file had already been created, leaving the creation step itself exposed to a pre-existing symlinked evidence parent.
- Root cause: safety validation was placed after, rather than before, the filesystem side effect.
- Failed approach to avoid: considering a post-creation identity check sufficient protection against a malicious parent present before file creation.

### Correction, executable recurrence guard and retry condition
- Call the existing canonical parent validator immediately before the exclusive file-creation operation; retain the post-creation parent and leaf identity checks and non-destructive cleanup guards.
- Retry exact-source runtime validation when a corresponding workflow run or executable checkout becomes available. Revisit if canonical fixture directories change, CI regresses or a demonstrated ancestor substitution bypass remains. Do not retry unchanged permission, clean-worktree or external-evidence blockers.

### Why safe, reusable mechanism and protected-authority check
- Only the existing synthetic candidate mutation harness changed. Production Status remains `NO_GO` at blob `ce67e9353d6583e4eaf792470563cad25a7396b3`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` at blob `dbaa36b082366737dca2461d15748103b9740ef6`; learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged.
- Distinct unsuperseded semantically eligible environments, a current human-approved objective, a current executable reviewed drill request, typed eight-domain non-resurrection coverage, independent review and separate non-automatic human promotion remain mandatory. Learning, synthetic tests and CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.
