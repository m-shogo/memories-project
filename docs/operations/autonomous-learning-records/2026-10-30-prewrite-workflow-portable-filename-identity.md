# Supplemental OPS learning — portable workflow filename identity (2026-10-30)

Append-only supplemental learning governed by `contracts/operations/autonomous-learning-system.json`. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains blob-SHA verified, with large-blob full-text transport unavailable. **This record never satisfies production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, recovery generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion gates.**

## Material failure / static workflow-source alias gap

- **symptom:** After casefold/extension alias detection, the workflow source scanner still accepted `NUL.yml`, `COM¹.yml`, `audit?.yml`, decomposed `cafe\u0301.yml` and `LONGFI~1.yml`. It also ignored `audit.yml:stream` because the full name did not end in `.yml`.
- **evidence:** [`369e89d7`](https://github.com/m-shogo/memories-project/commit/369e89d727d9ba29226a98ed8cbbc3a451b4a289) checked casefold and extension shape, but did not apply the portable concrete-path grammar to workflow leaf names. The candidate filter checked only the complete suffix, missing a colon-separated alternate-stream suffix. This is a prospective static alias gap, not observed production behavior.
- **rootCauseOrUnknown:** Verified mismatch between validated target-path grammar and workflow source-name grammar, plus missing NTFS alternate-stream candidate recognition.
- **failedApproach:** Treating every `.yml` leaf as a portable independent workflow source without validating its component name, and ignoring a colon-bearing alias solely because its full suffix differed.
- **correction:** [`73dcf3d3`](https://github.com/m-shogo/memories-project/commit/73dcf3d330d6c650a3961439a18796ca8bd7c3f7) applies `validate_relative_path` to candidate workflow names, recognizes colon-suffixed potential YAML aliases and rejects unsafe leaves with an exact workflow-filename diagnostic. [`3477da84`](https://github.com/m-shogo/memories-project/commit/3477da843c7bea74edf1b2d0a5c206784bd57115) adds six real CLI negatives.
- **recurrenceGuard:** Six synthetic and six exact-diagnostic/exit-1/empty-stdout CLI negatives cover reserved device, superscript device, wildcard, Unicode NFD, DOS 8.3 and NTFS alternate stream workflow filenames. Previously reviewed canonical workflow positives remain. Fail-closed negatives **485 → 491**, fanout synthetic **176 → 182**.
- **retryCondition:** Any exception requires reviewed cross-platform workflow checkout identity, GitHub event recognition and real CLI controls. Do not retry unchanged external MinIO 401, workflow-write permission, canonical-learning transfer or human promotion blockers.

## Material success / protected authority

- **outcome:** Exact-source [Autonomous Learning Guard #41014489101](https://github.com/m-shogo/memories-project/actions/runs/41014489101) completed **SUCCESS** for `3477da843c7bea74edf1b2d0a5c206784bd57115`.
- **evidence:** CI log reports append-only PASS, learning contract PASS, **491** fail-closed negatives, **182** fanout synthetic cases, **1,186** helper-ancestor negative mutations, entry-document PASS and read-only completion.
- **whySafe:** Only the read-only prewrite auditor and CI-reachable negative suite changed. No workflow YAML, production code, credentials, traffic, recovery evidence, readiness, generation/objective or promotion authority changed.
- **reusableMechanism:** Apply one conservative portable path-identity grammar to both requested targets and discovered workflow-source names, including aliases that would otherwise be omitted from suffix-only enumeration.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained equal to run-start `7d2a0617`, including canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and no human recovery/promotion authority.
- **limits / nextSafeTarget:** This is not full Git index identity or transitive CI closure. Independently require a direct push/PR workflow match in strict prewrite mode, while preserving the distinction between direct matching and actual CI reachability.
