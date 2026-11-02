# Supplemental OPS learning — transaction pinned importer refuses inert open flags (2026-11-02)

Append-only learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, request, request-bound evidence, typed eight-domain coverage, independent review, final candidate or promotion evidence.

## Material failure / latent unsafe condition

- **symptom:** The new generation transaction negative harness pinned importer checked only `hasattr(os, O_DIRECTORY/O_NOFOLLOW/O_NONBLOCK)`, allowing a present but zero/noninteger flag to pass the availability check.
- **evidence:** At previous `so` HEAD `567a326e0f759483cbf55d4dd109e4f12e3d9614`, `pinned_writer_source` used `all(hasattr(os, name) ...)`. A zero-valued `O_NOFOLLOW` would remove the intended no-follow protection from its open flags. This was a verified source-level guard gap; no real OS platform fault or exploitation was observed.
- **rootCauseOrUnknown:** Verified availability-by-name rather than positive integer capability check. Actual platform flag corruption or adversarial injection is unknown.
- **failedApproach:** Treating a defined constant as a guaranteed effective no-follow/directory/nonblocking flag.
- **correction:** [`c43c9920`](https://github.com/m-shogo/memories-project/commit/c43c99201d157b145f7f76c367cee28c1ae78c99) requires exact positive integer values for all three flags before any owned-FD open.
- **recurrenceGuard:** The read-only transaction negative sets each flag to zero in turn, requires the exact `pinned import unavailable` rejection, and restores the parent process's original flag. Existing positive source and after-capture parent-swap negatives still run.
- **retryCondition:** Revisit on flag semantics, descriptor acquisition or negative-harness import changes. Do not retry unchanged publisher-coupled writer edits, Quay MinIO HTTP 401, canonical large-blob transport or absent human evidence.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41394771425](https://github.com/m-shogo/memories-project/actions/runs/41394771425) completed **SUCCESS** on exact source `c43c99201d157b145f7f76c367cee28c1ae78c99`; the job logged `generation evidence registry transaction negative PASS` and `production decision: NO_GO`. [Backup Restore Admission Chain #41394771379](https://github.com/m-shogo/memories-project/actions/runs/41394771379) also completed SUCCESS.
- **evidence:** Exact-source CI run conclusions and negative-suite job output; no production recovery evidence.
- **whySafe:** The only executable change was a synthetic, independently read-only CI-reachable negative harness; the production-capable Generation Evidence publisher's trigger list excludes it. No production authority or evidence was mutated.
- **reusableMechanism:** Check platform safety flags for exact positive integer values and prove fail-closed behavior with zero-flag fault injection before opening any source descriptor.
- **protectedAuthorityCheck:** Post-change `so` tree retained production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation `bfd1b045`, objectives `f4d74f33`, drill `acebcd02`, evidence `ae7e57ef`, typed eight-domain `26bb1cc7`, promotion `99cb895f`, canonical learning `b809c69d` and mandatory contract `87712ea9` unchanged. Registered/semantically eligible generations 0/0, current human-approved objective 0, executable reviewed request 0, request-bound recovery evidence 0, complete typed coverage 0, final candidate 0. Original preflight/final-candidate/human-promotion gates remain strict and separate.

## Next safe target

Reuse the same zero-flag fault injection in the independently read-only generation-evidence transport and generation-binding transport pinned importers.
