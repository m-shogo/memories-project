# Supplemental OPS learning — canonical stream ValueError fail-closed (2026-11-01)

Append-only operational history subordinate to the canonical learning document and `contracts/operations/autonomous-learning-system.json`. Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered or eligible environment generation, approved recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final recovery candidate, or human promotion evidence.

## Material failure

- **symptom:** A canonical binary stream acquisition or read raising ordinary `ValueError` could escape the reviewed `ValidationFailure` diagnostic channel. No production incident was observed.
- **evidence:** The canonical reader at `62d8e7c0` caught only `OSError` around `os.fdopen` and the stream read. A synthetic `ValueError` at either boundary would propagate as a raw exception rather than the exact unreadable-authority diagnostic. The Upload Route had independently learned this ordinary non-OSError class, but its separate guard did not cover the canonical learning reader.
- **rootCauseOrUnknown:** Verified exception-class mismatch at the canonical reader's acquisition/read handler. Whether a valid real OS stream ordinarily raises `ValueError` at these boundaries is not claimed; the fault is injected deterministically.
- **failedApproach:** Treating an OSError-only acquisition/read handler and OSError-only fdopen negative as complete coverage. No unchanged MinIO or workflow-permission blocker was retried.
- **correction:** [`e483657d`](https://github.com/m-shogo/memories-project/commit/e483657deee34bd32f0e1308353bb5f7bc0c14ed) maps both `OSError` and `ValueError` to the canonical unreadable-authority failure while preserving an already raised `ValidationFailure`.
- **recurrenceGuard:** [`698aec10`](https://github.com/m-shogo/memories-project/commit/698aec1080fcd3ee194086e752f582879601ffc3) adds two CI-reached real-FD fault injections: `fdopen` ValueError before stream acquisition and `read` ValueError after non-owning acquisition. Both require exact diagnostics, no raw-FD leak and a successful subsequent clean read.
- **retryCondition:** Revisit if Python stream acquisition/read exception classes, raw FD ownership, canonical error classification or the negative harness change. Do not retry unchanged external MinIO HTTP 401 or workflow write-permission failures.

## Material success

- **outcome:** The canonical authority reader rejects injected ValueError acquisition/read faults through the reviewed fail-closed diagnostic and releases its retained raw descriptor.
- **evidence:** [Autonomous Learning Guard #41283761279](https://github.com/m-shogo/memories-project/actions/runs/41283761279) completed SUCCESS on exact code HEAD `e483657d`; [Autonomous Learning Guard #41283774143](https://github.com/m-shogo/memories-project/actions/runs/41283774143) completed SUCCESS on exact test HEAD `698aec10`. The canonical negative harness executes these fault cases as part of its descriptor suite; they are synthetic, not production/recovery tests.
- **whySafe:** Only the read-only canonical Python validator and its disposable negative harness changed. No workflow, Go production route, credential, traffic, recovery evidence, readiness or promotion authority was modified.
- **reusableMechanism:** Classify ordinary acquisition/read errors at the authoritative boundary; require real-descriptor cleanup and exact rejection diagnostics in the same CI-reachable fault matrix.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs were unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objectives `f4d74f33`, reviewed requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, generations registered/semantically eligible 0/0, approved objectives 0. All existing objective, request-binding, eight-domain, independent-review and human-promotion gates remain separate and unsatisfied.

## Next safe target

Reject non-byte binary stream results before their length or decoding is trusted; verify the original descriptor and independent canary are preserved in the same read-only CI path.
