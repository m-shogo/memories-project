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
PUBLISHER = ".github/workflows/deletion-worker-sigkill-recovery.yml"
INDEPENDENT = ".github/workflows/deletion-worker-sigkill-recovery-diagnostic-source-negative.yml"
SCRIPT = "scripts/validate-memory-os-deletion-worker-sigkill-recovery-diagnostic-source-negative.py"
RECONCILER = "scripts/reconcile-memory-os-deletion-worker-sigkill-recovery.py"
RECONCILE_NEGATIVE = "scripts/validate-memory-os-deletion-worker-sigkill-recovery-reconcile-negative.py"
REVIEWED_RECONCILER = "c8ff62fd44902d2f0998747f6a6b74efcc7190b4"
REVIEWED_RECONCILE_NEGATIVE = "430beb14c031d1faab9f6e0dbed5b1047957c2b1"
REVIEWED = "1ae00600d8ccbe1e9c70ad6d2bbfb6212e729313"
REVIEWED_INDEPENDENT = "b3193ff950a1a872523fa6f50098d2ee4021116c"
TARGET = "docs/fixtures/memory-os-operability/deletion-worker-sigkill-recovery-diagnostic.last.json"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
SETUP_GO = "uses: actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5"


def source(name):
    p = ROOT / name
    if p.is_symlink() or not p.is_file() or p.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != name:
        raise SystemExit("SIGKILL source missing, symlinked or escaped: " + name)
    return p.read_text(encoding="utf-8")


def blob(value):
    raw = value.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


REQUIRED = (
    "  push:\n    branches:\n      - so\n",
    "  workflow_dispatch:",
    '[[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]',
    'test "${GITHUB_REF:-}" = "refs/heads/so"',
    '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
    'trap \'rm -f "$log"\' EXIT',
    'echo "Local MinIO health failed; raw container logs withheld."',
    '"output": "Worker SIGKILL recovery proof failed; raw validator output withheld."',
    '"containsSecrets": False',
    '"productionEvidence": False',
    '"productionEquivalentDependencies": False',
    '"sourceCommitSha": os.environ["SOURCE_SHA"]',
    '"actualProcessKillCovered": False',
    '"actualHostFailureCovered": False',
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(tmp, path)",
    "tmp.unlink()",
)


def policy(value):
    for marker in REQUIRED:
        if marker not in value:
            raise AssertionError("Worker SIGKILL recovery diagnostic source policy missing: " + marker[:70])
    if value.count("git fetch origin so") != 5:
        raise AssertionError("Pre-fence CAS fetch multiplicity drift")
    if value.count(CHECKOUT) != 1 or value.count(SETUP) != 1 or value.count(SETUP_GO) != 1:
        raise AssertionError("Pre-fence mutation immutable Actions source drift")
    if any(marker in value for marker in ("checkout@v4", "setup-go@v5", "setup-python@v5",
                                         "docker logs memory-os-deletion-sigkill-minio", "text[-12000:]",
                                         "path.write_text(", "path.parent.mkdir(")):
        raise AssertionError("Pre-fence mutation raw output/unsafe writer regression")


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
    print(f"PASS: worker SIGKILL recovery diagnostic policy source negatives ({len(REQUIRED) + 2} cases)")


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
    code = step(text, "Record privacy-safe failure diagnostic")
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
                                    env=dict(os.environ, SOURCE_SHA="a" * 40, PROOF_EXIT_CODE="23"),
                                    capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != (case in ("existing", "new")):
                raise AssertionError("SIGKILL inline writer acceptance drift: " + case)
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("SIGKILL inline writer changed outside canary")
            if case in ("existing", "new"):
                value = json.loads(target.read_text(encoding="utf-8"))
                if (value["output"] != "Worker SIGKILL recovery proof failed; raw validator output withheld." or value["containsSecrets"] or value["productionEvidence"] or value["productionEquivalentDependencies"] or value["sourceCommitSha"] != "a" * 40 or value["result"] != "FAIL" or value["actualProcessKillCovered"] is not False or value["actualHostFailureCovered"] is not False or value["exitCode"] != 23):
                    raise AssertionError("SIGKILL diagnostic redaction/authority drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise AssertionError("SIGKILL diagnostic mode drift")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise AssertionError("SIGKILL atomic rollback drift")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("SIGKILL temp residue")
    print("PASS: worker SIGKILL recovery actual inline diagnostic writer redaction/atomic/symlink runtime (7 cases)")


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
    publisher = source(PUBLISHER)
    if blob(publisher) != REVIEWED:
        raise SystemExit("SIGKILL publisher complete Git blob unreviewed")
    independent = source(INDEPENDENT)
    for marker in (PUBLISHER, INDEPENDENT, SCRIPT, RECONCILER, RECONCILE_NEGATIVE, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'):
        if marker not in independent:
            raise AssertionError("SIGKILL independent CI reachability/source drift: " + marker)
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("SIGKILL independent workflow complete Git blob drift")
    if blob(source(RECONCILER)) != REVIEWED_RECONCILER:
        raise SystemExit("SIGKILL reconciler complete Git blob unreviewed")
    if blob(source(RECONCILE_NEGATIVE)) != REVIEWED_RECONCILE_NEGATIVE:
        raise SystemExit("SIGKILL reconcile negative complete Git blob unreviewed")
    identity_runtime(independent, "Require exact clean worker SIGKILL recovery diagnostic source")
    policy(publisher)
    mutations(publisher)
    writer_runtime(publisher)
    print("PASS: worker SIGKILL recovery exact-source read-only diagnostic proof; production evidence generated: false; production decision changed: false")


if __name__ == "__main__":
    main()
