# Supplemental OPS learning — workflow directory membership drift and escaped-fixture recovery (2026-10-30)

Append-only operational learning, separate from the canonical learning authority and mandatory contract. This record **cannot satisfy** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery, complete typed eight-domain non-resurrection, independent review or human promotion gates.

## Material risk A — workflow added after direct-fanout enumeration

- **symptom:** The read-only prewrite auditor enumerated `.github/workflows` once, then read the discovered files. A new YAML workflow added during the read could be omitted from the returned direct trigger matches.
- **evidence:** Source inspection of `matching_workflows` at `b1aacc7a` found no before/after directory metadata comparison. A disposable test injects a second workflow after enumeration and before the reader returns. This is a prospective audit undercount, **not** an observed production incident.
- **rootCauseOrUnknown:** Verified missing directory membership/identity reconciliation around source enumeration and reading.
- **failedApproach:** Trusting a single `iterdir` pass and stable individual file descriptors as sufficient proof of a stable workflow *set*.
- **correction:** [`663af06d`](https://github.com/m-shogo/memories-project/commit/663af06de4b97c2ca79048b1e5c7d2ebe974067d) compares workflow directory device, inode, mtime and ctime before enumeration and after all matching; a missing/replaced/changed directory fails closed.
- **recurrenceGuard:** The CI-reachable negative validator imports the real auditor, proves a clean single-workflow positive, injects `late.yml` during the reader, and requires exact `workflow directory changed during audit` rejection. The synthetic directory ctime is deterministically advanced to avoid filesystem timestamp-resolution assumptions.
- **retryCondition:** Revisit when workflow directory enumeration or source snapshot semantics change; this is not an atomic filesystem snapshot or proof of transitive workflow reachability.

## Material failure B — repeated JavaScript-to-Python newline over-escaping

- **symptom:** The first directory-race fixture used a literal backslash followed by `n` instead of a real YAML line terminator. The source inspection caught this even though the first exact-source CI was running.
- **evidence:** At `663af06d`, the two new Python fixture string literals contained two backslashes before `n`. The prior [Git replace-ref learning](https://github.com/m-shogo/memories-project/blob/so/docs/operations/autonomous-learning-records/2026-10-30-prewrite-git-replace-ref-original-head-guard.md) already documented the same escaping failure mode. [CI #41040901914](https://github.com/m-shogo/memories-project/actions/runs/41040901914) eventually returned SUCCESS, but that cannot establish the intended newline fixture semantics.
- **rootCauseOrUnknown:** Verified repeated over-escaping while constructing Python source through a JavaScript template string. This is a test-authoring failure, not a production defect.
- **failedApproach:** Reusing the previously failed extra-escaping approach without checking the emitted Python literal's actual file bytes before the first commit. Its recorded retry precondition had not changed.
- **correction:** [`b6f0a117`](https://github.com/m-shogo/memories-project/commit/b6f0a11775b80a765962b814bce73497349756bb) corrects both fixture strings and adds exact `read_bytes() == b"on: push\\n"` checks for the initial and injected workflow files.
- **recurrenceGuard:** The real source fixture now fails if a future patch writes literal backslash-n instead of LF. For future JavaScript-to-Python patches, inspect committed source and assert the actual byte-level fixture representation before interpreting a CI PASS.
- **retryCondition:** Retry fixture changes only with explicit source-byte assertions and a verified changed construction approach; never treat a semantically malformed fixture's CI PASS as coverage.

## Material success and protected authority

- **outcome:** [Autonomous Learning Guard #41040978756](https://github.com/m-shogo/memories-project/actions/runs/41040978756) completed **SUCCESS** on exact corrected source `b6f0a11775b80a765962b814bce73497349756bb`.
- **evidence:** CI job logs confirm append-only and learning contract PASS, 517 canonical fail-closed negatives, 195 fanout synthetic cases, 1,186 helper-ancestor negative mutations, entry-document and read-only PASS. The new directory-race fixture is an additional nested in-process negative and is not separately included in the 517 count.
- **whySafe:** Only the read-only prewrite auditor and CI-reachable negative validator were modified. The race injection creates files only in a disposable temporary directory. No workflow YAML, production runtime, credential, traffic, backup/restore, generation/objective, typed eight-domain authority, evidence or promotion gate was changed.
- **reusableMechanism:** Treat directory membership as independent source authority from individual file inode identity; test enumeration races at the precise read boundary and require exact fixture bytes.
- **protectedAuthorityCheck:** GitHub comparison from `b1aacc7a` to `b6f0a117` shows only two Python script paths changed. All ten protected authorities remain unchanged, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639` and OPS-P0-007 snapshot `dbaa36b0`. `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with registered/eligible generations 0/0, no approved recovery objective, executable reviewed drill request, request-bound evidence, complete typed eight-domain record, final candidate or separate human promotion.

## Next independent safe target

Audit the remaining read-only checkout/directory source identity boundaries and prove complete Go/Python transitive input and Push/PR trigger coverage before proposing any workflow changes. Existing Upload Route Go tests remain after external MinIO startup in current workflows. Do not retry unchanged Quay 401, workflow-write permission, canonical large-file transport or human-promotion blockers. This learning-only HEAD is not a full production admission success.
