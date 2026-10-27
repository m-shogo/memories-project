#!/usr/bin/env python3
"""Fail-closed executable-source and event/ref negatives for review independence CI."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/production-equivalent-environment-review-independence.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "56d15ffd78c816ccecd0ff27c9e159f78c913bf4"
REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("self trigger", '      - "scripts/validate-memory-os-production-equivalent-environment-review-independence-workflow-negative.py"\n', 2),
    ("checkout SHA", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", 2),
    ("setup SHA", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("publisher credentials", "          persist-credentials: true\n", 1),
    ("PR base", '          test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR SHA format", '          [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("publisher branch", '          test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("publisher event", '          [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]\n', 1),
    ("publisher scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", 1),
    ("self execution", "\n          python scripts/validate-memory-os-production-equivalent-environment-review-independence-workflow-negative.py\n", 2),
    ("retry self execution", "            python scripts/validate-memory-os-production-equivalent-environment-review-independence-workflow-negative.py\n", 1),
    ("writer SHA", '          expected="${GITHUB_SHA:-}"\n', 1),
    ("PR SHA", '          expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("HEAD check", '          test "$(git rev-parse HEAD)" = "$expected"\n', 2),
    ("write scope", "      contents: write\n", 1),
    ("retry latest", "            git reset --hard origin/so\n", 1),
    ("redacted diagnostic", "              'output': 'REDACTED: environment review-independence validation failed; raw output withheld',\n", 1),
    ("suppressed CI log", '          printf "Environment review-independence validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', 1),
    ("no raw diagnostic tail", "text[-12000:]", 0),
    ("no raw CI log", '          cat "$log"\n', 0),
)


def validate(source: str, *, check_blob: bool = True) -> None:
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit("review independence CI workflow source drift: " + label)
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("review independence CI complete workflow source drift")


def prove_branch_guards_runtime() -> None:
    pr = REQUIRED[6][1].strip()
    push = REQUIRED[8][1].strip()
    cases = (
        ("PR so", pr, "GITHUB_BASE_REF", "so", True),
        ("PR main", pr, "GITHUB_BASE_REF", "main", False),
        ("PR missing", pr, "GITHUB_BASE_REF", "", False),
        ("push so", push, "GITHUB_REF", "refs/heads/so", True),
        ("push main", push, "GITHUB_REF", "refs/heads/main", False),
        ("push tag", push, "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("review independence CI runtime branch guard drift: " + label)
    print("PASS: review independence CI PR/push branch guard runtime (6 cases)")



def prove_diagnostic_redaction_runtime(source: str) -> None:
    """Run the actual inline diagnostic writer in an isolated temporary directory."""
    start, end = "          python - <<'PY'\n", "          PY\n"
    if source.count(start) != 1 or source.count(end) != 1:
        raise SystemExit("review independence diagnostic writer is not uniquely reachable")
    inline = source.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="semantic-eligibility-diagnostic-") as directory:
        env = os.environ.copy()
        env.update({"SOURCE_SHA": "e" * 40, "VALIDATION_EXIT_CODE": "23",
                    "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_REVIEW"})
        result = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                capture_output=True, text=True, check=False)
        if result.returncode:
            raise SystemExit("review independence isolated diagnostic failed: " + result.stderr[:500])
        output = Path(directory) / "docs/fixtures/memory-os-operability/production-equivalent-environment-review-independence-diagnostic.last.json"
        raw = output.read_text(encoding="utf-8")
        value = json.loads(raw)
        if value.get("output") != "REDACTED: environment review-independence validation failed; raw output withheld":
            raise SystemExit("review independence diagnostic persisted raw validator output")
        if value.get("sourceCommitSha") != "e" * 40 or value.get("exitCode") != 23:
            raise SystemExit("review independence diagnostic source/exit binding drift")
        for field in ("containsSecrets", "generationCreated", "reviewEvidenceCreated", "productionEvidence", "productionReady"):
            if value.get(field) is not False:
                raise SystemExit("review independence diagnostic evidence/readiness drift: " + field)
        if "CANARY_DO_NOT_PERSIST_REVIEW" in raw:
            raise SystemExit("review independence diagnostic persisted synthetic canary")
    print("PASS: review independence isolated diagnostic redaction (1 runtime case)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_branch_guards_runtime()
    prove_diagnostic_redaction_runtime(source)
    cases = (
        ("PR target", REQUIRED[0][1], "  pull_request:\n    paths:\n"),
        ("self trigger", REQUIRED[1][1], ""),
        ("checkout floating", REQUIRED[2][1], "uses: actions/checkout@v4"),
        ("setup floating", REQUIRED[3][1], "uses: actions/setup-python@v5"),
        ("PR credentials", REQUIRED[4][1], "          persist-credentials: true\n"),
        ("writer credentials", REQUIRED[5][1], ""),
        ("PR base", REQUIRED[6][1], ""),
        ("SHA format", REQUIRED[7][1], '          test -n "$expected"\n'),
        ("publisher branch", REQUIRED[8][1], ""),
        ("publisher event", REQUIRED[9][1], ""),
        ("publisher scope", REQUIRED[10][1], "    if: github.event_name != 'pull_request'\n"),
        ("self execution", REQUIRED[11][1], ""),
        ("retry self execution", REQUIRED[12][1], ""),
        ("writer SHA", REQUIRED[13][1], '          expected="${{ github.sha }}"\n'),
        ("PR SHA", REQUIRED[14][1], '          expected="${GITHUB_SHA:-}"\n'),
        ("HEAD check", REQUIRED[15][1], ""),
        ("write scope", REQUIRED[16][1], "      contents: read\n"),
        ("retry latest", REQUIRED[17][1], ""),
        ("raw diagnostic", REQUIRED[18][1], "              'output': Path('/tmp/production-equivalent-environment-review-independence.log').read_text(),\n"),
        ("raw CI log", REQUIRED[19][1], '          cat "$log"\n'),
        ("missing redaction", REQUIRED[18][1], ""),
        ("inserted Action", "      - name: Capture exact review-independence authority source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact review-independence authority source\n"),
        ("inserted shell", "      - name: Capture exact review-independence authority source\n", "      - run: echo unreviewed\n      - name: Capture exact review-independence authority source\n"),
    )
    blob_only = {"inserted Action", "inserted shell"}
    if len(cases) != 23 or sum(label in blob_only for label, _, _ in cases) != 2:
        raise SystemExit("review independence CI workflow negative inventory drift")
    for label, old, new in cases:
        if old not in source:
            raise SystemExit("review independence CI negative fixture missing: " + label)
        mutated = source.replace(old, new, 1)
        if mutated == source:
            raise SystemExit("review independence CI negative fixture unchanged: " + label)
        try:
            validate(mutated, check_blob=label in blob_only)
        except SystemExit:
            continue
        raise SystemExit("review independence CI accepted unreviewed mutation: " + label)
    print(f"PASS: review independence CI workflow source admission ({len(cases) - 2} semantic anchor + 2 blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
