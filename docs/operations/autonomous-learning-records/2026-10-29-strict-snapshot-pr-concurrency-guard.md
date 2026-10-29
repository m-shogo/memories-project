# Supplemental OPS learning — strict OPS-P0-007 snapshot PR concurrency (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production/backup/restore/RPO/RTO/skew/drill/credential/traffic/readiness/promotion evidence. Cannot register generations, approve objectives, execute reviewed drills, satisfy typed eight-domain coverage, independently review candidates or authorize human promotion.

## Material failure / executable recurrence prevention
- **Symptom:** Strict OPS-P0-007 snapshot PR-only workflow had approved PR-number cancellation but its permission-negative validator independently pinned only readonly and publisher concurrency; PR group/cancellation shadows lacked exact diagnostic classification. Static semantic coverage gap, not observed production bypass.
- **Observed evidence:** Reviewed PR workflow blob `61ab809781c870e4dba4b4a1aa2c0131540decc2` declares `ops-p0-007-admission-snapshot-pr` PR-number group and `cancel-in-progress: true`. Previous validator blob `8392d8b207e94b712779c951ec82a9511e6dba84` pinned readonly and publisher but not PR concurrency leaves.
- **Verified root cause:** Whole-source digest and other role-specific concurrency guards do not independently prove PR-only cancellation semantics or reject YAML-equivalent shadow leaves with PR-specific diagnostics.
- **Failed approach:** Assuming the readonly `true` cancellation or publisher `false` cancellation guard also covered the distinct PR workflow.
- **Correction / executable recurrence guard:** [Commit `248c5087`](https://github.com/m-shogo/memories-project/commit/248c5087024cdc670a1475fae01c96eaa1087011) adds PR-number-scoped `cancel-in-progress: true` validator and ten exact-diagnostic in-memory negatives: global group, disabled cancellation, duplicate/spaced/quoted group/cancellation leaves, unreviewed leaf and missing cancellation.
- **Retry condition:** Revisit only if reviewed PR concurrency policy changes, a bypass is observed or exact-source CI regresses. Unchanged MinIO 401, canonical learning transfer, workflow-write permission and human approval blockers are not retried.

## Material success / protected authority
- **Observed outcome/evidence:** [OPS P0 007 Snapshot Permission Boundary #40817350336](https://github.com/m-shogo/memories-project/actions/runs/40817350336) completed **SUCCESS** at exact code `248c5087`. Log explicitly confirms ten PR, ten readonly and ten publisher concurrency exact-diagnostic negatives. Other snapshot and full admission runs remain separate results.
- **Why safe:** Only existing CI-reachable read-only Python validator changed (+48 lines, zero deletions); no reviewed workflow, protected evidence/registry, credentials, traffic or human promotion authority was modified.
- **Reusable mechanism:** Require distinct reviewed concurrency semantics for PR validation (`true`), readonly snapshot (`true`) and publisher (`false`) with expected diagnostics. Preserve strict OPS-P0-007 registered-versus-eligible generations, distinct unsuperseded environments, human-approved current objective, executable reviewed request, complete typed eight-domain non-resurrection, independent review and separate human promotion.
- **Protected-authority check:** Production status blob `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `productionDecision=NO_GO`; autonomous learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. CI and learning cannot satisfy production readiness.
- **Canonical learning limitation:** Canonical large-file authority remains unavailable via existing connector; unchanged transport blocker not retried.
- **Next safe target:** Audit remaining PR-only concurrency semantics and broad upload-route push path glob while keeping protected production gates unchanged.
