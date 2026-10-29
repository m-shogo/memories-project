# Supplemental OPS learning — Upload Route deployment-principal password skip (2026-10-30)

Append-only supplemental history only; canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under mandatory `contracts/operations/autonomous-learning-system.json`. Learning cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure — prospective second transitive skip path

- **Symptom:** The focused live HTTP tests could silently skip even with their database and S3 environment variables present if the `appLoginPool` helper changed its password-check branch to unconditional skip or the selected test setup bypassed that helper.
- **Observed evidence:** Read-only inspection of `server_live_test.go` found `appLoginPool` called from `newLiveServer`. Its `t.Skip` is conditional on an empty password parsed from the database URL. Both reviewed Upload Route workflows supply a localhost PostgreSQL URL with a password. The previous guard bound `newLiveServer`'s environment skip but not this second transitive skip site.
- **Verified root cause:** Guarding only the first helper does not establish all transitive skip preconditions.
- **Failed approach:** Assuming that a single conditional skip guard covers every helper reached by the selected Go tests.
- **Correction / executable recurrence guard:** [`dcf8f3c9`](https://github.com/m-shogo/memories-project/commit/dcf8f3c9f8ee9dd09ae32e8d002c3f0475096962) binds the exact `parsed.User.Password()` conditional-skip block, the `newLiveServer` to `appLoginPool` call edge, and exactly one `t.Skip` in that helper. Four nested negatives reject unconditional skip, removed skip, extra skip and bypassed call.
- **Retry condition:** Any legitimate password-source, deployment-principal setup or helper skip change requires explicit review of workflow env and Go test semantics, exact-source CI and protected authorities. This static check does not prove a live database, MinIO availability or successful Go integration execution.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40951621284](https://github.com/m-shogo/memories-project/actions/runs/40951621284) completed **SUCCESS** on exact source `dcf8f3c9f8ee9dd09ae32e8d002c3f0475096962`. Logs confirm append-only PASS, 201 printed canonical negatives, 1,186 helper-ancestor negative mutations and clean read-only job completion. The four new nested skip negatives are additional to the printed 201.
- **Why safe:** Only `scripts/validate-autonomous-learning-system-negative.py` changed (+44 lines). No actual workflow YAML, Go service, credentials, traffic, readiness, generation/objective, drill, evidence, non-resurrection, independent review or promotion authority changed.
- **Reusable mechanism:** Review every transitive `t.Skip` path of a selected test and bind both the exact conditional precondition and the caller edge, rather than relying on top-level test declarations.
- **Protected-authority check:** Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` unchanged. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0 and no approved objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain record, final candidate or human promotion.

## Next safe target

Complete a bounded set-equality audit of all `t.Skip` sites in the two files containing the four selected Go tests: `route_authority_test.go` currently has zero and `server_live_test.go` currently has two, both individually reviewed. A new skip in another function could otherwise evade the two named-helper guards. The 109 reviewed static inputs and at least 81 uncovered trigger inputs per workflow remain lower bounds; do not narrow triggers without complete closure.
