# Supplemental OPS learning — MinIO-first Import API CI is not independent Go proof (2026-10-30)

Append-only supplemental history under mandatory `contracts/operations/autonomous-learning-system.json`. Canonical learning authority remains unchanged and blob-SHA verified, not fully transferred. **This record cannot satisfy production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review or human promotion gates.**

## Material failure — missing known external dependency in prewrite classification

- **symptom:** The conservative prewrite direct-workflow classifier recognized both Upload Route reconciler workflows as external MinIO-dependent, but omitted `.github/workflows/import-api-security-slice.yml`. A future Go-only path with only that workflow matching could be classified `BOUNDED_DIRECT_MATCH_ONLY` despite Go tests being gated by external MinIO startup.
- **evidence:** At source `013ee3c6`, `KNOWN_EXTERNAL_BLOCKED_WORKFLOWS` contained only the two Upload Route reconciler workflows. The actual `import-api-security-slice.yml` has a broad `services/import-api/**` Push/PR trigger and a `Start MinIO` step before Go setup, vet and `go test -race ./...`. This is a prospective CI-classification gap, not proof that all Go CI routes fail or that any production test ran.
- **rootCauseOrUnknown:** Verified: incomplete known-external-workflow inventory in the conservative direct fanout classifier.
- **failedApproach:** Assuming the two explicitly reconciler-named workflows exhaust MinIO-first CI coupling.
- **correction:** [`47568d89`](https://github.com/m-shogo/memories-project/commit/47568d89b3c47bb50e737c9fbc0920e77689a383) adds `import-api-security-slice.yml` to the external-dependent set and a classifier self-test. [`2e396d80`](https://github.com/m-shogo/memories-project/commit/2e396d806293377c09bdc49bb3b72945d28d75fb) adds an actual CLI negative using the real workflow source as the sole workflow in a disposable checkout and a Go-only `internal/httpserver/server.go` path.
- **recurrenceGuard:** The CI-bound test requires the real workflow to retain its observed MinIO-before-Go-test order and the actual prewrite CLI to exit 2 with `BLOCKED_KNOWN_EXTERNAL_DEPENDENCY` and exactly one matching workflow. No workflow YAML was modified.
- **retryCondition:** Reclassify only after reviewed workflow source actually decouples focused Go tests from MinIO, all transitive Go/Python inputs and Push/PR trigger coverage are independently validated, exact-source CI passes and protected authorities remain unchanged. Do not retry the unchanged Quay MinIO HTTP 401 or workflow-write permission blocker.

## Material success — bounded guard, not CI closure

- **outcome:** The missing known external-dependency classification is now encoded in a read-only executable guard and a real-workflow CLI negative. Exact-source CI for `2e396d80` was **pending** at record creation, so this is not a claim of CI success.
- **evidence:** The actual Import API Security Slice YAML ordering and path filters, the new classifier entry and synthetic/direct CLI test source.
- **whySafe:** Only read-only Python audit/negative scripts and append-only supplemental history changed. No Go service code, workflow YAML, MinIO deployment, credential, traffic, recovery evidence or promotion authority changed.
- **reusableMechanism:** Classify workflow reachability separately from dependency independence, and bind known external startup ordering to an actual workflow-source CLI negative before making any CI coverage claim.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged through `2e396d80`, including canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six recovery registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, approved current recovery objective 0, executable reviewed request 0, request-bound evidence 0, complete typed eight-domain records 0, final candidate 0. Human promotion remains separate and non-automatic.

## Next safe target

Verify exact-source CI and persist independent success proof. Continue dependency-closed Go-only Focused Upload Route CI design before MinIO startup without changing workflow YAML until write authority and trigger closure are reviewed.
