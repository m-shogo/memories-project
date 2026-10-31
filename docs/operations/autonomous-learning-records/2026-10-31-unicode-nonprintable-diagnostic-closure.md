# Supplemental OPS learning — Unicode nonprintable child diagnostic closure (2026-10-31)

Append-only operational learning under `contracts/operations/autonomous-learning-system.json`. The canonical learning history remains unchanged. **This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final recovery candidate, or human promotion evidence.**

## Material failure — incomplete enumerated Unicode diagnostic sanitizer

- **symptom:** A bounded child failure diagnostic could preserve Unicode formatting code points omitted by the previous regular-expression allowlist, including U+00AD soft hyphen, U+200D zero-width joiner, U+00A0 no-break space, and an unpaired surrogate. This was an observed synthetic classification gap, not a real hostile subprocess or production incident.
- **evidence:** At prior source blob `e362fc672cf1340fb7b85efd2d81d84e45e34fa7`, `bounded_learning_guard_failure_detail` substituted a finite enumerated Unicode range. Python `str.isprintable()` returns false for the four new fixture characters; the prior regex did not match them. A visible Japanese diagnostic remains printable and must not be damaged.
- **rootCauseOrUnknown:** Verified omission of nonprinting Unicode classes from an enumerated regex; actual exploitability in GitHub Actions logs is unknown.
- **failedApproach:** Expanding a list of selected Unicode controls and assuming it exhausts nonprintable formatting.
- **correction:** [`fb7d1831`](https://github.com/m-shogo/memories-project/commit/fb7d183185acf60e9d0f800c8906469e8878eab1) replaces the enumerated regex with a bounded 800-code-point pass that retains Python-printable characters and replaces each nonprintable with a space.
- **recurrenceGuard:** Four new deterministic nonprintable negatives and one visible Japanese positive are CI-bound in `prove_learning_guard_classifier`. Existing C0/C1, Unicode separators, bidi, zero-width/BOM, bounded-tail and nonstring capture controls remain. This is not a claim to detect every visually invisible printable combining code point.
- **retryCondition:** Revisit only for a demonstrated missed formatting class, a reviewed change in diagnostic policy, or exact-source CI false rejection; preserve deterministic positive and negative controls.

## Material success — exact-source guard verification

- **outcome:** The formatter now replaces every character Python classifies as nonprintable in the bounded diagnostic tail, while retaining visible Japanese text and the exact success classifier.
- **evidence:** 13 local synthetic Unicode sanitizer cases PASS. [Autonomous Learning Guard #41149911498](https://github.com/m-shogo/memories-project/actions/runs/41149911498) completed **SUCCESS** at exact code SHA `fb7d183185acf60e9d0f800c8906469e8878eab1`. Logs show append-only PASS, learning contract PASS, 601 direct and 601 independent nested negative cases, 52 workflow/63 Python-command/204 fixture source-negative reachability, 195 fanout synthetic, 1,186 helper-ancestor negatives, entry-document PASS and clean read-only completion.
- **whySafe:** The code commit modifies only the read-only `scripts/validate-memory-os-entry-docs.py`, with no runtime service, workflow YAML, MinIO, credentials, traffic, production evidence, generation, objective, request, review or promotion change. The nonurgent learning write waited for all observed active writer workflows to complete.
- **reusableMechanism:** Prefer an explicit Unicode printability boundary to an incomplete manual control list for bounded log diagnostics, while keeping strict PASS parsing independent and testing visible non-ASCII output.
- **protectedAuthorityCheck:** At code HEAD `fb7d1831`, all ten protected blob SHAs match its parent: canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`.

## Independent Go/CI audit and unchanged blockers

Two focused `services/import-api/internal/httpserver/route_authority_test.go` tests are pure route/template and `New(Config{})` prefilter checks, unlike the `server_live_test.go` upload lifecycle and account-deletion HTTP tests that create a live server and use presigned MinIO uploads. Existing `import-api-security-slice.yml` and Upload Route reconciliation start MinIO before the focused Go tests, so independent pre-MinIO CI execution is still not established. Workflow write permission remains blocked; no workflow YAML was changed. Existing source-negative audit pins the 109 direct inputs, 81 uncovered Push/PR inputs and 11 SQL migration trigger gaps. Do not claim full transitive trigger closure.

`productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED` with registered/semantically eligible generations 0/0 and no human-approved current recovery objective. Preflight requires two unsuperseded semantically eligible generations from distinct environments plus human approval. Reviewed drill requests are planning-only; generation evidence requires a current executable reviewed request; final candidates need all existing gates, typed eight-domain non-resurrection coverage and independent review; human promotion is separate/nonautomatic.

**Next safe target:** Authorized supplemental learning Push/PR append-only event coverage and pre-MinIO focused Go CI for the two pure route tests. Do not retry unchanged MinIO HTTP 401, workflow-write, canonical learning transfer, or human approval blockers.
