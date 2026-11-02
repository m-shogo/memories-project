# Supplemental OPS learning — exact real strict prewrite transcript (2026-11-02)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Learning, read-only tests and synthetic fixtures never satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion gates.

## Material failure / correction

- **symptom:** The real strict-source prewrite CLI audit still compared `stdout.splitlines()` to its reviewed transcript, accepting missing terminal LF and CRLF as equivalent. No observed malicious output or unsafe production write.
- **evidence:** Prior `scripts/validate-autonomous-learning-system-negative.py` built `expected_real_transcript` but only checked `real_lines != expected_real_transcript`; the adjacent synthetic oracle was already corrected in `84c8b665` and exact-source [CI #41434764088](https://github.com/m-shogo/memories-project/actions/runs/41434764088) completed SUCCESS, including 601 fail-closed cases and 195 synthetic fanout cases.
- **rootCauseOrUnknown:** Verified same normalized-line oracle weakness in a separate real-source execution boundary; exploit occurrence unknown.
- **failedApproach:** Treating normalized line parity as a complete byte-exact CLI proof.
- **correction:** [`990afc03`](https://github.com/m-shogo/memories-project/commit/990afc032c3431d28e10fc88264b1e7fff01696d) adds `require_strict_source_transcript` and binds the actual real-source result to exact LF-terminated stdout, exact `CompletedProcess`, integer exit code and string streams.
- **recurrenceGuard:** Ten executable synthetic mutations reject missing LF, CRLF, extra line, wrong path, unreviewed workflow identity, missing advisory, Boolean exit status, byte stdout, byte stderr and extra stderr. Existing real-source count/identity/risk/exit and Git-index parity checks remain.
- **retryCondition:** Revisit only if reviewed CLI grammar, exact source path or workflow topology changes. Do not repeat the normalized-line approach.

## Observed safe progress

- **outcome:** The code commit and its single-file diff were verified on `so`; exact-source [Autonomous Learning Guard #41435421359](https://github.com/m-shogo/memories-project/actions/runs/41435421359) was running at the time of this record. This is **not** a claim of completed CI success.
- **evidence:** GitHub comparison of parent `46791f90` to `990afc03` reported only the negative suite changed. Source re-read confirmed the new helper and ten mutations. GitHub Actions reported the exact SHA as the run head.
- **whySafe:** The change is read-only negative-test code and cannot publish production authority.
- **reusableMechanism:** Reuse byte-exact, type-strict process transcript mutation tests for every independent CLI classifier, not only synthetic fixtures.
- **protectedAuthorityCheck:** All ten protected Git blob SHA identities were re-fetched unchanged after the code commit: production `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, contract `87712ea9`.

## Scoped execution-environment failures and corrected retry conditions

- **symptom:** A direct local `git clone` attempt failed with `Could not resolve host: github.com`; a one-call 35/221-file workflow scan exceeded the orchestration call budget.
- **evidence:** Local Git returned DNS failure before any checkout; the oversized tool batch returned a maximum-tool-calls error. Neither failure modified the repository or production evidence.
- **rootCauseOrUnknown:** Local DNS/network access remains unverified; the tool-call budget for a single batch was exceeded.
- **failedApproach:** Retrying an unavailable direct clone or scanning all workflow files in one oversized tool call.
- **correction:** Use connected GitHub source reads and exact-source CI for validation; scan immutable commit workflow sources in bounded 12-file batches.
- **recurrenceGuard:** Preserve immutable ref and per-file blob identities, cap source-read batches, reconcile final `so` HEAD, and do not infer YAML effective permissions from lexical markers.
- **retryCondition:** Retry direct cloning only when DNS/network access changes; increase batch size only when the call budget changes. No unchanged blocker was retried.
- **observed outcome/evidence:** Bounded GitHub reads completed all 221 workflow files at `84c8b665` without fetch errors; 104 had both lexical write and push markers. The inventory remains diagnostic, not a permission proof.
- **whySafe / reusableMechanism:** Read-only immutable-source retrieval and bounded batching; no workflow dispatch or publisher mutation.
- **protectedAuthorityCheck:** The same ten protected authority blobs remained unchanged and `productionDecision=NO_GO`.

## Next safe target

Apply byte-exact transcript checks to the independently exercised known-external and shared-entrypoint prewrite CLI paths, then establish an executable source-derived writer-inventory guard with negative fixtures and read-only CI.
