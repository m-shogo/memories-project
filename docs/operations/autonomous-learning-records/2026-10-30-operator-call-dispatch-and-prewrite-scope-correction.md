# Supplemental OPS learning — operator.call eager dispatch and scoped prewrite correction (2026-10-30)

Append-only supplemental execution history only. Canonical authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy: `contracts/operations/autonomous-learning-system.json`. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, approved recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective dynamic callable-dispatch bypass

- **Symptom:** `operator.call(sys.exit, 0)` or `call(os.abort)` before the learning guard can terminate execution while the canonical guard call remains in the AST. In the Python prewrite checker, `operator.call(exec, "main = None")` can rebind the protected module `main` without a direct `exec(...)` AST callee.
- **Observed evidence:** At reviewed source `6084aa2d99d45e363c816dbab8065a86a352d772`, `can_terminate_before_guard` and `module_shadows_main` inspected direct, reflective, dictionary and callable-factory calls, but not immediate `operator.call` dispatch. The existing exact negatives had no `operator.call` case. This is a prospective static gap, not an observed CI compromise or production incident.
- **Verified root cause:** The visitor inspected the outer AST callee `operator.call` but did not model the first argument as a callable invoked immediately.
- **Failed approach:** Inferring that the direct-callee exit/exec checks also cover indirect dispatch wrappers.
- **Correction / executable recurrence guard:** [`7c49cad2`](https://github.com/m-shogo/memories-project/commit/7c49cad27602a801d9fc78893d69ba15239c2fa8) conservatively rejects `operator.call(...)` and direct-name `call(...)` at eager module/pre-guard sites, including the prewrite main-binding validator. Four canonical exact-diagnostic negatives cover module and main-body termination. Two nested prewrite negatives cover module-level exec dispatch. Paired deferred function-body positives preserve the distinction between definition and execution.
- **Retry condition:** A legitimate eager operator.call use requires reviewed callable binding/receiver and execution-order proof, changed preconditions, exact-source CI, bounded prewrite diff, CAS and protected-authority verification. No complete dynamic alias closure is claimed.

## Prewrite failure — ambiguous global source replacement prevented

- **Symptom:** The initial proposed change aborted before creating any GitHub object because the target string `if isinstance(node, ast.Call):` with the following dictionary-lookup comment occurred in two different validator functions.
- **Observed evidence:** The local prewrite exact-anchor check raised `anchor not unique module rebinding call wrapper` before any `create_blob`, `create_tree`, `create_commit` or branch update. No repository or CI failure was created.
- **Verified root cause:** A global string replacement targeted a source fragment shared by `module_scope_rebinds` and `module_shadows_main`.
- **Failed approach:** Attempting to replace a non-unique cross-function source fragment.
- **Correction / recurrence guard:** Re-read latest `so` and the target source, then bounded the replacement to the unique `module_shadows_main` function region and required exactly one match within that scope. The corrected prewrite passed and only then wrote the commit with expected-HEAD CAS.
- **Retry condition:** Any future repeated source fragment must use function-scoped unique anchors and re-read current HEAD/file before write. Do not retry the ambiguous global replacement unchanged.

## Material success

- **Observed outcome/evidence:** Exact-source [Autonomous Learning Guard #40985489704](https://github.com/m-shogo/memories-project/actions/runs/40985489704) completed **SUCCESS** on `7c49cad27602a801d9fc78893d69ba15239c2fa8`. Logs show append-only PASS, learning contract PASS, **367 canonical fail-closed cases** (up from 363), 74 fanout synthetic cases, entry-document PASS, 1,186 helper-ancestor negatives and clean read-only execution PASS. Two new nested prewrite negatives are additional to the printed 367.
- **Why safe:** The code commit changed only two CI-reachable read-only validators (+23/-0 and +5/-0 lines). Dangerous-looking dispatch calls are statically parsed in disposable fixtures, never executed. No workflow YAML, Go service, production traffic, credentials, recovery evidence, readiness or human promotion authority changed.
- **Reusable mechanism:** Classify eager callable dispatch separately from direct AST callee names; require function-scoped prewrite anchors and paired deferred positives.
- **Protected-authority check:** Ten protected blobs unchanged: canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `55b3e639763601a66b5cfeb1a6ac409005a093e3`, OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6`, generation `bfd1b04561a257d1a288bd127572bdad762bfae5`, objective `f4d74f333a4884f9aba2284a31ac011aae8b71bd`, drill request `acebcd02de9d4ec44891e70ff00b6898174451dd`, generation evidence `ae7e57efce7ca21d546c1cb336d3ee7bb7ebf93a`, typed non-resurrection `26bb1cc70c64ab3dfa09bee011545a52d46afc00`, promotion review `99cb895fbefb5b459d461926851186dbed742f88`. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound evidence 0, complete typed eight-domain records 0, final candidates 0 and human promotion 0.
- **Limits:** The canonical learning body (~4.17 MB) remains unavailable through the current connector, with unchanged blob identity. The learning CI success is not a full production admission chain. The Go-only, pre-MinIO focused-test trigger gap remains unclosed.

## Next safe target

Audit other eager callable dispatch wrappers and prewrite source-binding control flow without assuming complete alias closure. Continue Go/Python dependency/trigger coverage analysis, but do not retry unchanged Quay MinIO HTTP 401, workflow-write permission, canonical large-append transport or human promotion blockers. Maintain OPS-P0-007 evidence and review strictness.
