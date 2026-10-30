# Supplemental OPS learning — Python 3.12 generic type-parameter import shadow (2026-10-31)

Append-only supplemental learning; canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` are unchanged. Canonical full-text transport remains unavailable. This record cannot serve as production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — generic type parameters bypass imported-name shadow detection

- **symptom:** The read-only Upload Route Python import binding guard could accept a Python 3.12 generic function or type alias whose type parameter reuses a reviewed imported runtime name, without any changed import-entry digest.
- **evidence:** Prior shadow detection covered `ast.Name(Store/Del)`, function/class names, `ast.arg`, exception aliases and `match` captures but not `ast.TypeVar`, `ast.ParamSpec` or `ast.TypeVarTuple`. Local Python 3.13 AST parsing of `def helper[Path](...)`, `def helper[**json]()`, `def helper[*json]()` and `type Alias[Path] = ...` produced those distinct type-parameter nodes without a Store/arg binding. Existing import-entry identities stayed unchanged.
- **rootCauseOrUnknown:** Verified: Python 3.12 type-parameter declarations introduce scoped names through dedicated AST nodes, outside the previously reviewed binding-node inventory.
- **failedApproach:** Assuming all import-name shadowing was represented by Store/Del, argument, exception, function/class or pattern-capture nodes.
- **correction:** [Code commit 8aa4684](https://github.com/m-shogo/memories-project/commit/8aa468425953834f33d91e4cc68122c054827179) extends the read-only shadow predicate to `ast.TypeVar`, `ast.ParamSpec` and `ast.TypeVarTuple` names.
- **recurrenceGuard:** Four exact-diagnostic negative fixtures cover generic TypeVar, ParamSpec, TypeVarTuple and generic type alias shadowing; a positive verifies a fresh generic type parameter `T` is permitted. These execute inside the existing CI-triggered negative validator.
- **retryCondition:** Revisit only if Python generic binding semantics or the reviewed interpreter version changes, with AST/runtime evidence, positive/negative fixtures, complete source and Push/PR trigger review, exact-source CI and protected-authority comparison. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical full-text transport or human-approval blockers.

## Material success — local AST proof, exact-source CI pending

- **outcome:** Generic type-parameter collisions with imported names are now explicit fail-closed cases in the existing read-only Python dependency guard.
- **evidence:** Local Python 3.13 AST reproducer identified all four collisions and accepted the fresh-`T` positive. GitHub comparison `34c96e2...8aa4684` shows one read-only validator changed (+25/-0). **Exact-source CI SUCCESS had not yet been observed** when this record was created.
- **whySafe:** No production Python or Go code, workflow YAML, MinIO, credentials, traffic, backup/restore, recovery generation/objective/request/evidence, typed eight-domain review or human promotion was modified or executed.
- **reusableMechanism:** Imported binding authority must include every language-specific declaration form, including new AST node types, before assuming stable imports imply stable runtime symbol resolution.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs matched the parent: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries.

## Production boundary and next safe target

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0; no approved current recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review, final candidate or human promotion. Next: verify Python 3.12 exact-source CI, then continue Go/Python transitive source and Push/PR trigger audits without changing blocked workflow YAML.
