# 2026-11-21 — Learning CI first run boundary source binding

## Material failure
- **Symptom:** Independent learning workflow run-boundary validator rejected the current reviewed workflow with `independent learning workflow run boundary drift`.
- **Observed evidence:** The first `LEARNING_RUN_BOUNDARIES` entry expected `FINAL_READONLY_LINE` immediately before `Enforce append-only learning authority against parent`, but the actual preceding step `Confirm exact clean source` ends in `test -z "$(git status --porcelain)"`. The final read-only line belongs to the last step instead.
- **Verified root cause:** Incorrect first-step sentinel was copied from the final postcondition into the first boundary.
- **Failed approach:** Treating the final read-only command as a universal boundary sentinel. The first attempted correction also accidentally encoded a double-backslash newline literal; this was immediately corrected in a separate commit.
- **Correction:** Commits `2c71bb36ecc87b1605e862941f7c24838c35bec0` and `79995e0bd00404502035ad7b10e55e8da328be6c` bind the first boundary to the actual reviewed clean-source command with a Python newline escape.
- **Executable recurrence guard:** Existing `validate_run_step_boundaries` exact-adjacency assertion and the independent learning negative mutation matrix remain intact; no permissive boundary fallback was added.
- **Retry condition:** Revisit on a reviewed workflow step-body change, or if post-change CI identifies another failing boundary. Do not retry the old final-line sentinel without a changed workflow topology.

## Material success and authority
- **Observed outcome:** GitHub accepted both commits; readback of `so` confirmed the corrected source sentinel and its exact adjacency in the reviewed workflow. This is static source verification, not a claim of CI PASS.
- **Why safe:** Only the read-only validator was edited, without weakening the negative guard or editing a workflow or production evidence.
- **Reusable mechanism:** Derive every boundary sentinel from the immediate preceding reviewed run body and verify the exact source bytes after writing.
- **Protected-authority check:** Production status blob `8d4e2848df463601eea6f836cce2817af4f19d25` remained unchanged; `productionDecision=NO_GO`. No recovery generation, objective, reviewed executable request, eight-domain non-resurrection evidence, independent review, or human promotion authority was created or modified. Learning remains separate from production evidence and readiness.
