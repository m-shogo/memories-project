# Supplemental OPS learning — generation transaction importer hardlink and mid-read chmod negatives (2026-11-02)

Append-only supplemental learning governed by `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, human-approved objective, reviewed drill request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure / regression coverage gap

- **symptom:** The generation-evidence registry transaction negative harness did not explicitly exercise hardlinked executable writer source or chmod of the writer source/parent during its pinned descriptor read.
- **evidence:** At `so` HEAD `3dd2bc56090529fa742fcfb5bb14d54931dbe5b0`, `pinned_writer_source` already rejected `st_nlink != 1` and checked before/after source and parent metadata. Its synthetic importer tests covered writable source and parent symlink swaps, but lacked these three deterministic cases. This was a verified regression-test gap, not observed unsafe acceptance.
- **rootCauseOrUnknown:** Verified omission of explicit negative fixtures for existing link-count and metadata-race checks. Real-world adversarial changes are unknown.
- **failedApproach:** Relying on source inspection and the parent symlink swap test to establish coverage for independent hardlink, leaf-mode and parent-mode mutation boundaries.
- **correction:** Commit [`0a9b75bd`](https://github.com/m-shogo/memories-project/commit/0a9b75bd497a661e396c6f4181f4d91743304d4f) adds a real hardlink alias and two `os.read` fault hooks that chmod the writer source or parent while the verified descriptor is being read.
- **recurrenceGuard:** The read-only transaction negative suite requires exact `source metadata unsafe`, `source changed during read` and `parent changed during read` failures, verifies each mutation hook actually ran, restores file modes and monkeypatched `os.read`, and preserves the existing positive control and after-capture parent-swap canary.
- **retryCondition:** Revisit only if the pinned transaction importer, source/parent metadata contract, fixture filesystem or read-only CI trigger changes. Do not retry unchanged production writer/publisher coupling, Quay MinIO HTTP 401, large canonical learning blob retrieval or missing human recovery evidence.

## Material success

- **outcome:** Exact-source [Generation Evidence Reconcile Negative #41396502831](https://github.com/m-shogo/memories-project/actions/runs/41396502831) completed **SUCCESS** on `0a9b75bd497a661e396c6f4181f4d91743304d4f`; job `125118859595` logged `PASS: generation transaction writer pinned source rejects hardlinks, mid-read chmod and swaps`, `generation evidence registry transaction negative PASS`, `Generation evidence reconcile negative suite PASS` and `production decision: NO_GO`.
- **evidence:** Exact-source GitHub Actions conclusion and job logs. This is synthetic validation only, not a production-equivalent generation or recovery.
- **whySafe:** Only the independently read-only transaction negative harness changed. Its source path triggers `contents: read` CI, not the write-capable Generation Evidence publisher. All new fixtures are temporary and restore the source and parent mode; no production authority was edited.
- **reusableMechanism:** Use real hardlinks to verify link-count rejection and deterministic descriptor-read chmod hooks to prove source and ancestor metadata stability checks are executable, not merely asserted in prose.
- **protectedAuthorityCheck:** Post-code GitHub blob SHA verification preserved production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generation registry `bfd1b045`, recovery objectives `f4d74f33`, drill request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review registry `99cb895f`, canonical learning `b809c69d` and mandatory contract `87712ea9`. Registered/semantically eligible generations 0/0; current approved objective, executable reviewed request, request-bound recovery, complete typed coverage and final candidate 0. Independent review and separate human production-promotion remain mandatory.

## Next safe target

Add malformed acquired-FD ownership/cleanup regression tests to the read-only generation transaction importer, reusing prior drill-binding invalid-FD learning and the actual ROOT/ancestor/leaf open sequence.
