# Supplemental OPS learning — exact single-line nested learning proof (2026-10-31)

Append-only operational learning under `contracts/operations/autonomous-learning-system.json`; canonical learning authority is unchanged. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection coverage, independent review or human promotion evidence.

## Material failure mode

- **symptom:** The nested learning guard success classifier accepted child stdout with a missing final newline, extra blank lines, leading/trailing padding or CRLF even though the actual reviewed validators emit exactly one LF-terminated PASS line. This was an observed static proof-boundary gap, not a production or CI exploit.
- **evidence:** At source `ebd7b53b`, `learning_guard_passed` used `completed.stdout.strip()`, erasing precisely the bytes that distinguish an exact child proof from an altered output. The existing synthetic classifier already rejected unrelated nonblank text but did not exercise newline/padding variants.
- **rootCauseOrUnknown:** Verified output normalization before proof comparison, not a missing subprocess execution or production evidence failure.
- **failedApproach:** Treating stripped textual equality as equivalent to the reviewed single-line child proof format.
- **correction:** [c383da6f](https://github.com/m-shogo/memories-project/commit/c383da6f7ff5db7dbbba221d3c116582c9c0e984) requires exactly one LF terminator (not CRLF) and compares the untrimmed preceding bytes with the known positive marker or the numeric negative-suite marker.
- **recurrenceGuard:** Four deterministic CI-reachable synthetic negatives reject extra blank line, missing terminator, CRLF and leading whitespace. Existing extra-output, wrong-count, missing-output, nonzero and stderr negatives remain. Actual 601-case direct and independently nested executions still run.
- **retryCondition:** Revisit only if the reviewed Python child output contract changes or a new exact-source CI failure supplies different evidence. Never relax the exact proof merely to accept unrelated stdout.

## Material success

- **outcome/evidence:** [Autonomous Learning Guard #41123671069](https://github.com/m-shogo/memories-project/actions/runs/41123671069) completed **SUCCESS** on exact `c383da6f7ff5db7dbbba221d3c116582c9c0e984`. Logs show append-only PASS, mandatory contract PASS, **601 direct** and **601 independently nested** negative cases PASS, **52 source-negative workflows / 63 direct Python commands / 204 semantic fixtures**, **195 fanout synthetic**, entry-document PASS, **1,186 helper-ancestor negatives**, and read-only completion.
- **whySafe:** Only the existing read-only `scripts/validate-memory-os-entry-docs.py` changed; no workflow YAML, production implementation, MinIO, credentials, traffic, generation/objective/request/evidence, typed eight-domain record, independent review or human promotion was written.
- **reusableMechanism:** Keep proof transport byte-exact instead of normalizing away distinguishing whitespace; verify both positive and negative controls at the same CI-bound classifier.
- **protectedAuthorityCheck:** The code commit changed only one read-only validator. Ten protected blob SHAs stayed unchanged: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries `bfd1b045`, `f4d74f33`, `acebcd02`, `ae7e57ef`, `26bb1cc7`, `99cb895f`.

## Boundary and next safe target

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered and semantically preflight-eligible generations 0/0. Preflight requires unsuperseded eligible generations from distinct environments and an explicitly human-approved current recovery objective. Reviewed requests are planning-only, new evidence must bind a current executable reviewed request, complete typed eight-domain non-resurrection and independent review remain required, and human promotion is separate/non-automatic.

Next: audit typed subprocess exit-code/stream validation for both child proof classifiers, then return to measured 601-case nested runtime headroom and Go/Python transitive Push/PR closure. Do not retry unchanged external MinIO HTTP 401, workflow-write permission or human approval blockers. The final learning-only HEAD does not establish full production admission-chain success.
