# Supplemental OPS learning — drill-generation binding reconcile strict JSON (2026-11-02)

Append-only learning subordinate to the canonical autonomous-learning policy. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion evidence.

## Material failure

- **symptom:** The drill-generation binding reconciler could silently accept duplicate JSON keys, nonfinite values, unbounded integer tokens or oversized planning authority bytes before computing a derived binding.
- **evidence:** At starting HEAD `7ffa1b62`, `load` used unbounded `path.read_text` and default `json.loads`, which accepts duplicate keys by last-write-wins and Python nonfinite constants. The new isolated negative exercises a valid object and five invalid payloads. No real malformed production authority was observed.
- **rootCauseOrUnknown:** Verified default Python JSON parser semantics and missing bound in source; occurrence in real authority unknown.
- **failedApproach:** Trusting default `json.loads` to enforce unique keys, finite numbers and bounded input.
- **correction:** [`0c255288`](https://github.com/m-shogo/memories-project/commit/0c2552885df5261a0d3b18f21213387e0d8c2b48) uses bounded binary read (1 MiB), unique-key hook, nonfinite/overflow rejection, 128-digit integer bound and explicit object-root requirement.
- **recurrenceGuard:** Existing CI-reached binding reconcile negative suite checks positive valid JSON and duplicate-key, NaN, overflow float, 129-digit integer and oversized-file negatives, then verifies canonical binding contract and drill registry bytes unchanged.
- **retryCondition:** Revisit only on reviewed loader/parser changes or exact-source CI regression. Do not retry unchanged MinIO HTTP 401, workflow permission, external production evidence or promotion blockers.

## Material success

- **outcome:** Ambiguous/oversized planning JSON fails closed before reconciliation.
- **evidence:** Exact-source [Backup Restore Drill Generation Eligibility Binding #41333209898](https://github.com/m-shogo/memories-project/actions/runs/41333209898) completed SUCCESS at code HEAD `0c255288`. This is a synthetic validation result, not an approved recovery objective or production evidence.
- **whySafe:** Only the binding reconciler's read path and an existing CI-reached negative suite changed; no production, registry, workflow or human authority was modified.
- **reusableMechanism:** Parse bounded UTF-8 JSON with duplicate-key rejection, finite-number enforcement, bounded integers and a positive control alongside synthetic malformed inputs.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound evidence 0, complete typed eight-domain coverage 0, final candidates 0. Preflight uses distinct unsuperseded semantically eligible environments plus explicitly human-approved current objective; reviewed requests remain planning-only, generation evidence remains bound to executable reviewed request, final candidates require all existing gates plus typed eight-domain coverage and independent review, and human promotion is separate/nonautomatic.

## Next safe target

Apply the same bounded strict JSON semantics to the independent binding validator's planning-authority reader and prove its negative reachability without changing any planning or production registry.
