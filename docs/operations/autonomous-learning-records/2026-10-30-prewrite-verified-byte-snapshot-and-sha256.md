# Supplemental OPS learning — consume verified workflow bytes and cover Git SHA-256 (2026-10-30)

Append-only supplemental history only. Mandatory policy is `contracts/operations/autonomous-learning-system.json`; canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains unchanged and verified by blob SHA, not fully transferred. **No learning entry is production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment-generation, recovery-objective, reviewed-request, request-bound evidence, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure A — read-after-identity-check window

- **symptom:** The strict Git index workflow audit read raw YAML bytes to verify blob identity, then `matching_workflows` reopened each workflow through `Path.read_text`. A concurrent modification between these reads could make the parser inspect bytes different from those whose Git identity was proved.
- **evidence:** Source inspection at `e89d69eb` showed `require_workflow_git_index_identity` discarding its validated raw bytes, followed by `workflow.read_text(encoding="utf-8")` in `matching_workflows`. This is a prospective time-of-check/time-of-use gap, not an observed concurrent production attack.
- **rootCauseOrUnknown:** Verified source-level cause: identity validation and event parsing consumed separate filesystem reads.
- **failedApproach:** Verifying a raw blob hash, discarding that byte buffer, then reopening the same path for semantic interpretation.
- **correction:** [`653f3a5d`](https://github.com/m-shogo/memories-project/commit/653f3a5de7382a450499772e4328de7f958f9271) makes strict index verification return a `dict[Path, bytes]` and parses precisely that verified buffer. Existing non-strict direct-match behavior remains unchanged.
- **recurrenceGuard:** The executable disposable Git self-test patches `Path.read_text` to reject any second workflow read during strict matching. [`094c2c0b`](https://github.com/m-shogo/memories-project/commit/094c2c0be4c7f62dc1a04f5bef13ffeb04978d4e) additionally pins the verified-byte handoff in the CI-bound negative validator, while the entry-document validator executes the actual self-test.
- **retryCondition:** Any alternative source reader requires an exact verified-byte-to-parser handoff, deterministic no-second-read positive/negative, exact-source CI and protected-authority comparison. This does not claim a lock on the checkout or a complete concurrent-writer model.

## Material failure B — untested Git SHA-256 object format

- **symptom:** The raw-blob guard chose SHA-1 for 40-character index IDs and SHA-256 for 64-character IDs, but the initial executable Git fixture exercised only the default SHA-1 repository format.
- **evidence:** A disposable `git init --object-format=sha256` repository produced a 64-character indexed blob ID, and local `hashlib.sha256` of the Git blob header plus raw bytes matched it. The absence of an actual SHA-256 CLI regression fixture was a test-coverage gap, not an observed hash mismatch.
- **rootCauseOrUnknown:** Verified: the original test inventory did not exercise the second supported Git object format.
- **failedApproach:** Treating a branch in hash-algorithm selection as validated solely by the SHA-1 fixture.
- **correction:** [`6c3f1b83`](https://github.com/m-shogo/memories-project/commit/6c3f1b8322047b0c6de1cb61887b30f259b67433) adds an actual SHA-256 Git repository CLI clean positive, dirty raw-blob negative and restored positive, asserting 64-character index object identity.
- **recurrenceGuard:** Real Git SHA-256 initialization and strict CLI verification; do not infer SHA-256 coverage from a mocked digest or the SHA-1 path.
- **retryCondition:** If runner Git lacks SHA-256 support, explicitly record the environment/toolchain blocker and independently establish support before rerunning; never silently downgrade the SHA-256 test to SHA-1.

## Material success and bounded evidence

- **outcome:** Strict matching now consumes verified raw bytes, and the negative suite covers both SHA-1 and SHA-256. The prior corrected [Autonomous Learning Guard #41019792366](https://github.com/m-shogo/memories-project/actions/runs/41019792366) completed SUCCESS on exact source `8043fc39` with 509 canonical fail-closed negatives, 193 fanout synthetic cases, 1,186 helper-ancestor mutations, contract/append-only/entry-docs/read-only PASS. Exact-source CI for `094c2c0b` and `6c3f1b83` was **pending** at record creation.
- **evidence:** GitHub Actions run/job logs for `8043fc39`, source-level verified-byte handoff, disposable no-second-read self-test, local SHA-256 Git blob calculation and committed actual CLI SHA-256 fixtures.
- **whySafe:** Only existing read-only Python audit and negative validator changed; no workflow YAML, production runtime, credential, traffic, recovery evidence, promotion authority or external MinIO was written.
- **reusableMechanism:** Keep the identity-verified byte snapshot immutable through parsing and exercise every supported Git object hash algorithm against real indexed blobs and actual CLI rejection.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged through `6c3f1b83`: canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and the six generation/objective/drill/evidence/non-resurrection/promotion registries. Snapshot remains `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, approved objective 0, executable reviewed request 0, request-bound evidence 0, complete typed eight-domain records 0, final candidates 0. `productionDecision=NO_GO` remains mandatory; human promotion is separate.

## Next safe target

Verify both exact-source CI runs and persist a separate append-only proof if successful. Then prioritize Go-only Upload Route CI reachability before MinIO and complete Go/Python transitive dependency closure; workflow trigger changes remain blocked by existing permissions and incomplete closure.
