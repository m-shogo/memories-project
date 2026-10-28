# Supplemental OPS learning — preflight reconcile independent source CI YAML authority (2026-10-29)

Append-only supplemental learning, not the canonical authority at `docs/operations/AUTONOMOUS-OPS-LEARNING.md`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, generation, objective, credential, traffic, readiness, promotion or evidence gates.

## Material failure / recurrence prevention
- **Symptom:** The independent preflight reconcile source-negative workflow pinned PR/push path inventories and full Git blob SHA, but lacked a digest-independent proof of effective YAML event, root-key and permission-leaf uniqueness. This is a discovered static guard gap, not an observed production bypass.
- **Observed evidence:** `validate_independent_trigger_reachability` checked only PR/push path blocks, while `INDEPENDENT_REQUIRED` matched visible text anchors. A duplicate `on :`, quoted root key, or `contents : write` shadow could avoid the independent semantic check; the full-source digest still rejected unreviewed source.
- **Verified root cause:** Exact path inventory and presence of a read-only permission token do not prove YAML mapping uniqueness or effective event authority.
- **Failed approach:** Treating blob-only rejection as equivalent to semantic event/root/permission validation.
- **Correction:** Commit [00b42824](https://github.com/m-shogo/memories-project/commit/00b42824d792218abdcc89bb7448d7923b6e0c9c) adds `validate_independent_yaml_authority` and `prove_independent_yaml_authority_negatives` to the existing CI-reachable read-only Python validator.
- **Executable recurrence guard:** Nine in-memory exact-diagnostic negatives reject one extra event, six root shadows, and two permission-leaf shadows, independently of the reviewed workflow digest; existing PR/push trigger inventories and SHA/branch runtime tests remain.
- **Retry condition:** Reassess only after a reviewed event/permission topology change or a demonstrated new YAML shadow bypass. Do not retry unchanged large canonical learning transport, workflow write permission, MinIO HTTP 401 or human approval blockers.

## Material success / authority boundary
- **Observed outcome/evidence:** [Preflight Reconcile Source Negative #40724513046](https://github.com/m-shogo/memories-project/actions/runs/40724513046) completed SUCCESS on exact code commit `00b42824`; its job log reports nine exact-diagnostic YAML negatives, six trigger removals, eight trigger additions, one shortened inventory, branch/SHA runtime cases, and existing source-admission negatives passing.
- **Why safe:** Only an already-executed read-only source-negative Python validator was changed; no production or reviewed workflow, generation, objective, drill, evidence, credential, traffic or promotion authority was written.
- **Reusable mechanism:** Bind expected event header, root mapping and permission leaves to reviewed source topology; inject semantic shadows and assert the specific failure diagnostic rather than accepting an arbitrary digest failure.
- **Protected-authority check:** Nine production/OPS-P0-007/registry/learning-contract file blob SHAs and the canonical learning blob were unchanged after code commit. `productionDecision=NO_GO`; preflight current state still has zero registered/semantically eligible generations, zero approved objectives, zero executable reviewed requests, and `productionReady=false`. Human promotion remains separate/non-automatic.
- **Next safe target:** Apply the same independent event/root/permission semantic proof to the backup-restore drill preflight publisher/independent source-negative validator, preserving source SHA and execution reachability.
