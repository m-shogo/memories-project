# Supplemental OPS learning — aggregate shell marker scope correction (2026-11-02)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. No learning, synthetic CI, or shell mock can satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection coverage, independent review, final candidate, or human promotion gates.

## Material failure and reused lesson

- **symptom:** A separate aggregate Bash shell-negative fixture also rejected the unchanged workflow's source boundary, even after the adjacent aggregate source-binding fixture was corrected.
- **observed evidence:** [Autonomous Learning Guard #41454065910](https://github.com/m-shogo/memories-project/actions/runs/41454065910) on `2c2603d5` and [#41454160185](https://github.com/m-shogo/memories-project/actions/runs/41454160185) on `06de34e1` both completed **FAILURE**. The latter failed at `prove_saturation_aggregate_shell_error_classes` with `saturation aggregate shell source step drift`. The reviewed workflow blob `1f4b20c0` contains two setup-python markers globally, one after the aggregate-step start.
- **verified root cause:** The shell-negative fixture independently repeated the same global closing-step uniqueness assumption already diagnosed in the adjacent aggregate source-binding fixture. The shell fixture was authored before the first aggregate CI failure was observed, so the previously recorded failure had not yet become a known retry prohibition at authoring time.
- **failed approach:** Counting `actions/setup-python` across all workflow jobs, rather than within the owning aggregate step.
- **correction:** [`935801ef`](https://github.com/m-shogo/memories-project/commit/935801ef5ce87e34ae21c196da48ba3c09d76fa3) scopes the shell fixture's closing marker to the source suffix after the unique aggregate-step start, reusing the exact correction from [`06de34e1`](https://github.com/m-shogo/memories-project/commit/06de34e142f64fc94ea3969aa1520ad4aa20f6e9).
- **recurrence guard:** Both aggregate validators now require the marker exactly once **after** the aggregate start. The standalone Bash mock was locally exercised with status 0/1/128 and bypass mutants; corrected exact-source CI is still required. Reuse this shared scoped-marker rule in any future multi-job YAML negative fixture.
- **retry condition:** Retry only if corrected exact-source CI fails or the aggregate job/step structure materially changes. Do not repeat workflow-global closing marker uniqueness with unchanged source.

## Material safe continuation

- **outcome:** Scoped correction committed, CI pending. No failed run is claimed as a success.
- **evidence:** Post-change `so` re-read confirms the scoped marker and all ten protected Git blobs unchanged.
- **why safe:** Only the read-only Python negative suite changed. No write-capable publisher, workflow YAML, real remote, production evidence, credential, traffic, readiness, or human promotion was modified.
- **reusable mechanism:** Shared root-cause learning across independently written test fixtures; scope repeated YAML markers to their owning step and confirm with exact-source CI.
- **protected authority check:** Production status `d677a1c9` (`NO_GO`), OPS-P0-007 `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9` unchanged.

## Next safe target

Verify both aggregate source binding and aggregate shell operational-error negatives under the corrected read-only CI. The five post-rebase soak source-lease gaps remain blocked on separately authorized workflow changes. Maintain `productionDecision=NO_GO` and separate human promotion review.
