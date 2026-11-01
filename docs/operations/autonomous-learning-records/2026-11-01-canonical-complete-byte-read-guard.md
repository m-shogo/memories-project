# Supplemental OPS learning — complete canonical byte read guard (2026-11-01)

Append-only operational learning subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered/semantically eligible generation, approved objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion gates.

## Material failure

- **symptom:** The canonical authority reader could accept an immutable `bytes` value shorter or longer than the pinned regular file's stable `st_size` when a stream returned a partial or fabricated payload without changing file metadata. This is a deterministic injected-read gap, not evidence of a production incident.
- **evidence:** At code HEAD `7d78034`, the reader checked byte type, maximum size, descriptor identity and before/after file metadata but did not require `len(raw) == before.st_size`. A synthetic short read `b"sta"` or surplus read `b"stableX"` from a stable six-byte file would satisfy the earlier checks.
- **rootCauseOrUnknown:** Verified missing comparison between the bytes actually returned and the pinned regular-file size. Normal buffered reads generally fill a requested count, but this is not a substitute for an explicit fail-closed completeness invariant under faults.
- **failedApproach:** Relying on stable `fstat` metadata and an upper bound alone to establish that all canonical authority bytes were read.
- **correction:** [`298095c2`](https://github.com/m-shogo/memories-project/commit/298095c23d368044235a49dd877acc72d01833b5) rejects any byte count differing from `before.st_size` after the existing path/inode/mode checks, using the canonical unreadable-authority diagnostic.
- **recurrenceGuard:** [`ce10d894`](https://github.com/m-shogo/memories-project/commit/ce10d8947702960cf71bb56700523e9381dd5f35) adds two CI-reached real-FD injected stream results (truncated and surplus) and checks exact rejection, raw FD closure, external canary integrity and clean-read recovery.
- **retryCondition:** Revisit on changes to bounded stream reads, pinned metadata, canonical byte transport, file replacement handling or negative harness reachability. Do not retry unchanged MinIO HTTP 401 or workflow-write permission blockers.

## Material success

- **outcome:** The canonical read-only authority loader now requires complete, exact-size immutable bytes from a stable pinned regular file.
- **evidence:** [Autonomous Learning Guard #41284267501](https://github.com/m-shogo/memories-project/actions/runs/41284267501) SUCCESS on exact runtime HEAD `298095c2`; [Autonomous Learning Guard #41284277425](https://github.com/m-shogo/memories-project/actions/runs/41284277425) SUCCESS on exact test HEAD `ce10d894`. The latter logged contract validation PASS, 601 fail-closed negatives PASS, 195 fanout synthetic PASS, 1,186 helper-ancestor negative mutations PASS, append-only and read-only checks PASS. These are synthetic/CI proofs only, not production evidence.
- **whySafe:** Only the read-only Python authority validator and its disposable negative suite changed. No production route, workflow, evidence registry, credential, traffic, readiness or promotion authority changed. The existing no-follow, bounded, non-owning FD, cleanup and identity checks remain intact.
- **reusableMechanism:** Couple bounded reads with both exact transport type and pinned-size equality, after file identity checks. Prove incomplete and fabricated surplus results with real-descriptor fault fixtures and independent canaries.
- **protectedAuthorityCheck:** Ten protected blobs unchanged at code HEAD `ce10d894`: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0 and approved objectives 0. Reviewed requests remain planning-only, executable request-bound evidence and complete typed eight-domain coverage plus independent review remain mandatory, and human production promotion remains separate/non-automatic.

## Next safe target

Review the remaining ordinary stream-exception classification and bounded read identity checks; prioritize executable negative guards rather than repeating unchanged MinIO or workflow-permission blockers. The independent pre-MinIO Focused Go test path remains unproven.
