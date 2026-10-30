# Supplemental OPS learning — Win32-invalid filename metacharacters (2026-10-30)

Append-only supplemental learning governed by `contracts/operations/autonomous-learning-system.json`. Canonical learning `docs/operations/AUTONOMOUS-OPS-LEARNING.md` is blob-SHA verified but its large-blob text transport remains unavailable. **This is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure / static source-identity gap

- **symptom:** The prewrite path validator previously accepted concrete path components containing Win32-invalid filename characters such as `docs/report?.md`, `docs/report*.md`, `docs/report|final.md` and angle brackets or double quotes.
- **evidence:** After the DOS 8.3 change, `validate_relative_path` rejected control, Unicode, colon, backslash, reserved-device and short-name aliases, but not the six Win32-invalid metacharacters `< > " | ? *`. This was a static path-identity gap, not a production incident.
- **rootCauseOrUnknown:** Verified missing filename-character grammar rule; actual Windows filesystem resolution of any hypothetical file was not exercised.
- **failedApproach:** Treating wildcard or reserved filename metacharacters as a portable concrete source path while inferring direct GitHub workflow trigger fanout.
- **correction:** [`332eab35`](https://github.com/m-shogo/memories-project/commit/332eab35f4c930edd2dbde5cfe203e33bea3d914) rejects all six metacharacters before workflow scanning. [`e4eaea51`](https://github.com/m-shogo/memories-project/commit/e4eaea516dc30caa55067bc5be20ce01cc229acb) adds six real CLI negatives.
- **recurrenceGuard:** Six synthetic negatives and six exact-diagnostic/exit-1/empty-stdout CLI negatives cover angle brackets, quote, pipe, question mark and asterisk; ordinary `docs/report-final.md` remains positive. Exact-source fail-closed negatives **475 → 481**, fanout synthetic **165 → 171**.
- **retryCondition:** Any exception requires a reviewed platform-specific concrete-file identity and checkout containment proof with matching CLI controls. Do not retry unchanged MinIO 401, workflow-write permission, canonical-learning transfer or human approval blockers.

## Material success / authority check

- **outcome:** Exact-source [Autonomous Learning Guard #41014116219](https://github.com/m-shogo/memories-project/actions/runs/41014116219) completed **SUCCESS** for `e4eaea516dc30caa55067bc5be20ce01cc229acb`.
- **evidence:** CI logs show append-only PASS, learning contract PASS, **481** fail-closed negatives, **171** fanout synthetic cases, **1,186** helper-ancestor negative mutations, entry-document PASS and read-only completion.
- **whySafe:** Only read-only auditor and CI-reachable negative validator changed; no workflow YAML, production runtime, recovery evidence, credentials, traffic, readiness, objectives, generations or promotion authority changed.
- **reusableMechanism:** Separate portable concrete-source path validation from GitHub workflow glob grammar, and reject reserved filename syntax before filesystem and trigger analysis.
- **protectedAuthorityCheck:** Ten protected authority blobs matched run-start `7d2a0617`, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and all human approval/recovery gates absent.
- **limits / nextSafeTarget:** No Git index or complete transitive Go/Python trigger closure is claimed. Review workflow filename aliases separately and continue MinIO-independent Go-only CI reachability analysis without unauthorized workflow changes.
