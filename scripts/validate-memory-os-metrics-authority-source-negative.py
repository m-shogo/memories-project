#!/usr/bin/env python3
"""Independent reviewed metrics writer/PR source and executable negative proof."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ".github/workflows/reconcile-metrics-scrape-status.yml"
PR = ".github/workflows/reconcile-metrics-scrape-status-pr.yml"
INDEPENDENT = ".github/workflows/metrics-authority-source-negative.yml"
SELF = "scripts/validate-memory-os-metrics-authority-source-negative.py"
CHECKOUT = "uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
SETUP_GO = "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"
SETUP_PY = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_WRITER = "bf2be5f5c50f2193b91e3f46be86ac7d783e58bd"
REVIEWED_PR = "6977ffa544aa2c2df762e76fd7c7e8c263b4795e"
REVIEWED_INDEPENDENT = "dbef991d6c20a405c05ad65e1d64e7dde9b04b96"

def read(path: str) -> str:
    target = ROOT / path
    if target.is_symlink() or not target.is_file():
        raise AssertionError("metrics source substituted: " + path)
    if target.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("metrics source escaped root: " + path)
    return target.read_text(encoding="utf-8")

def blob(s: str) -> str:
    data = s.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

WRITER_REQUIRED = (
    "if: (github.event_name == 'push' || github.event_name == 'schedule' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
    "persist-credentials: true",
    'test "$' + '{GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "$' + '{GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$EVENT_SHA" = "$' + '{GITHUB_SHA:-}"',
    'test "$(git rev-parse HEAD)" = "$EVENT_SHA"',
    "git ls-remote origin refs/heads/so",
    "git push origin HEAD:so",
)
PR_REQUIRED = (
    "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
    "persist-credentials: false",
    'test "$' + '{GITHUB_EVENT_NAME:-}" = "pull_request"',
    'test "$' + '{GITHUB_BASE_REF:-}" = "so"',
    '[[ "$' + '{PR_HEAD_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
)

def policy(s: str, required: tuple, label: str) -> None:
    if any(s.count(action) != 1 for action in (CHECKOUT, SETUP_GO, SETUP_PY)):
        raise AssertionError("metrics " + label + " immutable Actions drift")
    if "actions/checkout@v4" in s or "actions/setup-go@v5" in s or "actions/setup-python@v5" in s:
        raise AssertionError("metrics floating Action regression")
    for marker in required:
        if marker not in s:
            raise AssertionError("metrics " + label + " required marker missing: " + marker)
    if s.count('test -z "$(git status --porcelain)"') != (2 if label == "PR" else 1):
        raise AssertionError("metrics " + label + " clean source/final multiplicity drift")

def negatives(source: str, required: tuple, label: str) -> None:
    for index, marker in enumerate(required):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE", 1)
        if changed == source:
            raise AssertionError("metrics negative unreachable: " + label + str(index))
        try:
            policy(changed, required, label)
        except AssertionError:
            continue
        raise AssertionError("metrics " + label + " source mutation accepted: " + str(index))
    print(f"PASS: metrics {label} source negatives ({len(required)} cases)")

def step(source: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if source.count(marker) != 1:
        raise AssertionError("metrics step missing/duplicated: " + name)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [p for p in (source.find("\n      - name:", start),
                             source.find("\n  reconcile:", start),
                             source.find("\n  validate:", start)) if p >= 0]
    end = min(boundaries) if boundaries else len(source)
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("metrics shell crossed job boundary")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

def identity_runtime(source: str, name: str, cases: tuple) -> None:
    shell = step(source, name)
    head = "a" * 40
    with tempfile.TemporaryDirectory(prefix="metrics-source-") as tmp:
        root = Path(tmp)
        git = root / "git"
        git.write_text("#!/bin/sh\n"
                       "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then echo " + head + "; exit 0; fi\n"
                       "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                       "exit 1\n", encoding="utf-8")
        git.chmod(0o755)
        for event, base, ref, sha, accepted in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       GITHUB_SHA=sha, EVENT_SHA=sha, PR_HEAD_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise AssertionError(f"metrics {name} event/base/ref/SHA drift: {(event, base, ref, sha, result.returncode)}")
    print(f"PASS: metrics {name} actual source shell ({len(cases)} cases)")

def cas_runtime(source: str) -> None:
    shell = step(source, "Commit reconciled authority files")
    head = "a" * 40
    cases = (
        ("noop", head, True, True, 0, 0),
        ("success", head, False, True, 0, 1),
        ("stale", "b" * 40, False, True, 75, 0),
        ("missing", "", False, True, 75, 0),
        ("diff-check", head, False, False, 1, 0),
    )
    fake_git = """#!/usr/bin/env python3
