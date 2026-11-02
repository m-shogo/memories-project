# Supplemental OPS learning — private fixture OS diagnostics (2026-11-02)

Append-only supplemental learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Learning and synthetic CI cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, human-approved recovery objective, executable reviewed drill request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human production-promotion authority.

## Material failure / latent private error disclosure

- **symptom:** The independent generation-evidence reconcile negative fixture manager interpolated raw filesystem `OSError` messages into public `Fail` diagnostics, potentially exposing private paths or canaries in CI logs.
- **evidence:** At `so` HEAD `4335af3c36885925140f3a9b05838c439b12a329`, the root-open and general fixture-operation `except OSError as exc` handlers used formatted `{exc}` and chained the raw exception. No actual production secret disclosure or observed CI failure was established.
- **rootCauseOrUnknown:** Verified raw exception interpolation and chained context at two independent fixture boundaries; actual private data occurrence unknown.
- **failedApproach:** Assuming an OS failure is safe to echo because it arises in a synthetic read-only test harness.
- **correction:** [`bc7eae76`](https://github.com/m-shogo/memories-project/commit/bc7eae762682d5888b3efd228b23840639ec7967) normalizes both boundaries to fixed domain errors with `from None`.
- **recurrenceGuard:** Executable private-canary `OSError` injection at root acquisition, ancestor acquisition and child mkdir; requires exact redacted failure, suppressed exception context and no fixture child creation. Monkeypatches are restored before subsequent tests.
- **retryCondition:** Revisit on fixture OS error handling, private diagnostic wording or exact-source CI reachability changes. Do not retry unchanged Quay MinIO 401, canonical learning large-blob transport, publisher-coupled writer changes or absent human evidence.

## Observed code-change outcome

- **outcome:** `bc7eae76` was committed to `so`; GitHub diff and source readback confirm both redacted handlers and the invoked negative controls.
- **evidence:** Commit diff, exact branch comparison and protected Git blob checks. The read-only Negative Suite workflow contains this script in its push trigger and invokes it with `contents: read`. The available commit status response was empty; **no exact-source CI SUCCESS is claimed**.
- **whySafe:** Only the independently read-only synthetic harness changed. The publisher trigger excludes it and no protected authority, production evidence or readiness state was written.
- **reusableMechanism:** Normalize private OS exceptions at every independent boundary, suppress exception context, and prove redaction through injected canaries at root/ancestor/child operations.
- **protectedAuthorityCheck:** Following the commit, unchanged Git blobs were verified for production status `d677a1c9` (`productionDecision=NO_GO`), generation registry `bfd1b045`, objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, canonical learning `b809c69d` and mandatory contract `87712ea9`. OPS-P0-007 production-equivalent prerequisites remain unsatisfied; human promotion remains separate and nonautomatic.

## Next safe target

Verify exact-source read-only Negative Suite outcomes for the accumulated fixture guards. If failures are observed, append their symptoms, evidence and verified cause before correction. Otherwise continue auditing independent read-only source transport and cleanup, without promoting synthetic evidence.
