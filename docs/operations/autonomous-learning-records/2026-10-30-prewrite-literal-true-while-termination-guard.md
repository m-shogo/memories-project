# Supplemental OPS learning — literal-true prewrite while termination (2026-10-30)

Append-only supplemental operational learning only. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion.

## Material failure / prospective static guard gap

- **symptom:** A prewrite candidate with a literal-true module-level `while` can terminate via `sys.exit(0)` or `raise SystemExit(0)` in its first iteration before the exact canonical main guard.
- **evidence:** Source review at `5573a99daffcef1e8a870b6ad8e533bb4126d9bb` found bounded eager termination handling for direct statements, class, literal-boolean if, with and try/finally, but not `ast.While`. The existing main-shadow visitor does not reject direct exits inside a `while` body. This is a prospective code coverage gap, not an observed production bypass.
- **rootCauseOrUnknown:** Verified omission of the statically guaranteed entered `while True` body from the source-order terminator classifier. Arbitrary loops, early `break`, condition side effects and full symbolic control flow remain outside the reviewed proof.
- **failedApproach:** Inferring reachability of an exact `__main__` AST guard without checking preceding literal-true loops.
- **correction:** [`6dcde8e8`](https://github.com/m-shogo/memories-project/commit/6dcde8e81fc077fd5c3a9593a043118d478bab50) adds bounded recursive direct-termination detection in `while True` bodies. Two exact-diagnostic negatives cover a direct `sys.exit` and a direct `raise SystemExit`; positives preserve `while False` and a deferred function containing a literal-true loop.
- **recurrenceGuard:** Existing CI-reachable `prove_prewrite_python_negatives` enforces both fail-closed negatives and both untaken/deferred positives; candidates are parsed/compiled but never executed.
- **retryCondition:** Revisit only with independently verified changed loop semantics or a legitimate false-positive case, paired exact diagnostics and exact-source CI. Do not retry unchanged Quay MinIO 401, workflow-write permission, canonical-learning large transfer or human-promotion blockers.

## Material success

- **outcome:** [Autonomous Learning Guard #41062369055](https://github.com/m-shogo/memories-project/actions/runs/41062369055) completed **SUCCESS** on exact source `6dcde8e81fc077fd5c3a9593a043118d478bab50`.
- **evidence:** GitHub Actions validate job `124085034876` completed SUCCESS. Job logs show append-only PASS, learning contract PASS, **547 canonical fail-closed negatives**, **195 fanout synthetic cases**, **1,186 helper-ancestor negative mutations**, entry-document PASS, exact clean checkout and read-only PASS. Four new nested prewrite fixtures are not separately counted in the 547.
- **whySafe:** Only CI-reachable read-only Python validator source changed (+15 lines), no workflow YAML, Go production code, traffic, credentials, generation/objective/drill/restore/eight-domain evidence, independent review or promotion authority.
- **reusableMechanism:** Recognize statically entered literal-true loops while preserving untaken and deferred execution controls; verify behavior through exact-source CI.
- **protectedAuthorityCheck:** Ten protected blobs remain unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, generation `bfd1b045`, objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0 and all independent evidence/review/human gates remain unsatisfied.

## Next safe target

Review statically nonempty module-level `for` iteration as another bounded eager termination path. The Go-only pre-MinIO Focused Upload Route Test, full Go/Python transitive input closure and Push/PR trigger coverage remain unproven; no workflow write or external MinIO retry without changed preconditions.
