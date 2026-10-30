# Supplemental OPS learning — canonical negative proof and Unicode diagnostic controls (2026-10-31)

Append-only operational learning under the mandatory `contracts/operations/autonomous-learning-system.json`; canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` is unchanged. This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, approved recovery objective, reviewed drill request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final recovery candidate, or human-promotion evidence.

## Material failure mode 1 — empty or terminal-control-tainted canonical negative reason

- **symptom:** A negative child could satisfy exit-1, canonical prefix and single-LF checks with an empty/whitespace-only reason or terminal control characters. This was a static classifier gap; no actual hostile CI child or production exploit was observed.
- **evidence:** At starting `so` `1603b942`, `require_canonical_rejection` checked exit type, stdout emptiness, stderr prefix/terminator and traceback text but did not validate the reason payload. Six deterministic synthetic `CompletedProcess` controls now cover empty, spaces-only, ANSI ESC, NUL, DEL and tab.
- **rootCauseOrUnknown:** Verified omission of a reason-content/control predicate from the negative admission classifier; exploitability outside the synthetic proof is unknown.
- **failedApproach:** Treating a canonical-looking prefix and one LF as sufficient rejection evidence while ignoring the content between them.
- **correction:** [`647cb0f5`](https://github.com/m-shogo/memories-project/commit/647cb0f5cccd37d6a8667776b4c6f31696366bba) requires a nonblank reason and rejects C0/DEL controls without changing the 601-case CLI inventory.
- **recurrenceGuard:** The existing CI-reachable `prove_failure_classifier` rejects all six mutated child outputs and retains the exact positive control. The nested 120-second deadline and success stream contract remain unchanged.
- **retryCondition:** Reconsider only if the reviewed canonical error format changes or an exact-source CI regression proves a legitimate reason was rejected; do not relax proof merely to accept injected terminal formatting.

## Material failure mode 2 — Unicode formatting in bounded child failure logs

- **symptom:** Failure-detail sanitization replaced ASCII C0/DEL but could leave Unicode NEL/LS/PS, bidirectional direction controls, zero-width format characters and BOM in a CI diagnostic. This is a latent log-formatting boundary, not an observed injected production log.
- **evidence:** At `383a5112`, `bounded_learning_guard_failure_detail` used only `[\\x00-\\x1f\\x7f]`. Three deterministic source-bound tests now cover C1/Unicode line separators, bidi markers and zero-width/BOM characters.
- **rootCauseOrUnknown:** Verified incomplete sanitizer character-class coverage; no observed malicious subprocess or CI log spoofing.
- **failedApproach:** Assuming the ASCII control range exhausts line-breaking and direction-changing Unicode code points.
- **correction:** [`afbe4fc0`](https://github.com/m-shogo/memories-project/commit/afbe4fc023e3e3bf3ebcdbfd681c3dec8e587265) extends the bounded substitution to C1, U+061C, U+200B–U+200F, U+2028–U+202E, U+2060–U+206F and U+FEFF, preserving the existing 800-character tail limit.
- **recurrenceGuard:** Three CI-bound synthetic positive/negative output checks verify the exact single-line normalized result; the parent still requires the original exact child PASS proof, never a sanitized success substitute.
- **retryCondition:** Revisit only for a demonstrated new Unicode formatting class or an actual diagnostic regression, with deterministic test cases and exact-source CI.

## Material failure mode 3 — Unicode-invisible canonical rejection reason

- **symptom:** The initial C0/DEL reason check still admitted invisible Unicode separators, bidi controls and zero-width characters in an otherwise canonical negative diagnostic.
- **evidence:** The `647cb0f5` guard explicitly checked only `ord(char) < 32` or DEL. Python `str.isprintable()` distinguishes reviewed visible Japanese text from NEL, U+2028, U+202E, U+200B and BOM; five synthetic rejection controls and one visible-Unicode positive were added.
- **rootCauseOrUnknown:** Verified limited code-point predicate, not a production incident.
- **failedApproach:** Enumerating only ASCII control code points and treating that as a complete nonprinting-character proof.
- **correction:** [`4afc7b06`](https://github.com/m-shogo/memories-project/commit/4afc7b066dc424b0a2c8ca754f25917ce6514209) requires a nonblank printable reason; visible Unicode remains accepted.
- **recurrenceGuard:** The CI-reachable synthetic classifier rejects five Unicode-invisible reason variants and accepts a printable Japanese reason. No additional subprocess-based fixture was added to the near-limit nested suite.
- **retryCondition:** Only a verified change in canonical diagnostic policy or a reproducible exact-source false rejection permits a revised classifier, with a positive restoration proof.

## Material successes and protected-authority verification

- **outcome:** All three source hardenings completed exact-source Autonomous Learning Guard CI successfully, including direct and independent nested negative execution.
- **evidence:** [#41143139833](https://github.com/m-shogo/memories-project/actions/runs/41143139833) **SUCCESS** at `647cb0f5`; [#41143607082](https://github.com/m-shogo/memories-project/actions/runs/41143607082) **SUCCESS** at `afbe4fc0`; [#41144419204](https://github.com/m-shogo/memories-project/actions/runs/41144419204) **SUCCESS** at `4afc7b06`. Logs show canonical append-only PASS, contract PASS, **601 direct and 601 independently nested negative cases**, 195 fanout synthetic, 52 source-negative workflows / 63 Python commands / 204 semantic fixtures, 1,186 helper-ancestor negatives, entry-document PASS and clean read-only completion.
- **whySafe:** Changes were confined to two existing CI-reachable **read-only** Python validators; no workflow YAML, runtime Go service, external MinIO, credentials, production traffic, production/recovery evidence, registered generation, objective, request, typed non-resurrection record, review or promotion was changed. The separately triggered metrics writer was allowed to finish before this nonurgent learning write.
- **reusableMechanism:** Validate both a child proof's exact transport and its diagnostic payload; normalize bounded failure logs without ever turning normalized text into an admission PASS; use cheap deterministic synthetic negatives instead of adding expensive per-case child processes.
- **protectedAuthorityCheck:** At code HEAD `4afc7b06`, all ten protected blob SHAs were re-read and unchanged: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, recovery objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, and promotion review `99cb895f`. Exact-source Git diffs show only the reviewed validator paths in these three code commits.

## Boundary and next safe target

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered / semantically preflight-eligible generations **0/0**. Preflight still requires two unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current objective. Reviewed requests remain planning-only; new generation recovery evidence must bind a current executable reviewed request; final candidates require all existing gates, complete typed eight-domain non-resurrection coverage and independent review; human production promotion is separate and nonautomatic.

Existing scoped blockers remain unchanged: supplemental-record-only Push/PR append-only CI coverage, workflow-write permission, pre-MinIO focused Upload Route Go CI, MinIO HTTP 401, canonical learning full-text transfer and human approval. None was retried. The final learning-only HEAD must not be reported as having a full production admission-chain SUCCESS.

Next safe target: audit non-string child capture handling in bounded failure diagnostics, and design an authorized supplemental-record-only append-only event gate with overwrite/delete/rename negatives. Preserve the 120-second nested deadline; do not change workflow YAML until permission changes.
