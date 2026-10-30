# Supplemental OPS learning — indented escaped root YAML key (2026-10-30)

Append-only supplemental history only. Canonical learning authority: `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory contract: `contracts/operations/autonomous-learning-system.json`. This is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective escaped-key undercount

- **Symptom:** An indented YAML root mapping key such as `  "o\\u006e": push` can decode to `on` while escaping the existing column-zero regex, allowing a conservative prewrite fanout undercount. This is a static-parser finding, not an observed production incident.
- **Observed evidence:** The previously reviewed escaped-key regex required a literal column-zero double quote; separate handling of indented literal `on` does not recognize the escaped spelling. Three focused Python regex reproductions confirmed two indented escaped-key matches and one unrelated plain-key nonmatch. Exact-source CI remains unverified.
- **Verified root cause:** Inconsistent indentation treatment between the literal-root and escaped-root YAML key guards.
- **Failed approach:** Assuming a column-zero-only escaped-key check covers valid indented root keys.
- **Correction:** [`4bf2de81`](https://github.com/m-shogo/memories-project/commit/4bf2de81c9fe9bd3f7969a328c06ac78496fbdf8) allows leading YAML whitespace in the conservative escaped-key detector.
- **Executable recurrence guard:** [`9053e612`](https://github.com/m-shogo/memories-project/commit/9053e6129de035d4ed54c9dbc8eebbefc62ca879) adds three ordered identity-pinned cases to the self-test and actual CLI suite, including a document-marker variant and an unrelated-key nonmatch.
- **Retry condition:** Revisit if exact-source CI or a reviewed YAML parser shows a counterexample, or when the workflow trigger parser is replaced with a semantics-preserving implementation. Do not retry unchanged external MinIO, workflow-write, canonical learning transfer or human approval blockers.

## Material success — bounded read-only guard change

- **Observed outcome/evidence:** Two commits modified only the read-only prewrite fanout script and its negative CLI validator. The exact GitHub compare from `b1098c41` to `9053e612` reports precisely those two files. Three focused regex reproductions passed; no exact-source GitHub Actions success has been observed.
- **Why safe:** This is conservative detection of ambiguous workflow source; it cannot create production evidence, credentials, traffic, eligible generations, recovery objectives, reviewed requests or promotion authority.
- **Reusable mechanism:** Treat escaped YAML keys as potentially semantic event keys independently of their indentation, and pair exact ordered self-test identities with real CLI positive/negative controls.
- **Protected-authority check:** The two-file code diff excludes all ten previously reviewed protected authorities. Canonical learning SHA `b809c69dda5d788245abd2a79b34c6e8c1d6c628` and contract SHA `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` remain unchanged; production status, OPS-P0-007 snapshot and six registries are not modified. Governing decision stays `NO_GO`, OPS-P0-007 stays `PREREQUISITES_BLOCKED`; no human promotion or production-equivalent evidence is asserted.

## CI visibility and next safe target

The connector returned empty combined statuses and no PR-filtered runs for exact code SHA `9053e6129de035d4ed54c9dbc8eebbefc62ca879`; this does not establish push CI success or failure. Reuse the CI visibility blocker and retry condition in the preceding root-flow learning record. Next safe targets: obtain exact-source CI evidence; audit complete Go/Python input closure and CI trigger coverage; design a permission-authorized, MinIO-independent focused Go test path. Keep workflow YAML unchanged until permissions and review permit.
