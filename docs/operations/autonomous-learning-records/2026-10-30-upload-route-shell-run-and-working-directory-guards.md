# Supplemental OPS learning — Upload Route shell, run-key and working-directory guards (2026-10-30)

Append-only supplemental learning/history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy remains `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, or human promotion.

## Material failure / observed prospective bypass 1 — wrapped shell dispatch

- **Symptom:** The existing read-only Upload Route command inventory recognized ten direct Python/Go commands per workflow, but the adjacent shell-dispatch guard did not reject additional commands wrapped by `timeout`, `nohup`, `nice`, `exec`, `xargs`, `eval`, option-bearing `env/command/sudo`, `find -exec`, or `bash -lc`.
- **Observed evidence:** Existing guard regex matched only immediate `env|command|sudo python/go` and `bash|sh -c`. A bounded local regex test confirmed 13 wrapper forms were rejected by the new patterns while the reviewed direct `python`/`go` commands and YAML `run: |` scalar remained accepted.
- **Verified root cause:** The prior regular-expression grammar was too narrow for shell prefix/option dispatch; this was a static prospective guard gap, not observed production compromise.
- **Failed approach:** Assuming an unchanged direct-command list implies all effective shell invocation routes are unchanged.
- **Correction / executable recurrence guard:** [`b50ad4a5`](https://github.com/m-shogo/memories-project/commit/b50ad4a5528283d5e68fd5e05d7e3c60d6fd4776) expands the fail-closed shell guard with 13 additional nested negatives. [Exact-source Autonomous Learning Guard #40942794991](https://github.com/m-shogo/memories-project/actions/runs/40942794991) SUCCESS.
- **Retry condition:** Revisit only for a reviewed, legitimate new wrapper with an updated explicit command/input graph, negative tests and exact-source CI. Do not treat this regex as complete shell/dataflow closure.

## Material failure / observed prospective bypass 2 — shadowed YAML run keys

- **Symptom:** A workflow step could gain a second `run` key with a non-Python/Go command while retaining the ten expected direct Python/Go commands, changing YAML execution semantics without invalidating the old direct-command fingerprint.
- **Observed evidence/root cause:** The old validator scanned Python/Go command lines, not the cardinality and identity of YAML `run` mapping keys. Reviewed Publisher and PR workflow sources have respectively 11 and 10 canonical `run` keys, at most one per named step.
- **Failed approach:** Using direct-command identity alone as a proxy for complete step-level `run` mapping identity.
- **Correction / executable recurrence guard:** [`f1939069`](https://github.com/m-shogo/memories-project/commit/f19390699aa41ae87eb2290154c8dc75b1e60ef7) enforces exact per-workflow run-key counts, canonical indentation and one run per named step, with eight nested negative controls. [Exact-source Guard #40943066552](https://github.com/m-shogo/memories-project/actions/runs/40943066552) SUCCESS.
- **Retry condition:** Change reviewed run-key inventory only after verifying YAML step semantics, direct runtime command parity, dependency trigger closure and exact-source CI.

## Material failure / observed prospective bypass 3 — Go working-directory drift

- **Symptom:** Changing `working-directory` could silently redirect Go formatting/tests while preserving the literal `go test` command and Go import inventory.
- **Observed evidence/root cause:** Both reviewed Upload Route workflows have exactly two `working-directory: services/import-api` mappings bound to named steps `Format and verify source diff` and `Run focused route and live upload regressions`. The previous command guard did not bind these mappings.
- **Failed approach:** Treating an unchanged command string as sufficient proof of the executed Go module context.
- **Correction / executable recurrence guard:** [`6cec6bc5`](https://github.com/m-shogo/memories-project/commit/6cec6bc5ab5355d49f3c423d9791bda05a08ecd1) enforces the exact two step-to-directory bindings, rejects added/default/quoted/spaced/duplicate mappings, and adds seven nested negatives. [Exact-source Guard #40943335457](https://github.com/m-shogo/memories-project/actions/runs/40943335457) SUCCESS.
- **Retry condition:** Re-review Go module/workspace resolution, command/test scope and trigger inputs before an authorized working-directory change; no workflow mutation was performed here.

## Prewrite failure avoided — nonunique source anchor

- **Symptom/evidence:** The first local candidate for the run-key guard failed the prewrite exact-anchor cardinality check because `reject_unreviewed_upload_route_shell_dispatch(source)` appears in both the synthetic test and actual workflow loop. The prewrite attempt aborted before any GitHub write.
- **Verified root cause:** The patch used a nonunique text anchor, not a repository syntax/CI failure.
- **Failed approach:** Global source replacement against an unscoped repeated function call.
- **Correction / recurrence guard:** Re-read the latest HEAD and target blob; anchor the insertion to the unique adjacent `upload_route_event_paths(source, event)` call, require exactly one match and a bounded +43-line delta before upload. The corrected commit and exact-source CI succeeded.
- **Retry condition:** Only use unique context-bearing anchors, callback-based literal replacement and bounded source diffs for future edits; do not repeat unscoped replacement.

## Material success / authority

- **Observed outcome/evidence:** Three code commits on `so`, all read-only negative-validator changes; the three exact-source Guard runs above completed SUCCESS. The last run independently reports 201 canonical fail-closed negatives, 74 fanout synthetic cases, 1,186 helper-ancestor mutations, append-only, entry-document and clean-source/read-only PASS. The 13 + 8 + 7 nested controls are separate from the printed 201 count.
- **Why safe:** No Upload Route workflow, production service, credentials, traffic, readiness registry, recovery evidence or promotion authority was modified. The three commits changed only `scripts/validate-autonomous-learning-system-negative.py` (+109/-2 aggregate).
- **Reusable mechanism:** Bind effective shell invocation wrappers, YAML run-key cardinality/step identity, and Go working-directory semantics independently of direct command/import fingerprints; require bounded prewrite checks and exact-source CI.
- **Protected-authority check:** After the code commits, canonical learning SHA `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, mandatory contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation/drill/evidence/non-resurrection/promotion registries remained unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0, no approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review or human promotion.
- **Next safe target:** Read-only pinning of Upload Route action `with` input identity, especially checkout refs and Go/Python setup/cache inputs; preserve known MinIO HTTP 401 and unapproved workflow/promotion boundaries without retry.
