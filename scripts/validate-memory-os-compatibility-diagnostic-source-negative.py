#!/usr/bin/env python3
"""Independent read-only source and atomic failure proof for compatibility diagnostics."""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-compatibility-authority-diagnostic.yml"
INDEPENDENT = ".github/workflows/compatibility-diagnostic-source-negative.yml"
SELF = "scripts/validate-memory-os-compatibility-diagnostic-source-negative.py"
REVIEWED = "5a8e31638d7c22f408d68cfb5e8a60dc360e6d00"
REVIEWED_INDEPENDENT = "e673a883f98c2a905ce6c56d7945d33a7f231a96"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
TARGET = "docs/fixtures/memory-os-operability/compatibility-authority-diagnostic.last.json"


def read(name):
    p = ROOT / name
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != name:
        raise SystemExit("compatibility source missing, escaped or symlinked: " + name)
    return p.read_text(encoding="utf-8")


def blob(text):
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


MARKERS = (
    "  pull_request:\n    branches:\n      - so\n",
    "  push:\n    branches:\n      - so\n",
    "github.base_ref == 'so'",
    "github.ref == 'refs/heads/so'",
    "persist-credentials: false",
    "persist-credentials: true",
    'test "${GITHUB_BASE_REF:-}" = "so"',
    'test "${GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]',
    'log="$(mktemp)"',
    "trap 'rm -f \"$log\"' EXIT",
    'echo "Compatibility validation completed; raw validator output withheld."',
    '"output": "Compatibility authority validation failed; raw validator output withheld."',
    '"containsSecrets": False',
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(tmp_name, path)",
    "os.unlink(tmp_name)",
)


def policy(text):
    for marker in MARKERS:
        if marker not in text:
            raise AssertionError("compatibility source policy missing: " + marker[:55])
    if text.count(CHECKOUT) != 2 or text.count(SETUP) != 2:
        raise AssertionError("compatibility immutable Actions drift")
    if text.count(MARKERS[8]) != 2:
        raise AssertionError("compatibility PR and writer SHA checks both required")
    if any(x in text for x in ("checkout@v4", "setup-python@v5", 'cat "$log"', "text[-12000:]",
                               "/tmp/memory-os-compatibility-authority.log")):
        raise AssertionError("compatibility raw-output/floating Actions regression")


def mutations(text):
    for index, marker in enumerate(MARKERS):
        mutated = text.replace(marker, "REMOVED_NEGATIVE", 1)
        try:
            policy(mutated)
        except AssertionError:
            continue
        raise AssertionError("compatibility source accepted mutation " + str(index))
    for action in (CHECKOUT, SETUP):
        try:
            policy(text.replace(action, "uses: actions/checkout@v4", 1))
        except AssertionError:
            continue
        raise AssertionError("compatibility source accepted floating Action")
    print("PASS: compatibility diagnostic source mutations (23 cases)")


def step(text, name):
    key = "      - name: " + name + "\n"
    if text.count(key) != 1:
        raise AssertionError("compatibility step ambiguous: " + name)
    start = text.index("        run: |\n", text.index(key)) + len("        run: |\n")
    end = text.find("\n      - name:", start)
    lines = text[start:end if end >= 0 else len(text)].splitlines()
    if not lines or any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("compatibility step indentation drift: " + name)
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"


