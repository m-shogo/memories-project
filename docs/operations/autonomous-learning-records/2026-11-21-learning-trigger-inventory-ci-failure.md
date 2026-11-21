# Supplemental OPS learning — trigger inventory CI failures (2026-11-21)

Append-only learning only. Not production, backup/restore, recovery, drill, credential, traffic, readiness or promotion evidence.

## Material failure 1: Autonomous Learning Guard

- **Symptom:** GitHub Actions run [44843007883](https://github.com/m-shogo/memories-project/actions/runs/44843007883), job 136655804632, failed in `Validate learning contract and executable negatives`.
- **Observed evidence:** The canonical learning contract validator printed PASS. The negative validator then raised `RuntimeError: Autonomous Learning Guard event trigger authority changed` from `autonomous_learning_guard_event_paths(..., event, 15)` in `prove_upload_route_go_direct_inputs` at line 5644. The newly committed workflow has 19 literal paths per push/PR event, not the previously hard-coded 15.
- **Verified root cause:** The newly added supplemental CI path triggers changed the reviewed workflow path inventory without updating the independent negative validator's hard-coded expected inventory. This is a source/validator consistency failure, **not** proof that supplemental history self-tests passed or failed.
- **Failed approach:** Extend the workflow triggers and executable steps in isolation without first checking all exact-count consumers of the workflow source.
- **Correction:** Reconcile the existing negative validator's reviewed inventory and its upload-route snapshot intersection using actual source inputs; preserve negative cases for missing/extra/duplicate/aliased triggers. Do not merely suppress or skip the validator.
- **Recurrence guard:** Add an executable negative that requires any workflow trigger addition to be reflected in all dependent reviewed inventories and still rejects omitted required paths.
- **Retry condition:** Re-read latest `so`, both source files, and the existing upload-route snapshot authority; run the affected negative suite and observe a clean CI run before claiming PASS.

## Material failure 2: Backup Restore Helper Ancestor Reachability

- **Symptom:** GitHub Actions run [44842982425](https://github.com/m-shogo/memories-project/actions/runs/44842982425), job 136655719367, failed at `Prove seven canonical ancestor negatives remain reachable`.
- **Observed evidence:** The job log printed `HELPER ANCESTOR REACHABILITY FAILED: independent learning workflow source trigger drift`. The independent validator's `validate_independent_learning_workflow` has an exact `required_authority_paths` set that predates the four supplemental workflow triggers.
- **Verified root cause:** A stale reviewed trigger inventory rejected the newly expanded workflow. The workflow's other semantic and security checks must still be retained.
- **Failed approach:** Update the learning workflow without reconciling the independently maintained ancestor reachability guard.
- **Correction:** Update the independently reviewed required trigger inventory and its step authority assertions to account for the new supplemental validator invocation, without weakening the seven canonical ancestor targets.
- **Recurrence guard:** Add a negative fixture proving the independent validator rejects removal of the supplemental history validator's CI trigger or execution step.
- **Retry condition:** Re-read latest `so` and both guard sources; run positive and negative modes, then verify the exact-source CI outcome.

## Protected authority and scope

Read-only CI logs establish failures, not production facts. At observation, `contracts/operations/production-operability-status.json` had blob SHA `8d4e2848df463601eea6f836cce2817af4f19d25` and `productionDecision=NO_GO`. No production authority, OPS-P0-007 generation eligibility, human recovery objective, reviewed executable drill request, typed eight-domain non-resurrection evidence, independent review, or human promotion decision is supplied by this record. The previously recorded canonical ~4.17MB transport failure remains a separate unchanged blocker and must not be retried unconditionally.
