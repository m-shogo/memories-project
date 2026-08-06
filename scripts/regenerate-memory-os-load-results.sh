#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$repo_root" ]]; then
  echo "ERROR: run inside the memories-project git checkout" >&2
  exit 1
fi
cd "$repo_root"

branch="$(git branch --show-current)"
if [[ "$branch" != "so" ]]; then
  echo "ERROR: expected branch so, got: $branch" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: worktree must be clean before generating evidence" >&2
  git status --short >&2
  exit 1
fi

source_sha="$(git rev-parse HEAD)"
origin_sha="$(git rev-parse origin/so 2>/dev/null || true)"
if [[ -n "$origin_sha" && "$source_sha" != "$origin_sha" ]]; then
  echo "ERROR: HEAD must equal origin/so before generating evidence" >&2
  echo "HEAD:      $source_sha" >&2
  echo "origin/so: $origin_sha" >&2
  exit 1
fi

result_path="docs/fixtures/memory-os-operability/load-results.sample.v1.json"
result_abs="$repo_root/$result_path"
result_dir="$(dirname "$result_abs")"
if [[ ! -d "$result_dir" ]]; then
  echo "ERROR: load-results directory is missing: $result_dir" >&2
  exit 1
fi

echo "Generating load results from source commit: $source_sha"
(
  cd services/import-api
  # go test executes the package binary from internal/loadtest, so a path
  # relative to services/import-api is not stable. Always pass the absolute
  # repository-root destination.
  MEMORY_OS_LOAD_RESULTS_PATH="$result_abs" \
  MEMORY_OS_COMMIT_SHA="$source_sha" \
    go test ./internal/loadtest -run '^TestWriteLoadResultsFixture$' -count=1
)

python scripts/validate-memory-os-load.py

echo
echo "Generated: $result_path"
echo "Source commit recorded in fixture: $source_sha"
echo
echo "Review before committing:"
echo "  git diff -- $result_path"
echo
echo "Then commit and push only the regenerated evidence:"
echo "  git add $result_path"
echo "  git commit -m 'test(load): regenerate results after contract hardening'"
echo "  git push origin so"
