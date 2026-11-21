# 2026-11-22 — Helper Ancestor per-domain negative mismatch diagnostics

Append-only supplemental learning, not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, or promotion evidence.

## Material failure
- **Symptom:** The strict Helper Ancestor negative mutation count fails by one.
- **Observed evidence:** GitHub Actions [44950544560](https://github.com/m-shogo/memories-project/actions/runs/44950544560), on exact commit `010e20762f8502dc0acb2539f4a133826815f599`, emitted `ancestor negative count mismatch (expected=1190, observed=1191)`. Seven canonical harnesses passed their ordinary checks; the negative step failed.
- **Root cause or unknown:** The off-by-one total is verified; the specific contributing fixture/domain remains **unknown**. No fixture was removed and no expected count was adjusted.
- **Failed approach:** Previous logs did not expose the observed total. The newly added aggregate diagnostic proves the difference but cannot isolate its source; guessing that 1191 is the intended expected count would risk silently approving drift.
- **Correction:** [f28f2435](https://github.com/m-shogo/memories-project/commit/f28f24353c7e1e8e169d0562af6e8e80b14e75cf) records per-harness and named-domain negative counts only on mismatch, retaining the exact `136 * len(TARGETS) + 238` equality gate.
- **Executable recurrence guard:** A fail-closed equality assertion remains; deterministic per-domain counts now expose the specific contributor without relaxing tests.
- **Retry condition:** Inspect the first CI execution on `f28f2435` or later containing the breakdown, compare its categories to the last passing baseline and existing fixture contracts, then correct only the proven drift. Do not blindly increase the expected count.

## Material success
- **Outcome/evidence:** GitHub reread of commit `f28f24353c7e1e8e169d0562af6e8e80b14e75cf` returned script blob `af640d8ddc9f98544fca0c2545686427617d6800` with named breakdown entries and the unchanged equality expression. A runtime PASS is **not** claimed.
- **Why safe:** The patch changes diagnostics and accounting visibility, not fixtures, permissions, workflow triggers, recovery evidence, or promotion criteria.
- **Reusable mechanism:** Preserve strict negative coverage totals while recording bounded, domain-labeled component counts on failures.
- **Protected-authority check:** The production status blob remains `8d4e2848df463601eea6f836cce2817af4f19d25` and declares `productionDecision=NO_GO`. OPS-P0-007 eligibility, approved objectives, current executable reviewed requests, typed eight-domain non-resurrection coverage, independent review, and separate human promotion remain unchanged.
