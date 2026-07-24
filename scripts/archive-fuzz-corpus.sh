#!/usr/bin/env bash
# Grow the committed fuzz seed corpus.
#
# Go keeps coverage-interesting inputs in the build cache, where they are
# invisible to everyone else and vanish with the cache. Only inputs that
# actually fail get written to testdata/fuzz automatically. That meant every
# interesting input this project's fuzzers had ever found was thrown away, and
# a regression could reintroduce a bug the fuzzer had already explored past.
#
# This script runs the fuzzers with a cache directory it can read, then copies
# the new entries into each package's testdata/fuzz. Committed seeds are
# replayed by every plain `go test`, so they become real regression tests.
#
# Usage:
#   scripts/archive-fuzz-corpus.sh [fuzztime]     # default 60s
set -euo pipefail

FUZZTIME="${1:-60s}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE_DIR="$(mktemp -d)"
trap 'rm -rf "$CACHE_DIR"' EXIT

# package-relative-path:FuzzFunctionName
TARGETS=(
  "internal/adapters/genericcsv:FuzzParserNeverPanicsOrExpandsLimits"
  "internal/appleauth:FuzzParseCompactTokenNeverPanics"
)

MODULE="github.com/m-shogo/memories-project/services/import-api"

for target in "${TARGETS[@]}"; do
  package="${target%%:*}"
  fuzzer="${target##*:}"
  echo "fuzzing ${package} ${fuzzer} for ${FUZZTIME}"
  docker run --rm \
    -v "${REPO_ROOT}:/src" \
    -v memory-os-gomod:/go/pkg/mod \
    -v "${CACHE_DIR}:/gocache" \
    -w /src/services/import-api \
    -e GOCACHE=/gocache/build \
    golang:1.23 \
    go test -run='^$' -fuzz="${fuzzer}" -fuzztime="${FUZZTIME}" -timeout=30m "./${package}"

  source_dir="${CACHE_DIR}/build/fuzz/${MODULE}/${package}/${fuzzer}"
  target_dir="${REPO_ROOT}/services/import-api/${package}/testdata/fuzz/${fuzzer}"
  if [ ! -d "$source_dir" ]; then
    echo "  no new interesting inputs"
    continue
  fi
  mkdir -p "$target_dir"
  before="$(find "$target_dir" -type f | wc -l | tr -d ' ')"
  cp "$source_dir"/* "$target_dir"/
  after="$(find "$target_dir" -type f | wc -l | tr -d ' ')"
  echo "  corpus: ${before} -> ${after} entries"
done

echo
echo "Committed seeds are replayed by plain 'go test'. Run the suite before committing:"
echo "  scripts/dev-test.sh -count=1 ./..."
