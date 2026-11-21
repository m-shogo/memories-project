# Supplemental learning run boundary: 2026-11-21

## Material failure
- Symptom: Backup Restore Helper Ancestor Reachability failed with `independent learning workflow run boundary drift` after supplemental history CI step was added.
- Observed evidence: `.github/workflows/autonomous-learning-guard.yml` places `Enforce supplemental append-only history and negative fixtures` between the entry-doc validator and independent helper ancestor validation; `LEARNING_RUN_BOUNDARIES` previously expected those two older steps to be adjacent. Earlier run #44874593014 reported failure; current-run post-change CI is not yet confirmed.
- Root cause: verified stale adjacent-step boundary inventory in `scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py`, not a reason to relax the fail-closed check.
- Failed approach: retaining the pre-supplemental step adjacency while inserting a new reviewed CI step.
- Correction: commit `7dde1801bd04ebd0d16f3a7536a59c6b9a8a63ae` pins both new adjacent run boundaries in the independent validator.
- Recurrence guard: exact source-boundary pairs must each occur once; new shell commands or step insertion require explicit inventory reconciliation and negative tests.
- Retry condition: rerun the ancestor workflow on the updated `so` SHA and inspect its exact failure logs; do not assert PASS before observing CI.

## Material success (bounded)
- Outcome: GitHub accepted the focused validator update and returned blob `bd8440e83218d37b032b8186b6a11f09841f9b44`; re-read of `so` confirmed both new boundary literals.
- Evidence: target re-read and workflow source show the two adjacent pairs match; this is a deterministic source check, not a completed runtime CI PASS.
- Why safe: existing strict boundary comparison and all other checks remain intact; no production evidence or promotion authority was edited.
- Reusable mechanism: when a reviewed CI step is added, reconcile exact shell run boundaries without weakening exact-match enforcement.
- Protected authority check: `contracts/operations/production-operability-status.json` SHA `8d4e2848df463601eea6f836cce2817af4f19d25` unchanged and `productionDecision=NO_GO`. OPS-P0-007, human objective/review, generation eligibility, typed eight-domain coverage, and production gates remain independent and unchanged.

Learning is append-only and never substitutes for production, recovery, backup/restore, RPO/RTO/skew, drill, credentials, traffic, readiness, or promotion evidence.
