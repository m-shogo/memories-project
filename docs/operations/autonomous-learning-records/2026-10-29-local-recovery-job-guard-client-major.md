# Supplemental OPS learning — local migration job scope and PostgreSQL client major (2026-10-29)

Append-only supplemental learning, not canonical `AUTONOMOUS-OPS-LEARNING.md` or production/backup/restore/RPO/RTO/skew evidence, generation/objective/drill authority, credential, traffic, readiness or human promotion.

## Material failure 1: expected diagnostic changed after nested job guard

- **Symptom:** [Local Migration Recovery Source Negative #40792672272](https://github.com/m-shogo/memories-project/actions/runs/40792672272) FAILED at source `eee859326c87cfdb8926f282290ceac70c1abb39`; its publisher's source-check step also failed.
- **Observed evidence:** The new 38 exact-diagnostic nested job negatives passed, but the pre-existing writer-scope mutation failed with `negative rejected for wrong reason: publisher writer scope: local recovery publisher rehearse job key shadow drift`.
- **Verified root cause:** The new job-key validator correctly rejected the modified `rehearse.if` before the older required-token inventory; the old fixture still expected `required source inventory drift`.
- **Failed approach:** Adding a stricter semantic validator without updating an existing mutation's expected rejection owner.
- **Correction:** [`1f5da30e`](https://github.com/m-shogo/memories-project/commit/1f5da30e4d5143c026970af7fb7c48359337e70d) pins that fixture's exact `local recovery publisher rehearse job key shadow drift` diagnostic without weakening the guard.
- **Executable recurrence guard:** The 38 new exact-diagnostic nested job negatives and the original 30 source negatives are both executed by the independently CI-reachable validator. [Source Negative #40792746537](https://github.com/m-shogo/memories-project/actions/runs/40792746537) completed **SUCCESS** with all 38 nested job, 14 YAML event/root/permission, 30 source, 18 runtime branch/SHA, and diagnostic-writer tests passing.
- **Retry condition:** Revisit this fixture only if the reviewed writer job condition or semantic guard ownership changes. Do not retry the already-corrected failing source revision.

## Material failure 2: local PostgreSQL recovery rehearsal uses mismatched client major

- **Symptom:** [Local Migration Recovery Artifact Rehearsal #40792746528](https://github.com/m-shogo/memories-project/actions/runs/40792746528) FAILED in `actual-recovery-artifact` on source `1f5da30e`; source admission passed.
- **Observed evidence:** Workflow job logs show Ubuntu installed `postgresql-client 18+290ubuntu1`, while the reviewed workflow service is `postgres:16-alpine`. PostgreSQL server log reported `ERROR: unrecognized configuration parameter "transaction_timeout"` for `SET transaction_timeout = 0;`. The exact-source redacted diagnostic [commit `37977099`](https://github.com/m-shogo/memories-project/commit/379770990a28509489fa6727a3e26b1f40024b99) records `failureStage=actual-recovery-artifact`, `result=FAIL`, `productionEvidence=false`, `productionReady=false`.
- **Verified root cause:** The runner's unpinned `postgresql-client` package resolved to major 18, incompatible with the PostgreSQL 16 service for restoring a dump containing the newer `transaction_timeout` SET command. This is an observed version-compatibility failure, not an OPS-P0-007 recovery admission.
- **Failed approach:** Assuming the runner's default `postgresql-client` matches the explicitly pinned PostgreSQL service major.
- **Correction:** No unreviewed workflow/image change was made. Preserve the PostgreSQL 16 server requirement and fail closed until a reviewed major-matched client installation or equivalent bounded correction is validated.
- **Recurrence guard:** Existing `pg_restore --exit-on-error` and the redacted diagnostic writer prevent this failure from being reported as a successful recovery; the immutable source SHA and CAS checks prevent stale writes. A deterministic client/server major preflight check and version-pinned client are the next executable prevention target, **not yet implemented**.
- **Retry condition:** Only run the rehearsal again after verifying a changed client/server major compatibility precondition. Re-running the unchanged `postgresql-client` 18 versus `postgres:16-alpine` configuration is prohibited.

## Material success and protected authority

- **Observed outcome/evidence:** [`eee85932`](https://github.com/m-shogo/memories-project/commit/eee859326c87cfdb8926f282290ceac70c1abb39) added 38 in-memory nested YAML job authority negatives, with exact publisher PR-read, publisher rehearsal-write, independent read-only, multi-line writer condition, `services` and `env` shadows. [Source CI #40792746537](https://github.com/m-shogo/memories-project/actions/runs/40792746537) and the publisher's source-validation step both passed after the correction.
- **Why safe:** Only a CI-reachable read-only validator was edited; the reviewed workflows, production status, registries, evidence and human promotion authority were not modified. The existing failed rehearsal diagnostic explicitly denies production evidence and readiness.
- **Reusable mechanism:** Validate nested job mapping/condition/permission authority independently of Git blob SHA, and require precise mutation diagnostics; match database client/server major before executing a recovery rehearsal.
- **Protected-authority check:** `production-operability-status.json` blob `3956bb805ee124ca7baf594ba05bcb0d986783b4` remains `productionDecision=NO_GO`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` and canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628` unchanged. No new production-equivalent generation, human-approved objective, executable reviewed drill, typed eight-domain non-resurrection proof, independent final review, or human promotion is asserted. Canonical learning read remains empty because of the existing transport limitation.
- **Next safe target:** Independently harden deletion-worker host-failure CI job authority while leaving the unchanged PostgreSQL version blocker untouched.
