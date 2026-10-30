# Supplemental OPS learning — Go package clause and import binding identity (2026-10-31)

Append-only supplemental learning only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and the mandatory execution policy remains `contracts/operations/autonomous-learning-system.json`. The canonical learning blob was identified but its full text was not retrieved through the connector; this supplemental record is not a substitute for canonical authority. Learning/history never supplies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed drill request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human-promotion evidence.

## Material failure A — declaration-looking Go package text in non-code

- **symptom:** The reviewed Upload Route source package identity guard could accept a sole `package httpserver` line inside a Go block comment or raw string as a package declaration, even though the file had no executable Go package clause.
- **evidence:** Prior `require_reviewed_upload_route_go_package` used a line-anchored `re.findall` over the entire source without checking that the declaration was outside a comment/string or preceded only by comments and whitespace. A local Go 1.23.2 `go test` of a comment-only package file returned `expected 'package', found 'EOF'`. Four adversarial fixtures were reproduced against the isolated guard.
- **rootCauseOrUnknown:** Verified: a textual line match does not establish the lexical position of a Go package clause.
- **failedApproach:** Relying on a single regex declaration count plus path-derived package name without validating the pre-package lexical region.
- **correction:** [330402bb](https://github.com/m-shogo/memories-project/commit/330402bb44084106b83b2941ef47886dc8030bac) retains the conservative exact declaration count and additionally rejects executable or incomplete prefix material before the matched clause.
- **recurrenceGuard:** Four deterministic negatives cover comment-only spoofing, raw-string spoofing, duplicate fake-and-real declarations, and executable pre-package code. Two positive fixtures preserve reviewed line-comment and block-comment headers; all run inside the existing CI-bound negative validator.
- **retryCondition:** Revisit only if a legitimate Go source syntax/layout change requires a reviewed new package-clause parser, with isolated Go toolchain checks, exact-source CI and protected-authority comparison. Do not repeat unchanged external MinIO, workflow-write, canonical full-text transport or human-approval blockers.

## Material success A

- **outcome:** The package-clause spoof guard is committed and validated without weakening the prior package/path/build constraints.
- **evidence:** [Autonomous Learning Guard #41105705073](https://github.com/m-shogo/memories-project/actions/runs/41105705073) completed **SUCCESS** on exact code SHA `330402bb44084106b83b2941ef47886dc8030bac`. Job logs show contract and append-only PASS, 601 canonical fail-closed cases, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, and entry-document validation PASS.
- **whySafe:** Only the read-only Python negative validator changed. No Go production source, workflow YAML, credentials, MinIO, traffic, recovery authority or human promotion was changed or executed.
- **reusableMechanism:** For a compiled language declaration, validate lexical placement and the allowed prelude as well as path/name identity; preserve positive controls for valid headers.
- **protectedAuthorityCheck:** The ten protected Git blob identities were unchanged after the code commit; canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and all six generation/objective/request/evidence/non-resurrection/promotion registries.

## Material failure B — duplicate Go import bindings collapsed by sets

- **symptom:** The static Go import-closure scanner returned sets of paths and aliases, so repeated identical imports could disappear from its reviewed identity inventories.
- **evidence:** The parser accumulated `paths` and `aliases` but returned `set(paths)` or `set(aliases)` without checking source multiplicity. Go 1.23.2 rejected repeated ordinary/identical explicit-alias imports as redeclarations, while it accepted two different explicit aliases for one import path. Repeated blank imports can be legal Go, but are conservatively treated as unreviewed multiplicity in this audit.
- **rootCauseOrUnknown:** Verified: set conversion discards repeated identical import bindings and cannot attest source declaration multiplicity.
- **failedApproach:** Using a distinct path/alias fingerprint as if it also proved declaration cardinality.
- **correction:** [998c3a8e](https://github.com/m-shogo/memories-project/commit/998c3a8e70dbfeed8e776561cf74ff09866e9a75) records `(alias-or-empty, import-path)` for both grouped and single-line imports and rejects duplicate bindings before converting to sets.
- **recurrenceGuard:** Four deterministic negatives cover grouped ordinary duplicates, grouped identical explicit aliases, repeated single-line imports and repeated blank imports; a positive verifies two distinct explicit aliases for one path remain accepted.
- **retryCondition:** Rebaseline only after an explicitly reviewed legitimate import-multiplicity or parser syntax change, with Go toolchain evidence, complete source/input and Push/PR reachability checks, exact-source CI and protected-authority verification.

## Material success B

- **outcome:** Duplicate Go import bindings now fail closed rather than silently preserving the old set inventory.
- **evidence:** [Autonomous Learning Guard #41106293843](https://github.com/m-shogo/memories-project/actions/runs/41106293843) completed **SUCCESS** on exact source `998c3a8e70dbfeed8e776561cf74ff09866e9a75`. Logs confirm contract and append-only PASS, 601 canonical fail-closed cases, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only checks PASS. The new nested fixtures are not separately included in the printed 601-case count.
- **whySafe:** Only the existing read-only Python negative validator changed; no production source, workflow, credential, traffic, generation, objective, drill, evidence or promotion authority changed.
- **reusableMechanism:** Verify binding multiplicity before set normalization and retain a positive control for legitimate distinct alias identities.
- **protectedAuthorityCheck:** The same ten protected Git blob identities were unchanged after both code commits: canonical `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, environment generation `bfd1b045`, recovery objective `f4d74f33`, reviewed drill request `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion review `99cb895f`.

## Production boundary, remaining blockers, next safe target

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`. Registered and semantically preflight-eligible generations remain 0/0. Preflight requires unsuperseded semantically eligible generations from two distinct environments and an explicitly human-approved current recovery objective. Reviewed drill requests are planning-only; new recovery evidence must remain bound to a current executable reviewed request. Final candidates require complete typed eight-domain non-resurrection coverage, independent review and all other existing generation/objective gates. Separate explicit human production promotion has not occurred.

Known Quay MinIO HTTP 401, workflow-write authorization, canonical learning full-text transport and human approvals remain blocked; no unchanged retry was made. The two focused Upload Route workflows still lack complete transitive Go/Python source and independent pre-MinIO Push/PR trigger coverage. Next safe target: extend bounded read-only Go/Python import and source-input closure with actual workflow classification; do not change blocked workflow YAML or infer production readiness from learning/CI.
