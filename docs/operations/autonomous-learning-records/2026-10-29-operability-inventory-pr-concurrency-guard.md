# Supplemental OPS learning — operability inventory PR concurrency (2026-10-29)

Append-only supplemental learning only, not canonical learning, production/backup/restore/RPO/RTO/skew/drill/credential/traffic/readiness/promotion evidence. Cannot register generations, approve objectives, execute reviewed drills, satisfy typed eight-domain coverage, independently review candidates, or authorize human promotion.

## Material failure and executable recurrence prevention
- **Symptom:** Operability inventory PR-only workflow had an approved PR-scoped cancellation policy but its independent source-negative validator pinned only source SHA, event/trigger/job/permission semantics, not the nested concurrency group and cancellation leaves. Static semantic-guard gap, not an observed production bypass.
- **Observed evidence:** Reviewed PR workflow blob `def6b2891a2c6f6ccda57dece11190ceb19b3cbf` declares `operability-admission-inventory-pr` group and `cancel-in-progress: true`. Prior validator blob `f2ce5971ccd7d6313892032f91f3f0a2ab4b01ad` lacked concurrency leaf classification.
- **Verified root cause:** Git blob binding and job/root checks do not independently diagnose YAML-equivalent concurrency shadow changes or cancellation-policy drift.
- **Failed approach:** Treating digest-only source rejection as proof of approved PR cancellation semantics, or assuming all workflows must use noncancelling policy.
- **Correction / executable recurrence guard:** [Commit `3f0ea75f`](https://github.com/m-shogo/memories-project/commit/3f0ea75f7929df9fb612d48f3dd68fb9b15e5935) pins reviewed `cancel-in-progress: true` and ten exact-diagnostic in-memory negatives: global group, disabled cancellation, duplicate/spaced/quoted leaves, extra leaf and missing cancellation.
- **Retry condition:** Revisit only on reviewed PR concurrency-policy change, observed bypass, or exact-source CI regression. Do not retry unchanged MinIO 401, canonical learning transfer, workflow-write permission or human approval blockers.

## Material success and protected authority
- **Observed outcome/evidence:** [Operability Admission Inventory PR Source Negative #40817179450](https://github.com/m-shogo/memories-project/actions/runs/40817179450) completed **SUCCESS** at exact code `3f0ea75f`; job log confirms ten new concurrency negatives, 24 job authority negatives, four permission leaf negatives, 29 trigger omissions, 12 additions, two shortened inventories, three event topology negatives, eight root shadows, and existing runtime/source tests.
- **Why safe:** Only the CI-reachable read-only source-negative Python validator changed (+48 lines, zero deletions). Reviewed PR and independent workflows, production status, protected evidence/registries, credentials, traffic and human promotion authority were untouched.
- **Reusable mechanism:** Preserve role-specific cancellation policy and require exact diagnostic classification for YAML-equivalent concurrency mutations. OPS-P0-007 registered and semantically eligible unsuperseded generations, approved current objective, executable reviewed request, complete typed eight-domain evidence, independent review and human promotion remain separate nonautomatic gates.
- **Protected-authority check:** Production status blob `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `productionDecision=NO_GO`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. Supplemental learning and CI cannot satisfy readiness.
- **Canonical learning limitation:** Canonical large-file learning authority remains unreadable through existing connector route; unchanged transport blocker not retried.
- **Next safe target:** Audit remaining PR/readonly concurrency gaps and broad upload-route push path glob without changing production authority.
