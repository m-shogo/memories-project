# Supplemental OPS learning — Go explicit import alias collision (2026-10-31)

Append-only supplemental learning only. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged; canonical full-text transport remains unavailable. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — distinct import paths sharing a Go local alias

- **symptom:** The reviewed static Go import parser accepted two distinct paths with the same explicit local alias in one Go source file, although the Go compiler rejects the redeclaration. The existing per-file alias/path digest distinguishes entries but did not enforce that they were valid unique local bindings.
- **evidence:** The prior parser rejected only repeated `(alias, path)` tuples; `alias "fmt"` plus `alias "math"` remained distinct. Local Go 1.23.2 `go test ./...` rejected a grouped fixture with `alias redeclared in this block`. Prior learning on explicit alias identity and import multiplicity was reviewed before the change.
- **rootCauseOrUnknown:** Verified: tuple uniqueness is weaker than unique explicit Go local-name binding.
- **failedApproach:** Treating a set of distinct alias/path pairs as proof that the imports can compile together.
- **correction:** [Code commit c5ebd3a](https://github.com/m-shogo/memories-project/commit/c5ebd3ab66909c887d34d7432416f0be77b8cdc9) rejects duplicate explicit local aliases after duplicate pair detection, while excluding Go's special blank and dot import forms from named-binding uniqueness.
- **recurrenceGuard:** Two deterministic exact-diagnostic negatives cover grouped and separate single-line declarations with the same alias and different import paths. Existing positive controls preserve distinct aliases on one path, ordinary imports, blank and dot imports.
- **retryCondition:** Only revisit after a legitimate Go import-binding change with compiler evidence, bounded positives/negatives, reviewed source and Push/PR reachability, exact-source CI and protected-authority checks. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical full-text transfer or human approval blockers.

## Material success — local proof and bounded publication, CI pending

- **outcome:** Explicit Go local-name collisions now fail closed in the existing read-only import-closure validator.
- **evidence:** Local Go 1.23.2 confirmed the compiler rejection; GitHub comparison `3811c80...c5ebd3a` shows one read-only validator changed (+19/-0). The code is published through a CAS-checked branch ref update; **exact-source CI SUCCESS was not yet observed** when this record was written.
- **whySafe:** No Go production source, Python production validator, workflow YAML, MinIO, credential, traffic, backup/restore, generation, objective, drill request, evidence, typed eight-domain record, independent review or promotion was modified or executed.
- **reusableMechanism:** Check both declaration pair multiplicity and local symbol uniqueness; static import inventories must not infer compilability from distinct paths alone.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs remained unchanged after the code commit: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries.

## Production boundary and next safe target

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered and semantically preflight-eligible generations 0/0; no approved current recovery objective, executable reviewed drill request, request-bound recovery evidence, complete typed eight-domain record, independent review, final candidate or human promotion. Next: confirm exact-source CI and continue static Go/Python transitive source/Push-PR trigger closure without changing blocked workflows.
