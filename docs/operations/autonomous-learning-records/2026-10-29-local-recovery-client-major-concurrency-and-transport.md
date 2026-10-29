# Supplemental OPS learning — local recovery concurrency and PostgreSQL client-major correction (2026-10-29)

Append-only supplemental learning only. Not the canonical learning authority, production-equivalent backup/restore/RPO/RTO/skew or drill evidence, an approved recovery objective, an executable reviewed drill request, credentials, traffic, readiness, promotion, or human review.

## Material failure 1 — unchanged PostgreSQL mismatch was re-triggered
- **Symptom:** A read-only source-validator change automatically triggered the local migration rehearsal, which failed in `actual-recovery-artifact` despite the validator passing.
- **Observed evidence:** [Source CI #40801650395](https://github.com/m-shogo/memories-project/actions/runs/40801650395) SUCCESS at `dc41a3dc`, including 10 new exact-diagnostic concurrency negatives. [Rehearsal #40801650541](https://github.com/m-shogo/memories-project/actions/runs/40801650541) FAILED; Ubuntu resolute installed `postgresql-client 18+290ubuntu1` against `postgres:16-alpine`; the server rejected `SET transaction_timeout = 0`. This was the already-known mismatch recorded in `2026-10-29-local-recovery-job-guard-client-major.md`.
- **Verified root cause:** The publisher push path inventory includes the read-only source validator; changing it retriggered the unchanged, previously failed client/server combination. The restore failure itself was caused by the PostgreSQL 18 dump client targeting PostgreSQL 16.
- **Failed approach:** Assuming a source-only validator edit could not re-execute a known blocked publisher, and relying on the runner's floating `postgresql-client` metapackage.
- **Correction:** [`700984ef`](https://github.com/m-shogo/memories-project/commit/700984ef93e40982675b49029035a733a6c1f47b) pinned the rehearsal job to `ubuntu-24.04` while retaining `postgres:16-alpine`, and added executable client/server-major checks before the rehearsal.
- **Recurrence guard:** The exact-source validator binds the reviewed runner and client/server-major preflight. The preflight requires PostgreSQL 16 for `psql`, `pg_dump`, `pg_restore`, and the connected server; mismatches fail before restore.
- **Retry condition:** A rehearsal retry is permitted only after a verified client/server-major precondition change; avoid unrelated source-only edits that automatically retrigger an unchanged external blocker.

## Material failure 2 — malformed client-major source literal
- **Symptom/evidence:** [Source CI #40801858645](https://github.com/m-shogo/memories-project/actions/runs/40801858645) and [Rehearsal #40801858808](https://github.com/m-shogo/memories-project/actions/runs/40801858808) FAILED at `700984ef` with Python `SyntaxError: invalid syntax`.
- **Verified root cause:** Programmatic patch construction over-escaped a Python string containing shell quotes.
- **Failed approach:** Writing a generated Python string without an exact syntax preflight.
- **Correction:** [`1a7fede1`](https://github.com/m-shogo/memories-project/commit/1a7fede13d77ac68688df65087a0ff624c5114ab) corrected the literal.
- **Recurrence guard:** The independent exact-source Python CI failed closed before any rehearsal work; subsequent patches use raw-string-safe construction and source checks. CI rejection is not evidence of a successful rehearsal.
- **Retry condition:** Only retry after the malformed literal is corrected and the exact-source validator can parse.

## Material failure 3 — runner fixture contained a literal newline
- **Symptom/evidence:** [Source CI #40801897345](https://github.com/m-shogo/memories-project/actions/runs/40801897345) and [Rehearsal #40801897364](https://github.com/m-shogo/memories-project/actions/runs/40801897364) FAILED at `1a7fede1` with `SyntaxError: unterminated string literal` at line 453.
- **Verified root cause:** A generated fixture accidentally converted the Python `\\n` escape into a physical newline inside a quoted string.
- **Failed approach:** Blind string-escape replacement during source generation.
- **Correction:** [`b4f562f4`](https://github.com/m-shogo/memories-project/commit/b4f562f4dff9e5b565f7d6c4cb3a28b0d3fe5215) preserved literal escaped newlines; [Source CI #40802007495](https://github.com/m-shogo/memories-project/actions/runs/40802007495) SUCCESS.
- **Recurrence guard:** Independent source CI detects invalid Python before the rehearsal. For future programmatic Python edits, require a syntax preflight and exact escaped-literal assertion before branch update.
- **Retry condition:** Only after the runner fixture is syntactically valid and preserves the reviewed job runner mutation.

## Material failure 4 — over-escaped version regex
- **Symptom/evidence:** [Rehearsal #40802008021](https://github.com/m-shogo/memories-project/actions/runs/40802008021) FAILED at the client-major preflight on `b4f562f4`; Ubuntu noble successfully installed PostgreSQL client 16, but the shell grep pattern had two backslashes and did not match the actual version output.
- **Verified root cause:** Over-escaped extended regular expression `PostgreSQL\\\\) 16\\\\.` in the workflow shell script.
- **Failed approach:** Treating generated source-code escapes as shell regex escapes without checking the effective literal.
- **Correction/recurrence guard:** [`b1344805`](https://github.com/m-shogo/memories-project/commit/b13448059fde2c2ba04ba77c7354adc7113b6720) uses `PostgreSQL\\) 16\\.` in the shell and pins that exact expression with an executable negative source fixture.
- **Retry condition:** Only after the version predicate matches the installed client and the server-major preflight succeeds.

## Material success — bounded local rehearsal only
- **Observed outcome/evidence:** [Source CI #40802113040](https://github.com/m-shogo/memories-project/actions/runs/40802113040) SUCCESS with 10 concurrency, 38 nested-job, 14 root/permission, and 33 source negatives. [Local Migration Recovery Artifact Rehearsal #40802113133](https://github.com/m-shogo/memories-project/actions/runs/40802113133) SUCCESS at code `b1344805`. The real local same-cluster evidence `docs/evidence/migrations/recovery/mig_20261029_b13448059fde.json` records `result=PASS`, `integrityResult=PASS`, actual exact logical-artifact restore, and 11 SQL integration tests after recovery.
- **Why safe:** The rehearsal used ephemeral PostgreSQL 16 and synthetic local data. Evidence explicitly says `environmentClass=LOCAL_POSTGRES_REHEARSAL`, `productionEvidence=false`, `productionTraffic=false`, `productionCredentials=false`; no production-equivalent restore or human promotion is asserted.
- **Reusable mechanism:** Pin the OS/client/server major and prove it at runtime before a bounded actual-artifact restore; preserve full workflow Git-blob identity, job permission/condition authority, exact diagnostics and concurrency cancellation scope.
- **Protected-authority check:** Existing CI appended local-only migration evidence and reconciled OPS-P0-001 `evidenceRefs`, changing the production-status blob from `3ab8092c` to `2c6b196a`; this was inspected rather than misreported as no drift. `productionDecision=NO_GO`, OPS-P0-007=`PARTIAL_FOUNDATIONS_ONLY` with `blocking=true`, and `productionReady=false` remain unchanged. Registered environment generations, approved recovery objectives, executable reviewed drill requests, generation evidence, typed eight-domain records and human promotion are not created by this rehearsal.
- **Next safe target:** Audit read-only distributed rate-limit nested job authority without changing publisher workflow or production evidence.
