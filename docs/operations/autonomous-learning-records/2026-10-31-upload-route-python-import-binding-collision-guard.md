# Supplemental OPS learning — Python imported-binding collision hidden by order-independent digests (2026-10-31)

Append-only supplemental operational learning only. Canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy is `contracts/operations/autonomous-learning-system.json`; canonical full text was not retrieved. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure — distinct imports collide on a runtime binding

- **symptom:** The scoped Upload Route Python import guard permitted two distinct import declarations binding the same runtime name. Reordering them preserved the sorted import-entry SHA-256 digest while changing the runtime object bound to that name.
- **evidence:** The previous `require_reviewed_upload_route_python_imports` rejected duplicate *entries* and ordinary Store/Del/function/argument shadows, but constructed the import binding inventory with `set.update` and never checked duplicate bound names between distinct import statements. Local Python AST/exec reproduction showed `from pathlib import Path; import json as Path` and the reversed order have the same sorted-entry SHA-256 prefix `ff64ac750c29` while `Path` resolves respectively to the `json` module and the `pathlib.Path` class.
- **rootCauseOrUnknown:** Verified: distinct import-entry identity does not imply unique runtime name binding, and order-independent digest normalization loses semantic import-order effects when names collide.
- **failedApproach:** Treating the distinct import-entry set and a deduplicated binding set as proof that no imported name could be overwritten by another import.
- **correction:** [Code commit 6f1fd52](https://github.com/m-shogo/memories-project/commit/6f1fd52ffa46a05254037b0bf0b39e77c9304494) collects top-level import bindings as a list and rejects duplicate runtime names before set conversion, preserving the existing Store/Del shadow checks.
- **recurrenceGuard:** Three exact-diagnostic negatives cover two opposite import orders with the *same* digest and a distinct `from ... as` collision. A positive confirms two imports with separate names remain valid. Tests run inside the existing CI-bound read-only negative validator.
- **retryCondition:** Only revisit for an explicitly reviewed Python import-binding semantics change with AST/runtime proof, bounded positive/negative fixtures, full source/Push/PR reachability and exact-source CI. Do not repeat unchanged MinIO HTTP 401, workflow-write permission, canonical full-text transfer or human-approval blockers.

## Material success — bounded local proof, CI pending

- **outcome:** The imported-name collision is now a deterministic fail-closed condition in the read-only Python dependency guard.
- **evidence:** Local Python 3.13 AST/exec demonstrated the collision and unchanged sorted digest; an isolated corrected guard rejected three collision cases and accepted the distinct-alias control. GitHub comparison `60f1814...6f1fd52` showed one read-only validator changed (+44/-3). [Autonomous Learning Guard #41115608827](https://github.com/m-shogo/memories-project/actions/runs/41115608827) was queued at publication; **exact-source CI SUCCESS is not yet claimed**.
- **whySafe:** No Python production validators, Go application source, workflow YAML, MinIO, credential, traffic, backup/restore, production evidence, recovery generation/objective/request, typed eight-domain review or promotion was modified or executed.
- **reusableMechanism:** Preserve declaration multiplicity and runtime binding uniqueness before normalizing import identities into order-independent sets or digests.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs matched the parent: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and the six generation/objective/request/evidence/non-resurrection/promotion registries.

## Production boundary and next safe target

`productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0, no approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, independent review, final candidate or human promotion. Next: verify exact-source CI and continue Go/Python transitive source closure and Push/PR trigger proof without changing blocked workflows.