def writer_runtime(text):
    shell = step(text, "Record privacy-safe diagnostic")
    if shell.count("python - <<'PY'\n") != 1 or shell.count("\nPY\n") != 1:
        raise AssertionError("compatibility writer extraction failed")
    code = shell.split("python - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0] + "\n"
    cases = ("existing", "new", "replace", "fsync", "symlink", "parent", "directory")
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="compatibility-diagnostic-") as tmp:
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
                                    env=dict(os.environ, SOURCE_SHA="a" * 40, COMPATIBILITY_EXIT_CODE="23"),
                                    capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != (case in ("existing", "new")):
                raise AssertionError("compatibility writer acceptance drift: " + case)
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("compatibility writer escaped canary")
            if case in ("existing", "new"):
                data = json.loads(target.read_text(encoding="utf-8"))
                if data["output"] != "Compatibility authority validation failed; raw validator output withheld." or data["containsSecrets"] or data["productionEvidence"] or data["releaseCompatibilityEvidence"]:
                    raise AssertionError("compatibility diagnostic redaction/evidence drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise AssertionError("compatibility diagnostic mode drift")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise AssertionError("compatibility atomic rollback drift")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("compatibility diagnostic temporary residue")
    print("PASS: compatibility actual inline writer atomic/redaction/symlink runtime (7 cases)")


def log_runtime(text):
    shell = step(text, "Validate and reconcile with stage capture")
    with tempfile.TemporaryDirectory(prefix="compatibility-log-") as tmp:
        root = Path(tmp)
        stub = root / "python"
        stub.write_text("#!/bin/sh\nprintf 'SYNTHETIC_SECRET_CANARY\\n'\nexit 23\n", encoding="utf-8")
        stub.chmod(0o755)
        output = root / "github-output"
        output.touch()
        env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                   TMPDIR=str(root), GITHUB_OUTPUT=str(output))
        result = subprocess.run(["bash", "-c", shell], cwd=root, env=env,
                                capture_output=True, text=True, timeout=10, check=False)
        if result.returncode != 0 or "SYNTHETIC_SECRET_CANARY" in result.stdout + result.stderr:
            raise AssertionError("compatibility raw stage output exposed")
        if "exit_code=23" not in output.read_text(encoding="utf-8"):
            raise AssertionError("compatibility stage failure swallowed")
        if list(root.glob("tmp.*")):
            raise AssertionError("compatibility raw log temp residue")
    print("PASS: compatibility actual stage shell withholds secret and records exit 23")



def identity_runtime(ci, title):
    command = step(ci, title)
    head = "a" * 40
    cases = (
        ("pull_request", "so", "", head, "", True),
        ("pull_request", "main", "", head, "", False),
        ("pull_request", "so", "", "A" * 40, "", False),
        ("pull_request", "so", "", "b" * 40, "", False),
        ("pull_request", "so", "", "", "", False),
        ("push", "", "refs/heads/so", "", head, True),
        ("push", "", "refs/heads/main", "", head, False),
        ("push", "", "refs/heads/so", "", "A" * 40, False),
        ("push", "", "refs/heads/so", "", "b" * 40, False),
        ("push", "", "refs/heads/so", "", "a" * 39, False),
        ("schedule", "", "refs/heads/so", "", head, False),
        ("workflow_dispatch", "", "refs/heads/so", "", head, False),
    )
    with tempfile.TemporaryDirectory(prefix="diagnostic-source-identity-") as temp:
        root = Path(temp)
        git = root / "git"
        git.write_text("#!/bin/sh\n"
                       "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                       "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                       "exit 1\n", encoding="utf-8")
        git.chmod(0o755)
        for event, base, ref, pr_sha, sha, allowed in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", command],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != allowed:
                raise AssertionError("diagnostic independent event/base/ref/SHA runtime drift: " + event)
    print("PASS: diagnostic independent exact-source event/base/ref/SHA shell runtime (12 cases)")



def main():
    text = read(PUBLISHER)
    if blob(text) != REVIEWED:
        raise SystemExit("compatibility publisher complete Git blob not reviewed")
    ci = read(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'):
        if marker not in ci:
            raise AssertionError("compatibility independent CI source/reachability drift: " + marker)
    if blob(ci) != REVIEWED_INDEPENDENT:
        raise SystemExit("compatibility independent workflow complete Git blob drift")
    identity_runtime(ci, "Require exact clean compatibility diagnostic source")
    policy(text)
    mutations(text)
    writer_runtime(text)
    log_runtime(text)
    print("PASS: compatibility exact-source read-only proof; production evidence generated: false; production decision changed: false")


if __name__ == "__main__":
    main()
