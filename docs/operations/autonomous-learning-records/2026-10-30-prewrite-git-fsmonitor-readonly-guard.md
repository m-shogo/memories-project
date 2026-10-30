# Supplemental OPS learning — disable executable Git fsmonitor during read-only audit (2026-10-30)

Append-only supplemental learning under `contracts/operations/autonomous-learning-system.json`. Canonical learning authority remains blob-SHA verified, not full-text retrieved. **Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure / read-only execution boundary

- **symptom:** The optional Git index source-identity audit invoked `git ls-files` and `git diff` without disabling a repository-configured `core.fsmonitor` hook. These nominally read-only Git commands can execute a shell program from checkout configuration.
- **evidence:** A disposable local Git repo configured `core.fsmonitor` to a benign executable script that appended a marker. `git status`, `git diff --quiet HEAD` and `git ls-files -v` each invoked the script. Re-running `git -c core.fsmonitor=false ... ls-files` did not create the marker. This is a controlled execution-boundary reproduction, not a production incident.
- **rootCauseOrUnknown:** Verified: Git may invoke the configured fsmonitor hook during index refresh/diff, so the existing subprocess wrapper was not strictly read-only for unreviewed checkout configuration.
- **failedApproach:** Assuming a Git query command cannot run checkout-controlled executable code.
- **correction:** [`4da5cffc`](https://github.com/m-shogo/memories-project/commit/4da5cffc9d1d835afc3e45e8f85e7379abb09cda) adds explicit `-c core.fsmonitor=false` to the audited Git subprocess wrapper. [`8189f41c`](https://github.com/m-shogo/memories-project/commit/8189f41cf4b52b240f75b637b2a0953adfc5ffd6) adds a disposable Git hook execution positive control and actual CLI no-execution check. [`54c27552`](https://github.com/m-shogo/memories-project/commit/54c275521988968da95a4d34f9a2ce9df2f0a78b) replaces an ambiguous generated shell `printf` escape with deterministic `echo /` before final CI validation.
- **recurrenceGuard:** The disposable probe must prove the configured fsmonitor hook is executable; the same audit with the explicit disable must return the clean direct-match positive without creating the hook marker. Exact CLI fixture rejects accidental hook execution, while the read-only guard remains opt-in for Git index source proof.
- **retryCondition:** Re-enable Git fsmonitor only after explicit review of hook provenance and executable side effects with real positive/negative evidence. Do not retry unchanged external MinIO, workflow permission, canonical learning transfer or human promotion blockers.

## Material success / bounded verification

- **outcome:** Local Git proof showed hook execution without the override and no execution with `core.fsmonitor=false`; guard and real CLI fixture were committed. Exact-source GitHub Actions completion was **not yet verified** when this record was written.
- **evidence:** Local temporary repo produced a marker on unguarded `ls-files`, none on guarded `ls-files`. The committed negative fixture tests the actual prewrite CLI and source checkout, not a mocked hook parser.
- **whySafe:** Only the read-only audit subprocess wrapper and disposable test fixture changed; no production workflow YAML, runtime, credential, traffic, recovery evidence or promotion authority changed.
- **reusableMechanism:** Neutralize checkout-controlled Git fsmonitor execution in read-only source-identity audits, then verify with a real harmless hook marker and deterministic cleanup.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged after each change, including canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, no approved current recovery objective or human promotion authority.
- **limits / nextSafeTarget:** Verify exact-source CI; assess remaining Git config/env execution paths and Go/Python transitive CI dependency closure without changing blocked workflow triggers.
