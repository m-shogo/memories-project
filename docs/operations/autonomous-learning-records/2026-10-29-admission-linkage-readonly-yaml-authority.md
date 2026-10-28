# Supplemental OPS learning — admission linkage readonly CI YAML authority (2026-10-29)

Append-only supplemental learning only; never canonical learning, production evidence, backup/restore, RPO/RTO/skew, drill execution, credential, traffic, readiness or human promotion authority.

## Material failure / recurrence prevention
- **Symptom:** Admission-authority linkage readonly CI pinned 16 reviewed PR/push trigger paths and a whole-workflow Git blob, but had no independent semantic guard for additional YAML events, root key shadows and quoted/spaced permission leaves. This was a static regression coverage gap, not an observed admission bypass.
- **Observed evidence:** Previous `validate_trigger_reachability` checked exact event path inventory; `REQUIRED` pinned visible `contents: read` and absence of literal `contents: write`. Quoted `'contents': write` could rely on blob-only rejection.
- **Verified root cause:** Visible token counts and source digest do not independently assert effective YAML mapping uniqueness and intended diagnostic.
- **Failed approach:** Treating any blob mismatch as sufficient semantic proof.
- **Correction / executable recurrence guard:** [bb2a56ef](https://github.com/m-shogo/memories-project/commit/bb2a56ef8555ac6935307b3002087f88e0892bd2) requires exact reviewed event header, root-key order and root read-only permission leaves. Nine exact-diagnostic negative fixtures reject an extra event, six root shadows and two permission shadows. Existing digest, branch, trigger and read-only authority gates remain.
- **Retry condition:** Revisit only after reviewed YAML topology or validator changes, or a new semantic bypass is demonstrated; do not retry unchanged canonical learning transport, workflow-write permission, MinIO HTTP 401 or human promotion blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Admission Authority Linkage Readonly #40734681325](https://github.com/m-shogo/memories-project/actions/runs/40734681325) completed SUCCESS on exact source `bb2a56ef`. Job log confirms nine YAML exact-diagnostic negatives, 32 event-specific removals, eight additions, one shortened inventory, six runtime branch cases and 20 semantic plus two blob-only source admission negatives.
- **Why safe:** Only an existing CI-executed read-only validator changed; reviewed workflows, production and recovery authorities, credentials, traffic and human promotion were untouched.
- **Reusable mechanism:** Bind effective YAML mapping semantics to an exact reviewed event/root/permission shape, and verify each negative rejects for the intended diagnostic rather than an unrelated blob mismatch.
- **Protected-authority check:** Twelve protected production/recovery contract, registry and canonical-learning Git blob SHAs remained unchanged after code commit. `productionDecision=NO_GO`, OPS-P0-007 blocking with `PARTIAL_FOUNDATIONS_ONLY`; zero registered/semantically eligible generations, human-approved objectives, executable reviewed drill requests, complete typed eight-domain records or final recovery candidates. Learning cannot satisfy production readiness or human promotion.
- **Next safe target:** Review remaining environment schema and unreadable-authority source-negative workflows for nonduplicate semantic YAML guard gaps, while preserving existing CI reachability and immutable production authority.
