# Supplemental OPS learning — non-text capture and bounded connector publication (2026-10-31)

Append-only learning under `contracts/operations/autonomous-learning-system.json`. Canonical learning is unchanged. **This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, approved-objective, reviewed-request, request-bound evidence, typed eight-domain non-resurrection, independent-review, final-candidate, or human-promotion evidence.**

## Material failure 1 — malformed child capture diagnostics

- **symptom:** The bounded child failure formatter could raise `AttributeError` for a missing stream or `TypeError` for a byte stream rather than produce bounded diagnostic text. This was a synthetic boundary gap, not an observed production incident.
- **evidence:** Previous entry-docs blob `e12cfa86` directly called `(completed.stderr or completed.stdout).strip()` and used a string regex. A `None` value has no `strip`, while nonempty `bytes` remain bytes. Six new `CompletedProcess` controls cover `None`, `bytes`, and arbitrary objects in stdout and stderr.
- **rootCauseOrUnknown:** Verified absent exact-type gate. Real `subprocess.run(text=True, capture_output=True)` normally returns strings; actual malformed GitHub Actions captures have not been observed.
- **failedApproach:** Trusting the subprocess transport contract in the failure formatter without validating the captured values.
- **correction:** [`63cc523f`](https://github.com/m-shogo/memories-project/commit/63cc523f8f299e08f45bcd990f8a0dfb0656883f) checks both streams are exact `str` before trimming and normalization, returning the fixed `unreviewed captured stream type` diagnostic otherwise.
- **recurrenceGuard:** Six deterministic in-process negative controls run through the existing CI-reachable `prove_learning_guard_classifier`; the eight prior diagnostic controls remain. No extra subprocesses, 120-second deadline relaxation, or PASS-classifier weakening.
- **retryCondition:** Reconsider only after a reviewed transport type change or an exact-source CI regression with a legitimate capture. Never stringify unreviewed objects to obtain a PASS.

## Material success 1 — verified exact-source CI

- **outcome:** Malformed capture types fail closed with a fixed bounded diagnostic; no malformed child is promoted to PASS.
- **evidence:** 14 isolated Python formatter cases PASS. [Autonomous Learning Guard #41148990141](https://github.com/m-shogo/memories-project/actions/runs/41148990141) **SUCCESS** at exact code SHA `63cc523f8f299e08f45bcd990f8a0dfb0656883f`: canonical append-only PASS, learning contract PASS, 601 direct and 601 independent nested negatives, 195 fanout synthetic, 52 workflow/63 Python command/204 fixture source-negative reachability, 1,186 helper-ancestor negatives, entry-document PASS, and read-only completion.
- **whySafe:** Only `scripts/validate-memory-os-entry-docs.py` changed. No workflow YAML, runtime Go, MinIO, credentials, traffic, production evidence, generation, objective, drill request, non-resurrection coverage, or promotion authority changed.
- **reusableMechanism:** Type-check untrusted subprocess captures before formatting failure evidence; keep bounded diagnostic formatting separate from exact PASS admission.
- **protectedAuthorityCheck:** Code HEAD `63cc523f` preserved all ten protected blob SHAs relative to its parent: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`.

## Material failure 2 — connector tool-call cap during learning publication

- **symptom:** An attempted new-record Git-object publication stopped with `Code Mode exceeded the maximum number of tool calls` after prewrite verification.
- **evidence:** The combined publication script repeatedly fetched the ref, commit, full recursive tree, and contract before each object write; the runtime rejected the script. Subsequent read confirmed `so` still at `63cc523f` and this record path absent. A dangling blob, if any, is not branch authority.
- **rootCauseOrUnknown:** Verified tool-call budget exhaustion; exact per-script cap and any dangling Git objects remain unknown.
- **failedApproach:** Combining repeated full-tree verification and all Git object/branch mutations into one connector orchestration call, contrary to the previously recorded bounded-call lesson.
- **correction:** Separate blob, tree, commit and CAS publication into short bounded tool calls, re-reading current `so` and target before each write.
- **recurrenceGuard:** Explicit expected HEAD/target-absence checks at each publication stage, final CAS ref update and postwrite protected-tree verification. Do not assume an interrupted write succeeded.
- **retryCondition:** Retry only with smaller bounded call batches and unchanged source HEAD/target absence, never with the same oversized orchestration.

## Independent safe audit and production boundary

Existing Upload Route source-negative checks explicitly report a 109-file direct-input lower bound, 81 uncovered inputs for each Push/PR trigger, and 11 SQL migration paths omitted by both. This is **not** complete transitive Go/Python trigger closure. The Import API Security Slice still starts MinIO before Go tests; no independent pre-MinIO focused upload-route test CI was established. Supplemental-record-only Push/PR append-only trigger coverage and workflow-write permission remain blocked; no unchanged blocker was retried.

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0, no human-approved current recovery objective. Preflight requires two distinct unsuperseded eligible environments and human approval; reviewed drill requests remain planning-only, new generation evidence must bind a current executable reviewed request, and final candidates require all existing gates plus typed eight-domain non-resurrection coverage and independent review. Human production promotion remains separate/nonautomatic.

**Next safe target:** Authorized supplemental-learning Push/PR append-only guard, independent pre-MinIO focused Go CI and complete Go/Python trigger closure. Do not retry unchanged MinIO 401, workflow permission, canonical learning full-transfer or human-approval blockers.
