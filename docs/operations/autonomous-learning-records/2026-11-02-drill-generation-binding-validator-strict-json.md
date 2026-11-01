# Supplemental OPS learning — drill-generation binding validator strict JSON (2026-11-02)

Append-only learning subordinate to canonical autonomous-learning policy. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion evidence.

## Material failure

- **symptom:** The independent drill-generation eligibility binding validator accepted ambiguous default-JSON semantics even after the reconciler reader was hardened.
- **evidence:** At starting HEAD `0330e199`, the validator's `load` still used unbounded `path.read_text` and default `json.loads`, allowing duplicate-key last-write-wins and nonfinite constants. The new isolated negative exercises valid JSON and five ambiguity/size cases. No malformed real production authority was observed.
- **rootCauseOrUnknown:** Verified source-level missing bounds and Python default JSON behavior; real-world occurrence unknown.
- **failedApproach:** Relying on the reconciler's strict parser while the independent validator retained a weaker parser for the same planning authorities.
- **correction:** [`6ffc962d`](https://github.com/m-shogo/memories-project/commit/6ffc962da62450d2b3a90ba0c1e9b27358ff00bc) adds a 1 MiB read bound, duplicate-key rejection, nonfinite/overflow rejection, 128-digit integer bound and object-root requirement to the validator.
- **recurrenceGuard:** Existing CI-reached binding reconcile negative suite checks validator positive valid JSON plus duplicate-key, Infinity, overflow float, oversized integer and oversized-file rejection; canonical binding contract and drill registry remain unchanged.
- **retryCondition:** Revisit on reviewed parser/authority changes or exact-source CI regression. Do not retry unchanged MinIO HTTP 401, workflow permissions, production evidence or human promotion blockers.

## Material success

- **outcome:** Reconciler and independent validator now share strict bounded JSON semantics, with separate executable negative proofs.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41333290319](https://github.com/m-shogo/memories-project/actions/runs/41333290319) completed SUCCESS at code HEAD `6ffc962d`. This is a validator result, not a reviewed drill or production recovery evidence.
- **whySafe:** Only the independent validator and an existing CI-reached negative suite changed; no protected production or planning authority, workflow permission, credential, traffic or human promotion was modified.
- **reusableMechanism:** Apply consistent fail-closed JSON parsing at each independent authority reader, and test both positive and malformed input without changing canonical registries.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound recovery evidence 0, complete typed eight-domain coverage 0, final candidates 0. Preflight uses distinct unsuperseded semantically eligible environments plus a human-approved current objective; reviewed requests are planning-only, new recovery evidence is bound to a current executable reviewed request, final candidates require typed eight-domain coverage and independent review, and human promotion remains separate/nonautomatic.

## Next safe target

Harden the validator's child negative-suite transport: explicit environment filtering, bounded timeout, private output and strict typed exit, with poisoned-environment negative tests.
