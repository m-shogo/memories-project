# Supplemental OPS learning — transactional operability inventory concurrency (2026-10-29)

Append-only supplemental history only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, an environment generation, approved current recovery objective, executable reviewed drill, typed eight-domain non-resurrection coverage, credentials, traffic, readiness, independent review or human promotion.

## Material failure / executable recurrence prevention

- **Symptom:** Transactional inventory source-negative CI pinned publisher/independent Git blobs, YAML event/root/job/permission semantics and runtime, but did not independently classify concurrency group/cancellation shadow leaves. Static coverage gap, not an observed production mutation.
- **Observed evidence:** Reviewed publisher workflow blob `8a829f858b451d39355c584a31ba762d53ccdf4e` declares `operability-admission-inventory-transactional-so` and `cancel-in-progress: false`. Previous validator blob `0b24279c49aea8e5fa534799feba0001fd3b606b` checked root `concurrency:` but had no dedicated nested leaf validator.
- **Verified root cause:** Whole-source Git blob mismatch and root-key checks do not independently diagnose YAML-equivalent concurrency shadows or unreviewed cancellation scope changes.
- **Failed approach:** Treating digest mismatch and root mapping presence as complete semantic proof of noncancelling inventory serialization.
- **Correction / executable recurrence guard:** [Commit `a91c1426`](https://github.com/m-shogo/memories-project/commit/a91c14261e16ce1a2e195351bc4f7997974d8bd9) adds exact reviewed concurrency-block validation and ten expected-diagnostic negatives: global group, enabled cancellation, duplicate/spaced/quoted group and cancellation, extra leaf and removed cancellation. All require `transactional publisher concurrency scope drift`.
- **Retry condition:** Revisit only after an approved concurrency-policy change, a demonstrated semantic bypass, or exact-source CI failure. Do not retry unchanged canonical-learning transfer, MinIO 401, workflow-write permission or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Transactional Source Negative #40811439463](https://github.com/m-shogo/memories-project/actions/runs/40811439463) completed **SUCCESS** on exact code `a91c1426`. Job log confirms 10 concurrency negatives, 39 existing YAML authority negatives, branch/event/SHA/PR-base runtime and 17 source negatives. [Transactional Inventory #40811439497](https://github.com/m-shogo/memories-project/actions/runs/40811439497) was **IN_PROGRESS** at learning capture; its terminal result is not asserted here.
- **Why safe:** Only the existing CI-reachable read-only Python validator changed. Reviewed workflows, canonical inventory, production status, generation/objective/drill registries, typed eight-domain records, credentials, traffic and promotion authority were not modified by this code commit.
- **Reusable mechanism:** Independently pin noncancelling publisher concurrency and require expected diagnostics for YAML-equivalent group/cancellation mutations; keep source CI and full workflow outcomes separate.
- **Protected-authority check:** Production status blob `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `productionDecision=NO_GO`; autonomous learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. Supplemental learning cannot satisfy any OPS-P0-007 or human promotion gate.
- **Canonical-learning limitation:** The canonical 4.17 MB learning authority returned empty content through the existing read path; unchanged transport blocker was not retried.
- **Next safe target:** Confirm transactional publisher terminal result and audit another CI-reachable concurrency gap, without modifying protected production authority.
