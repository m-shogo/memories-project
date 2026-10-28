# Supplemental autonomous OPS learning — 2026-10-28

This is append-only supplemental execution history, not the canonical learning authority, production evidence, readiness, a recovery objective, a drill request, or promotion authority.

## Incident diagnostic permission-leaf shadow hardening

### Material failure: symptom, observed evidence, verified root cause, failed approach, correction, recurrence guard, retry condition

- **Semantic symptom / evidence:** The incident-control diagnostic publisher and independent CI semantic guard checked the root `permissions:` key but not effective YAML `contents` leaf uniqueness. Quoted `'contents':` and spaced `contents :` could shadow the reviewed leaf while preserving the event header/root inventory. This was a static guard gap, not an observed production or credential incident; full reviewed Git blob pins still rejected actual unreviewed source drift.
- **Verified root cause / failed approach:** Visible permission leaf plus prefix/root inventory and a Git blob pin do not independently prove YAML leaf uniqueness.
- **Correction / executable recurrence guard:** [319d829c](https://github.com/m-shogo/memories-project/commit/319d829c9f7c37a805f2cadb91353a596fc40378) pins publisher `contents: write` and independent CI `contents: read` separately. Four exact-diagnostic negative fixtures reject quoted/spaced shadows. Prewrite checks passed two baseline inventories and four mutations.
- **Retry condition:** Revalidate only after independently reviewed permission topology changes; never silently substitute a read-only publisher or elevate independent CI.

### Material success: outcome, evidence, why safe, reusable mechanism, protected-authority check

- **Outcome / evidence:** Exact-source [Incident Control Exercise Diagnostic Source Negative #40705897076](https://github.com/m-shogo/memories-project/actions/runs/40705897076) completed **SUCCESS** on `319d829c`. Logs explicitly prove four permission-leaf negatives, 32 trigger omissions, 12 additions, two shortened inventories, three topology negatives, eight root shadows, 22 branch/base/SHA runtime cases, 27 source mutations and 15 diagnostic runtime cases.
- **Why safe / reusable mechanism:** Only the CI-reachable read-only validator changed. Publisher write authority and independent CI read authority remain reviewed and unchanged. No workflow, production evidence, credential, traffic, readiness or human promotion was written.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning Git blob SHAs remained unchanged after the code commit. `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`, with no registered/eligible generations, approved objectives, executable reviewed requests, generation-bound evidence, complete typed eight-domain records or final candidates. Human promotion remains separate and non-automatic. Supplemental history cannot satisfy canonical learning or production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion gates.

## Supplemental learning transport failure and bounded correction

### Material failure: symptom, evidence, root cause or unknown, failed approach, correction, recurrence guard, retry condition

- **Symptom / observed evidence:** A Git blob creation for the existing approximately 170 KB supplemental addenda succeeded (unreferenced blob `5ab2f89944fdc27e6d113a5cf2d251cdd454600f`), but the subsequent `create_tree` returned `RemoteProtocolError: Server disconnected without sending a response`. Independent post-failure reads proved branch `so` remained at `319d829c`, the addenda blob remained `d6227cb6`, and the new lesson was absent. No branch write was inferred from the successful unreferenced blob creation.
- **Root cause or unknown:** Transport/backend disconnect is **unknown**; no evidence establishes whether an unreachable tree object was created. The failed approach was another full supplemental-file Git tree update after prior contents-API disconnect.
- **Correction / executable recurrence guard:** Use a distinct small, create-only supplemental record with a new path, verifying latest branch HEAD and path nonexistence before creation. Verify the resulting commit touches only the intended new record and that all protected authority blobs remain unchanged. Do not silently replace or truncate existing addenda.
- **Retry condition:** Do not repeat the same large-payload tree operation until transport/payload conditions demonstrably change. A small create-only record is a separate bounded path; no production or CI reachability claim follows from its creation.

**Next safe target:** Audit incident-control authority and operability inventory PR independent validators for read-only permission-leaf shadows. The existing supplemental-history CI trigger limitation remains unresolved.
