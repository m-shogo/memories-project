# Supplemental OPS learning — Upload Route localhost test environment fingerprint and CI recovery (2026-10-30)

Append-only supplemental history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy is `contracts/operations/autonomous-learning-system.json`. Learning cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, human-approved recovery-objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure 1 — prospective external test endpoint drift

- **Symptom:** Upload Route workflows could change local PostgreSQL/S3 test endpoints, service ports/health options, database name, or step-specific source-SHA environment bindings without changing the pinned Go/Python command and import fingerprints.
- **Observed evidence:** Both actual Publisher/PR workflows use local PostgreSQL `127.0.0.1:5432`, local S3 `127.0.0.1:9000`, reviewed Postgres service settings and a source/PR-head SHA step environment. Previous toolchain environment guard rejected resolver overrides but did not fingerprint these service/job/step blocks. This is a prospective risk, not observed production traffic.
- **Verified root cause:** Direct command/import/action fingerprints do not bind service configuration and environment dataflow.
- **Failed approach:** Treating stable runtime command strings and action inputs as sufficient proof of local-only test execution.
- **Correction / executable recurrence guard:** [`58be080c`](https://github.com/m-shogo/memories-project/commit/58be080c844600d93781ca9c4ba652a86941b5e6) adds exact SHA-256 fingerprints for the PostgreSQL service, job-level test environment, and service/step environment blocks, separately for Publisher and PR. The CI-reachable read-only guard rejects service/endpoint/credential-label/port/health/SHA binding drift. No workflow YAML was changed.
- **Retry condition:** Any legitimate test service/environment change requires explicit review of endpoint isolation and credential impact, deterministic fingerprint update, exact-source CI, and protected-authority verification. Never infer production safety from local fixture success.

## Material failure 2 — nonunique negative-fixture anchor

- **Symptom:** Initial [Autonomous Learning Guard #40947042434](https://github.com/m-shogo/memories-project/actions/runs/40947042434) **FAILED** with `RuntimeError: Upload Route test environment fixture anchor changed: S3 endpoint`; no production workflow was run.
- **Observed evidence:** Both reviewed workflows contain `http://127.0.0.1:9000` twice: once in `MEMORY_OS_TEST_S3_ENDPOINT`, once in the MinIO health-check `curl` command. The initial negative fixture incorrectly required the unqualified URL substring to occur once.
- **Verified root cause:** The fixture anchor was not scoped to the intended YAML environment key. The failure was in the test fixture, not evidence of service drift or a production problem.
- **Failed approach:** Global occurrence-count assertion on a URL shared by two distinct workflow execution inputs.
- **Correction / executable recurrence guard:** [`a4263894`](https://github.com/m-shogo/memories-project/commit/a426389459fc9dd1237616eb60ef8c6dd9a1d437) replaces the fixture anchor with the unique `MEMORY_OS_TEST_S3_ENDPOINT: http://127.0.0.1:9000` mapping. A prewrite audit checked every fixture anchor in both actual workflows; all event-relevant anchors occurred exactly once. The corrected commit changed only the read-only validator (+2/-1 lines).
- **Retry condition:** Do not reuse an unqualified shared endpoint string. Re-read both actual workflow sources, require one exact intended mapping per negative, and run exact-source CI before treating the guard as proven.

## Prewrite prevention

A proposed source insertion was stopped before GitHub write because the selected function-call anchor occurred twice (synthetic and real-workflow paths). A separate proposed conditional tuple expression would have skipped common PR negatives due to Python conditional precedence. The committed version uses a unique two-line call-site anchor and an explicit per-event `cases.append`; these prewrite failures did not create repository commits. Reuse unique anchor cardinality and explicit branch-wise negative inventories.

## Material success

- **Observed outcome/evidence:** Corrected [Autonomous Learning Guard #40947154758](https://github.com/m-shogo/memories-project/actions/runs/40947154758) completed **SUCCESS** on exact source `a426389459fc9dd1237616eb60ef8c6dd9a1d437`. Logs confirm append-only and contract PASS, 201 printed canonical negatives, 74 fanout synthetic cases, entry-document PASS, 1,186 helper-ancestor negative mutations and read-only completion. The 26 nested service/environment mutations (13 per workflow) are additional to the printed 201.
- **Why safe:** Only the existing CI-reachable read-only negative validator changed; no real workflow YAML, production source, credentials, traffic, generation/objective, reviewed requests, recovery evidence, typed eight-domain records, readiness, independent review or human promotion was altered.
- **Reusable mechanism:** Fingerprint complete local test service/job/step environment blocks; use per-event negative mutations with unique exact-key anchors, and require exact-source CI rather than accepting a local-only parser check.
- **Protected-authority check:** Both code commits modified only `scripts/validate-autonomous-learning-system-negative.py`. Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, mandatory contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remain unchanged. `productionDecision=NO_GO`, registered/semantically eligible generations 0/0, and all separate human/recovery/eight-domain gates unsatisfied.

## Next safe target

Pin critical Upload Route shell run blocks: MinIO readiness, clean-source checks, Publisher source-SHA CAS writer, and PR whole-worktree verification. Keep workflow YAML unchanged; do not retry unchanged Quay MinIO 401 or narrow unproven Go/Python trigger closure.
