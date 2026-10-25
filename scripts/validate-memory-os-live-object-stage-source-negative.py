#!/usr/bin/env python3
"""Independent exact-source event/branch/SHA runtime proof for live object diagnostics."""
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-live-object-stage-diagnostics.yml"
INDEPENDENT = ".github/workflows/live-object-stage-source-negative.yml"
SELF = "scripts/validate-memory-os-live-object-stage-source-negative.py"
REVIEWED_PUBLISHER = "7df80744055bd48c4dd7e87137109178d1c1f185"
REVIEWED_INDEPENDENT = "104cea3178b0f03407bd1c1e0bdcccc6bc65d6d5"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP_PY = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
SETUP_GO = "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"

def source(path):
    p = ROOT / path
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise SystemExit("live object stage source missing or substituted: " + path)
    return p.read_text(encoding="utf-8")

def blob(value):
    raw = value.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

REQUIRED = (
    "  pull_request:\n    branches:\n      - so\n",
    "  push:\n    branches:\n      - so\n",
    "github.base_ref == 'so'",
    "github.ref == 'refs/heads/so'",
    "persist-credentials: false",
    "persist-credentials: true",
    'test "${GITHUB_BASE_REF:-}" = "so"',
    'test "${GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
    'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
    "git ls-remote origin refs/heads/so",
    'if [[ "$remote_sha" != "$SOURCE_SHA" ]]',
    "git push origin HEAD:so",
)

def policy(text):
    for marker in REQUIRED:
        if marker not in text:
            raise AssertionError("live object stage policy missing: " + marker[:65])
    if any(text.count(action) != 2 for action in (CHECKOUT, SETUP_PY, SETUP_GO)):
        raise AssertionError("live object stage immutable Actions drift")
    if any(marker in text for marker in ("checkout@v4", "setup-python@v5", "setup-go@v5")):
        raise AssertionError("live object stage floating Actions regression")

def negatives(text):
    for index, marker in enumerate(REQUIRED):
        if text.count(marker) != 1:
            raise AssertionError("live object stage mutation marker multiplicity drift: " + str(index))
        changed = text.replace(marker, "REMOVED_NEGATIVE", 1)
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("live object stage source accepted mutation " + str(index))
    for action in (CHECKOUT, SETUP_PY, SETUP_GO):
        try:
            policy(text.replace(action, "uses: actions/checkout@v4", 1))
        except AssertionError:
            continue
        raise AssertionError("live object stage floating Action accepted")
    print("PASS: live object stage source negative mutations (18 cases)")

def step(text, title):
    marker = "      - name: " + title + "\n"
    if text.count(marker) != 1:
        raise AssertionError("live object stage source step ambiguous")
    start = text.index("        run: |\n", text.index(marker)) + len("        run: |\n")
    end = text.find("\n      - name:", start)
    lines = text[start:end if end >= 0 else len(text)].splitlines()
    if not lines or any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("live object stage step indentation drift")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

def runtime(text, title, writer):
    shell = step(text, title)
    if writer:
        shell = shell.split("python -m py_compile", 1)[0]
    else:
        shell = shell.split("python -m py_compile", 1)[0]
    head = "a" * 40
    cases = (
        ("pull_request", "so", "", head, "", not writer),
        ("pull_request", "main", "", head, "", False),
        ("pull_request", "so", "", "A" * 40, "", False),
        ("pull_request", "so", "", "b" * 40, "", False),
        ("push", "", "refs/heads/so", "", head, writer),
        ("push", "", "refs/heads/main", "", head, False),
        ("push", "", "refs/heads/so", "", "A" * 40, False),
        ("push", "", "refs/heads/so", "", "b" * 40, False),
        ("schedule", "", "refs/heads/so", "", head, False),
        ("workflow_dispatch", "", "refs/heads/so", "", head, writer),
    )
    with tempfile.TemporaryDirectory(prefix="live-object-source-") as tmp:
        root = Path(tmp)
        git = root / "git"
        git.write_text("#!/bin/sh\n"
                       "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                       "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                       "exit 1\n", encoding="utf-8")
        git.chmod(0o755)
        envfile = root / "github-env"
        for event, base, ref, pr_sha, sha, allowed in cases:
            envfile.write_text("", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha, GITHUB_ENV=str(envfile))
            r = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell], cwd=root,
                               env=env, capture_output=True, text=True, timeout=10, check=False)
            if (r.returncode == 0) != allowed:
                raise AssertionError("live object stage source shell event/base/ref/SHA drift: " + title + "/" + event)
    print("PASS: live object stage actual " + ("writer" if writer else "PR") + " source shell runtime (10 cases)")

def main():
    publisher, independent = source(PUBLISHER), source(INDEPENDENT)
    if blob(publisher) != REVIEWED_PUBLISHER or blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("live object stage complete source blob drift")
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP_PY,
                   "persist-credentials: false", "contents: read",
                   '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'):
        if marker not in independent:
            raise AssertionError("live object stage independent source/reachability drift: " + marker)
    policy(publisher)
    negatives(publisher)
    runtime(publisher, "Validate diagnostic source read-only", False)
    runtime(publisher, "Reconcile stage diagnostics", True)
    print("PASS: live object stage read-only source proof; production evidence generated: false; production decision changed: false")

if __name__ == "__main__":
    main()
