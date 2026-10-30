# Supplemental OPS learning — Upload Route deployment-principal RLS identity proof (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure — potential vacuous RLS integration test

- **symptom:** The reviewed Upload Route live-test helper `appLoginPool` must connect as unprivileged `memory_app_login` and reject superuser or BYPASSRLS connections. Existing source checks pinned the password Skip and advisory lock but not the final database principal identity assertion. If removed, the HTTP integration tests could pass under a privileged connection without proving FORCE RLS behavior.
- **evidence:** Read-only inspection of `services/import-api/internal/httpserver/server_live_test.go` found `neturl.UserPassword("memory_app_login", password)`, a connection ping, a `pg_roles` query for `current_user`, `rolsuper`, `rolbypassrls`, and a fatal assertion that rejects any mismatch or privileged role. A search of the CI-reachable negative validator found no prior `rolsuper` or `bypassesRLS` guard. This was a prospective static-guard gap, not an observed production RLS failure.
- **rootCauseOrUnknown:** Verified: prior guard coverage bound role password and advisory lock behavior, but not the separate post-connect non-superuser/non-BYPASSRLS proof. Dynamic database execution remains unproven.
- **failedApproach:** Treating successful deployment-principal connection creation or an unchanged `ALTER ROLE` statement as proof that the HTTP test runs under the intended RLS-limited principal.
- **correction:** [`74ce9c64`](https://github.com/m-shogo/memories-project/commit/74ce9c64b1fbc7c0fef38c35d71b933198bc5c50) pins the reviewed connection/ping/cleanup chain and the actual `pg_roles` identity assertion in the function-scoped read-only validator.
- **recurrenceGuard:** Ten executable source mutations must be rejected: wrong principal, skipped ping, removed cleanup, wrong catalog column, query through admin, ignored superuser flag, ignored BYPASSRLS flag, ignored username, suppressed fatal and returned admin pool. All mutations target only the reviewed helper and must produce the exact identity-proof diagnostic.
- **retryCondition:** A legitimate principal/role proof change requires independent RLS semantics review, matching synthetic negatives, exact-source CI, and protected-authority verification. Do not retry unchanged external MinIO, workflow-write or human-promotion blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41030245225](https://github.com/m-shogo/memories-project/actions/runs/41030245225) completed **SUCCESS** on exact source `74ce9c64b1fbc7c0fef38c35d71b933198bc5c50`.
- **evidence:** CI logs show append-only and learning contract PASS, 509 canonical fail-closed negatives, 193 prewrite fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only checks PASS. The ten new principal-identity negatives are nested and do not increase the printed 509.
- **whySafe:** Only `scripts/validate-autonomous-learning-system-negative.py` changed (+83 lines); no Go production/test code, PostgreSQL migrations, workflows, credentials, traffic, production evidence or protected registries changed.
- **reusableMechanism:** Independently bind the identity of the connection used for security-sensitive tests, including privilege flags and fail-closed assertions, rather than trusting successful connection establishment.
- **protectedAuthorityCheck:** The commit diff contains only the CI-reachable read-only validator; canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and protected recovery/review registries are unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0; approved current recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain record, independent review and human promotion remain absent.

## Next safe target

Bind the `newLiveServer` HTTP handler composition to the unprivileged `appPool` and fenced service graph; an identity-verified pool alone does not prove every route uses it. Continue Go-only pre-MinIO CI reachability and complete Go/Python runtime dependency/trigger closure without modifying workflow YAML.
