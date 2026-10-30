# Supplemental OPS learning — Go escaped physical newline lexical guard (2026-10-31)

Append-only supplemental learning; canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json` is mandatory. The canonical learning blob was identified but its full text was not retrieved through the connector. This record is not a substitute for that authority, production evidence, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, or human promotion.

## Material failure — escaped physical newline hidden by Go lexical scanner

- **symptom:** The reviewed read-only Go import-closure scanner accepted a backslash followed by a physical LF inside an interpreted string or rune literal, although Go rejects that source. It could then treat later textual imports as evidence of a compiled dependency graph.
- **evidence:** The prior `reject_invalid_go_lexical_regions` skipped two characters unconditionally after a backslash while in `quoted` or `rune` state. An isolated local Python reproducer accepted both an escaped-LF string and rune. Local Go 1.23.2 `go test ./...` rejected the escaped-LF string with `unknown escape` and `newline in string`; CRLF already failed indirectly but lacked the specific boundary guard.
- **rootCauseOrUnknown:** Verified: unconditional escape skipping bypassed the physical-newline validation in the lexical state machine.
- **failedApproach:** Assuming any backslash and following character could be skipped without checking Go's physical-line restrictions.
- **correction:** [Code commit 5d9246e](https://github.com/m-shogo/memories-project/commit/5d9246e642cf2b21dce806565245d48d0b9980fa) explicitly rejects LF or CR after a backslash in interpreted string/rune state.
- **recurrenceGuard:** Three deterministic negative fixtures cover quoted LF, rune LF, and quoted CRLF, each requiring the exact `unreviewed Go escaped newline in literal` diagnostic. An additional positive checks a legitimate escaped backslash. These run inside the existing CI-bound Go import parser negative suite.
- **retryCondition:** Revisit only after a legitimate Go lexical syntax change with Go compiler evidence, bounded positive/negative fixtures, exact-source CI and protected-authority comparison. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical learning full-text transport or human approval blockers.

## Material success — bounded local correction, CI pending

- **outcome:** A read-only validator-only change was published to `so` without modifying Go production source, workflow YAML, credentials, traffic, or any recovery authority.
- **evidence:** Isolated local Python reproducer rejected quoted LF, rune LF, and quoted CRLF with the intended diagnostic and accepted a valid escaped quote. GitHub comparison `ed8cbcea...5d9246e` showed exactly one read-only validator changed (+12/-0). [Autonomous Learning Guard #41114898126](https://github.com/m-shogo/memories-project/actions/runs/41114898126) was in progress when this record was written; **exact-source CI SUCCESS is not yet claimed**.
- **whySafe:** No external MinIO, Go deployment, credential, production/backup/restore action, recovery generation, approved objective, reviewed drill, request-bound evidence, typed eight-domain record, independent review or human promotion was created or executed.
- **reusableMechanism:** A lexical-state scanner must validate escape targets before advancing; an import graph derived from source is not proof of compiled semantics when the source is syntactically invalid.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs were unchanged after the code commit: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/request/evidence/non-resurrection/promotion registries.

## Production boundary and next safe target

Observed source authorities retain `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0, no approved current recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review, final candidate or separate human promotion. Next: confirm exact-source CI and reject escaped Go import-path spellings that the current static import parser could mistake for literal paths; continue Go/Python transitive input and Push/PR trigger audits without changing blocked workflows.
