# Supplemental OPS learning — qualified eager reflective `getattr` (2026-10-30)

Append-only supplemental history only. Canonical learning authority remains `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and the mandatory contract remains `contracts/operations/autonomous-learning-system.json`. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent-review or human-promotion gates.

## Material failure — prospective qualified reflective bypass

- **Symptom:** An eager `builtins.getattr(importlib, "import_module")("math")` or `builtins.getattr(loader, method)(None)` was outside the direct-name `getattr` guard.
- **Observed evidence:** At source `afc509e4fc308ec70a4fd9d9249e49c2506c7b80`, both AST visitors recognized `ast.Name(id="getattr")` but not `ast.Attribute(attr="getattr")`. The latter syntax can retrieve the same callable without a lexical direct-name call. This was a static bypass, not observed production execution or exploitation.
- **Verified root cause:** The previously bounded reflective-call inventory omitted qualified attribute-based invocation of `getattr`.
- **Failed approach:** Assuming that direct-name `getattr` rejection also covered qualified `builtins.getattr` or other receiver-qualified calls.
- **Correction / executable recurrence guard:** [`49247882`](https://github.com/m-shogo/memories-project/commit/492478828336d7419e6c349203d34df103a46ab0) conservatively rejects eager qualified `.getattr` with a dangerous literal or computed attribute name in both CI entrypoint and prewrite visitors, with a deferred function-local positive and two nested prewrite negatives. [`4cbd61cd`](https://github.com/m-shogo/memories-project/commit/4cbd61cd435b8476dd63bf4f80bd0e38776e0570) adds four isolated CI entrypoint negatives with exact-first-diagnostic rejection. [`4e6863b0`](https://github.com/m-shogo/memories-project/commit/4e6863b0d367ae957b1dfca33bfd06730b0e5f14) adds two real prewrite CLI negatives.
- **Retry condition:** Allowing qualified eager reflective access requires independently reviewed receiver/alias binding and side-effect evidence plus positive/negative controls. `operator.attrgetter`, renamed `getattr` aliases, multi-step dynamic imports and complete import closure remain unproven. Do not retry unchanged MinIO HTTP 401, workflow-write permission, large canonical-history transport or human-promotion blockers.

## Material success

- **Outcome/evidence:** Exact-source [Autonomous Learning Guard #40972023755](https://github.com/m-shogo/memories-project/actions/runs/40972023755) SUCCESS on the visitor/nested controls; [#40972178660](https://github.com/m-shogo/memories-project/actions/runs/40972178660) SUCCESS on the CI entrypoint negatives; [#40972324901](https://github.com/m-shogo/memories-project/actions/runs/40972324901) SUCCESS on real CLI controls with **250 canonical fail-closed cases**, 74 fanout synthetic cases, 1,186 helper-ancestor negative mutations, append-only, entry-document and read-only checks PASS.
- **Why safe:** Only the two read-only learning validator scripts changed. No workflow YAML, service, production status, environment/objective/drill/evidence/non-resurrection/promotion registry, credential or traffic mutation occurred.
- **Reusable mechanism:** Treat eager qualified reflective attribute lookup as an unknown-execution boundary, but preserve deferred function-local positives. Verify the actual CLI and CI first diagnostic, not only an AST predicate.
- **Protected-authority check:** The `contracts/` subtree SHA remained `4f592ff6bd9c7f1af4f671e45304b22984f3ad36`; `docs/` subtree stayed unchanged through the three code commits. Canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, and all six protected registries were unchanged. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound evidence 0, complete typed eight-domain records 0, final candidates 0, human promotion 0. Canonical large-history full-text transfer remains unavailable; its blob identity was verified.

## Existing scoped blockers

[Mixed-Version Apply Compatibility #40971934809](https://github.com/m-shogo/memories-project/actions/runs/40971934809) failed at Start local MinIO; [Chaos and Failure Drills v2 #40972156112](https://github.com/m-shogo/memories-project/actions/runs/40972156112) failed at Start MinIO. These are external service bootstrap failures, not evidence of qualified reflective guard failure. No unchanged MinIO retry was attempted.

## Next safe target

Audit the separate `operator.attrgetter` eager execution lookup path and independent Go-only pre-MinIO focused-test CI reachability without changing workflow triggers until write permission and complete dependency closure are established.
