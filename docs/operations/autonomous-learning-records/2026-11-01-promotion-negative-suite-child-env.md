# Supplemental OPS learning — promotion negative-suite child environment (2026-11-01)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, executable reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — promotion negative child inherited interpreter/loader overrides

- **symptom:** The promotion-review validator launched its negative suite with bounded private output but inherited unreviewed Python/import, dynamic-loader and Git overrides.
- **evidence:** Source at `ec9f0f29` in `scripts/validate-memory-os-backup-restore-promotion-review.py` invoked `subprocess.run` without explicit `env`. The prior [child environment learning](2026-11-01-child-validator-environment-isolation.md) reproduces a synthetic `PYTHONPATH` early-success bypass. No actual CI compromise or human promotion manipulation was observed.
- **rootCauseOrUnknown:** Verified implicit inherited child environment. External adversarial control of that environment remains unknown.
- **failedApproach:** Assuming canonical negative script path, 60-second timeout, DEVNULL streams and integer-looking zero exit were sufficient without a reviewed child environment.
- **correction:** [`31ca4abf`](https://github.com/m-shogo/memories-project/commit/31ca4abff9a46c1be858be4214dc2649598bb6b1) filters `PYTHON*`, `LD_*`, `DYLD_*`, `GIT_*` for the negative child and requires an actual `CompletedProcess` with exact integer-zero exit. Existing timeout/private failure behavior is retained; ValueError and TypeError are now fail-closed unavailable classes.
- **recurrenceGuard:** Existing CI-reachable `scripts/validate-memory-os-backup-restore-promotion-review-negative.py` poisons six parent overrides, requires exact sanitized child environment and preserved benign canary, and retains nonzero, boolean, timeout, unavailable and private-output rejection controls. Code and test were committed together with an expected-HEAD ref lease.
- **retryCondition:** Revisit only on reviewed child execution topology, interpreter/loader trust boundary or exact-source CI changes. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permission or missing human evidence.

## Material success — exact-source promotion negative CI

- **outcome:** Promotion-review negative-suite execution now has explicit child environment isolation and strict typed result acceptance without changing human promotion policy.
- **evidence:** Exact-source [Backup Restore Promotion Review Readonly #41318423459](https://github.com/m-shogo/memories-project/actions/runs/41318423459) completed **SUCCESS** at `31ca4abf`, and its workflow directly executes `scripts/validate-memory-os-backup-restore-promotion-review-negative.py`. Other long-running workflows were not yet claimed successful.
- **whySafe:** Git compare shows only the existing promotion-review validator and its negative test changed. No reviewed workflow, protected production status, objective/generation/request/evidence/typed/promotion registry, credential or traffic was written. Synthetic negative execution cannot authorize human promotion.
- **reusableMechanism:** Even an already bounded private negative subprocess needs explicit sanitized `env` plus poisoned-environment/benign-positive executable tests and exact typed exit checks.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs remained unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, environment generation `bfd1b045`, objective `f4d74f33`, drill request `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion registry `99cb895f`. `productionDecision=NO_GO`. Registered and semantically eligible generations remain distinct, preflight requires unsuperseded distinct-environment eligibility plus explicit current human-approved objective, reviewed requests remain planning-only until executable, evidence remains request-bound, typed eight-domain coverage and independent review remain mandatory, and human promotion is separate/nonautomatic.

## Next safe target

Continue auditing child validator transport and exact-source CI without altering reviewed production promotion or evidence authority.
