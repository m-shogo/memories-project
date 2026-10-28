# Supplemental OPS learning — backup restore contracts CI job authority (2026-10-29)

Append-only supplemental learning only; not canonical learning, production-equivalent generation or recovery evidence, backup/restore, RPO/RTO/skew, reviewed drill, credentials, traffic, readiness, or human promotion authority.

## Material guard gap / failure learning
- **Symptom:** Backup Restore Contracts source-negative validator checked root YAML semantics and full workflow blob, but lacked an independent nested job mapping/permission guard. This is a static admission gap, not an observed unauthorized production event.
- **Observed evidence:** Reviewed `.github/workflows/backup-restore-contracts.yml` has one `validate` job inheriting root `contents: read`, with exactly `runs-on: ubuntu-latest`, `timeout-minutes: 5`, and `steps`; the previous nine YAML negatives did not exercise job-level shadows.
- **Verified root cause:** Root permissions and digest pinning do not separately establish the effective job mapping and absence of job-scoped write or execution bypass keys.
- **Failed approach:** Depending on complete Git blob mismatch alone for nested job YAML mutations, without exact semantic rejection evidence.
- **Correction / executable recurrence guard:** [07c77609](https://github.com/m-shogo/memories-project/commit/07c77609af2c7d1c6660f4c8f844461f19ba1608) pins job identity and job-key sequence, with nine new exact-diagnostic negatives: duplicate/spaced/quoted jobs, plain/spaced/quoted write permission overrides, false job condition, spaced timeout override, and continuation override. YAML negative total is 18.
- **Retry condition:** Revisit only for independently reviewed workflow topology/permission changes or a demonstrated bypass; unchanged MinIO 401, canonical learning transport, workflow write permission, and human promotion blockers are not retried.

## Material success / protected authority
- **Observed outcome/evidence:** [Backup and Restore Contracts #40774571035](https://github.com/m-shogo/memories-project/actions/runs/40774571035) completed SUCCESS on exact source `07c77609af2c7d1c6660f4c8f844461f19ba1608`. Job log confirms 18 exact-diagnostic YAML negatives, 98 event-specific path-removal negatives, and 19 semantic plus two blob-only source admission negatives.
- **Why safe:** Only an existing CI-reachable read-only Python validator changed (+39/-2). No workflow, contract, registry, production/recovery evidence, credential, traffic, or promotion authority changed.
- **Reusable mechanism:** Enforce a unique reviewed YAML job mapping and allowed top-level job-key inventory, with synthetic negative mutations requiring exact diagnostic rather than generic SHA failure.
- **Protected-authority check:** Git compare shows only validator changes. Production status blob `3956bb805ee124ca7baf594ba05bcb0d986783b4` remains `productionDecision=NO_GO`; canonical learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. Empty generation recovery, reviewed request and typed eight-domain registries were not changed. Supplemental learning never satisfies admission/promotion gates.
- **Next safe target:** Admission Authority Linkage Readonly CI nested job authority; retain separate full-chain and human approval gates.
