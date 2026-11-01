# Supplemental OPS learning — canonical byte transport and fixture-order recovery (2026-11-01)

Append-only history subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered/eligible environment generation, approved recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final recovery candidate or human-promotion evidence.

## Material failure A — non-byte canonical read transport

- **symptom:** A binary stream returning a non-`bytes` object could bypass an exact immutable-byte contract or produce an uncontrolled `TypeError` at `len(raw)`. This is an injected transport-fault class, not an observed production incident.
- **evidence:** At `698aec10`, the canonical reader called `len(raw)` after `stream.read` without a strict type check. A `bytearray`, `memoryview` or `str` can have a length while not being canonical immutable bytes; `None` cannot be measured.
- **rootCauseOrUnknown:** Verified missing exact transport-type check at the trust boundary. Whether a normal Python binary file stream ever returns these values is not claimed.
- **failedApproach:** Relying on the `rb` mode and the downstream length/UTF-8 handling as proof that the returned object was immutable `bytes`.
- **correction:** [`129b0b80`](https://github.com/m-shogo/memories-project/commit/129b0b80d242fb1637df70fb33d1aeb35e211beb) rejects any `type(raw) is not bytes` before measuring length or decoding.
- **recurrenceGuard:** [`fceb3448`](https://github.com/m-shogo/memories-project/commit/fceb34481debfaa7a8a808ba04d428fc47ddca76) adds four disposable nonbyte read cases (`None`, `str`, `bytearray`, `memoryview`) with exact canonical rejection, real raw-FD closure, independent canary and clean-read recovery. [`9cfb387c`](https://github.com/m-shogo/memories-project/commit/9cfb387c2a927a88f609b496f55cb130bd0de847) repairs fixture initialization so the matrix executes in CI.
- **retryCondition:** Revisit on a change to stream transport type, read length, canonical byte parsing or the negative fixture. No production or external blocker retry is authorized by this synthetic test.

## Material failure B — test fixture initialized after use

- **symptom:** The first nonbyte test commit failed CI before testing its intended behavior.
- **evidence:** [Autonomous Learning Guard #41283865706](https://github.com/m-shogo/memories-project/actions/runs/41283865706) at exact HEAD `fceb3448` FAILED in `prove_canonical_descriptor_read_negatives` with `UnboundLocalError: cannot access local variable 'canary' where it is not associated with a value`, line 795. The `canary` and `real_close` bindings had remained below the newly inserted matrix.
- **rootCauseOrUnknown:** Verified local-variable initialization order in the Python test function. This was a test harness defect, not a failure of the intended runtime byte-type guard.
- **failedApproach:** Inserting a new fault matrix above existing fixture setup while reusing names whose definitions occurred later in the function.
- **correction:** [`9cfb387c`](https://github.com/m-shogo/memories-project/commit/9cfb387c2a927a88f609b496f55cb130bd0de847) moves the canary creation and original `os.close` binding before the first consumer, removing the later duplicate assignments without weakening the test assertions.
- **recurrenceGuard:** The exact-source CI executes the full four-case matrix; any future use-before-initialization fails the read-only validator run. Before extending this matrix, inspect the whole function's fixture-definition order, not only the insertion anchor.
- **retryCondition:** Retry only with corrected fixture ordering or an independently verified equivalent fixture initialization; the unchanged failing `fceb3448` source must not be rerun as a purported fix.

## Material success

- **outcome:** Strict immutable-byte transport rejection and all four nonbyte real-FD cases now pass with the existing canonical reader and preserved external canary.
- **evidence:** [Autonomous Learning Guard #41283854867](https://github.com/m-shogo/memories-project/actions/runs/41283854867) SUCCESS at exact runtime HEAD `129b0b80`; [Autonomous Learning Guard #41283897294](https://github.com/m-shogo/memories-project/actions/runs/41283897294) SUCCESS at corrected test HEAD `9cfb387c`. The latter logged canonical contract PASS, 601 fail-closed cases PASS, 195 fanout synthetic cases PASS, 1,186 helper-ancestor mutations PASS and read-only/append-only checks PASS.
- **whySafe:** Only the read-only Python validator and isolated negative tests changed; the repaired test uses disposable files and never writes protected authority or production evidence. The canonical `closefd=False` ownership and bounded/no-follow/inode checks remain in force.
- **reusableMechanism:** Enforce exact immutable-byte types before length/decoding, and pair transport fault matrices with real-descriptor closure, independent canaries, positive recovery and executable CI reachability. Place fixture bindings before all consumers.
- **protectedAuthorityCheck:** All ten protected blobs unchanged after corrected code: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, approved objectives 0. Human approval, executable request binding, typed eight-domain coverage, independent review and separate promotion remain unsatisfied.

## Next safe target

Audit stable-file short-read acceptance: compare actual byte count with pinned `fstat` size after all identity checks, using an isolated short-read injection. Keep external MinIO HTTP 401, workflow write permission and independent Pre-MinIO Go test blockers scoped and unchanged.
