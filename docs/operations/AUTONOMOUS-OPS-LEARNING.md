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
