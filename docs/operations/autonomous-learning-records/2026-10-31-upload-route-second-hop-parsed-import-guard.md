# Supplemental OPS learning — parsed second-hop Go import-edge authority (2026-10-31)

Append-only operational learning only, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective/request, typed eight-domain non-resurrection, independent-review or human-promotion evidence.

## Material failure mode and executable correction

- **symptom:** The second-hop dependency proof for `httpapi/account_handler.go` accepted the mere presence of quoted paths to `accountdelete`, `epochguard` and `security` anywhere in the source. A line comment could retain the same path string after the executable Go import was replaced.
- **evidence:** Before correction, the test used `f'"{module}/internal/{package}"' in account_source`. A disposable mutation replaces each of the three actual import strings with `example.com/unreviewed` while appending the original quoted path in a `//` comment; the old substring predicate stays true, but the parsed Go import set excludes the missing edge.
- **rootCauseOrUnknown:** Verified source-identity gap: quoted substring presence is not proof of a compiled Go import declaration. This is a static validator failure mode, not a reported production incident.
- **failedApproach:** Binding second-hop Go dependency closure to arbitrary string occurrence rather than the existing conservative Go import parser.
- **correction:** [16037e6](https://github.com/m-shogo/memories-project/commit/16037e6ae511010e76a0a18857feda50cb8de4b5) replaces the substring predicate with `upload_route_local_go_imports(..., include_external=True)` and requires all three exact module-qualified edges.
- **recurrenceGuard:** Three executable comment-spoof negative fixtures, one for each imported package, call the same helper as the real source assertion. The parser's separate block-comment and raw-string guards remain active.
- **retryCondition:** Change this source-edge inventory only after reviewing actual Go imports, preserving equivalent spoof negatives and direct/nested exact-source CI PASS within the existing bounded deadline. Do not retry the known five-subprocess classification, MinIO HTTP 401 or workflow-write permission blocker without their recorded changed prerequisites.

## Material success

- **outcome:** All three second-hop import edges must be present in the parsed executable Go import inventory, not merely quoted in comments.
- **evidence:** Exact-source [Autonomous Learning Guard #41099430928](https://github.com/m-shogo/memories-project/actions/runs/41099430928) for `16037e6ae511010e76a0a18857feda50cb8de4b5` completed **SUCCESS**. Direct and nested canonical negative suite each reported **601** fail-closed CLI cases; 195 fanout synthetic, 1,186 helper ancestor negatives, learning contract, append-only, entry-document and read-only checks PASS. Three new in-process spoof negatives do not increment the separately reported CLI case count.
- **whySafe:** Only the existing read-only Python negative validator changed. No Go runtime source, workflow YAML, MinIO, production credentials/traffic, recovery evidence or promotion authority was touched.
- **reusableMechanism:** Reuse the validated lexical import parser for source-edge claims and test comment spoofing against the exact same guard. Static import identity is not equivalent to independent Push/PR CI reachability.
- **protectedAuthorityCheck:** Code commit `16037e6` changed only `scripts/validate-autonomous-learning-system-negative.py`; canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and all six protected generation/objective/request/evidence/non-resurrection/promotion registries remained unchanged.

## Boundaries and next safe target

The earlier core `httpserver/server.go` → `httpapi` and `httpapi/upload_handler.go` / `httpserver/server_live_test.go` → `upload` checks still use quoted-string presence and need the same parsed-import guard. Complete transitive Go/Python closure, all Push/PR workflow trigger reachability and pre-MinIO independent Go regression proof remain unproven. Canonical learning full-text transport is unavailable; supplemental history cannot satisfy it. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no human-approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain non-resurrection, independent review or human promotion.
