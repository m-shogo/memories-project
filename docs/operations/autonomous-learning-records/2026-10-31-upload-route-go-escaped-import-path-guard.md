# Supplemental OPS learning — Go escaped import path semantic identity (2026-10-31)

Append-only supplemental learning only. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` are unchanged; the canonical full text was not retrieved through the connector. This supplemental record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — lexical Go import path differs from compiled path

- **symptom:** The static Go dependency scanner accepted an interpreted Go import path such as `"\\u0066mt"` and recorded its literal escape spelling instead of the compiled dependency `fmt`. This could misstate transitive Go import identity if the reviewed source baseline changed.
- **evidence:** Both grouped and single-line import regexes captured `match.group(2)` without decoding or rejecting backslashes. A local isolated Python reproduction returned the literal `'\\u0066mt'`; local Go 1.23.2 `go test ./...` successfully compiled `import "\\u0066mt"` and `import ("\\x66mt")` as `fmt` imports.
- **rootCauseOrUnknown:** Verified: Go import paths are interpreted string literals; the regex parser treated their raw textual spelling as semantic import identity.
- **failedApproach:** Recording the raw regex capture in path/alias sets and reviewed import digests as if it were the actual compiled import path.
- **correction:** [Code commit 4282054](https://github.com/m-shogo/memories-project/commit/4282054764bb3121acd56f346eb534ecf6337162) rejects any backslash in grouped and single-line Go import path captures rather than trying to partially decode Go escapes.
- **recurrenceGuard:** Four deterministic exact-diagnostic negatives cover `\\u`, `\\x`, octal and `\\U` spellings across single-line, grouped and aliased imports; a positive preserves the ordinary `fmt` path. These execute inside the existing CI-triggered negative validator.
- **retryCondition:** Only rebaseline if a legitimate Go import syntax change requires an explicitly reviewed Go-aware parser, compiler evidence, complete Go/Python source and Push/PR trigger closure, exact-source CI and protected-authority checks. Do not retry unchanged external MinIO HTTP 401, workflow-write permission, canonical large-file transport or human approval blockers.

## Material success — bounded source guard, CI pending

- **outcome:** The import-path ambiguity is now an explicit fail-closed lexical condition in the existing read-only negative validator; no Go source or workflow was modified.
- **evidence:** Local Go 1.23.2 compiler accepted the semantic-escape import forms; GitHub comparison `03ee5f4...4282054` shows one validator changed (+25/-0). [Autonomous Learning Guard #41115227581](https://github.com/m-shogo/memories-project/actions/runs/41115227581) was queued when recorded, so **exact-source CI SUCCESS is not yet claimed**.
- **whySafe:** The change is limited to a read-only CI-bound validator. No MinIO invocation, credentials, traffic, production readiness, recovery generation/objective/request/evidence, typed eight-domain review or human promotion occurred.
- **reusableMechanism:** A static dependency inventory must either parse the language's string-literal semantics completely or fail closed on escapes; path fingerprints must describe compiled identity rather than source spelling.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs were unchanged after the code commit: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries.

## Production boundary and next safe target

`productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0, no approved recovery objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain record, independent review, final candidate or human promotion. Next: confirm exact-source CI; audit Go import parser's remaining lexical/source-identity boundaries and the full Go/Python transitive CI closure without changing blocked workflow YAML.
