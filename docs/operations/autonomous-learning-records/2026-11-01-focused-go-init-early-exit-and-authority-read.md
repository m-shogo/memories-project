# Supplemental OPS learning — Go package init early exit and large-authority read (2026-11-01)

Append-only execution learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure 1 — package initializer can produce a false-green Go test

- **symptom:** A package `init()` can call `os.Exit(0)` before the Go test runner starts, yielding a successful `go test` despite a failing selected test that never executes. The previous package-level `TestMain` guard did not cover this independent bypass.
- **evidence:** Standalone Go 1.23.2 synthetic packages with `func init() { os.Exit(0) }` and `func /* split */ init() { os.Exit(0) }` returned `go test` success despite a deliberately failing `TestMustRun`. Repository inspection found one legitimate `init()` in `sustained_local_soak_test.go`, which only references `sort.Ints`; all other 23 package `*_test.go` files had no `init` declaration. No actual repository test bypass was observed.
- **rootCauseOrUnknown:** Verified Go initialization order and source-admission gap: package initializers execute before tests, and `TestMain`-only source checks do not constrain them. This is not an observed production defect.
- **failedApproach:** Treating absence of `TestMain` as sufficient evidence that the package cannot terminate successfully before executing selected tests.
- **correction:** [`f56eb7d8`](https://github.com/m-shogo/memories-project/commit/f56eb7d880da6350f7aac5769c4a18ae2757ff40) adds a conservative `init` source guard. It permits only the existing reviewed `sustained_local_soak_test.go` initializer with its non-exiting `_ = sort.Ints` body, and rejects other `init` tokens in the current package test inventory. Incidental `init` text outside the reviewed shape is intentionally fail-closed, pending explicit review.
- **recurrenceGuard:** Three new executable negative fixtures reject a new direct `init` with `os.Exit(0)`, a Go-valid comment-split `init`, and injection of `os.Exit(0)` into the previously reviewed initializer. They require the exact `unreviewed Upload Route package init bypass` diagnostic.
- **retryCondition:** Revisit if the reviewed initializer, package Go source inventory, Go compiler semantics, test execution harness, or authorized independent pre-MinIO runner changes. Do not retry unchanged MinIO HTTP 401 or workflow-write blockers.

## Material failure 2 — a large authority read returned empty content

- **symptom:** Two attempted guarded validator writes were stopped before mutation because the prewrite canonical-learning read returned an empty content string even though the file SHA was present.
- **evidence:** `fetch_file` returned `content=""` and canonical learning blob `b809c69d` both for a line-range read and a full read. A separate GitHub REST contents fetch returned the actual nonempty learning text (4,171,820 characters) at the same authority path; the attempted writes were aborted by explicit nonempty preflight checks. No bad commit was created.
- **rootCauseOrUnknown:** The exact connector-side reason for empty `fetch_file` content is **unknown**; large-file response handling is suspected but not verified. The canonical authority itself was not empty.
- **failedApproach:** Treating a file metadata SHA plus empty `fetch_file` content as an adequate prewrite authority read.
- **correction:** Re-read this large authority through the supported GitHub REST contents fetch and verify its nonempty append-only policy text before writing. Retain SHA and branch-head checks.
- **recurrenceGuard:** A prewrite check must reject empty/partial authority text regardless of returned blob metadata; use the already verified alternative read path for this large canonical learning file, not repeated unchanged `fetch_file` attempts.
- **retryCondition:** Reassess `fetch_file` only after a verified connector behavior/capability change or if the canonical authority size/representation changes. Otherwise reuse the successful REST contents read path.

## Material success

- **outcome:** The existing read-only CI negative validator now rejects the three package-test initializer bypass mutations while retaining the reviewed harmless initializer.
- **evidence:** [Autonomous Learning Guard #41274267736](https://github.com/m-shogo/memories-project/actions/runs/41274267736) completed **SUCCESS** on exact code HEAD `f56eb7d880da6350f7aac5769c4a18ae2757ff40`. Observed logs: 601 canonical fail-closed negatives PASS; 39 supplemental-history fixtures PASS; 195 fanout synthetic cases PASS; helper ancestor reachability and 1,186 negatives PASS; append-only and read-only checks PASS. GitHub compare `da90fe68..f56eb7d8` reports only `scripts/validate-autonomous-learning-system-negative.py` changed (+55 lines, no deletions).
- **whySafe:** The mutation affects only the existing read-only negative validator, not Go implementation/tests, workflows, production/recovery authority, credentials, traffic, readiness or promotion. The allowed initializer is based on observed source, not fabricated runtime evidence.
- **reusableMechanism:** Treat Go package initializers as separate pre-test execution authority, preserve legitimate initialization through a reviewed narrow allowlist, and prove bypass rejection with compiler-valid negative fixtures. Preserve a nonempty, verified canonical authority read before every write.
- **protectedAuthorityCheck:** The code commit modified one validator file and no protected authority. Canonical learning blob `b809c69d`, contract blob `87712ea9`, production status blob `b55ee4ad` and `productionDecision=NO_GO` remain unchanged. OPS-P0-007 registered/semantically eligible generation, distinct-environment, approved current objective, executable reviewed request, request-bound evidence, complete typed eight-domain non-resurrection, independent review and human promotion gates remain unsatisfied and separate.

## Evidence boundary and next safe target

This is exact-source **static validator CI**, not a focused Go package test run. The guard currently scans `*_test.go` files, not all three non-test `.go` files in `internal/httpserver`; review whether extending the same initializer admission across all direct package compilation inputs is warranted. An independent non-skipped pre-MinIO Go test remains unverified.
