# Supplemental OPS learning — module-dictionary early termination and concurrent branch reconciliation (2026-10-30)

Append-only supplemental history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. This is **never** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, approved recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human-promotion evidence.

## Material failure A — prospective early-termination bypass

- **Symptom:** A syntactically valid CI entrypoint could terminate before its live `main()` or `validate_learning_guards()` invocation via a callable obtained from a module dictionary.
- **Observed evidence:** Before [`08f0845c`](https://github.com/m-shogo/memories-project/commit/08f0845c7e47dbc90a24f6e57f80421638b5880f), the direct qualified `os.abort`/`sys.exit` checks omitted `os.__dict__["abort"]()`, `builtins.__dict__["exit"](0)`, `vars(sys)["exit"](0)`, `os.__dict__[method]()` and `__builtins__["quit"](0)`. The last form is deliberately conservative because `__builtins__` can be a module or mapping. No production incident or actual CI bypass was observed.
- **Verified root cause:** `can_terminate_before_guard` did not inspect `ast.Subscript` callees, so module-dictionary lookup was not modeled as a possible eager termination entry point.
- **Failed approach:** Assuming direct attribute termination checks established complete CI guard-call reachability.
- **Correction / executable recurrence guard:** [`08f0845c`](https://github.com/m-shogo/memories-project/commit/08f0845c7e47dbc90a24f6e57f80421638b5880f) adds bounded module `__dict__`, `vars(module)`, and `__builtins__` subscript termination checks, with 10 exact negative mutations (five before module main dispatch and five before the live learning-guard call) and two deferred function-body positives.
- **Retry condition:** Revisit only with changed reviewed execution/alias preconditions, exact-source CI and unchanged protected admission authorities; do not infer complete alias closure.

## Material failure B — concurrent branch head changed before learning write

- **Symptom:** The first append-only learning commit attempt aborted **before creating any Git object** because the branch HEAD no longer matched its reviewed code commit.
- **Observed evidence:** Expected HEAD `08f0845c7e47dbc90a24f6e57f80421638b5880f`; actual `so` HEAD `b2593c7e53b8d6ae2ce7722ca24204d3ae6adb2d`, two commits ahead. Compare showed only `contracts/operations/production-operability-status.json` and two parser-inflight diagnostic fixtures changed. The new production status blob is `55b3e639763601a66b5cfeb1a6ac409005a093e3`, with `productionDecision=NO_GO`, `asOf=2026-10-30`; OPS-P0-007 snapshot remains unchanged.
- **Verified root cause:** Independent commits advanced `so` after the code CI completed and before the learning write preflight. Their authorship and broader operational cause were not established; no assumption of a specific automation or operator is made.
- **Failed approach:** Using the previously verified code commit as a still-current learning write base.
- **Correction / recurrence guard:** Abort on stale-head preflight, read the new branch tree and target authority, reconcile the exact independent diff, then use a fresh expected-HEAD lease for the append-only record. No force-push or protected-status rollback.
- **Retry condition:** Retry only against the newly observed HEAD after confirming its parentage, protected gates and absence of the target path; abort again if the HEAD advances.

## Material success

- **Observed outcome/evidence:** Exact-source [Autonomous Learning Guard #40978898792](https://github.com/m-shogo/memories-project/actions/runs/40978898792) completed **SUCCESS** on `08f0845c7e47dbc90a24f6e57f80421638b5880f`: append-only PASS, contract PASS, **338 fail-closed negatives** (up from 328), 74 fanout synthetic cases, entry-docs validation PASS, 1,186 helper-ancestor negatives and clean read-only execution PASS.
- **Why safe:** Only two read-only learning validators changed in the code commit. The injected abort/exit payloads are rejected in disposable fixtures, never executed. No workflow YAML, Go service, credentials, traffic, recovery evidence or promotion authority was modified by this code change.
- **Reusable mechanism:** Check termination through both qualified attribute and dictionary-subscript call paths, separately from dynamic code/import execution, with exact rejection diagnostics and deferred-scope positive controls. Use a branch-head CAS to prevent a stale learning append from overwriting concurrent work.
- **Protected-authority check:** At the code commit, all ten protected blobs were unchanged: canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective `f4d74f333a4884f9aba2284a31ac011aae8b71bd`, drill request `acebcd02de9d4ec44891e70ff00b6898174451dd`, generation evidence `ae7e57efce7ca21d546c1cb336d3ee7bb7ebf93a`, typed non-resurrection `26bb1cc70c64ab3dfa09bee011545a52d46afc00`, promotion review `99cb895fbefb5b459d461926851186dbed742f88`. **Afterward, an independent branch advance updated only the production-status blob among those ten**; it remains `NO_GO`. OPS-P0-007 is `PREREQUISITES_BLOCKED`; generation/objective/request/evidence/typed non-resurrection/promotion registries remain empty.
- **Limits:** Canonical learning's approximately 4.17 MB body is unavailable via the connector; its blob SHA is unchanged. No full production admission chain or complete dynamic Python alias closure is claimed.

## Next safe target

Prioritize a MinIO-independent, Go-only CI-reachable Focused Upload Route Test and complete Go/Python transitive input/trigger closure once workflow-write permission or other prerequisites actually change. Continue independent read-only guards without retrying unchanged MinIO HTTP 401, large canonical learning transport or human approval blockers.
