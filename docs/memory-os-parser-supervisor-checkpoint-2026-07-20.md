# Memory OS Isolated Parser Supervisor Checkpoint

最終更新: 2026-07-20

## Verdict

```txt
Preview spool + PostgreSQL domain + commit repository + object storage adapter:
PARTIAL IMPLEMENTATION (live-tested)

isolated parser supervisor (process boundary):
PARTIAL IMPLEMENTATION CREATED

executable server / clients:
NOT IMPLEMENTED

production:
NO-GO
```

This checkpoint creates the transaction-free parse boundary: one supervised worker process per attempt that can reach only its stdin source and stdout frames — never the spool, database, credentials or files.

## Implemented files

```txt
services/import-api/internal/parsersup/frames.go
services/import-api/internal/parsersup/supervisor_linux.go
services/import-api/internal/parsersup/supervisor_unsupported.go
services/import-api/internal/parsersup/worker.go (test harness)
services/import-api/internal/parsersup/supervisor_linux_test.go
services/import-api/internal/parsersup/race_{enabled,disabled}_test.go
.github/workflows/import-api-security-slice.yml (non-race bounds step)
```

## Supervision flow

```txt
verify pinned worker artifact SHA-256 (O_NOFOLLOW, regular file)
→ create one spool attempt and claim its bounded stream writer
→ spawn the worker in its own process group
  stdin  = version-bound source content, read-only
  stdout = synchronous tagged frames (1-byte A/R + 8-byte length + canonical bytes)
  stderr = 4 KiB bounded capture
  env    = explicit minimal allowlist; credential-shaped names rejected up front
→ apply kernel limits via prlimit64 before consuming output:
  RLIMIT_AS / RLIMIT_CPU / RLIMIT_NOFILE / RLIMIT_FSIZE=0 / RLIMIT_CORE=0
→ stream frames into WriteAccepted/WriteRejected under supervisor-side
  output-byte and wall-clock (pipe read deadline) caps
→ clean EOF + exit 0 → fsync / no-replace seal → sealed evidence
→ any violation, crash, timeout or cancellation → SIGKILL the process group,
  reap, and remove the attempt fail-closed
```

The worker holds no spool, database, storage or credential handles at any point; `RLIMIT_FSIZE=0` additionally kills any attempt to write file content.

## Live evidence (12 top-level tests)

- end-to-end: supervised parse → seal → **independent `previewspool.Verifier` pass** with matching recomputed evidence;
- tampered worker binary digest refuses to execute (nothing spawned, no attempt);
- credential-shaped environment (AWS_/PG*/DATABASE*/…SECRET/TOKEN/PASSWORD/API_KEY…) rejected at construction; the worker itself proves it sees exactly one env var (no PATH/HOME leak);
- 6 GiB memory hog killed by RLIMIT_AS (0.5 s); CPU spin killed by RLIMIT_CPU (~2 s); stalled worker killed by the wall-clock deadline;
- garbage output, oversized (3 MiB) frames and torn frames are terminal protocol violations;
- output-byte flood rejected by the supervisor cap;
- worker file write dies under RLIMIT_FSIZE=0 and leaves no written bytes;
- zero-accepted parses cannot seal;
- every failure path leaves an empty spool root (fail-closed cleanup).

## Validation language

```txt
local golang:1.23 + postgres:16 + minio (fresh), exact HEAD c09ef41bcf8cacd023ecba6c46086c8d554085c4:
gofmt clean + go vet + go test ./... + go test -race ./... (16 packages,
live DB/object-store/supervision tests included) + both 5s fuzz smokes PASS

remote workflows:
recorded after the push completes
```

The race-instrumented suite skips only the RLIMIT_AS hog test (the race runtime reserves enormous shadow address space, making RLIMIT_AS unenforceable on instrumented workers); CI runs the package additionally without race instrumentation so the memory bound is proven remotely too.

## Residual risks

- **network isolation is not claimed here**: it requires a network namespace / container at deployment; the supervisor provides process, credential, filesystem-write and resource isolation only;
- kernel limits land microseconds after spawn; the window is bounded by wall/output caps and the digest-pinned (reviewed) worker code, but a fork-freeze shim would close it fully;
- the harness worker stands in for reviewed adapter artifacts; the canonical-record contract for real adapter output is still not reviewed;
- worker runs as the same UID; user-namespace / seccomp hardening remains deployment work.

## Immediate next task

```txt
Compose the supervised import flow end to end (still no HTTP server):
quarantine object fetch (objectstore) → supervised parse (parsersup)
→ independent verification (previewspool.Verifier)
→ atomic commit (previewcommit) against live PostgreSQL + MinIO in one test-proven flow
```

Do not add executable-server or client wiring in that checkpoint.
