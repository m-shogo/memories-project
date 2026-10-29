# Supplemental OPS learning — worker SIGKILL recovery concurrency serialization (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production or backup/restore/RPO/RTO/skew evidence, a generation, approved objective, executable reviewed drill, typed eight-domain non-resurrection evidence, credentials, traffic, readiness, independent recovery review or human promotion.

## Material failure / executable recurrence prevention
- **Symptom:** Worker SIGKILL recovery source-negative CI pinned reviewed Git blobs, inherited publisher write authority, job permissions and runtime identity but lacked an independent semantic diagnostic for publisher concurrency cancellation or group shadowing. Static coverage gap, not observed production cancellation.
- **Observed evidence:** Publisher blob `1ae00600d8ccbe1e9c70ad6d2bbfb6212e729313` declares `group: deletion-worker-sigkill-recovery-so` and `cancel-in-progress: false`. Previous validator blob `aeac193f0172a9f8ae9e3a1f23813a2508be0ac2` pinned root `concurrency:` but not its nested leaves.
- **Verified root cause:** Whole-file SHA and root mapping checks reject changed bytes without independently classifying effective cancellation or YAML shadow semantics.
- **Failed approach:** Treating the reviewed source digest and root `concurrency:` key as sufficient standalone noncancellation proof.
- **Correction / executable recurrence guard:** [`67ece266`](https://github.com/m-shogo/memories-project/commit/67ece266d452f71052bf0a6156c7e954bdec8766) adds an exact reviewed static-group/noncancellation guard and ten exact-diagnostic negatives for global group, cancellation enabled, duplicate/spaced/quoted leaves, unreviewed leaf and missing cancellation.
- **Retry condition:** Revisit only for a reviewed policy change or demonstrated effective YAML shadow bypass; do not retry unchanged external MinIO 401, canonical-learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Deletion Worker SIGKILL Recovery Diagnostic Source Negative #40806397108](https://github.com/m-shogo/memories-project/actions/runs/40806397108) completed **SUCCESS** at exact code `67ece266`. Logs confirm ten new concurrency negatives, 24 existing nested-job negatives and explicit `production evidence generated: false; production decision changed: false`.
- **Why safe:** Only the CI-reachable read-only validator changed (+48 lines, no deletions). Publisher/independent workflows, production status, evidence, registry, credentials, traffic and promotion authority were unchanged.
- **Reusable mechanism:** Pin static writer serialization/noncancellation independently of source SHA and root YAML, proving mutation-specific in-memory negatives.
- **Protected-authority check:** Production status blob `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` still records `productionDecision=NO_GO`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. No registered generation, approved objective, executable reviewed request, generation evidence, complete typed eight-domain record, final candidate or human promotion.
- **Next safe target:** Audit worker container-kill recovery diagnostic concurrency and source-negative reachability without altering production authorities.
