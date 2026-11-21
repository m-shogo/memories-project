# Supplemental OPS learning — CI reachability for supplemental append-only history (2026-11-21)

Append-only operational learning, not production evidence, readiness, recovery, credential, traffic, or promotion authority. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md`.

## Observed success

- **Outcome:** Commit `89032a22d45bb2bbb9f8f71d68d2a6c0094a3a05` connected `scripts/validate-autonomous-learning-records-history.py --self-test` to `.github/workflows/autonomous-learning-guard.yml`, with push/PR path triggers for the validator and three supplemental history scopes. Fresh `so` read confirmed the committed workflow blob `13d01190439e09f56605b180deb7f8181dcb2b7f` and the new step. This is **source-level reachability only**, not an observed CI or validator PASS.
- **Evidence:** At the immediately preceding HEAD `cb4cd523ec4e8cf4b291ac246c6b3071983c459d`, the existing workflow ran the canonical learning validators but did not invoke the supplemental history validator. The supplemental validator already contained 39 negative/positive fixtures and fail-closed all-parent history checks; no replacement or weakening was needed. A post-commit workflow-runs query filtered by the new SHA returned zero runs at observation time, so CI execution remains unverified.
- **Why safe:** Only a read-only workflow was extended; no production evidence, generation, recovery objective, drill request, or promotion registry was written. The existing exact-SHA checkout, full history fetch, clean-source check and read-only token permissions remain intact.
- **Reusable mechanism:** Make supplemental append-only protection executable at the CI entrypoint, and include its validator and protected record scopes in push/PR path filters. Use `--self-test` to run negative fixtures as well as the real history check; require a later observed workflow result before claiming runtime success.
- **Protected-authority check:** Post-change production authority remained `productionDecision=NO_GO` with blob `8d4e2848df463601eea6f836cce2817af4f19d25`. OPS-P0-007 eligibility, typed eight-domain non-resurrection, independent review, and explicit human promotion gates remain unchanged.

## Follow-up / retry condition

Observe the workflow run for the exact new source commit. If the CI job fails, diagnose its concrete logs before modifying the validator or workflow; never assume a source-level guard proves runtime PASS. Existing canonical ~4.17MB upload transport blocker is unchanged and must not be retried via the same full-content API path.
