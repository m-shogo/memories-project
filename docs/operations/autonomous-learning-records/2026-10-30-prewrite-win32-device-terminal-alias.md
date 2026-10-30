# Supplemental OPS learning — Win32 device and trailing-component aliases (2026-10-30)

Append-only learning under `contracts/operations/autonomous-learning-system.json`. Canonical learning authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md` (large-blob transport remains unavailable; blob SHA verified). This record is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure / observed static gap

- **symptom:** The read-only prewrite path validator previously accepted `docs/CON`, `assets/nul.txt`, `docs/COM¹.txt`, `docs/notes.` and `docs/notes /readme.md`, despite Win32 reserved-device and trailing-component aliases.
- **evidence:** At run-start `7d2a0617`, `validate_relative_path` checked Git metadata aliases, controls, separators and colons but did not check reserved device stems or trailing dots/spaces for ordinary components. This was a static path-identity gap, **not** an observed production incident.
- **rootCauseOrUnknown:** Verified omission from the portable repository-relative path grammar; actual platform resolution of hypothetical paths was not exercised.
- **failedApproach:** Treating Win32 device stems with extensions and terminal dot/space components as ordinary independent source paths during direct workflow-trigger matching.
- **correction:** [`b660ed51`](https://github.com/m-shogo/memories-project/commit/b660ed516c5b6ac7b726c4e0796e1dddb7e6f3fe) rejects `CON`, `PRN`, `AUX`, `NUL`, `CONIN$`, `CONOUT$`, `COM1..9`, `LPT1..9`, their documented superscript digit variants and trailing dots/spaces. [`a7586aa9`](https://github.com/m-shogo/memories-project/commit/a7586aa9fa62e06a7502e5cd7b460c72ba83271d) adds actual CLI negative coverage.
- **recurrenceGuard:** Ten synthetic path negatives and ten exact-diagnostic, exit-1, empty-stdout CLI negatives; normal Japanese, `.gitignore`, `docs/conifer.md` and `docs/company.txt` remain positive. Fail-closed negatives **459 → 469** and fanout synthetic **149 → 159** at exact-source CI.
- **retryCondition:** Relaxing any rejected path requires a separately reviewed, platform-specific file identity and root-containment proof with matching positive and negative real-CLI tests. Unchanged MinIO HTTP 401, workflow-write permission, canonical-learning large-blob transfer and human-approval blockers must not be retried.

## Material success / protected-authority check

- **outcome:** Exact-source [Autonomous Learning Guard #41013596413](https://github.com/m-shogo/memories-project/actions/runs/41013596413) completed **SUCCESS** on `a7586aa9fa62e06a7502e5cd7b460c72ba83271d`.
- **evidence:** Job log reports append-only PASS, learning contract PASS, **469** canonical fail-closed negatives, **159** prewrite fanout synthetic cases, **1,186** helper-ancestor negative mutations, entry-document PASS and clean read-only completion.
- **whySafe:** Only read-only Python auditor and CI-reachable negative validator changed. No workflow YAML, production code, generation/objective registries, recovery evidence, credentials, traffic, readiness or promotion authority changed.
- **reusableMechanism:** Reject cross-platform alias-prone repository-relative path components before filesystem reads and workflow glob matching, and require a real CLI negative for each new rejected form.
- **protectedAuthorityCheck:** After both code changes and the subsequent independent Unicode-normalization code/test changes, all ten protected authority blobs matched run-start `7d2a0617`, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0 and all human approval/recovery gates absent.
- **limits / nextSafeTarget:** This does not prove Git index checkout identity, complete transitive Go/Python dependency closure or a MinIO-independent Go-only CI route. Audit Unicode canonical equivalence separately; do not use this learning as production gate evidence.
