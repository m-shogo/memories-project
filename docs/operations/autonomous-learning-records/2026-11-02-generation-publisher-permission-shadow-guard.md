# Supplemental OPS learning — generation publisher permission shadow guard (2026-11-02)

Append-only operational learning under canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — static authority gap (no production incident)

- **symptom:** The existing read-only publisher guard required one literal top-level `permissions:` and one job-level permissions block but did not reject a later quoted top-level `'permissions':` or a duplicate job-level `'contents':` key.
- **evidence:** At preceding `so` HEAD `fb969ba6`, `classify_generation_publisher_coupling` checked top-level `on`/`jobs` uniqueness and job-level `if`/`permissions` uniqueness, but not the two permission-key shadow cases. The reviewed publisher has one top-level `permissions` and one `validate` job `contents: write`. This was a source-level negative-coverage gap; no actual privilege change was observed.
- **rootCauseOrUnknown:** Verified incomplete YAML key uniqueness checks; any real exploitation is explicitly unknown.
- **failedApproach:** Relying on a single safe-looking permissions substring while allowing a later YAML duplicate key to override it.
- **correction:** [`faf3a335`](https://github.com/m-shogo/memories-project/commit/faf3a335869716c5b7a4e166e2d1472a537fb02d) requires exactly one top-level permissions key and exactly one job-level `contents` key in the reviewed publisher, including quoted variants.
- **recurrenceGuard:** Existing publisher-free read-only `scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-workflow-negative.py` adds two deterministic negative mutations (quoted duplicate top-level permissions and quoted duplicate job contents) and retains the inert-mutation guard, bringing publisher semantic negatives to 14.
- **retryCondition:** Revisit if publisher permissions, job shape, source lease, YAML syntax or read-only CI binding changes. Do not retry unchanged workflow-write permissions, MinIO 401 or missing human evidence.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41389022797](https://github.com/m-shogo/memories-project/actions/runs/41389022797) completed **SUCCESS** at exact source `faf3a335869716c5b7a4e166e2d1472a537fb02d`.
- **evidence:** Job `125096112411` logged `PASS: generation evidence publisher source lease, branch and YAML shadow guards (14 negatives)`, `PASS: generation evidence JSON parent swap rejected at pinned leaf open`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`.
- **whySafe:** Only the already CI-triggered read-only workflow-negative script changed. Publisher YAML, credentials, traffic, production evidence, recovery authorities and human promotion review were not written; mutations exist only as in-memory negative fixtures.
- **reusableMechanism:** Enforce unambiguous permissions at both workflow and write-capable job scopes, including quoted duplicate keys, before trusting publisher source-lease checks.
- **protectedAuthorityCheck:** Ten protected blobs remain unchanged from initial `so` `25ac906d`: learning `b809c69d`, contract `87712ea9`, production status `d677a1c9`, OPS-P0-007 snapshot `dbaa36b0`, generation `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007 prerequisites blocked; registered/semantically eligible generations 0/0, approved objectives 0, executable requests 0, request-bound evidence 0, complete typed coverage 0, final candidates 0. Human promotion remains separate and nonautomatic.

## Next safe target

Audit whether commented-out source-lease and push commands can satisfy publisher static token checks; add active-command negative mutations only in the existing read-only suite. Do not modify the publisher workflow or treat CI as recovery evidence.
