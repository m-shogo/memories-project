#!/usr/bin/env python3
"""Independent exact-source and event/SHA negative checks for incident control authority."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-incident-control-authority.yml"
INDEPENDENT = ".github/workflows/incident-control-authority-source-negative.yml"
SELF = "scripts/validate-memory-os-incident-control-authority-source-negative.py"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PUBLISHER = "ba7f30a04b9c81142a896e3fcab95d2f656cdffb"
REVIEWED_INDEPENDENT = "efbb317ad48d26d5424ae784843cb9462575d564"

def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def require_reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("incident authority " + label + " complete Git blob drift")

def reviewed_blob_negatives(publisher: str, independent: str) -> None:
    require_reviewed_source(publisher, REVIEWED_PUBLISHER, "publisher")
    require_reviewed_source(independent, REVIEWED_INDEPENDENT, "independent CI")
    for label, original, expected in (
        ("publisher", publisher, REVIEWED_PUBLISHER),
        ("independent CI", independent, REVIEWED_INDEPENDENT),
    ):
        try:
            require_reviewed_source(original + "\n# synthetic source drift\n", expected, label)
        except AssertionError:
            continue
        raise AssertionError("incident authority reviewed Git blob accepted synthetic source drift: " + label)
    print("PASS: incident authority publisher and independent CI complete Git blob source negatives (2 cases)")

def read(path: str) -> str:
    p = ROOT / path
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("incident authority source missing/substituted: " + path)
    return p.read_text(encoding="utf-8")

def step(source: str, title: str) -> str:
    marker = "      - name: " + title + "\n"
    if source.count(marker) != 1:
        raise AssertionError("incident authority source step missing: " + title)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    end = source.find("\n      - name:", start)
    lines = source[start:end if end >= 0 else len(source)].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("incident authority step indentation drift")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

REQUIRED = (
    "  pull_request:\n    branches:\n      - so\n",
    "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
    "github.ref == 'refs/heads/so'",
    "persist-credentials: false",
    "persist-credentials: true",
    'test "${GITHUB_EVENT_NAME:-}" = "pull_request"',
    'test "${GITHUB_BASE_REF:-}" = "so"',
    '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
    'test "${GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
    'remote_sha="$(git ls-remote origin refs/heads/so',
)
def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("incident authority policy missing: " + marker[:65])
    if source.count(CHECKOUT) != 2 or source.count(SETUP) != 2:
        raise AssertionError("incident authority immutable Actions drift")
    if source.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("incident authority all three clean-worktree boundaries required")
    for forbidden in ("actions/checkout@v4", "actions/setup-python@v5"):
        if forbidden in source:
            raise AssertionError("incident authority floating Actions regression")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("incident authority mutation unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("incident authority mutation accepted: " + str(index))
    print(f"PASS: incident authority source mutations ({len(REQUIRED)} cases)")

def identity(source: str, title: str, writer: bool) -> None:
    shell = step(source, title)
    head = "a" * 40
    if writer:
        cases = (("push", "", "refs/heads/so", "", head, True),
                 ("schedule", "", "refs/heads/so", "", head, True),
                 ("workflow_dispatch", "", "refs/heads/so", "", head, True),
                 ("pull_request", "", "refs/heads/so", "", head, False),
                 ("push", "", "refs/heads/main", "", head, False),
                 ("push", "", "refs/heads/so", "", "b" * 40, False),
                 ("push", "", "refs/heads/so", "", "A" * 40, False),
                 ("push", "", "refs/heads/so", "", "a" * 39, False))
    else:
        cases = (("pull_request", "so", "", head, "", True),
                 ("pull_request", "main", "", head, "", False),
                 ("push", "so", "", head, "", False),
                 ("pull_request", "so", "", "b" * 40, "", False),
                 ("pull_request", "so", "", "A" * 40, "", False),
                 ("pull_request", "so", "", "a" * 39, "", False))
    with tempfile.TemporaryDirectory(prefix="incident-authority-source-") as temp:
        root = Path(temp)
        stub = root / "git"
        stub.write_text("#!/bin/sh\n"
                        "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                        "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                        "exit 1\n", encoding="utf-8")
        stub.chmod(0o755)
        for event, base, ref, pr_sha, sha, allowed in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != allowed:
                raise AssertionError("incident authority event/base/ref/SHA shell drift: " + str((title, event, ref, result.returncode)))
    print(f"PASS: incident authority {title} event/ref/SHA shell runtime ({len(cases)} cases)")

def main() -> None:
    publisher = read(PUBLISHER)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("incident authority independent CI reachability drift: " + marker)
    reviewed_blob_negatives(publisher, independent)
    policy(publisher)
    mutations(publisher)
    identity(publisher, "Confirm exact clean PR authority source", False)
    identity(publisher, "Confirm exact clean authority source", True)
    print("PASS: incident control authority exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
