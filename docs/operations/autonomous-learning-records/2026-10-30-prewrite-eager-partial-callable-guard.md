# Supplemental OPS learning — eager partial wrappers in prewrite main authority (2026-10-30)

Append-only supplemental learning only. Mandatory contract: `contracts/operations/autonomous-learning-system.json`; canonical learning: `docs/operations/AUTONOMOUS-OPS-LEARNING.md` (unchanged blob, full large-file transfer remains blocked). This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, approved recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective main-binding bypass

- **symptom:** A module-level `functools.partial(mutate)()` or `@functools.partial(mutate)` function/class decorator can invoke a locally defined callable that mutates `main` before the canonical entry guard, without a direct `Name(mutate)` call or a direct decorator name.
- **evidence:** Read-only source inspection of `2f8698eb0a75d0da8b9eb36e79a53e2586dce56f` found the prewrite `module_shadows_main` visitor checked direct local-helper calls, immediate lambdas and direct decorator names, but not a partial-factory `Call` as a callee/decorator. Local Python AST parsing/compilation confirmed three syntactically valid wrapper forms. This is a prospective static-analysis gap, not an observed production incident or demonstrated live CI compromise.
- **rootCauseOrUnknown:** Verified lexical-model omission: factory construction, invocation and decorator application are distinct AST stages; the prewrite visitor modeled only direct callable names.
- **failedApproach:** Inferring that direct `Name` call detection and lambda checks cover all eager callable wrappers.
- **correction:** [`2f426ec7`](https://github.com/m-shogo/memories-project/commit/2f426ec7cc4fb141cc09f451ae9777563a0a2f8c) adds a bounded `partial_factory` classifier and rejects immediate factory invocation and partial-factory decorators in function and class definitions. This is conservative lexical rejection, **not** general alias closure.
- **recurrenceGuard:** Four actual `validate_prewrite_python` fail-closed negatives require the exact `main binding shadowed` diagnostic (local-helper invocation, wrapped `exec`, function decorator and class decorator). Two positive controls preserve deferred partial construction and deferred local-helper partial creation.
- **retryCondition:** Reconsider eager partial execution only after reviewed callable/binding proof, changed source preconditions, paired executable positive/negative fixtures, exact-source CI and protected-authority verification. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical-learning large-file transport or human-promotion blockers.

## Material success

- **outcome:** Exact-source [Autonomous Learning Guard #41053996919](https://github.com/m-shogo/memories-project/actions/runs/41053996919) completed **SUCCESS** on `2f426ec7cc4fb141cc09f451ae9777563a0a2f8c`.
- **evidence:** GitHub Actions job log confirms append-only PASS, learning contract PASS, **547 canonical fail-closed cases**, **195 prewrite fanout synthetic cases**, entry-document PASS, **1,186 helper-ancestor negatives**, and clean/read-only workflow completion.
- **whySafe:** Only the CI-triggered read-only Python validator changed (+32 lines); no candidate fixture is executed as live Python, no workflow YAML, Go service, credentials, traffic, evidence, recovery authority, readiness or promotion was modified.
- **reusableMechanism:** Distinguish deferred callable-factory construction from eager factory invocation/decorator application, with exact diagnostic negative tests and deferred positive controls.
- **protectedAuthorityCheck:** All ten protected authority Git blobs remained unchanged: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, recovery objective registry `f4d74f33`, drill request registry `acebcd02`, generation recovery evidence registry `ae7e57ef`, typed non-resurrection registry `26bb1cc7`, human promotion review registry `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`, registered/eligible generations 0/0; approved objectives, executable reviewed requests, request-bound evidence, complete typed eight-domain records, final candidates and human promotion remain absent.

## Next safe target

Bounded alias tracking for an assigned partial factory followed by an eager alias call/decorator, while keeping deferred partial construction admissible. Independently continue the known Go-only pre-MinIO CI reachability and Go/Python transitive closure audits; do not edit workflow YAML without changed permission and reviewed dependency preconditions.
