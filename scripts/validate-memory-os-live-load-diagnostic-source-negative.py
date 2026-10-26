#!/usr/bin/env python3
"""Independent exact-source negative and runtime checks for live load diagnostics."""
from __future__ import annotations
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-live-load-authority-v2.yml"
INDEPENDENT = ".github/workflows/live-load-authority-diagnostic-source-negative.yml"
PR = ".github/workflows/reconcile-live-load-authority-v2-pr.yml"
SELF = "scripts/validate-memory-os-live-load-diagnostic-source-negative.py"
TARGET = "docs/fixtures/memory-os-operability/live-load-authority-diagnostic.last.json"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
REVIEWED_PR = "2a02dd661662a1ed60676c7b20f2b3e53e2f8cdf"
REVIEWED_INDEPENDENT = "dc50ba77b412001552410c2ec1e1f1a5f0b401de"

def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def require_reviewed_source(content: str, expected: str, label: str) -> None:
    if blob(content) != expected:
        raise AssertionError("live load " + label + " complete Git blob drift")

def reviewed_blob_negatives(pr: str, independent: str) -> None:
    require_reviewed_source(pr, REVIEWED_PR, "PR")
    require_reviewed_source(independent, REVIEWED_INDEPENDENT, "independent CI")
    for label, original, expected in (
        ("PR", pr, REVIEWED_PR),
        ("independent CI", independent, REVIEWED_INDEPENDENT),
    ):
        try:
            require_reviewed_source(original + "\n# synthetic source drift\n", expected, label)
        except AssertionError:
            continue
        raise AssertionError("live load reviewed Git blob accepted synthetic source drift: " + label)
    print("PASS: live load PR and independent CI complete Git blob source negatives (2 cases)")

def read(path: str) -> str:
    target = ROOT / path
    if target.is_symlink() or not target.is_file() or target.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
        raise AssertionError("live load source substituted: " + path)
    return target.read_text(encoding="utf-8")

