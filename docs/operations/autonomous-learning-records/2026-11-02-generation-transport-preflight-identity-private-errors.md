# Supplemental OPS learning — pre-FD validator identity probes (2026-11-02)

Append-only learning subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This record and synthetic CI are never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered/eligible generation, approved objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate, or human promotion evidence.

## Material failure mode / verified coverage gap

- **symptom:** Two independent pinned validator importers could expose private filesystem exception text during their initial `Path.resolve(strict=True)` identity probe, before the protected FD-read `try` boundary.
- **evidence:** At starting `so` HEAD `3bf43b4b2f413e7a5cbd7e13773a5e4fec83b41d`, `require_validator_identity` in both `scripts/validate-memory-os-backup-restore-generation-binding-transport-negative.py` and `scripts/validate-memory-os-backup-restore-generation-evidence-transport-negative.py` called `Path.resolve` outside the exception-normalizing reader block. Existing tests covered pinned reads, descriptor ownership and parent swaps, but not this pre-FD exception boundary. No actual private leak or production incident was observed.
- **rootCauseOrUnknown:** Verified source-level preflight exception normalization gap; occurrence in a real runner is unknown.
- **failedApproach:** Assuming the reader's existing `except (OSError, ValueError, TypeError)` also covers an identity check invoked before that `try`. The earlier fixed-domain `Fail` masking lesson prohibits an unqualified broad catch.
- **correction:** [`d9ab75aa`](https://github.com/m-shogo/memories-project/commit/d9ab75aa05586b86ec82823bf182fee9aec54328) and [`9521cb77`](https://github.com/m-shogo/memories-project/commit/9521cb774e3e418e8033deb37ea3bfeca0260459) normalize only `OSError`, `ValueError` and `TypeError` in each preflight identity probe to a fixed private `Fail`, without changing successful identity checks.
- **recurrenceGuard:** Both independently executed negative suites inject each exception class through `Path.resolve` on the exact fixture validator, require the exact fixed-domain error, suppressed context and no private canary, restore the patched method, then continue existing positive pinned import, malformed-FD, bounded-read, cleanup, metadata and parent-swap negatives.
- **retryCondition:** Revisit only if pre-FD identity semantics, exception classification, source ownership, or exact-source CI regress. Do not retry unchanged canonical large-blob retrieval, MinIO HTTP 401, missing external human evidence or writer-trigger coupling without a changed precondition.

## Material success — binding transport

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41427058782](https://github.com/m-shogo/memories-project/actions/runs/41427058782) completed **SUCCESS** on `d9ab75aa05586b86ec82823bf182fee9aec54328`.
- **evidence:** Job `125216102580` logged `PASS: generation-binding transport pinned importer rejects EOF, nonbytes and private read failures; fragmented read works`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`. The committed source executes all three new identity canary negatives before this PASS.
- **whySafe:** Synthetic fixtures only; source change restricted to the read-only negative harness; no protected production authority or production evidence changed. However the broad Admission Chain wildcard also triggered a write-capable workflow, separately recorded as a scoped trigger-topology failure; this must not be misrepresented as an entirely read-only workflow graph.
- **reusableMechanism:** Normalize narrow pre-acquisition path-probe exceptions separately from the owned-FD reader and test exact private error/context behavior.

## Material success — generation-evidence transport

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41427240300](https://github.com/m-shogo/memories-project/actions/runs/41427240300) completed **SUCCESS** on `9521cb774e3e418e8033deb37ea3bfeca0260459`.
- **evidence:** Job `125216698866` logged `Memory OS generation-evidence execution transport negative PASS`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`. Three injected identity probe failures execute before the suite summary.
- **whySafe:** The change only hardens synthetic validator importer diagnostics; the code neither registers production evidence nor promotes readiness. The separate write-capable Admission Chain trigger is not a safety proof and requires its own guard.
- **reusableMechanism:** Apply the same narrowly scoped, fail-closed pre-FD probe classification to each independently executable importer, with a per-importer canary matrix and exact-source CI.

## Protected-authority check

After both code commits, ten protected Git blob identities remained unchanged: production status `d677a1c9` (`productionDecision=NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), environment generations `bfd1b045`, recovery objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, and mandatory contract `87712ea9`. Registered/semantically eligible generations 0/0; approved current objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain coverage, final candidate and human promotion review 0. Human promotion remains separate and nonautomatic.

## Next safe target

Build an independent read-only trigger-topology negative that catches wildcard matches against write-capable workflows before editing any further `scripts/*backup*.py` path. Do not let supplemental learning or synthetic CI satisfy any production gate.
