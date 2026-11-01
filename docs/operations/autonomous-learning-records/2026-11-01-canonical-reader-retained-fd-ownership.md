# Supplemental OPS learning — canonical reader retains FD ownership (2026-11-01)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, or human-promotion evidence.

## Material failure

- **symptom:** The canonical learning-authority reader handed its raw descriptor to `os.fdopen(fd, "rb")` and, if construction raised, attempted `os.close(fd)` using the old numeric descriptor. Ambiguous constructor ownership could permit an unrelated recycled FD to be closed. This is a source-level latent safety risk, not an observed production incident.
- **evidence:** At code HEAD `d9eebe5b040c013d60c82ccae6c1bb9a4d0b3aa0`, `read_canonical_authority_bytes` used default stream ownership, an exceptional unconditional raw-FD close, and a stream-owned success path. Prior Upload Route learning had already documented same-number/same-inode reuse and the insufficiency of an unqualified post-handoff close; the canonical reader used a separate implementation.
- **rootCauseOrUnknown:** Verified ownership ambiguity at a stream-construction exception boundary: numeric FD reuse is not an ownership proof. No actual incident or post-effect fdopen failure in this canonical reader was observed.
- **failedApproach:** Assuming a raising `fdopen` could not have consumed/released the descriptor, then closing by its old integer value. The previous Upload Route fstat-then-close approach was not reused because it is not an atomic FD compare-and-swap.
- **correction:** [adffee1a](https://github.com/m-shogo/memories-project/commit/adffee1a560f9f999db32cc7b975f3b82016bb61) uses `os.fdopen(fd, "rb", closefd=False)`, retaining raw FD ownership while the non-owning stream is active. One outer `finally` closes the retained descriptor; cleanup errors fail closed on success and preserve an already-pending validation/read failure. The stream no longer takes ownership under normal Python `closefd=False` semantics.
- **recurrenceGuard:** Existing descriptor-positive, fdopen-acquisition failure, bounded-read, hardlink, permissions and path-swap negatives execute in exact-source CI. A follow-up dedicated negative must bind the explicit `closefd=False` argument and exercise pre-/post-effect raw-close errors and original-error preservation; do not claim those additional faults were CI-proven in this code commit.
- **retryCondition:** Revisit on a change to the Python stream ownership contract, canonical descriptor cleanup, injected FD-reuse evidence, or the existing read-only CI path. Do not retry unchanged MinIO HTTP 401 or workflow-write permission blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41282705847](https://github.com/m-shogo/memories-project/actions/runs/41282705847) completed SUCCESS on exact code HEAD `adffee1a560f9f999db32cc7b975f3b82016bb61`.
- **evidence:** Logs show canonical contract PASS, 601 canonical fail-closed negatives PASS, 52 workflows / 63 Python commands / 204 source-negative fixtures, 195 fanout synthetic cases PASS, 1,186 helper-ancestor negatives PASS, append-only and read-only checks PASS. Local isolated Python 3.13 experiments also confirmed `os.fdopen(..., closefd=False)` leaves the underlying raw FD open after the stream context exits and preserves the original exception when a cleanup failure is suppressed. Those synthetic experiments are not exact-source GitHub tests.
- **whySafe:** Only `scripts/validate-autonomous-learning-system.py` changed (+13/-10 lines); canonical contract/history, reviewed workflow, production/recovery evidence, Go service, credentials, traffic, readiness and human promotion were untouched. The original bounded descriptor/path identity checks remain intact.
- **reusableMechanism:** Keep raw descriptor ownership explicit with `closefd=False`, close once in an outer finally, and distinguish a cleanup failure on the success path from cleanup during an already-failing read.
- **protectedAuthorityCheck:** Canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`, registered/eligible 0/0, approved objectives 0), and six protected registries remained unchanged and empty. No human promotion authority was satisfied.

## Next safe target

Add deterministic real-FD negative tests for explicit non-owning `fdopen` and for close-before/close-after fault effects while retaining the original read/validation failure and external canary.
