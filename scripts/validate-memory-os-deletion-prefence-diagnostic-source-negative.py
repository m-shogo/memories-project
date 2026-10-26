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
PUBLISHER = ".github/workflows/deletion-prefence-linearization.yml"
INDEPENDENT = ".github/workflows/deletion-prefence-diagnostic-source-negative.yml"
SCRIPT = "scripts/validate-memory-os-deletion-prefence-diagnostic-source-negative.py"
REVIEWED = "fdcc951be6c589518f1f48bcb363b5dcd0b88602"
REVIEWED_INDEPENDENT = "f5a6fd14a2c39a42be23bd2c47953327a45d6123"
TARGET = "docs/fixtures/memory-os-operability/deletion-prefence-linearization-diagnostic.last.json"
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
    '"output": "Pre-fence proof failed; raw validator output withheld."',
    '"containsSecrets": False',
    '"productionEvidence": False',
    '"productionEquivalentDependencies": False',
    '"sourceCommitSha": os.environ["SOURCE_SHA"]',
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(tmp, path)",
    "tmp.unlink()",
    'if git diff --cached --quiet; then',
    'echo "RESULT_COMMIT_SHA=$SOURCE_SHA" >> "$GITHUB_ENV"',
    'Branch advanced before pre-fence result push; refusing stale evidence.',
    'if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]; then',
)


def policy(value):
    for marker in REQUIRED:
        if marker not in value:
            raise AssertionError("Pre-fence diagnostic source policy missing: " + marker[:70])
    if value.count("git fetch origin so") != 7:
        raise AssertionError("Pre-fence CAS fetch multiplicity drift")
    if value.count('if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]; then') != 2:
        raise AssertionError("Pre-fence post-commit CAS guard multiplicity drift")
    if value.count("git diff --cached --quiet") != 3:
        raise AssertionError("Pre-fence staged no-op guard multiplicity drift")
    if value.count(CHECKOUT) != 1 or value.count(SETUP) != 1 or value.count(SETUP_GO) != 1:
        raise AssertionError("Pre-fence immutable Actions source drift")
    if any(marker in value for marker in ("checkout@v4", "setup-go@v5", "setup-python@v5",
                                         "docker logs memory-os-prefence-minio", "text[-12000:]",
                                         "path.write_text(", "path.parent.mkdir(")):
        raise AssertionError("Pre-fence raw output/unsafe writer regression")


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
    print(f"PASS: pre-fence diagnostic policy source negatives ({len(REQUIRED) + 2} cases)")


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
                                    env=dict(os.environ, SOURCE_SHA="a" * 40, PREFENCE_PROOF_EXIT_CODE="23"),
                                    capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != (case in ("existing", "new")):
                raise AssertionError("SIGKILL inline writer acceptance drift: " + case)
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("SIGKILL inline writer changed outside canary")
            if case in ("existing", "new"):
                value = json.loads(target.read_text(encoding="utf-8"))
                if (value["output"] != "Pre-fence proof failed; raw validator output withheld." or value["containsSecrets"] or value["productionEvidence"] or value["productionEquivalentDependencies"] or value["sourceCommitSha"] != "a" * 40 or value["result"] != "FAIL" or value["exitCode"] != 23):
                    raise AssertionError("SIGKILL diagnostic redaction/authority drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise AssertionError("SIGKILL diagnostic mode drift")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise AssertionError("SIGKILL atomic rollback drift")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("SIGKILL temp residue")
    print("PASS: pre-fence actual inline diagnostic writer redaction/atomic/symlink runtime (7 cases)")


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




def result_commit_runtime(publisher):
    """Execute the real result publisher in a disposable fake-Git CAS/no-op sandbox."""
    command = step(publisher, "Commit exact-source result")
    source_sha, new_sha, stale_sha = "a" * 40, "c" * 40, "b" * 40
    fake_git = """#!/usr/bin/env python3
import os
import sys
from pathlib import Path
args = sys.argv[1:]
root = Path(os.environ["FAKE_GIT_STATE"])
with (root / "calls").open("a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\\n")
if args == ["fetch", "origin", "so"]:
    count = int((root / "fetches").read_text()) + 1
    (root / "fetches").write_text(str(count))
    if count == 2 and os.environ["FAKE_RACE"] == "1":
        (root / "remote").write_text("b" * 40)
elif args == ["rev-parse", "HEAD"]:
    print((root / "head").read_text())
elif args == ["rev-parse", "origin/so"]:
    print((root / "remote").read_text())
elif args == ["diff", "--cached", "--quiet"]:
    sys.exit(0 if os.environ["FAKE_NOOP"] == "1" else 1)
elif args[:2] == ["commit", "-m"]:
    (root / "head").write_text("c" * 40)
elif args[0] in ("config", "add", "push"):
    pass
else:
    sys.exit(92)
"""
    cases = (
        ("noop", source_sha, source_sha, True, False, 0, 0, 0, source_sha),
        ("success", source_sha, source_sha, False, False, 0, 1, 1, new_sha),
        ("stale-remote", stale_sha, source_sha, False, False, 75, 0, 0, None),
        ("missing-remote", "", source_sha, False, False, 75, 0, 0, None),
        ("stale-local", source_sha, stale_sha, False, False, 75, 0, 0, None),
        ("race-after-commit", source_sha, source_sha, False, True, 75, 0, 1, new_sha),
    )
    for label, remote, local, noop, race, expected_exit, expected_push, expected_commit, expected_result in cases:
        with tempfile.TemporaryDirectory(prefix="prefence-result-cas-") as temp:
            root = Path(temp)
            git = root / "git"
            git.write_text(fake_git, encoding="utf-8")
            git.chmod(0o755)
            for name, value in (("head", local), ("remote", remote), ("fetches", "0"), ("calls", "")):
                (root / name).write_text(value, encoding="utf-8")
            env_file = root / "github-env"
            env_file.write_text("", encoding="utf-8")
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       SOURCE_SHA=source_sha, GITHUB_ENV=str(env_file), FAKE_GIT_STATE=str(root),
                       FAKE_NOOP="1" if noop else "0", FAKE_RACE="1" if race else "0")
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", command],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    timeout=10, check=False)
            calls = (root / "calls").read_text(encoding="utf-8").splitlines()
            pushes = sum(call == "push origin HEAD:so" for call in calls)
            commits = sum(call.startswith("commit -m ") for call in calls)
            if (result.returncode != expected_exit or pushes != expected_push or
                    commits != expected_commit):
                raise AssertionError(f"pre-fence result {label} CAS/no-op drift: "
                                     f"exit={result.returncode}, pushes={pushes}, commits={commits}")
            expected_env = "" if expected_result is None else "RESULT_COMMIT_SHA=" + expected_result + "\n"
            if env_file.read_text(encoding="utf-8") != expected_env:
                raise AssertionError("pre-fence result source-binding environment drift: " + label)
    print(f"PASS: pre-fence actual result publisher CAS/no-op shell ({len(cases)} cases)")


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
    if blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("SIGKILL independent workflow complete Git blob drift")
    identity_runtime(independent, "Require exact clean pre-fence diagnostic source")
    policy(publisher)
    mutations(publisher)
    writer_runtime(publisher)
    result_commit_runtime(publisher)
    print("PASS: pre-fence exact-source read-only diagnostic proof; production evidence generated: false; production decision changed: false")


if __name__ == "__main__":
    main()
