# Supplemental OPS learning — aggregate cross-job step marker failure (2026-11-02)

Append-only subordinate to canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This negative/CI is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection coverage, independent review, final candidate or human promotion authority.

## Material failure

- **symptom:** A new saturation aggregate source-binding negative rejected the unchanged reviewed workflow, failing the exact-source learning CI.
- **observed evidence:** [Autonomous Learning Guard #41453828232](https://github.com/m-shogo/memories-project/actions/runs/41453828232) on code HEAD [`e0c53ccd`](https://github.com/m-shogo/memories-project/commit/e0c53ccda93bd4be9711c59f69ebd0efc402f2f4) completed **FAILURE** at `prove_saturation_aggregate_source_binding`, reporting `saturation aggregate source step boundary drift`. The reviewed `controlled-saturation-repeatability.yml` blob `1f4b20c0` contains **two** `actions/setup-python@a26af69b...` step markers across separate jobs, but exactly **one** after the aggregate-step start.
- **verified root cause:** The first guard counted the aggregate closing marker across the entire YAML file rather than within its owning job/step. The other job's setup-python action was incorrectly treated as a duplicate aggregate boundary.
- **failed approach:** Using workflow-wide uniqueness for a valid repeated YAML step marker, instead of an exact owning-step scope.
- **correction:** [`06de34e1`](https://github.com/m-shogo/memories-project/commit/06de34e142f64fc94ea3969aa1520ad4aa20f6e9) first validates the unique aggregate-step start, then counts the closing setup-python marker only in the suffix after that start. Source-derived checks confirmed global count 2 and aggregate-scoped count 1.
- **recurrence guard:** Retain the scoped marker boundary and ten aggregate ancestry/path/exit mutation controls. Keep the separate publisher array parser and negative suite; a corrected exact-source CI SUCCESS is required before closing this failure.
- **retry condition:** Revisit only if the corrected exact-source CI fails or the reviewed aggregate job/step structure materially changes. Do not repeat global setup-python uniqueness assumptions.

## Material safe progress

- **outcome:** One scoped code correction accepted on `so`, with corrected CI pending. No success is attributed to the failed run.
- **evidence:** Post-correction `so` re-read confirmed the source-scope fix and unchanged ten protected authority blob SHA prefixes.
- **why safe:** Only `scripts/validate-autonomous-learning-system-negative.py` was edited. No writer workflow, production authority, credential, traffic, evidence, readiness or human promotion was touched.
- **reusable mechanism:** Anchor a source marker to its owning job/step before asserting uniqueness; preserve exact-source CI as the arbiter after local source-derived controls.
- **protected authority check:** Production status `d677a1c9` remains `NO_GO`, OPS-P0-007 `dbaa36b0` remains `PREREQUISITES_BLOCKED`, generations `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9` unchanged.

## Next safe target

Confirm the corrected aggregate source-binding and independent aggregate shell error-class tests under read-only exact-source CI. The five post-rebase soak publisher gaps and workflow-write permission blocker remain separately scoped; do not retry unchanged authority. Keep `productionDecision=NO_GO` and human promotion review separate.
