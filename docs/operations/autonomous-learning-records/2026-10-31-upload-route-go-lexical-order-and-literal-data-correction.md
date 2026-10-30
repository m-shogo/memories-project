# Supplemental OPS learning — order-aware Go lexical scan supersedes count-only guard (2026-10-31)

Append-only supplemental learning; canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy is `contracts/operations/autonomous-learning-system.json`. Neither this record nor its local fixtures are production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective/request, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure and correction

- **symptom:** The immediately preceding count-only Go lexical guard could accept an orphan `*/` followed by `/*` because the number of delimiters matched. It also rejected legitimate Go source containing `"/*"`, `// /*`, or a raw literal containing `/*` despite no actual block-comment boundary.
- **evidence:** Local isolated Python reproducer showed the prior regex counts `fmt` as a fake import in `package test\n*/\nimport "fmt"\n/*\n`; the count-only guard evaluates `1 == 1` and would not reject it. Separate positive examples contain delimiter-shaped characters inside valid Go strings and line comments. The previous guard's exact-source CI remained queued when this correction was prepared; no production effect is asserted.
- **rootCauseOrUnknown:** Verified: counting token spellings ignores their lexical order and whether they occur inside interpreted strings, raw strings, line comments or actual block comments.
- **failedApproach:** The count-only checks introduced in [037d4a7a](https://github.com/m-shogo/memories-project/commit/037d4a7a609da96447f41bd57a2f7a639d3d82c4) were insufficient as a general fail-closed Go lexical boundary.
- **correction:** [73c6912b](https://github.com/m-shogo/memories-project/commit/73c6912b102def3100b8f3906b5c84eaa7e2e771) replaces counts with a bounded, deterministic lexical-state scan for code, line/block comments, raw strings, interpreted strings and rune literals. Orphan block closers, unterminated regions and invalid multiline interpreted literals fail closed.
- **recurrenceGuard:** Four deterministic negatives cover unfinished block comment, orphan close, equal-count inverted delimiters and unfinished raw literal. Four positives cover normal interpreted-string, line-comment and raw-string delimiter text plus an escaped quote. A standalone local reproducer exercised nine cases (including a normal import) with nine PASS results. Existing Go import closure tests remain in the CI-bound suite.
- **retryCondition:** Review any legitimate Go syntax the bounded scanner cannot classify using Go-aware lexer/compiler evidence, keep all negative/positive fixtures, verify direct and nested exact-source CI, and recheck protected authorities. Do not rerun unchanged MinIO HTTP 401, workflow-write permission or canonical large-file transport blockers.

## Observed bounded success; CI not yet claimed

- **outcome/evidence:** One read-only validator file changed (+61/-11 lines) and was published on `so` at `73c6912b` through a CAS branch update. A local Python scanner fixture passed nine cases. This is a scoped local check; **exact-source GitHub Actions SUCCESS has not been confirmed**.
- **whySafe:** No Go production source, workflow YAML, external MinIO, credential, traffic, production readiness, recovery generation/objective/request/evidence, typed eight-domain review or human promotion was modified or executed.
- **reusableMechanism:** Lexical state and delimiter order are source-authority inputs; source inventories must not mistake comments/literals for compiled dependencies. Validate both bypass negatives and valid-source positives before CI claims.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs matched the parent: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0; no approved objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain coverage, final candidate or human promotion.

## Next safe target

Wait for exact-source CI to reach a terminal state and persist a separate verified result. Continue the third-hop `epochguard -> dbscope -> security` import/trigger closure audit, preserving the distinction between static reachability and independent pre-MinIO Go test execution.
