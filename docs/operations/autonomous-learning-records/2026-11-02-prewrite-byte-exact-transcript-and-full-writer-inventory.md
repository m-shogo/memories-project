# Supplemental OPS learning — byte-exact prewrite transcript and full workflow lexical inventory (2026-11-02)

Append-only subordinate record to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This learning, source audit and synthetic CI are **never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed drill request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material verifier failure / correction

- **symptom:** The prewrite synthetic CLI oracle could accept an output lacking its terminal LF or using CRLF, despite claiming to verify an exact transcript. No malicious CLI output or production mutation was observed.
- **evidence:** At prior source `230e9543`, `require_exact_count` compared `result.stdout.splitlines()` with expected lines. Python `splitlines()` erases terminal-line-ending distinctions and did not enforce exact stream/status types.
- **rootCauseOrUnknown:** Verified test-oracle equivalence too broad; exploit or operational occurrence unknown.
- **failedApproach:** Treating normalized lines as a byte-exact CLI transcript.
- **correction:** [`84c8b665`](https://github.com/m-shogo/memories-project/commit/84c8b6655ee1bc77057610683a0baaf628843077) requires an exact LF-terminated stdout string, exact `CompletedProcess`, integer exit status and string streams.
- **recurrenceGuard:** Six executable negative mutations reject missing final LF, CRLF, extra blank line, Boolean success code, byte stdout and byte stderr. Existing wrong-path/duplicate/missing-advisory/extra-output/wrong-risk mutations remain.
- **retryCondition:** Revisit only if the reviewed CLI output grammar or Python process API changes; never weaken exactness to accept unknown output.

## Observed safe validation

- **outcome:** Exact-source read-only [Autonomous Learning Guard #41434764088](https://github.com/m-shogo/memories-project/actions/runs/41434764088) completed its `Validate learning contract and executable negatives` job step successfully on `84c8b665`; the overall workflow was still in progress when this record was written, so a completed workflow SUCCESS is not claimed.
- **evidence:** GitHub Actions job `125241717689` reported successful checkout, clean exact-source verification, append-only learning check and validator/negative-suite step. The commit changed only `scripts/validate-autonomous-learning-system-negative.py`; subsequent GitHub comparison showed no other files changed.
- **whySafe:** Read-only test code only; no publisher, production registry, credentials, traffic, readiness or promotion authority was modified.
- **reusableMechanism:** Mutation-test byte-level transcript oracles, including process and stream types, rather than only normalized output lines.
- **protectedAuthorityCheck:** Ten checked Git blob SHA identities unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), environment generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, learning contract `87712ea9`. No production gate advanced.

## Material source-derived writer-inventory blocker

- **symptom:** The seven-entry `KNOWN_WRITER_CAS_WORKFLOWS` list is not a complete writer-permission inventory; earlier 40-source sampling observed 37 unclassified lexical writer signals.
- **evidence:** At immutable `so` HEAD `84c8b665`, GitHub listed **221** `.github/workflows/*.yml` entries. All 221 files were fetched at that commit in bounded 12-file batches with no fetch errors. **104** sources contained both a line matching `contents: write` and a `git push` token; the seven named writer-CAS workflows and one known external-blocked writer are included, leaving **96** sources outside those two reviewed sets with both lexical signals. Newly observed examples beyond the earlier 40-source sample include `admission-authority-linkage.yml` (`454db6f5`), `backup-restore-drill-generation-eligibility-binding.yml` (`f5bf77c9`), `backup-restore-drill-preflight.yml` (`355bfae3`), and `backup-restore-preflight-generation-eligibility-consistency.yml` (`4eb6040b`). This is a **lexical source inventory only**, not proof of effective permissions, trigger overlap, execution, transitive workflow calls or unsafe production writes.
- **rootCauseOrUnknown:** Verified finite hard-coded classification incompleteness. YAML semantic permission resolution, actual matched paths and transitive reachability remain unknown.
- **failedApproach:** Assuming the seven named writers or bounded direct trigger count represents all write-capable workflows.
- **correction:** Preserve a scoped hold on unreviewed matched workflow writes. Continue independent read-only CI hardening; do not automatically expand the allowlist or grant write authorization from lexical signals.
- **recurrenceGuard:** Required next executable mechanism: source-derived, fail-closed writer-permission inventory and negative fixtures, with exact-source read-only CI; before any sensitive write, independently reconcile matched workflow source identity, effective job permissions, Git push path and source lease.
- **retryCondition:** Revisit classification only with an exact-source reviewed inventory validator and a CI-proven safe update path. Do not retry unchanged external MinIO, unavailable canonical learning bytes, or missing human production evidence.

## Next safe target

Mutation-test exact LF/CRLF/terminal-output semantics in the real strict-source prewrite CLI oracle, then build an independent source-derived writer inventory guard without treating lexical markers as permission authority.
