# Supplemental OPS learning — late job-permission shadows in typed non-resurrection admission (2026-10-29)

Append-only supplemental learning only; not canonical learning, production evidence, typed eight-domain non-resurrection coverage, generation/objective, reviewed drill, backup/restore, RPO/RTO/skew, credentials, traffic, readiness or human promotion.

## Material semantic failure mode / recurrence prevention

- **Symptom:** The newly introduced job-scoped YAML validator examined permission leaves only between `permissions:` and `runs-on:`; a second spaced or quoted `permissions` mapping inserted after `runs-on` could evade that specific semantic check, though the complete Git blob still rejected the unreviewed workflow. This is a verified static validator gap, not an observed production exploit.
- **Observed evidence:** The reviewed publisher has `validate-pr` (read) and `validate` (write); independent has `source-admission` (read). Prior job checks pinned header IDs and early permission leaves but did not enumerate all top-level job keys after `runs-on`.
- **Verified root cause:** Limiting the permission-leaf parser to the pre-`runs-on` section does not prove absence of later YAML mapping overrides.
- **Failed approach:** Assuming a single early permission section and its leaves guarantee effective job permission uniqueness throughout the job body.
- **Correction / executable guard:** [902d05e5](https://github.com/m-shogo/memories-project/commit/902d05e5c535d8186e2d8b3dba27e5963ce40ceb) pins all reviewed top-level job keys and adds nine exact-diagnostic in-memory negatives for plain/spaced/quoted permission overrides after `runs-on` in each of the three jobs. Total YAML negatives increase from thirty to thirty-nine.
- **Retry condition:** Revisit if reviewed job-key topology changes or another demonstrated YAML shadow bypass appears. Do not retry unchanged MinIO HTTP 401, canonical-learning transfer, workflow-write permission or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Non-Resurrection Admission Source Negative #40762394227](https://github.com/m-shogo/memories-project/actions/runs/40762394227) completed **SUCCESS** on exact code `902d05e5c535d8186e2d8b3dba27e5963ce40ceb`. Job log confirms thirty-nine exact-diagnostic YAML negatives, 120 trigger removals, sixteen additions, two shortened inventories, twelve branch-runtime, four writer-event, 24 SHA, five redaction/atomic cases and the existing 29+2 publisher/11+2 independent source mutations.
- **Why safe:** Only the CI-reachable read-only source-negative Python validator changed. The reviewed publisher/independent workflow bytes, typed evidence, registries, credentials, traffic and human promotion authority were untouched.
- **Reusable mechanism:** Validate the complete top-level job-key inventory in addition to job ID and early permission leaves; mutate permission keys after `runs-on` to prevent location-sensitive semantic guard bypasses.
- **Protected-authority check:** Git tree comparison `5d60f8e1` → `902d05e5` found only this validator changed, with zero contract/backup-evidence/canonical-learning blob drift. `productionDecision=NO_GO`; this guard cannot establish production-equivalent recovery, readiness or human promotion.
- **Next safe target:** Apply post-`runs-on` job-key inventory checks to other OPS-P0-007 publisher/independent source-negative validators that currently inspect only early permission leaves.
