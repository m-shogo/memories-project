#!/usr/bin/env python3
"""Exact-source, read-only runtime negatives for SIGKILL failure diagnostics."""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-deletion-sigkill-authority.yml"
INDEPENDENT = ".github/workflows/deletion-sigkill-diagnostic-source-negative.yml"
SCRIPT = "scripts/validate-memory-os-deletion-sigkill-diagnostic-source-negative.py"
REVIEWED = "0906a248b52297e836738d0c6ff00daaf49fed7d"
TARGET = "docs/fixtures/memory-os-operability/deletion-sigkill-authority-diagnostic.last.json"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"


def source(name):
    p = ROOT / name
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != name:
        raise SystemExit("SIGKILL source missing, symlinked or escaped: " + name)
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
    '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'log="$(mktemp)"',
    "trap 'rm -f \"$log\"' EXIT",
    'python scripts/reconcile-memory-os-deletion-sigkill-authority.py >"$log" 2>&1 || code=$?',
    '"output": "SIGKILL reconcile failed; raw validator output withheld."',
    '"containsSecrets": False',
    '"productionDecision": "NO_GO"',
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(tmp, path)",
    "tmp.unlink()",
    "git fetch origin so",
)


def policy(text):
    for item in REQUIRED:
        if item not in text:
            raise AssertionError("SIGKILL source policy missing: " + item[:70])
    if text.count(CHECKOUT) != 2 or text.count(SETUP) != 2:
        raise AssertionError("SIGKILL Actions source drift")
    if any(x in text for x in ("checkout@v4", "setup-python@v5", "tee /tmp/sigkill",
                               "sigkill-reconcile-output.txt", "[-16000:]")):
        raise AssertionError("SIGKILL raw output/floating Actions regression")


def mutations(text):
    for i, marker in enumerate(REQUIRED):
        mutated = text.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if mutated == text:
            raise AssertionError("SIGKILL negative unreachable: " + str(i))
        try:
            policy(mutated)
        except AssertionError:
            continue
        raise AssertionError("SIGKILL accepted source mutation: " + str(i))
    for marker in (CHECKOUT, SETUP):
        try:
            policy(text.replace(marker, "uses: actions/checkout@v4", 1))
        except AssertionError:
            continue
        raise AssertionError("SIGKILL accepted floating Action")
    print("PASS: SIGKILL diagnostic policy source negatives (24 cases)")


def step(text, name):
    marker = "      - name: " + name + "\n"
    if text.count(marker) != 1:
        raise AssertionError("SIGKILL step not unique: " + name)
    start = text.index("        run: |\n", text.index(marker)) + len("        run: |\n")
    end = text.find("\n      - name:", start)
    lines = text[start:end if end >= 0 else len(text)].splitlines()
    if not lines or any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("SIGKILL inline indentation drift: " + name)
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"


def writer_runtime(text):
    code = step(text, "Publish exact-source SIGKILL reconcile failure diagnostic")
    if code.count("python - <<'PY'\n") != 1 or code.count("\nPY\n") != 1:
        raise AssertionError("SIGKILL inline writer missing")
    code = code.split("python - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0] + "\n"
    cases = ("existing", "new", "replace", "fsync", "symlink", "parent", "directory")
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="sigkill-diagnostic-") as tmp:
            root = Path(tmp)
            parent = root / "docs/fixtures/memory-os-operability"
            parent.mkdir(parents=True)
            target = root / TARGET
            outside = root / "outside"
            outside.mkdir()
            canary = outside / "canary"
            canary.write_bytes(b"SYNTHETIC_SECRET_CANARY")
            if case in ("existing", "replace", "fsync"):
                target.write_bytes(b"before\n")
                target.chmod(0o640)
            if case == "symlink":
                target.symlink_to(canary)
            if case == "parent":
                parent.rmdir()
                parent.symlink_to(outside, target_is_directory=True)
            if case == "directory":
                target.mkdir()
            inject = ""
            if case in ("replace", "fsync"):
                func = "replace" if case == "replace" else "fsync"
                inject = "import os\n" + "def deny(*args): raise OSError('synthetic failure')\n" + "os." + func + " = deny\n"
            result = subprocess.run([sys.executable, "-c", inject + code], cwd=root,
                                    env=dict(os.environ, SOURCE_SHA="a" * 40),
                                    capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != (case in ("existing", "new")):
                raise AssertionError("SIGKILL inline writer acceptance drift: " + case)
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("SIGKILL inline writer changed outside canary")
            if case in ("existing", "new"):
                value = json.loads(target.read_text(encoding="utf-8"))
                if value["output"] != "SIGKILL reconcile failed; raw validator output withheld." or value["containsSecrets"] or value["productionDecision"] != "NO_GO":
                    raise AssertionError("SIGKILL diagnostic redaction/authority drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise AssertionError("SIGKILL diagnostic mode drift")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise AssertionError("SIGKILL atomic rollback drift")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("SIGKILL temp residue")
    print("PASS: SIGKILL actual inline writer redaction/atomic/symlink runtime (7 cases)")


def log_runtime(text):
    shell = step(text, "Reconcile actual process-kill evidence")
    with tempfile.TemporaryDirectory(prefix="sigkill-log-") as tmp:
        root = Path(tmp)
        stub = root / "python"
        stub.write_text("#!/bin/sh\nprintf 'SYNTHETIC_SECRET_CANARY\\n'\nexit 23\n", encoding="utf-8")
        stub.chmod(0o755)
        env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"), TMPDIR=str(root))
        result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
        if result.returncode != 23 or "SYNTHETIC_SECRET_CANARY" in result.stdout + result.stderr:
            raise AssertionError("SIGKILL reconcile log exposed or exit code swallowed")
        if list(root.glob("tmp.*")):
            raise AssertionError("SIGKILL raw log temp residue")
    print("PASS: SIGKILL actual shell withholds synthetic secret and returns exit 23")


def main():
    publisher = source(PUBLISHER)
    if blob(publisher) != REVIEWED:
        raise SystemExit("SIGKILL publisher complete Git blob unreviewed")
    independent = source(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SCRIPT, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'):
        if marker not in independent:
            raise AssertionError("SIGKILL independent CI reachability/source drift: " + marker)
    policy(publisher)
    mutations(publisher)
    writer_runtime(publisher)
    log_runtime(publisher)
    print("PASS: SIGKILL exact-source read-only proof; production evidence generated: false; production decision changed: false")


if __name__ == "__main__":
    main()
