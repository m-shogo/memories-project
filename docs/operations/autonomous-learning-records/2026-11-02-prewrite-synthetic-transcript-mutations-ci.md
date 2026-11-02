# Supplemental OPS learning — mutation-tested synthetic prewrite CLI transcript (2026-11-02)

Append-only subordinate record under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. Learning and synthetic CI are never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure / executable correction

- **symptom:** The shared `require_exact_count` helper in the prewrite negative suite previously accepted any stdout containing the expected risk/count line. It did not bind synthetic cases to the requested `scripts/a.py` path, exact fixture identity, complete output grammar or advisory. No actual unsafe production write was observed.
- **evidence:** Prior `scripts/validate-autonomous-learning-system-negative.py` checked `expected in result.stdout.splitlines()`; 195 synthetic prewrite cases exercised the CLI but could overlook a wrong-path or extra-line transcript when the expected count was present.
- **rootCauseOrUnknown:** Verified weak test-oracle predicate, not an observed malicious CLI result.
- **failedApproach:** Single-line membership assertion as a complete CLI audit oracle.
- **correction:** [`230e9543`](https://github.com/m-shogo/memories-project/commit/230e9543b4e5be629d7a91c5948fe0afcc078aae) replaces the helper with exact four-line/three-line transcript comparison for the reviewed one-workflow fixture, strict `CompletedProcess` type and count domain, and five synthetic negative mutations.
- **recurrenceGuard:** The helper now rejects wrong audited path, duplicate workflow identity, missing advisory, extra stdout and wrong risk. The existing count-prefix collision negative remains. Exact-source read-only CI executes these mutations before treating the prewrite audit as validated.
- **retryCondition:** Revisit only if the CLI's reviewed transcript grammar or fixture topology changes; do not loosen matching to accommodate unknown workflows. Unchanged external MinIO/canonical learning/human production evidence blockers are not retried.

## Observed success

- **outcome:** Exact-source [Autonomous Learning Guard #41432628469](https://github.com/m-shogo/memories-project/actions/runs/41432628469) completed SUCCESS on `230e9543b4e5be629d7a91c5948fe0afcc078aae`.
- **evidence:** GitHub Actions job `125234690232` passed exact clean source, append-only authority, learning contract/executable negatives, helper ancestor reachability and read-only execution. Logs show `Autonomous learning negative validation PASS (601 fail-closed cases)`, `prewrite fanout audit PASS: 195 synthetic cases`, and no workflow executed by the audit. Five new mutation checks are inside the existing suite, not separately counted by the printed 601-case total.
- **whySafe:** Only the read-only negative test file changed; no writer workflow, production authority, evidence, credentials, traffic, readiness or promotion path was edited.
- **reusableMechanism:** Mutation-test the audit oracle itself and compare complete deterministic transcripts, rather than relying on risk/count substrings.
- **protectedAuthorityCheck:** Ten checked protected Git blobs remained unchanged: production `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), generations `bfd1b045`, objectives `f4d74f33`, requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`. No OPS-P0-007 production gate advanced.

## Next safe target

Design a source-derived, fail-closed read-only writer-permission inventory validator for the 37 unclassified write-capable workflows found in the bounded 40-source audit, with exact-source negative CI before changing the prewrite classifier.
