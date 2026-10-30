# Supplemental OPS learning — strict prewrite Git metadata post-audit snapshot (2026-10-31)

Append-only operational learning only. The canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json` remain unchanged. This record is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review or promotion evidence.

## Material source-authority failure risk and correction

- **symptom:** The strict prewrite workflow audit could accept a Git index or metadata directory that changed after its initial `lstat` and before the audit returned, even when indexed workflow bytes and `git diff --cached` remained consistent.
- **evidence:** At `69225c518e38b50929043b438e117773a4d1016f`, `.git` and `.git/index` were checked only before the Git subprocess sequence. Disposable Git controls confirmed the ordinary read-only Git commands preserve the index metadata. Three deterministic CI fixtures now mutate the index permission, replace the index inode with byte-identical content, or grant metadata-directory group write permission immediately after `ls-files --stage`. No production incident is claimed.
- **rootCauseOrUnknown:** Verified absence of a post-Git index/directory identity check. Unobserved ABA changes and complete Git object-store trust are outside this bounded proof.
- **failedApproach:** Trusting a single preflight filesystem snapshot together with later Git output and raw workflow blob parity.
- **correction:** [`43f34c3b`](https://github.com/m-shogo/memories-project/commit/43f34c3bbf0a65d4a78784179f84cfd3e6c3802f) compares directory and index device, inode, mode, size, timestamps and link count after the read-only Git commands; mismatch fails closed.
- **recurrenceGuard:** Three deterministic actual-Git mutation negatives require the exact `prewrite Git metadata changed during audit` diagnostic, no accepted audit result, and a restoration positive after each mutation. The canonical negative count increased from 581 to **584**.
- **retryCondition:** Reconsider only after a reviewed Git checkout/index authority change or a reproducible runner-specific metadata mutation, with exact-source positive and negative controls. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical-learning full-text transport or human approval blockers.

## Material fixture weakness discovered before completion

- **symptom:** The initial test fixture encoded the two literal characters backslash and `n` instead of a line-feed terminator, permitting an ambiguous YAML source to count as an unfiltered push match.
- **evidence:** Source inspection after `43f34c3b` found `b"on: push\\n"` in the fixture, rather than a single Python newline escape. The first exact-source CI [#41083576179](https://github.com/m-shogo/memories-project/actions/runs/41083576179) succeeded but did not prove the fixture used valid LF-terminated YAML.
- **rootCauseOrUnknown:** Verified double-escaping while constructing the GitHub patch; no production source or protected authority was affected.
- **failedApproach:** Treating a positive matcher classification alone as proof that the fixture bytes represented the intended YAML.
- **correction:** [`39f3072c`](https://github.com/m-shogo/memories-project/commit/39f3072c0c0d4bbb04fdacced11360bdebb89daa) uses the correct Python newline escape and independently asserts the expected LF byte `bytes((10,))`.
- **recurrenceGuard:** A byte-exact fixture assertion now rejects the escaped-literal mistake before mutation tests run.
- **retryCondition:** Revisit only for a changed YAML source encoding or explicit byte-format contract; do not reuse an ambiguous matcher positive as source-format proof.

## Material success and protected authority

- **outcome:** Two read-only Python files now guard Git metadata/index stability through the strict audit and validate it with three fail-closed controls.
- **evidence:** Exact-source [Autonomous Learning Guard #41084135852](https://github.com/m-shogo/memories-project/actions/runs/41084135852) for `39f3072c0c0d4bbb04fdacced11360bdebb89daa` completed **SUCCESS**. Logs show append-only PASS, learning contract PASS, **584** canonical fail-closed negatives, 195 fanout synthetic cases, 1,186 helper ancestor negative mutations, entry-document PASS and clean/read-only completion.
- **whySafe:** The Git mutations occur only in disposable local test repositories. Production code, workflow YAML, environment generation/objective, credentials, traffic, evidence and promotion authorities were not changed.
- **reusableMechanism:** Bind a source proof to both initial and final metadata snapshots; test inode replacement and chmod after the actual subprocess boundary, not only at entry.
- **protectedAuthorityCheck:** The baseline-to-code diff changes only `scripts/audit-memory-os-workflow-trigger-fanout.py` and `scripts/validate-autonomous-learning-system-negative.py`. All ten protected authority Git blobs are unchanged, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and the six generation/objective/request/recovery/non-resurrection/promotion registries. Canonical learning full text was not transferred and this supplemental record cannot substitute for it.
- **production boundary:** `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0; no current approved objective, executable reviewed request, request-bound recovery evidence, complete typed eight-domain record, final candidate, independent review or human promotion.

## Next safe target

Detect a Git `HEAD` ref moving during strict prewrite audit while the index and workflow blobs remain unchanged. Prove the gap with an unrelated-commit ref move in a disposable repository and require a bounded before/after `HEAD^{commit}` identity check. Separately continue read-only Go/Python transitive dependency and MinIO-first CI trigger closure analysis; do not edit workflow YAML without the required authority.
