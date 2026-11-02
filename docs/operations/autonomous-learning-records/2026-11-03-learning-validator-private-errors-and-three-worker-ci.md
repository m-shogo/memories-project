# Supplemental OPS learning — autonomous validator private errors and nested negative deadline (2026-11-03)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This synthetic read-only record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered/eligible generation, approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human production promotion.

## Material failure class 1 — private unexpected validator exception

- **symptom:** The autonomous-learning positive validator's unexpected-error CLI could expose private source/OS exception messages.
- **evidence:** Before [`65131920`](https://github.com/m-shogo/memories-project/commit/6513192060383744d9c449cdc09464ddb2867656), `scripts/validate-autonomous-learning-system.py` interpolated arbitrary `{exc}` in its broad `except Exception` diagnostic. This is verified source risk, **not** an observed real secret disclosure.
- **rootCauseOrUnknown:** Verified forwarding of unreviewed exception text at the CLI boundary; actual external disclosure is unknown.
- **failedApproach:** Treating arbitrary runtime/OS exception text as an approved validation domain message.
- **correction:** [`65131920`](https://github.com/m-shogo/memories-project/commit/6513192060383744d9c449cdc09464ddb2867656) maps unexpected exceptions to a fixed private-safe diagnostic and preserves the distinct reviewed `ValidationFailure` exit-1 domain.
- **recurrenceGuard:** Five executable, CI-reachable canary cases inject `OSError`, `RuntimeError`, `ValueError`, `TypeError` and a reviewed `ValidationFailure` through the actual CLI `main`, require exact exit/stderr, empty stdout and no private canary.
- **retryCondition:** Revisit only if validator error-domain policy, CLI entrypoint or synthetic injection topology changes.

## Material failure class 2 — observed nested 120-second timeout

- **symptom:** The first exact-source CI after adding the five canary cases failed despite a direct negative-suite PASS.
- **evidence:** [Autonomous Learning Guard #41490973100](https://github.com/m-shogo/memories-project/actions/runs/41490973100) on `6513192060383744d9c449cdc09464ddb2867656` reported `Autonomous learning negative validation PASS (611 fail-closed cases)` at 17:27:24 UTC, then `ENTRYPOINT DOCUMENT VALIDATION FAILED - autonomous-learning guard timed out after 120s: scripts/validate-autonomous-learning-system-negative.py` at 17:30:01 UTC. The direct suite's PASS did not establish nested PASS.
- **rootCauseOrUnknown:** Verified deadline exhaustion in the independently invoked nested suite. The exact per-phase bottleneck or runner scheduling contribution remains **unknown**; no claim that the five new canary checks alone caused the timeout.
- **failedApproach:** Reusing the two-worker isolated negative fixture execution with only a narrow 120-second nested deadline margin as if the direct PASS proved nested completion.
- **correction:** [`e4d91fae`](https://github.com/m-shogo/memories-project/commit/e4d91fae6d675a215b45916e81bde72b8f715c91) precreates three exclusive worker fixture parents and uses three thread-local workers for independent canonical mutations. The reviewed 120-second deadline and every negative case remain unchanged.
- **recurrenceGuard:** The existing source-ordered complete-case assertion, isolated precreated fixture parent topology, exact-source direct and independently nested 611-case runs, entry-document validator and read-only CI remain mandatory. No case or protected ancestor-ctime check was removed.
- **retryCondition:** If the nested deadline fails again, obtain bounded per-phase timing or a concrete contention trace before changing the harness. Do not raise the 120-second deadline, reduce case inventory or repeat the unchanged two-worker approach.

## Material success — observed exact-source CI

- **outcome:** [Autonomous Learning Guard #41491950199](https://github.com/m-shogo/memories-project/actions/runs/41491950199) completed **SUCCESS** on exact `e4d91fae6d675a215b45916e81bde72b8f715c91`. The positive validator privacy fix and all 611 direct/nested negative cases passed.
- **evidence:** Job `125436940896` logged `Autonomous improvement/learning contract validation PASS`, direct `Autonomous learning negative validation PASS (611 fail-closed cases)` at 17:32:58 UTC, independently nested `Autonomous learning negative validation PASS (611 fail-closed cases)` at 17:34:53 UTC, `prewrite fanout audit PASS: 195 synthetic cases`, entry-document PASS, append-only PASS and final read-only steps. The nested suite retained only a small margin below the 120-second limit; this is not a permanent performance guarantee.
- **whySafe:** Only the two existing read-only validators and their isolated synthetic harness changed. The workflow uses `contents: read`, exact-source checkout and no persisted checkout credentials. No production writer workflow, external credentials, traffic, backup/restore evidence, generation, objective, reviewed request, readiness or promotion authority changed.
- **reusableMechanism:** Fixed-domain exception redaction with actual CLI canary injection; deterministic source-ordered parallel fixtures under exclusive precreated parents; independent nested timeout enforcement without increasing the deadline.
- **protectedAuthorityCheck:** Ten protected Git blobs remained unchanged after both code commits: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed request registry `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. Registered/semantically eligible generations remain 0/0, no current human-approved objective or executable reviewed request exists, and no complete typed eight-domain final candidate or human promotion exists.

## Next safe target

Profile the nested negative-suite phase budget if another timeout is observed; independently audit the prewrite fanout CLI's remaining unexpected `RuntimeError` boundary in read-only synthetic tests. Never convert lexical writer inventory or learning records into write permission or production readiness.
