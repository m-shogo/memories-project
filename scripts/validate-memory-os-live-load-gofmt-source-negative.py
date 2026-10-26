#!/usr/bin/env python3
"""Read-only reviewed gofmt publisher source, negative, and shell runtime proof."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-live-load-gofmt.yml"
INDEPENDENT = ".github/workflows/live-load-gofmt-source-negative.yml"
SELF = "scripts/validate-memory-os-live-load-gofmt-source-negative.py"
CHECKOUT = "uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
SETUP_GO = "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"
REVIEWED_PUBLISHER = "0dab671f968cf5bb7033a89f19a8e851363979dc"
REVIEWED_INDEPENDENT = "e9a41bf00b8ccb6bfba02b32e56f7b2ae5b079e2"

def read(path: str) -> str:
    target = ROOT / path
    if target.is_symlink() or not target.is_file():
        raise AssertionError("gofmt source substituted: " + path)
    if target.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("gofmt source escaped root: " + path)
    return target.read_text(encoding="utf-8")

def blob(source: str) -> str:
    data = source.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

REQUIRED = (
    "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
    "persist-credentials: false",
    "persist-credentials: true",
    'test "$' + '{GITHUB_BASE_REF:-}" = "so"',
    '[ "$' + '{PR_HEAD_SHA:-}" =~ ^[0-9a-f]{40}$ ]',
    "github.event_name == 'push' || github.event_name == 'workflow_dispatch'",
    "github.ref == 'refs/heads/so'",
    'test "$' + '{GITHUB_REF:-}" = "refs/heads/so"',
    'test "$(git rev-parse HEAD)" = "$' + '{GITHUB_SHA:-}"',
    "git push origin HEAD:so",
)

def policy(source: str) -> None:
    if source.count(CHECKOUT) != 2 or source.count(SETUP_GO) != 2:
        raise AssertionError("gofmt immutable Actions drift")
    if source.count("persist-credentials: false") != 1 or source.count("persist-credentials: true") != 1:
        raise AssertionError("gofmt credential separation drift")
    if "actions/checkout@v4" in source or "actions/setup-go@v5" in source:
        raise AssertionError("gofmt floating Action regression")
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("gofmt source marker missing: " + marker)
    if source.count("github.ref == 'refs/heads/so'") != 2:
        raise AssertionError("gofmt writer ref scope multiplicity drift")
    if source.count('test -z "$(git status --porcelain)"') != 4:
        raise AssertionError("gofmt clean source/final multiplicity drift")

def step(source: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if source.count(marker) != 1:
        raise AssertionError("gofmt step missing/duplicated: " + name)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [p for p in (source.find("\n      - name:", start),
                             source.find("\n  format:", start),
                             source.find("\n  validate-pr:", start)) if p >= 0]
    end = min(boundaries) if boundaries else len(source)
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("gofmt shell extraction crossed job boundary")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

def runtime(source: str, name: str, cases: tuple) -> None:
    shell = step(source, name)
    head = "a" * 40
    with tempfile.TemporaryDirectory(prefix="gofmt-source-") as tmp:
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
                raise AssertionError(f"gofmt actual shell admission drift: {name}: {(event, base, ref, sha, result.returncode)}")
            if accepted and name == "Capture exact source" and envfile.read_text() != "SOURCE_SHA=" + head + "\n":
                raise AssertionError("gofmt source capture drift")
    print(f"PASS: gofmt {name} actual event/base/ref/SHA shell ({len(cases)} cases)")

def cas_runtime(source: str) -> None:
    """Execute the actual publisher CAS shell against disposable fake Git."""
    shell = step(source, "Commit formatting authority")
    head = "a" * 40
    other = "b" * 40
    cases = (
        ("noop", head, head, head, True, True, 0, 0),
        ("success", head, head, head, False, True, 0, 1),
        ("stale-first", head, other, head, False, True, 75, 0),
        ("stale-second", head, head, other, False, True, 75, 0),
        ("stale-head", other, head, head, False, True, 75, 0),
        ("diff-check", head, head, head, False, False, 1, 0),
    )
    fake_git = """#!/usr/bin/env python3