def step(text: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if text.count(marker) != 1:
        raise AssertionError("live load step missing/duplicated: " + name)
    begin = text.index("        run: |\n", text.index(marker)) + len("        run: |\n")
    end = text.find("\n      - name:", begin)
    lines = text[begin:end if end >= 0 else len(text)].splitlines()
    if any(line and not line.startswith("          ") for line in lines):
        raise AssertionError("live load shell indentation drift")
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"

REQUIRED = (
    "trap 'rm -f \"$log\"' EXIT",
    'python scripts/validate-memory-os-live-load.py >"$log" 2>&1 || postgres_code=$?',
    'python scripts/validate-memory-os-live-object-load.py >>"$log" 2>&1 || object_code=$?',
    'if [ "$code" -eq 0 ]; then',
    'echo "exit_code=$code" >> "$GITHUB_OUTPUT"',
    "'output': 'Live load validation completed; raw validator output withheld.'",
    "'containsSecrets': False",
    "'productionDecision': 'NO_GO'",
    "candidate.is_symlink()",
    "path.parent.resolve(strict=True).relative_to(repo)",
    "path.exists() and not path.is_file()",
    "os.fchmod(fd, mode)",
    "os.fsync(handle.fileno())",
    "os.replace(temp_path, path)",
    "temp_path.unlink()",
    "git fetch origin so",
)

def policy(source: str) -> None:
    for marker in REQUIRED:
        if marker not in source:
            raise AssertionError("live load policy missing: " + marker[:70])
    if source.count(CHECKOUT) != 1 or source.count(SETUP) != 1:
        raise AssertionError("live load immutable Actions drift")
    if source.count("git fetch origin so") != 4:
        raise AssertionError("live load CAS fetch multiplicity drift")
    for forbidden in ("read_text(\n              encoding='utf-8', errors='replace'", "output = re.sub(", "[-10000:]", "actions/checkout@v4", "actions/setup-python@v5"):
        if forbidden in source:
            raise AssertionError("live load raw diagnostic/floating Action regression")
    if "permissions:\n  contents: write" not in source:
        raise AssertionError("live load writer permission drift")

def mutations(source: str) -> None:
    for index, marker in enumerate(REQUIRED):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("unreachable live load mutation " + str(index))
        try:
            policy(changed)
        except AssertionError:
            continue
        raise AssertionError("live load policy accepted mutation " + str(index))
    print(f"PASS: live load diagnostic source mutations ({len(REQUIRED)} cases)")

def writer_runtime(source: str) -> None:
    shell = step(source, "Validate committed live evidence")
    if shell.count("python - <<'PY'\n") != 1 or shell.count("\nPY\n") != 1:
        raise AssertionError("live load writer heredoc missing")
    code = shell.split("python - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0] + "\n"
    for case in ("existing", "new", "replace", "fsync", "symlink", "parent", "directory", "bad_sha", "bad_exit"):
        with tempfile.TemporaryDirectory(prefix="live-load-diagnostic-") as temp:
            root = Path(temp)
            parent = root / Path(TARGET).parent
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
                operation = "replace" if case == "replace" else "fsync"
                inject = "import os\ndef deny(*args): raise OSError('synthetic failure')\nos." + operation + " = deny\n"
            env = dict(os.environ, SOURCE_SHA="a" * (39 if case == "bad_sha" else 40),
                       VALIDATION_EXIT_CODE="999" if case == "bad_exit" else "17")
            result = subprocess.run([sys.executable, "-c", inject + code], cwd=root,
                                    env=env, capture_output=True, text=True, timeout=10, check=False)
            accepted = case in ("existing", "new")
            if (result.returncode == 0) != accepted:
                raise AssertionError("live load diagnostic writer acceptance drift: " + case + " " + result.stderr[-200:])
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("live load diagnostic escaped target")
            if accepted:
                value = json.loads(target.read_text(encoding="utf-8"))
                if value["output"] != "Live load validation completed; raw validator output withheld." or value["containsSecrets"] or value["productionDecision"] != "NO_GO" or value["productionEvidence"] or value["productionReady"] or value["exitCode"] != 17:
                    raise AssertionError("live load diagnostic redaction/authority drift")
                if stat.S_IMODE(target.stat().st_mode) != (0o640 if case == "existing" else 0o600):
                    raise AssertionError("live load diagnostic mode drift")
            if case in ("replace", "fsync"):
                if target.read_bytes() != b"before\n" or stat.S_IMODE(target.stat().st_mode) != 0o640:
                    raise AssertionError("live load diagnostic rollback drift")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("live load diagnostic temp residue")
    print("PASS: actual live load diagnostic writer atomic/symlink/privacy runtime (9 cases)")

def validator_shell_runtime(source: str) -> None:
    shell = step(source, "Validate committed live evidence")
    for pg, obj, expected in ((0, 0, 0), (17, 0, 17), (0, 23, 23), (17, 23, 17)):
        with tempfile.TemporaryDirectory(prefix="live-load-shell-") as temp:
            root = Path(temp)
            stub = root / "python"
            stub.write_text("#!/bin/sh\ncase \"$1\" in\n"
                            "  scripts/validate-memory-os-live-load.py) echo SYNTHETIC_SECRET_CANARY; exit \"$PG_EXIT\";;\n"
                            "  scripts/validate-memory-os-live-object-load.py) echo SYNTHETIC_SECRET_CANARY; exit \"$OBJECT_EXIT\";;\n"
                            "  -) cat >/dev/null; exit 0;;\n"
                            "  *) exit 91;;\nesac\n", encoding="utf-8")
            stub.chmod(0o755)
            output = root / "github-output"
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       TMPDIR=str(root), GITHUB_OUTPUT=str(output), PG_EXIT=str(pg),
                       OBJECT_EXIT=str(obj), SOURCE_SHA="a" * 40)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode != 0 or output.read_text(encoding="utf-8") != f"exit_code={expected}\n":
                raise AssertionError("live load first/second validator failure swallowed: " + str((pg, obj, result.returncode, result.stderr[-100:])))
            if "SYNTHETIC_SECRET_CANARY" in result.stdout + result.stderr:
                raise AssertionError("live load validator shell exposed raw log")
            if list(root.glob("tmp.*")):
                raise AssertionError("live load validator shell temp residue")
    print("PASS: live load first/second validator exit and secret-free shell runtime (4 cases)")

def pr_policy(source: str) -> None:
    required = (
        "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
        "permissions:\\n      contents: read",
        "persist-credentials: false",
        'test "${GITHUB_EVENT_NAME:-}" = "pull_request"',
        'test "${GITHUB_BASE_REF:-}" = "so"',
        '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
        'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
        'test -z "$(git status --porcelain)"',
    )
    for marker in required:
        if marker.replace("\\n", "\n") not in source:
            raise AssertionError("live load PR source policy missing: " + marker)
    if source.count(CHECKOUT) != 1 or source.count(SETUP) != 1:
        raise AssertionError("live load PR immutable Actions drift")
    if source.count('test -z "$(git status --porcelain)"') != 2:
        raise AssertionError("live load PR clean worktree checks must remain at source and final boundary")
    if "actions/checkout@v4" in source or "actions/setup-python@v5" in source:
        raise AssertionError("live load PR floating Action regression")

def pr_mutations(source: str) -> None:
    required = (
        "if: github.event_name == 'pull_request' && github.base_ref == 'so'",
        "persist-credentials: false",
        'test "${GITHUB_EVENT_NAME:-}" = "pull_request"',
        'test "${GITHUB_BASE_REF:-}" = "so"',
        '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
        'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
        'test -z "$(git status --porcelain)"',
        CHECKOUT,
        SETUP,
    )
    for index, marker in enumerate(required):
        changed = source.replace(marker, "REMOVED_BY_NEGATIVE_TEST", 1)
        if changed == source:
            raise AssertionError("live load PR mutation unreachable: " + str(index))
        try:
            pr_policy(changed)
        except AssertionError:
            continue
        raise AssertionError("live load PR mutation accepted: " + str(index))
    print(f"PASS: live load PR source mutations ({len(required)} cases)")

def pr_identity_runtime(source: str) -> None:
    shell = step(source, "Verify exact clean PR source")
    head = "a" * 40
    cases = (
        ("pull_request", "so", head, True),
        ("pull_request", "main", head, False),
        ("push", "so", head, False),
        ("pull_request", "so", "b" * 40, False),
        ("pull_request", "so", "A" * 40, False),
        ("pull_request", "so", "a" * 39, False),
    )
    with tempfile.TemporaryDirectory(prefix="live-load-pr-identity-") as temp:
        root = Path(temp)
        stub = root / "git"
        stub.write_text("#!/bin/sh\n"
                        "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                        "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                        "exit 1\n", encoding="utf-8")
        stub.chmod(0o755)
        for event, base, sha, accepted in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, PR_HEAD_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise AssertionError("live load PR identity shell drift: " + str((event, base, sha, result.returncode)))
    print("PASS: live load PR event/base/head SHA shell runtime (6 cases)")

def independent_identity_runtime(source: str) -> None:
    shell = step(source, "Require exact clean live load diagnostic source")
    head = "a" * 40
    cases = (
        ("pull_request", "so", "", head, "", True),
        ("pull_request", "main", "", head, "", False),
        ("pull_request", "so", "", "b" * 40, "", False),
        ("pull_request", "so", "", "A" * 40, "", False),
        ("pull_request", "so", "", "", "", False),
        ("push", "", "refs/heads/so", "", head, True),
        ("push", "", "refs/heads/main", "", head, False),
        ("push", "", "refs/heads/so", "", "b" * 40, False),
        ("push", "", "refs/heads/so", "", "A" * 40, False),
        ("push", "", "refs/heads/so", "", "a" * 39, False),
        ("schedule", "", "refs/heads/so", "", head, False),
        ("workflow_dispatch", "", "refs/heads/so", "", head, False),
    )
    with tempfile.TemporaryDirectory(prefix="live-load-independent-identity-") as temp:
        root = Path(temp)
        stub = root / "git"
        stub.write_text("#!/bin/sh\n"
                        "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then printf '" + head + "\\n'; exit 0; fi\n"
                        "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
                        "exit 1\n", encoding="utf-8")
        stub.chmod(0o755)
        for event, base, ref, pr_sha, sha, accepted in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", shell],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != accepted:
                raise AssertionError("live load independent CI event/base/ref/SHA drift: " + str((event, base, ref, result.returncode)))
    print("PASS: live load independent CI event/base/ref/SHA shell runtime (12 cases)")

def main() -> None:
    publisher = read(PUBLISHER)
    pr = read(PR)
    independent = read(INDEPENDENT)
    for marker in (PUBLISHER, PR, INDEPENDENT, SELF, CHECKOUT, SETUP,
                   "persist-credentials: false", "contents: read",
                   'test "$(git rev-parse HEAD)" = "$expected"',
                   'test -z "$(git status --porcelain)"'):
        if marker not in independent:
            raise AssertionError("independent live load source guard reachability missing: " + marker)
    reviewed_blob_negatives(pr, independent)
    independent_identity_runtime(independent)
    policy(publisher)
    mutations(publisher)
    writer_runtime(publisher)
    validator_shell_runtime(publisher)
    pr_policy(pr)
    pr_mutations(pr)
    pr_identity_runtime(pr)
    print("PASS: live load diagnostic exact-source read-only proof; production evidence generated: false")

if __name__ == "__main__":
    main()
