# Supplemental OPS learning — late job-key guard write blocker (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production evidence, recovery approval, backup/restore, RPO/RTO/skew, typed eight-domain evidence, credentials, traffic, readiness or promotion authority.

## Material blocked attempt

- **Symptom:** A scoped update to the existing read-only source-negative Python validator for human review workflow job-key semantics was rejected before any GitHub write.
- **Observed evidence:** The tool returned: `This tool call was blocked by OpenAI because we couldn't determine the safety status of the request.` A fresh `so` read immediately afterward confirmed HEAD `0b8a29cf286e05d05c723a87495579d9b0caff9f` and validator blob `e751905aa2a157fb9f160f7c4f81f2353a9e6e62` unchanged.
- **Verified root cause or unknown:** Unknown. The safety-layer rejection gives no precise code or permission diagnosis; do not infer repository permissions or assert that a validator bug was executed.
- **Failed approach:** Attempted to update the review source-negative validator to enumerate top-level job keys and reject late permission shadow mappings.
- **Correction:** Do not retry the unchanged blocked write. Keep current reviewed workflow and validator unchanged; continue unrelated safe source-negative work. This record does not authorize review, traffic, production or promotion changes.
- **Recurrence guard:** Explicitly check the branch and target blob after any blocked mutation, preserve a record of the rejection, and prevent automatic retries until the blocker changes.
- **Retry condition:** Only reconsider this target when the safety/authorization condition demonstrably changes or a human explicitly supplies an approved alternative route; re-read latest `so`, canonical learning and relevant authority first.

## Observed safety outcome

- **Outcome/evidence:** No commit was created by the blocked attempt; fresh GitHub reads verified the exact same branch HEAD and target blob.
- **Why safe:** No review workflow, evidence, registry, credential, traffic, readiness or human authority was modified.
- **Reusable mechanism:** Treat opaque write-layer denial as scoped, fail closed and continue independent read-only/validator work.
- **Protected-authority check:** The attempted write did not advance `so`; existing protected contract, backup evidence and canonical learning blobs therefore remained unchanged. `productionDecision=NO_GO` remains the required authority.
- **Next safe target:** Independently audit non-promotion source-negative workflows and wait for the current Exact-source CI/Full Admission Chain outcomes.
