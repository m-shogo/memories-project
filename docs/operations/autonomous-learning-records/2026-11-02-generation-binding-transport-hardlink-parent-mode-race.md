# Supplemental OPS learning — generation-binding pinned importer hardlink and parent-mode race (2026-11-02)

Append-only supplemental learning governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, human-approved recovery objective, reviewed request, request-bound evidence, typed eight-domain coverage, independent review, final candidate or promotion evidence.

## Material failure / latent regression risk

- **symptom:** The generation-binding transport negative harness exercised writable source and after-capture parent swaps, but did not explicitly prove rejection of a hardlinked validator or a parent permission change during pinned source reading.
- **evidence:** At `so` HEAD `60b1faa2d2e8b1f4a8281d3b3ad14e0e9aff9af9`, `pinned_validator_source` already checked `st_nlink == 1` and stable parent `st_mode/st_ctime_ns`; `prove_pinned_validator_import` had no hardlink or mid-read parent-chmod fixture. This was a verified **negative coverage gap**, not an observed acceptance of unsafe source.
- **rootCauseOrUnknown:** Verified missing executable regression tests for existing inode and parent metadata checks. Actual exploitation or filesystem race outside the disposable fixture is unknown.
- **failedApproach:** Treating static guard inspection and the existing parent-symlink swap negative as sufficient proof for hardlink and mid-read mode changes.
- **correction:** Commit [`8fcef420`](https://github.com/m-shogo/memories-project/commit/8fcef420bdeccd35a85e6855dd877e19df099f5e) adds a real hardlink alias fixture and a deterministic `os.read` hook that changes the source parent to world-writable mid-read.
- **recurrenceGuard:** The read-only suite requires the exact `source metadata unsafe` failure for the hardlink, the exact `parent changed during read` failure for chmod, an exercised mutation hook, restoration of monkeypatched `os.read` and parent mode, and unchanged existing pinned-source/swap controls.
- **retryCondition:** Revisit if the importer, parent identity fields, hardlink semantics, fixture filesystem, or read-only CI trigger changes. Do not retry unchanged writer/publisher coupling, MinIO 401, canonical large-blob retrieval or missing human evidence.

## Material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41396193099](https://github.com/m-shogo/memories-project/actions/runs/41396193099) completed **SUCCESS** on `8fcef420bdeccd35a85e6855dd877e19df099f5e`; job `125117928036` logged `PASS: generation-binding transport validator pinned against hardlink, parent-mode race and swap`, `Memory OS generation-binding loader transport negative PASS`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`.
- **evidence:** GitHub Actions exact-source conclusion and job logs; these are synthetic safety tests, not actual recovery or production evidence.
- **whySafe:** Only the independently read-only generation-binding transport negative harness changed. The tests use temporary source files and restore the parent mode and `os.read` monkeypatch; the production-capable publisher does not trigger from this script path.
- **reusableMechanism:** Pair an inode/link-count guard with a real hardlink negative; pair stable parent metadata with a deterministic mutation at the descriptor-read boundary, checking the precise failure class and fixture activation.
- **protectedAuthorityCheck:** After code commit, GitHub Blob SHAs remained unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), environment generations `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, recovery evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, and mandatory learning contract `87712ea9`. Registered/semantically eligible generations 0/0; current human-approved objective, executable reviewed request, request-bound recovery, complete typed coverage and final candidate all 0. No production or promotion gate was changed.

## Next safe target

Apply independent hardlink and mid-read metadata-race regression tests to the generation-evidence transaction writer **negative harness**, without changing publisher-coupled production writer code.
