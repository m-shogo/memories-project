# 2026-11-21 — Reviewed learning trigger / upload snapshot overlap correction

This is append-only operational learning, not production evidence, readiness, recovery evidence, or promotion authority.

## Material failure
- **Symptom:** Autonomous Learning Guard negative validator rejected the reviewed upload-route snapshot trigger reach.
- **Observed evidence:** Prior Actions run 44874593005 failed with `Autonomous Learning Guard reviewed snapshot trigger reach changed`. Current reviewed Autonomous Learning Guard push and pull_request trigger inventories contain 19 literal paths each; 15 are ordinary tracked source paths included by the upload-route snapshot inventory. Three supplemental learning history globs and the canonical learning Markdown are excluded from the snapshot inventory.
- **Verified root cause:** `scripts/validate-autonomous-learning-system-negative.py` pinned the old overlap count 14 after the supplemental history validator was added to the reviewed triggers. The current literal inventory yields 15. No evidence suggests the production upload-route snapshot semantics should change.
- **Failed approach:** Retaining the stale literal count while expanding the reviewed CI trigger inventory. Do not broaden the snapshot to include append-only learning history or weaken trigger grammar to pass.
- **Correction:** Commit eab28c8b8b524071ab8296e5d201311c83a08519 changes only the overlap assertion/comment from 14 to 15; the 19-path exact trigger inventory, canonical learning exclusion, history exclusions, and negative checks remain.
- **Recurrence guard:** Existing `prove_upload_route_go_direct_inputs` assertion continues to fail closed on overlap drift and canonical learning snapshot inclusion. Existing reviewed trigger grammar remains exact.
- **Retry condition:** Recalculate the actual inventory and review the guard only if reviewed trigger paths, snapshot inventory exclusions, or CI outcome changes; do not repeat unchanged external credential or production-evidence blockers.

## Material success / verification boundary
- **Observed outcome/evidence:** GitHub accepted eab28c8b8b524071ab8296e5d201311c83a08519 on `so`; re-fetch confirmed the new 15-path assertion and removal of the old 14-path assertion. The production-operability authority blob remains `8d4e2848df463601eea6f836cce2817af4f19d25`, with `productionDecision=NO_GO`.
- **Why safe:** Only a read-only negative validator's reviewed inventory expectation changed. No environment generation, recovery objective, drill request, credentials, traffic, backup/restore, RPO/RTO/skew, eight-domain coverage, production evidence or promotion authority changed.
- **Reusable mechanism:** Count literal CI trigger paths against the snapshot inclusion/exclusion contract before updating a pinned overlap; preserve exact grammar and independent negative coverage.
- **Protected-authority check:** Production decision remains NO_GO; OPS-P0-007 eligibility and human review are not bypassed. This record is never admissible as production evidence.
- **Unverified:** No post-commit CI/validator PASS was observed in this run. Recheck actual Actions jobs before claiming runtime success.
