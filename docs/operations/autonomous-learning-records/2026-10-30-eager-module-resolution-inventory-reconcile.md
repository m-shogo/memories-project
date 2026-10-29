# Supplemental OPS learning — eager module-resolution closure and inventory reconciliation (2026-10-30)

Append-only supplemental history only. Canonical authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under `contracts/operations/autonomous-learning-system.json`. This record **never** counts as production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, approved recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, or human promotion evidence.

## Material failure A — prewrite patch ambiguity and incorrect change-budget expectation

- **Symptom:** The first attempted source transformation aborted before any GitHub write because its `eager-direct-reload` replacement anchor matched two occurrences; the next prewrite attempt aborted on a self-imposed lower-bound assertion.
- **Observed evidence:** The negative validator had both a four-space reviewed-payload declaration and a twelve-space live fixture entry for `eager-direct-reload`. A substring-only anchor matched both. After correcting the anchor, the generated patch was **+22** lines in the positive validator and **+31** in the negative validator, whereas the provisional lower bound incorrectly required at least 25 positive lines.
- **Verified root cause:** The patch generator did not distinguish an inventory constant from its live fixture; its initial line-budget minimum was a guess rather than a measured bound.
- **Failed approach:** Unqualified substring replacement and a speculative minimum delta.
- **Correction:** Restrict replacement anchors to exact newline plus indentation, verify unique occurrence, and change the prewrite bound only after measuring the intended 22/31-line patch. Both aborted attempts performed **zero** GitHub writes.
- **Executable recurrence guard:** Exact-match-count preflight, preserved Python escaped-newline checks, bounded diff checks, and expected HEAD/contract checks before creating Git objects.
- **Retry condition:** Retry only after the ambiguous anchor has been made unique or the measured line delta has been explicitly reviewed; never relax a failed check without its observed cause.

## Material failure B — missing dynamic CI fixture enumeration

- **Symptom:** [Autonomous Learning Guard #40975206744](https://github.com/m-shogo/memories-project/actions/runs/40975206744) on [`3bcd7a64`](https://github.com/m-shogo/memories-project/commit/3bcd7a64ad9a2ae649442abb3b84806ee43d7359) FAILED with `RuntimeError: reviewed reflective CI negative inventory drift`.
- **Observed evidence:** The first committed patch added six reviewed `find_spec` / `resolve_name` payloads and their real CLI negatives but omitted the six matching entries from the live `for kind, mutation` CI negative enumeration. The strict inventory checker rejected the mismatch at line 76; append-only and learning-contract checks had already passed.
- **Verified root cause:** The new reviewed inventory constant and actual CI fixture producer were edited independently; the producer retained only prior reload cases.
- **Failed approach:** Treating an inventory declaration and CLI cases as proof that the CI fixture enumeration was also extended.
- **Correction:** [`fadc94ee`](https://github.com/m-shogo/memories-project/commit/fadc94ee908c5339caea0b82e4ebc355f0c5c0ae) adds the six missing exact negative tuples to the live fixture enumeration without changing the approved payloads.
- **Executable recurrence guard:** `require_reviewed_reflective_inventory` requires exact reviewed tuple identity and rejects missing, duplicate or substituted payloads. The real prewrite CLI inventory separately binds six new labels and expected rejection bytes.
- **Retry condition:** Do not rerun the unchanged failed source; update all three coupled surfaces (reviewed payloads, live CI cases, CLI cases) and require a new exact-source CI PASS.

## Material success — module resolution APIs fail closed

- **Observed outcome/evidence:** A local disposable-package check confirmed that `importlib.util.find_spec("sideeffectpkg.child")` executed the parent package initializer, and `pkgutil.resolve_name("sideeffectpkg")` executed the package initializer. These are local semantic probes, **not** production evidence. The corrected [Autonomous Learning Guard #40975321542](https://github.com/m-shogo/memories-project/actions/runs/40975321542) completed **SUCCESS** on exact source `fadc94ee908c5339caea0b82e4ebc355f0c5c0ae`: append-only PASS, contract PASS, **289 fail-closed cases**, 74 fanout synthetic cases, entry-document PASS, 1,186 helper ancestor negatives and clean/read-only execution PASS.
- **Why safe:** Code changes touched only the two read-only learning validators. No workflow YAML, service code, production data, credentials, traffic, recovery evidence or promotion authority was changed. Synthetic package imports ran only in disposable local directories.
- **Reusable mechanism:** Model `find_spec` and `resolve_name` as potentially eager import execution, including direct-name, attribute and reflective calls. Cover both protected CI bindings, six prewrite in-process negatives, two deferred positives, six real CLI negatives, and exact inventory identity.
- **Protected-authority check:** Ten protected blobs remained unchanged: canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective `f4d74f333a4884f9aba2284a31ac011aae8b71bd`, drill request `acebcd02de9d4ec44891e70ff00b6898174451dd`, generation evidence `ae7e57efce7ca21d546c1cb336d3ee7bb7ebf93a`, typed non-resurrection `26bb1cc70c64ab3dfa09bee011545a52d46afc00`, promotion review `99cb895fbefb5b459d461926851186dbed742f88`. Actual registries remain empty, OPS-P0-007 remains `PREREQUISITES_BLOCKED`, and `productionDecision=NO_GO`.
- **Limitations:** The static checks are bounded lexical rejection, not full Python alias/import closure; the 109 reviewed Upload Route static inputs and 81 trigger gaps per workflow remain lower bounds. Canonical learning's full 4.17 MB content is still unavailable via the current connector transport.

## Next safe target

Investigate another independently proven dynamic import entry point only if its execution semantics can be demonstrated and its guard is CI-reachable. Prioritize the unresolved Go-only Focused Test CI trigger gap and complete Go/Python transitive input closure when workflow permissions or other preconditions actually change. Never promote learning to production evidence.
