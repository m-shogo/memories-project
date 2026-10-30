# Supplemental OPS learning — eager abort and qualified exit reachability (2026-10-30)

Append-only supplemental learning only; canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory policy is `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, or human promotion evidence.

## Material failure / prospective CI guard bypass

- **Symptom:** A CI entrypoint can preserve the correct live `main()` and `validate_learning_guards()` AST yet terminate before reaching them via `os.abort()`, `builtins.exit(0)` or `builtins.quit(0)`.
- **Observed evidence:** At `28374f60c1a798068b9834b4267a921eaa5b9de6`, `can_terminate_before_guard` recognized `sys.exit`, `os._exit`, direct `exit`/`quit` and dynamic `exec`/`eval`, but omitted the three qualified calls. The negative fixture inventory likewise lacked these termination variants. This was a prospective static bypass, not an observed CI compromise or production incident.
- **Verified root cause:** The reviewed early-termination API tuple set was incomplete for common direct qualified exits.
- **Failed approach:** Treating the presence of a syntactically correct live guard and the existing `sys.exit`/`os._exit` checks as a complete reachability proof.
- **Correction:** [`2d90ad34`](https://github.com/m-shogo/memories-project/commit/2d90ad34c889a56c71f3a771f29f602dbb5361b6) extends the conservative termination detector with `os.abort`, `builtins.exit` and `builtins.quit`.
- **Executable recurrence guard:** Six real CI negative mutations cover all three APIs before the module-level main guard and before the live learning-guard invocation. They retain the canonical guard AST and require the exact existing early-termination diagnostic, not merely a nonzero exit.
- **Retry condition:** Reconsider a rejected legitimate eager termination only after a reviewed control-flow proof and changed precondition, with exact-source CI, negative diagnostics, protected-blob comparison and no promotion shortcut. Unknown alias/dictionary forms remain outside the demonstrated closure.

## Material success

- **Observed outcome/evidence:** Exact-source [Autonomous Learning Guard #40978589042](https://github.com/m-shogo/memories-project/actions/runs/40978589042) completed **SUCCESS** on `2d90ad34c889a56c71f3a771f29f602dbb5361b6`. Logs confirm append-only PASS, learning contract PASS, **328 fail-closed negatives** (up from 322), 74 fanout synthetic cases, entry-docs guard PASS, 1,186 helper-ancestor negatives and clean read-only execution PASS.
- **Why safe:** Only the two read-only learning validators changed; new cases use disposable source fixtures and do not execute the injected abort/exit calls. No workflow YAML, Go service, production evidence, credential, traffic, recovery or promotion authority was modified.
- **Reusable mechanism:** Model early termination separately from protected-binding shadowing; require both module startup and main-body guard-call reachability with negative tests for each reviewed terminating API.
- **Protected-authority check:** Ten protected blobs remain unchanged: canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, learning contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective `f4d74f333a4884f9aba2284a31ac011aae8b71bd`, drill request `acebcd02de9d4ec44891e70ff00b6898174451dd`, generation evidence `ae7e57efce7ca21d546c1cb336d3ee7bb7ebf93a`, typed non-resurrection `26bb1cc70c64ab3dfa09bee011545a52d46afc00`, promotion review `99cb895fbefb5b459d461926851186dbed742f88`. Registries remain empty, OPS-P0-007 is `PREREQUISITES_BLOCKED`, `productionDecision=NO_GO`.
- **Limits:** The canonical learning 4.17 MB body remains unavailable through the current connector, though its blob SHA is unchanged. These controls do not prove arbitrary Python alias resolution or the full production admission chain.

## Next safe target

Audit the still-unreviewed dictionary-subscript early-termination boundary (`os.__dict__["abort"]()`, `builtins.__dict__["exit"]()`) with exact positive/negative controls, or prioritize an independently CI-reachable Go-only Focused Test path once workflow-write permissions change. Do not retry unchanged MinIO HTTP 401, canonical large-append transport, workflow permissions or human approval blockers.
