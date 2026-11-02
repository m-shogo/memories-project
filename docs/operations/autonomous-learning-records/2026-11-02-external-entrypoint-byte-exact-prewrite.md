# Supplemental OPS learning — external and shared-entrypoint byte-exact prewrite checks (2026-11-02)

Append-only subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Synthetic test output and learning are not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure / executable correction

- **symptom:** The known external-dependency and shared-entrypoint prewrite audit oracles compared normalized `stdout.splitlines()`, accepting noncanonical CRLF and missing terminal LF despite checking path/count/risk/identity/advisory. No observed unsafe write or forged CLI output.
- **evidence:** The two remaining `lines != expected_*_transcript` predicates in `scripts/validate-autonomous-learning-system-negative.py` did not bind exact stream bytes or types. Adjacent real-source check was corrected in `990afc03`, and its [exact-source CI #41435421359](https://github.com/m-shogo/memories-project/actions/runs/41435421359) completed SUCCESS.
- **rootCauseOrUnknown:** Verified reused normalized-line test-oracle weakness; operational exploit occurrence unknown.
- **failedApproach:** Treating line-normalized CLI output as an exact source-authority transcript.
- **correction:** [`40038d9e`](https://github.com/m-shogo/memories-project/commit/40038d9e54d03be5c70503ccbe32f88ea0e6950d) introduces a shared `require_complete_prewrite_transcript` check for both CLI boundaries.
- **recurrenceGuard:** Nine synthetic mutations for each boundary (18 total) reject missing terminal LF, CRLF, extra blank line, wrong audited path, missing advisory, Boolean status, byte stdout, byte stderr and unexpected stderr. Existing source-derived identity/count/risk and exit-code assertions remain.
- **retryCondition:** Revisit only after reviewed CLI grammar, target path or workflow topology changes; do not revert to `splitlines()` as an exact transcript oracle.

## Observed safe progress

- **outcome:** GitHub source re-read confirmed the shared helper and both mutation suites; the exact-source [Autonomous Learning Guard #41435871981](https://github.com/m-shogo/memories-project/actions/runs/41435871981) was in progress when this record was written, so completed CI success is not claimed.
- **evidence:** GitHub parent comparison `21845d37...40038d9e` showed only `scripts/validate-autonomous-learning-system-negative.py` modified. The workflow was queued on the exact code SHA, and all ten protected authority blob identities were independently re-fetched unchanged.
- **whySafe:** Only read-only negative-test code changed. No publisher, production evidence, credentials, traffic, readiness, review or promotion path was modified.
- **reusableMechanism:** One strict, type-checked, LF-terminated CLI transcript predicate reused across independent known-risk and shared-entrypoint checks, with mutation coverage per boundary.
- **protectedAuthorityCheck:** Production `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), environment generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d` and learning contract `87712ea9` stayed unchanged.

## Next safe target

Add a read-only, exact-source, source-derived workflow writer-signal inventory regression guard. Keep lexical signals distinct from effective YAML permissions and do not allow a diagnostic inventory to authorize writes or satisfy OPS-P0-007 gates.
