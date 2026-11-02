# Supplemental OPS learning — private prewrite audit CLI exception boundary (2026-11-03)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This synthetic read-only record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or semantically eligible generation, human-approved recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human production-promotion evidence.

## Material failure class — verified source defect, no observed production disclosure

- **symptom:** The prewrite workflow fanout CLI could echo private filesystem/decoder exception text in its unexpected-error diagnostic.
- **evidence:** Before [`314455a3`](https://github.com/m-shogo/memories-project/commit/314455a3fa4d87568452befce8a44dd94378ae62), `scripts/audit-memory-os-workflow-trigger-fanout.py` caught `(OSError, UnicodeError, AuditFailure)` together and printed `str(exc)`. A path probe or decoder exception may contain a private checkout path or other canary. This was a source-observed disclosure risk, **not** an observed real credential leak or production incident.
- **rootCauseOrUnknown:** Verified broad exception-to-text forwarding at the CLI boundary; actual external exposure is unknown.
- **failedApproach:** Treating arbitrary OS/decoder exception messages as if they were reviewed fixed-domain `AuditFailure` diagnostics.
- **correction:** [`314455a3`](https://github.com/m-shogo/memories-project/commit/314455a3fa4d87568452befce8a44dd94378ae62) retains reviewed `AuditFailure` text but maps unexpected `OSError`, `UnicodeError`, `ValueError` and `TypeError` to a single fixed diagnostic with exit code 1.
- **recurrenceGuard:** The CI-reachable autonomous-learning negative suite injects private-canary instances of four exception classes and a reviewed-domain control directly into the real CLI entrypoint, verifies the injected path executed, requires exact stderr and no stdout, and checks no canary escaped.
- **retryCondition:** Revisit if the audit CLI exception classifier, source-inspection exception types, `runpy` fixture topology or CI entrypoint changes. Do not retry unchanged MinIO HTTP 401, workflow-write permissions, oversized canonical learning transport or absent human evidence blockers.

## Material success — observed exact-source CI

- **outcome:** [Autonomous Learning Guard #41489911500](https://github.com/m-shogo/memories-project/actions/runs/41489911500) completed **SUCCESS** on exact source `314455a3fa4d87568452befce8a44dd94378ae62`.
- **evidence:** GitHub Actions job `125429911541` reported `Autonomous improvement/learning contract validation PASS`, `Autonomous learning negative validation PASS (606 fail-closed cases)`, `prewrite fanout audit PASS: 195 synthetic cases`, and successful append-only, helper reachability and read-only steps. Commit diff contains only the audit CLI and its read-only negative harness.
- **whySafe:** Exact-source checkout used `contents: read`, disabled persisted checkout credentials and changed no publisher workflow, production evidence, traffic, credential, readiness or promotion authority. The synthetic injected exception contains no actual secret.
- **reusableMechanism:** Separate fixed-domain failures from arbitrary private exception text at the CLI boundary; test both private-canary rejection and a legitimate reviewed-domain diagnostic through the actual entrypoint, with exact stderr matching.
- **protectedAuthorityCheck:** Ten protected blob SHAs were unchanged after the code commit: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed request registry `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. Registered and semantically eligible generations, current human-approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent final candidate and human promotion remain absent.

## Next independent safe target

Audit the neighboring autonomous learning positive validator's unexpected-exception CLI path for private diagnostic disclosure; add an executable read-only canary negative without weakening its `ValidationFailure` domain or production `NO_GO`.
