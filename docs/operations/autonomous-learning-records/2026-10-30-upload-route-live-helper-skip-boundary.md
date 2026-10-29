# Supplemental OPS learning — Upload Route live helper conditional skip boundary (2026-10-30)

Append-only supplemental history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under `contracts/operations/autonomous-learning-system.json`. This cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure — prospective silent skip through test helper

- **Symptom:** The two selected HTTP integration tests could remain declared and assertion-bearing while their shared `newLiveServer(t)` helper unconditionally skips, changes its required environment inputs, or is bypassed.
- **Observed evidence:** Read-only source inspection found a single `t.Skip` in `newLiveServer`, conditional on either `MEMORY_OS_TEST_DATABASE_URL` or `MEMORY_OS_TEST_S3_ENDPOINT` being empty. Both reviewed workflows set these job-level inputs. The prior focused-test declaration guard did not independently bind this helper condition or each selected test's helper invocation.
- **Verified root cause:** A direct test-body check does not cover transitive helper skip paths. The workflow's pinned command and source declarations alone do not establish execution.
- **Failed approach:** Assuming direct `t.Skip` absence in the selected tests proves their helpers cannot silently skip.
- **Correction / executable recurrence guard:** [`f6e5ab1e`](https://github.com/m-shogo/memories-project/commit/f6e5ab1eb75e6373de8ac2edae3e5836ad9680f2) adds a CI-reachable read-only guard binding the exact `newLiveServer` environment-read and conditional-skip prefix, exactly one helper skip, and exactly one `newLiveServer(t)` invocation in each selected live test. Five nested negative mutations cover unconditional skip, removed skip, changed environment input, extra skip and missing helper call.
- **Retry condition:** Any legitimate helper skip/env change requires review of actual workflow env, Go test execution semantics, exact-source CI and protected authorities. This static guard does not demonstrate successful MinIO/Go integration execution.

## Material prewrite failure — local anchor transcription

- **Symptom/evidence:** The first candidate's prewrite positive check rejected the helper prefix with observed count zero; no GitHub write occurred.
- **Verified root cause:** The JavaScript prewrite verification string accidentally omitted the `t` in `t.Helper()` while the actual Go source and proposed Python validator contained the correct call.
- **Failed approach:** Relying on a manually retyped verification anchor without comparing it to actual source bytes.
- **Correction / recurrence guard:** Re-read the actual helper source and corrected the prewrite anchor to `t.Helper()`; checked unique full prefix and five mutation anchors before committing. This changed the failed precondition and avoided a malformed write.
- **Retry condition:** Recheck exact real-source anchor cardinality after any source or generator change; do not retry the incorrect anchor.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40951308034](https://github.com/m-shogo/memories-project/actions/runs/40951308034) completed **SUCCESS** on exact source `f6e5ab1eb75e6373de8ac2edae3e5836ad9680f2`. Logs show append-only PASS, 201 printed canonical fail-closed cases, 1,186 helper-ancestor negative mutations, and clean read-only completion. The five new nested helper negatives are separate from the printed 201.
- **Why safe:** Only the CI-reachable read-only negative validator changed (+56 lines). No workflow YAML, Go service, credentials, production traffic, readiness, generation/objective, drill, recovery evidence, typed eight-domain records, independent review or promotion changed.
- **Reusable mechanism:** Bind transitive test-helper skip preconditions independently from selected test names and workflow env identities; prove negative mutation rejection with exact-source CI.
- **Protected-authority check:** Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remain unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, and all separate human/objective/evidence/eight-domain/review/promotion gates remain unsatisfied.

## Next safe target

The same `server_live_test.go` also contains a second `t.Skip` in `appLoginPool` when the database URL lacks a password. The selected live tests transitively call it through `newLiveServer`; bind this independent skip precondition and the reviewed call edge with negative controls. Do not modify the MinIO 401 blocker or infer production readiness.
