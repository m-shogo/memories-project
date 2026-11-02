# Supplemental OPS learning — saturation critical array multi-step CI failure and correction (2026-11-02)

Append-only subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. CI/fixture observations cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion authority.

## Material failure

- **symptom:** Exact-source [Autonomous Learning Guard #41443485948](https://github.com/m-shogo/memories-project/actions/runs/41443485948) on `60b7d6ee` FAILED in the learning Negative Suite with `RuntimeError: saturation critical array source boundary drift`. The canonical contract validation passed; later helper/read-only steps were skipped, not successful.
- **evidence:** Job `125270806281` traceback identified `prove_saturation_critical_path_array_binding`. Immutable workflow blob `1f4b20c0` contains two `critical=(` declarations in different YAML steps; the new test incorrectly required one across the whole file. The publisher step itself has exactly one array and guard.
- **rootCauseOrUnknown:** Verified file-wide cardinality assumption error, not observed stale publication or a production incident.
- **failedApproach:** Treating a generic `critical=(` token as unique across independent shell steps.
- **correction:** [`344e09db`](https://github.com/m-shogo/memories-project/commit/344e09dbda1198f6e324180591888bc27bcaa3bb) anchors the `Publish append-only repeatability run` to `Record privacy-safe ramp diagnostic` YAML step interval before checking the unique critical array.
- **recurrenceGuard:** The real workflow's two arrays serve as a source-backed negative against file-wide uniqueness; the publisher-step boundary and exact 16-path array are now independently required. The separate rebase inventory rejects push commands found only in another YAML step/job.
- **retryCondition:** Accept the correction only after exact-source read-only CI succeeds on `344e09db` or an equivalent later code HEAD. Do not repeat file-wide uniqueness without changed workflow topology.

## Material safe progress

- **outcome:** Corrected code committed on `so`; GitHub source re-read confirmed step-scoped extraction. Exact-source [Autonomous Learning Guard #41443729374](https://github.com/m-shogo/memories-project/actions/runs/41443729374) was queued at record creation; no CI SUCCESS is claimed.
- **evidence:** Two file-wide arrays versus one publisher-step array, failing CI traceback, corrected single-script diff and immutable source blob.
- **whySafe:** No writer workflow, production authority, credentials, traffic, readiness, promotion or remote result was modified. Local Bash expansion remains restricted to exact literal paths.
- **reusableMechanism:** Scope source inventory checks to the actual executable YAML step/job, not whole-file lexical cardinality; keep positive and negative cases.
- **protectedAuthorityCheck:** Post-code Git tree showed unchanged ten protected blob SHAs: production status `d677a1c9` (`NO_GO`), OPS-P0-007 `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, contract `87712ea9`.

## Next safe target

Confirm exact-source CI for corrected array and cross-step rebase guard. Diagnose any further failure before another code write. Maintain `productionDecision=NO_GO` and human promotion review separately.
