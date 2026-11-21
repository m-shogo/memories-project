# 2026-11-22 — Bounded Helper Ancestor negative-count diagnostics

This supplemental append-only learning record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, recovery-generation, or promotion evidence.

## Material failure
- **Symptom:** Helper Ancestor negative CI reported `ancestor negative count mismatch` without observed mutation count.
- **Observed evidence:** Existing CI run 44907655631 failed its negative step; the validator expected `136 * 7 + 238 = 1190`, while the failing run did not disclose the observed count.
- **Root cause or unknown:** The missing diagnostic count is verified in the previous fail-closed assertion; the underlying count discrepancy remains **unknown** pending an actual rerun.
- **Failed approach:** Repeatedly reading the same CI log cannot reveal a count it never emitted; changing the expected count without observing the actual count is prohibited.
- **Correction:** Commit `010e20762f8502dc0acb2539f4a133826815f599` retains the exact equality gate and adds bounded integer-only expected/observed diagnostics to the failure message.
- **Executable recurrence guard:** The original `require(total == 136 * len(TARGETS) + 238, ...)` still fails closed; only its diagnostic string changed. Do not weaken the assertion or infer a new expected count from this record.
- **Retry condition:** Run the negative validator on the changed source in CI or a verified local checkout, capture observed count and per-component contributions, then correct the proven source of drift while preserving negative fixtures.

## Material success
- **Outcome/evidence:** GitHub reread of `so` confirmed commit `010e2076`, blob `0ad7045c33607e28a0a24b8b0bb37c616cc1fcab`, and the unchanged equality expression with bounded diagnostic interpolation.
- **Why safe:** This is diagnostic-only; no expected count, fixture, workflow, recovery, or promotion gate was changed. No runtime PASS is claimed.
- **Reusable mechanism:** Emit bounded nonsecret observed/expected counters at a failing deterministic equality gate before considering any threshold adjustment.
- **Protected-authority check:** Production Status blob `8d4e2848df463601eea6f836cce2817af4f19d25` was unchanged after the code commit and still reads `productionDecision=NO_GO`. OPS-P0-007 generation/objective/typed-eight-domain/independent-review/human-promotion requirements remain separate and untouched.
