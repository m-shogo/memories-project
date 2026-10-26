#!/usr/bin/env python3
"""Independent read-only observability-access authority source and runtime negatives."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-observability-access.yml"
INDEPENDENT = ".github/workflows/observability-access-source-negative.yml"
SELF = "scripts/validate-memory-os-observability-access-source-negative.py"
CHECKOUT = "uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "21753278254d4152e29519125f19db03eef6f5cf"

def read(path: str) -> str:
    p = ROOT / path
    if p.is_symlink() or not p.is_file():
        raise AssertionError("load missing source substituted: " + path)
    if p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("load missing source escaped root")
    return p.read_text(encoding="utf-8")

def blob(s: str) -> str:
    data = s.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

REQUIRED = (
    "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
    "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
    "persist-credentials: false",
    "persist-credentials: true",
    'test "$' + '{GITHUB_EVENT_NAME:-}" = "pull_request"',
    'test "$' + '{GITHUB_BASE_REF:-}" = "so"',
    '[[ "$' + '{PR_HEAD_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
    'test "$' + '{GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "$' + '{GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$' + '{GITHUB_SHA:-}"',
    "git push origin HEAD:so",
)

def policy(s: str) -> None:
    if s.count(CHECKOUT) != 2 or s.count(SETUP) != 2:
        raise AssertionError("observability-access immutable Actions drift")
    if s.count("persist-credentials: false") != 1 or s.count("persist-credentials: true") != 1:
        raise AssertionError("observability-access credential separation drift")
    if "actions/checkout@v4" in s or "actions/setup-python@v5" in s:
        raise AssertionError("observability-access floating Action regression")
    for marker in REQUIRED:
        if marker not in s:
            raise AssertionError("observability-access required source marker absent: " + marker)
    if s.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("observability-access source/final clean multiplicity drift")

def step(source: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if source.count(marker) != 1:
        raise AssertionError("observability-access step missing/duplicated: " + name)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [p for p in (source.find("\n      - name:", start),
                             source.find("\n  reconcile:", start),
                             source.find("\n  validate-pr:", start)) if p >= 0]
    end = min(boundaries) if boundaries else len(source)
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("observability-access shell crossed job boundary")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

def runtime(source: str, name: str, cases: tuple) -> None:
    shell = step(source, name)
    head = "a" * 40
    with tempfile.TemporaryDirectory(prefix="load-missing-source-") as tmp:
        root = Path(tmp)
        git = root / "git"
        git.write_text("#!/bin/sh\n"
                       "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then echo " + head + "; exit 0; fi\n"
                       "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                       "exit 1\n", encoding="utf-8")
        git.chmod(0o755)
        envfile = root / "env"
        for event, base, ref, sha, accepted in cases:
            envfile.write_text("", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_ENV=str(envfile), GITHUB_EVENT_NAME=event,
                       GITHUB_BASE_REF=base, GITHUB_REF=ref, GITHUB_SHA=sha, PR_HEAD_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise AssertionError(f"observability-access actual shell source drift: {name} {(event, base, ref, sha, result.returncode)}")
    print(f"PASS: observability-access {name} actual event/base/ref/SHA shell ({len(cases)} cases)")

def cas_runtime(source: str) -> None:
    """Execute the real blocker publisher commit/CAS shell in a disposable fake-Git sandbox."""
    shell = step(source, "Commit reconciled authority files")
    head = "a" * 40
    other = "b" * 40
    cases = (
        ("noop", head, True, True, 0, 0),
        ("success", head, False, True, 0, 1),
        ("stale-remote", other, False, True, 75, 0),
        ("missing-remote", "", False, True, 75, 0),
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
elif args[0] in ("add", "config", "commit", "fetch", "push"):
    pass
else:
    sys.exit(92)
"""
    for label, remote, noop, check, exit_code, pushes in cases:
        with tempfile.TemporaryDirectory(prefix="load-missing-cas-") as tmp:
            root = Path(tmp)
            git = root / "git"
            git.write_text(fake_git, encoding="utf-8")
            git.chmod(0o755)
            log = root / "git.log"
            log.write_text("", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       SOURCE_SHA=head, FAKE_GIT_LOG=str(log), FAKE_REMOTE=remote,
                       FAKE_NOOP="1" if noop else "0", FAKE_CHECK="1" if check else "0")
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            calls = log.read_text(encoding="utf-8").splitlines()
            if result.returncode != exit_code:
                raise AssertionError(f"observability-access CAS {label}: unexpected exit {result.returncode}: {result.stderr[-100:]}")
            if sum(line == "push origin HEAD:so" for line in calls) != pushes:
                raise AssertionError("observability-access CAS pushed on stale/no-op/invalid source: " + label)
            if label == "noop" and any(line.startswith("commit ") for line in calls):
                raise AssertionError("observability-access no-op committed")
    print(f"PASS: observability-access actual publisher CAS/no-op shell ({len(cases)} cases)")

def main() -> None:
    source = read(PUBLISHER)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, SELF, CHECKOUT, SETUP, "persist-credentials: false",
                   "contents: read", 'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("observability-access independent CI reachability missing: " + marker)
    if blob(source) != REVIEWED_PUBLISHER:
        raise AssertionError("observability-access complete publisher Git blob drift")
    if blob(source + "\n# synthetic whole-source drift\n") == REVIEWED_PUBLISHER:
        raise AssertionError("observability-access whole-source mutation accepted")
    policy(source)
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE", 1)
        if changed == source:
            raise AssertionError("observability-access negative unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("observability-access source mutation accepted: " + str(index))
    print(f"PASS: observability-access publisher reviewed blob and {len(REQUIRED)} source negatives")
    head = "a" * 40
    runtime(source, "Confirm exact clean PR authority source", (
        ("pull_request", "so", "", head, True),
        ("pull_request", "main", "", head, False),
        ("push", "so", "", head, False),
        ("pull_request", "so", "", "b" * 40, False),
        ("pull_request", "so", "", "A" * 40, False),
        ("pull_request", "so", "", "a" * 39, False),
    ))
    runtime(source, "Confirm exact clean authority source", (
        ("push", "", "refs/heads/so", head, True),
        ("workflow_dispatch", "", "refs/heads/so", head, True),
        ("schedule", "", "refs/heads/so", head, False),
        ("pull_request", "", "refs/heads/so", head, False),
        ("push", "", "refs/heads/main", head, False),
        ("push", "", "refs/heads/so", "b" * 40, False),
        ("push", "", "refs/heads/so", "A" * 40, False),
        ("push", "", "refs/heads/so", "a" * 39, False),
    ))
    cas_runtime(source)
    print("PASS: independent read-only observability-access source guard; production evidence generated: false")

if __name__ == "__main__":
    main()