import os
import sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["FAKE_GIT_LOG"]).open("a", encoding="utf-8") as f:
    f.write(" ".join(args) + "\\n")
if args[:2] == ["rev-parse", "HEAD"]:
    print("a" * 40)
elif args[:2] == ["ls-remote", "origin"]:
    print(os.environ["FAKE_REMOTE"] + "\\trefs/heads/so")
elif args[:3] == ["diff", "--cached", "--quiet"]:
    sys.exit(0 if os.environ["FAKE_NOOP"] == "1" else 1)
elif args[:3] == ["diff", "--cached", "--check"]:
    sys.exit(0 if os.environ["FAKE_CHECK"] == "1" else 1)
elif args[0] in ("add", "config", "commit", "push"):
    pass
else:
    sys.exit(92)
"""
    for label, remote, noop, check, exit_code, pushes in cases:
        with tempfile.TemporaryDirectory(prefix="metrics-cas-") as tmp:
            root = Path(tmp)
            git = root / "git"
            git.write_text(fake_git, encoding="utf-8")
            git.chmod(0o755)
            log = root / "git.log"
            log.write_text("", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       FAKE_GIT_LOG=str(log), FAKE_REMOTE=remote,
                       FAKE_NOOP="1" if noop else "0", FAKE_CHECK="1" if check else "0")
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            calls = log.read_text(encoding="utf-8").splitlines()
            if result.returncode != exit_code:
                raise AssertionError(f"metrics CAS {label} unexpected exit {result.returncode}: {result.stderr[-100:]}")
            if sum(line == "push origin HEAD:so" for line in calls) != pushes:
                raise AssertionError("metrics CAS pushed on stale/no-op/invalid source: " + label)
    print(f"PASS: metrics actual publisher CAS/no-op shell ({len(cases)} cases)")

def main() -> None:
    writer = read(WRITER)
    pr = read(PR)
    independent = read(INDEPENDENT)
    for marker in (WRITER, PR, SELF, CHECKOUT, SETUP_PY,
                   "persist-credentials: false", "contents: read",
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("metrics independent CI reachability missing: " + marker)
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise AssertionError("metrics complete independent CI Git blob drift")
    if blob(independent + "\n# synthetic whole-source drift\n") == REVIEWED_INDEPENDENT:
        raise AssertionError("metrics independent CI mutation accepted")
    for label, source, expected in (("writer", writer, REVIEWED_WRITER), ("PR", pr, REVIEWED_PR)):
        if blob(source) != expected:
            raise AssertionError("metrics " + label + " complete reviewed Git blob drift")
        if blob(source + "\n# synthetic whole-source drift\n") == expected:
            raise AssertionError("metrics " + label + " whole-source mutation accepted")
    policy(writer, WRITER_REQUIRED, "writer")
    policy(pr, PR_REQUIRED, "PR")
    negatives(writer, WRITER_REQUIRED, "writer")
    negatives(pr, PR_REQUIRED, "PR")
    head = "a" * 40
    identity_runtime(writer, "Confirm exact source state", (
        ("push", "", "refs/heads/so", head, True),
        ("schedule", "", "refs/heads/so", head, True),
        ("workflow_dispatch", "", "refs/heads/so", head, True),
        ("pull_request", "", "refs/heads/so", head, False),
        ("push", "", "refs/heads/main", head, False),
        ("push", "", "refs/heads/so", "b" * 40, False),
        ("push", "", "refs/heads/so", "A" * 40, False),
        ("push", "", "refs/heads/so", "a" * 39, False),
    ))
    identity_runtime(pr, "Confirm exact clean PR source", (
        ("pull_request", "so", "", head, True),
        ("pull_request", "main", "", head, False),
        ("push", "so", "", head, False),
        ("pull_request", "so", "", "b" * 40, False),
        ("pull_request", "so", "", "A" * 40, False),
        ("pull_request", "so", "", "a" * 39, False),
    ))
    cas_runtime(writer)
    print("PASS: metrics independent source guard; production evidence generated: false")

if __name__ == "__main__":
    main()
