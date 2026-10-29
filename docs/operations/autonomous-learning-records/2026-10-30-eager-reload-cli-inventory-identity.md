# Supplemental OPS learning — exact reload negative inventory and real prewrite CLI (2026-10-30)

Append-only supplemental learning only; canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` under `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, request-bound recovery, typed eight-domain non-resurrection, independent review or human promotion gates.

## Material failure / recurrence risk

- **Symptom:** The eager module reload guard initially had six CI-entrypoint and three in-process prewrite negative cases, but their exact mutation payloads were not all bound to the existing reviewed reflective execution inventory or exercised through the real prewrite CLI.
- **Observed evidence:** The initial [`aa044160`](https://github.com/m-shogo/memories-project/commit/aa0441608f5915c85be1d395c7ffd4633c8a81e4) source included the new `eager-direct-reload`, `eager-importlib-reload`, and `eager-getattr-reload` cases, while `REVIEWED_REFLECTIVE_EXECUTION` and `REVIEWED_REFLECTIVE_CLI_LABELS` did not include them. CI was successful, but no exact CLI negative attested those three forms.
- **Verified root cause:** The initial change extended the runtime scanner and synthetic cases but not the separate fixture-identity/CLI coverage authority.
- **Failed approach:** Treating an in-process prewrite rejection and unpinned negative case labels as sufficient to prevent silent fixture removal or prove CLI argument/diagnostic behavior.
- **Correction / executable recurrence guard:** [`51edd021`](https://github.com/m-shogo/memories-project/commit/51edd02149a61cb5015557ef73620632385797dd) adds all three exact reload payloads to the reviewed inventory, binds the matching negative-case enumeration, and adds three actual prewrite CLI cases with exact rejection diagnostics. The existing inventory tests reject removed, duplicated and substituted entries; the CLI inventory also enforces exact ordering and payload identity.
- **Retry condition:** Update reviewed payloads only when an explicitly reviewed API/guard change warrants it; require negative inventory mutation tests, exact-source CI and protected-authority check. Do not repeat unchanged MinIO HTTP 401, workflow-write permission, large canonical-learning transfer or human approval attempts.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40974873765](https://github.com/m-shogo/memories-project/actions/runs/40974873765) completed **SUCCESS** on exact source `51edd02149a61cb5015557ef73620632385797dd`. Logs show append-only PASS, learning contract PASS, **271 fail-closed cases** (up from 268), prewrite fanout 74 synthetic cases, entry-document PASS, helper ancestor 1,186 negative mutations, and clean/read-only execution PASS.
- **Why safe:** Only the read-only negative validator changed (+17/-1 lines). No workflows, production services, external dependencies, evidence, credentials, traffic or promotion authority were modified.
- **Reusable mechanism:** Couple every new reflective/dynamic execution rejection to a deterministic mutation payload identity and a real CLI rejection with exact exit status, stdout and stderr, not merely an in-process predicate.
- **Protected-authority check:** The ten protected Git blobs remain unchanged: canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective `f4d74f333a4884f9aba2284a31ac011aae8b71bd`, reviewed request `acebcd02de9d4ec44891e70ff00b6898174451dd`, generation evidence `ae7e57efce7ca21d546c1cb336d3ee7bb7ebf93a`, typed non-resurrection `26bb1cc70c64ab3dfa09bee011545a52d46afc00`, promotion review `99cb895fbefb5b459d461926851186dbed742f88`. Actual registries remain empty. OPS-P0-007 is `PREREQUISITES_BLOCKED`; `productionDecision=NO_GO`.
- **Limitation:** Static reload recognition and reviewed fixture identity do not prove complete alias or transitive import closure; canonical learning full-text transfer remains blocked and supplemental records cannot replace it.

## Next safe target

Audit eager `importlib.util.find_spec` and `pkgutil.resolve_name` execution (which can import package code) with negative/positive controls, and independently continue Go-only CI trigger reachability without touching blocked workflow writes.
