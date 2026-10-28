# Supplemental OPS learning — backup/restore contracts CI YAML authority (2026-10-29)

Append-only supplemental learning only; not canonical learning, production evidence, backup/restore, RPO/RTO/skew, drill execution, credential, traffic, readiness or human promotion authority.

## Material failure / recurrence prevention
- **Symptom:** The backup/restore contracts CI source validator pinned 49 reviewed paths in each event and complete Git blob identity, but lacked independent semantic rejection of extra YAML events, root key shadows and permission-leaf overrides. This was a static guard gap, not an observed backup/restore bypass.
- **Observed evidence:** Earlier `validate_trigger_reachability` checked exact PR/push path entries; `REQUIRED` pinned visible read-only tokens; effective YAML mapping uniqueness was not independently asserted when the digest gate was disabled for semantic fixtures.
- **Verified root cause:** Source-digest and token membership alone cannot prove a unique effective YAML event/root/permission mapping.
- **Failed approach:** Relying on Git blob mismatch as the only rejection for mapping shadows; this fails to establish a specific regression diagnostic.
- **Correction / executable recurrence guard:** [288c2fbf](https://github.com/m-shogo/memories-project/commit/288c2fbfd5c1e9680a8ce3ca5cd682246b32dddd) adds exact reviewed event header, root-key order and read-only permission leaf checks. Nine executable negatives require the intended diagnostic for an extra event, six shadow root keys and two permission shadows. Existing blob, trigger and runtime branch gates remain unchanged.
- **Retry condition:** Revalidate if reviewed workflow topology or validator changes, or a new YAML bypass is demonstrated. Do not repeat unchanged large canonical-learning transfer, workflow-write permission, Quay MinIO HTTP 401 or human approval attempts.

## Material success / protected authority
- **Observed outcome/evidence:** [Backup and Restore Contracts #40734476581](https://github.com/m-shogo/memories-project/actions/runs/40734476581) completed SUCCESS on exact code `288c2fbf`. Job log confirms 98 path removals, eight trigger additions, one shortened inventory negative, nine exact-diagnostic YAML negatives, six runtime branch cases, and 19 semantic plus two blob-only source admission negatives.
- **Why safe:** Only the existing CI-executed read-only validator changed; no reviewed workflow, production/recovery evidence, credential, traffic or human promotion authority was altered.
- **Reusable mechanism:** Validate effective YAML root and permission uniqueness separately from source digest; use exact-diagnostic in-memory negative mutations to guard the semantic boundary.
- **Protected-authority check:** Twelve protected production/recovery contracts, registries and canonical-learning Git blob SHAs matched the baseline after the code commit. `productionDecision=NO_GO`, with no new registered/eligible generation, approved objective, executable reviewed request, complete typed eight-domain record or final candidate. Preflight and human promotion remain independent, non-automatic authorities. Learning is never a production gate.
- **Next safe target:** Audit remaining unguarded drill-generation binding, unreadable-authority and review/admission workflow source validators; add only nonduplicate semantic guards after verifying CI reachability.