import os
import sys
from pathlib import Path
args = sys.argv[1:]
log = Path(os.environ["FAKE_GIT_LOG"])
with log.open("a", encoding="utf-8") as f:
    f.write(" ".join(args) + "\\n")
count = Path(os.environ["FAKE_GIT_COUNT"])
if args[:2] == ["fetch", "origin"]:
    count.write_text(str(int(count.read_text()) + 1))
elif args[:2] == ["rev-parse", "HEAD"]:
    print(os.environ["FAKE_HEAD"])
elif args[:2] == ["rev-parse", "origin/so"]:
    print(os.environ["FAKE_REMOTE_FIRST"] if int(count.read_text()) < 2 else os.environ["FAKE_REMOTE_SECOND"])
elif args[:3] == ["diff", "--cached", "--quiet"]:
    sys.exit(0 if os.environ["FAKE_NOOP"] == "1" else 1)
elif args[:3] == ["diff", "--cached", "--check"]:
    sys.exit(0 if os.environ["FAKE_CHECK"] == "1" else 1)
elif args[0] in ("add", "config", "commit", "push"):
    pass
else:
    sys.exit(92)
"""
    for label, local, first, second, noop, check, exit_code, pushes in cases:
        with tempfile.TemporaryDirectory(prefix="gofmt-cas-") as tmp:
            root = Path(tmp)
            git = root / "git"
            git.write_text(fake_git, encoding="utf-8")
            git.chmod(0o755)
            log = root / "git.log"
            count = root / "count"
            log.write_text("", encoding="utf-8")
            count.write_text("0", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       SOURCE_SHA=head, FAKE_GIT_LOG=str(log), FAKE_GIT_COUNT=str(count),
                       FAKE_HEAD=local, FAKE_REMOTE_FIRST=first, FAKE_REMOTE_SECOND=second,
                       FAKE_NOOP="1" if noop else "0", FAKE_CHECK="1" if check else "0")
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            calls = log.read_text(encoding="utf-8").splitlines()
            if result.returncode != exit_code:
                raise AssertionError(f"gofmt CAS runtime {label}: unexpected exit {result.returncode}: {result.stderr[-100:]}")
            if sum(line == "push origin HEAD:so" for line in calls) != pushes:
                raise AssertionError("gofmt CAS runtime pushed on stale/no-op/invalid source: " + label)
            if label in ("stale-first", "stale-head") and any(line.startswith("add ") for line in calls):
                raise AssertionError("gofmt CAS wrote before stale-source rejection: " + label)
            if label == "stale-second" and any(line.startswith("push ") for line in calls):
                raise AssertionError("gofmt CAS pushed after concurrent source advance")
    print(f"PASS: gofmt actual publisher CAS/no-op/rollback-safe shell ({len(cases)} cases)")

def main() -> None:
    source = read(PUBLISHER)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, SELF, CHECKOUT, "persist-credentials: false",
                   "contents: read", 'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("gofmt independent CI reachability missing: " + marker)
    if blob(source) != REVIEWED_PUBLISHER:
        raise AssertionError("gofmt complete publisher Git blob drift")
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise AssertionError("gofmt complete independent CI Git blob drift")
    if blob(independent + "\n# synthetic whole-source drift\n") == REVIEWED_INDEPENDENT:
        raise AssertionError("gofmt independent CI whole-source mutation accepted")
    if blob(source + "\n# synthetic whole-source drift\n") == REVIEWED_PUBLISHER:
        raise AssertionError("gofmt whole-source mutation accepted")
    policy(source)
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE", 1)
        if changed == source:
            raise AssertionError("gofmt negative unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("gofmt mutation accepted: " + str(index))
    print(f"PASS: gofmt complete Git blob and {len(REQUIRED)} publisher source negatives")
    head = "a" * 40
    runtime(source, "Verify exact clean PR source", (
        ("pull_request", "so", "", head, True),
        ("pull_request", "main", "", head, False),
        ("push", "so", "", head, False),
        ("pull_request", "so", "", "b" * 40, False),
        ("pull_request", "so", "", "A" * 40, False),
        ("pull_request", "so", "", "a" * 39, False),
    ))
    runtime(source, "Capture exact source", (
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
    print("PASS: read-only gofmt source guard; production evidence generated: false")

if __name__ == "__main__":
    main()
