#!/usr/bin/env python3
"""Read-only source and actual PR/writer identity negatives for upload completion load."""
from __future__ import annotations
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-upload-completion-load-authority.yml"
INDEPENDENT = ".github/workflows/upload-completion-load-source-negative.yml"
SELF = "scripts/validate-memory-os-upload-completion-load-source-negative.py"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"

def read(path: str) -> str:
    p = ROOT / path
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("upload completion source missing/substituted: " + path)
    return p.read_text(encoding="utf-8")

def step(source: str, title: str) -> str:
    marker = "      - name: " + title + "\n"
    if source.count(marker) != 1:
        raise AssertionError("upload completion step missing: " + title)
    start = source.index("        run: |\n", source.index(marker)) + len("        run: |\n")
    boundaries = [source.find(marker, start) for marker in ("\n      - name:", "\n  reconcile:", "\n  validate-pr:")]
    end = min((index for index in boundaries if index >= 0), default=len(source))
    lines = source[start:end].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("upload completion indentation drift")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

REQUIRED = (
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
    'git fetch origin so',
    'git push origin HEAD:so',
)
def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("upload completion policy missing: " + marker[:60])
    if source.count(CHECKOUT) != 2 or source.count(SETUP) != 2:
        raise AssertionError("upload completion immutable Actions drift")
    if source.count('test -z "$(git status --porcelain)"') != 3:
        raise AssertionError("upload completion three clean worktree boundaries drift")
    if "actions/checkout@v4" in source or "actions/setup-python@v5" in source:
        raise AssertionError("upload completion floating Action regression")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("upload completion mutation unreachable: " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("upload completion accepted source mutation: " + str(index))
    print(f"PASS: upload completion source mutations ({len(REQUIRED)} cases)")

def identity(source: str, title: str, writer: bool) -> None:
    shell = step(source, title)
    shell = shell.split('echo "SOURCE_SHA=', 1)[0] if writer else shell.split("python -m py_compile", 1)[0]
    head = "a" * 40
    if writer:
        cases = (("push", "", "refs/heads/so", "", head, True),
                 ("workflow_dispatch", "", "refs/heads/so", "", head, True),
                 ("schedule", "", "refs/heads/so", "", head, False),
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
    with tempfile.TemporaryDirectory(prefix="upload-completion-identity-") as temp:
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
                raise AssertionError("upload completion event/base/ref/SHA drift: " + str((title, event, ref, result.returncode)))
    print(f"PASS: upload completion {title} identity shell runtime ({len(cases)} cases)")

def main() -> None:
    publisher = read(PUBLISHER)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("upload completion independent CI reachability drift: " + marker)
    policy(publisher)
    mutations(publisher)
    identity(publisher, "Validate exact PR-head upload completion authority", False)
    identity(publisher, "Capture exact source", True)
    print("PASS: upload completion exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
