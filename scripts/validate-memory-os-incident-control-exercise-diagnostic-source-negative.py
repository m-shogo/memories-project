#!/usr/bin/env python3
"""Read-only exact-source and fault-injection proof for both incident-control diagnostic writers."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/incident-control-exercise.yml"
INDEPENDENT = ".github/workflows/incident-control-exercise-diagnostic-source-negative.yml"
SELF = "scripts/validate-memory-os-incident-control-exercise-diagnostic-source-negative.py"
REVIEWED_PUBLISHER = "c59d6f2b832d9c995391882c4f1829d5670950b9"
REVIEWED_INDEPENDENT = "7498034f740e5b6e807a053d457026995b719955"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit("incident control source missing/substituted: " + relative) from exc


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate(publisher: str, independent: str) -> None:
    publisher_required = (
        ("  schedule:\n", 1),
        ("  workflow_dispatch:\n", 1),
        ("permissions:\n  contents: write\n", 1),
        ("def guarded_target(path: Path) -> Path:", 2),
        ("def atomic_write_text(path: Path, text: str) -> None:", 2),
        ("if candidate.is_symlink():", 2),
        ("if not target.parent.is_dir():", 2),
        ("if target.exists() and not target.is_file():", 2),
        ("os.fchmod(fd, existing_mode)", 2),
        ("os.fsync(handle.fileno())", 2),
        ("os.replace(temporary, target)", 2),
        ("temporary.unlink()", 2),
        ("guarded_target(path).read_text(encoding='utf-8')", 1),
        ("'Incident control exercise completed; raw output withheld.'", 1),
        ("'Incident control exercise and validation completed; raw output withheld.'", 1),
    )
    independent_required = (
        "  pull_request:\n    branches:\n      - so\n",
        "  push:\n    branches:\n      - so\n",
        '      - "' + PUBLISHER + '"', '      - "' + INDEPENDENT + '"',
        '      - "' + SELF + '"', CHECKOUT, SETUP,
        "          persist-credentials: false\n", PR_BASE, PUSH_REF, SHA_FORMAT,
        "          python " + SELF, "permissions:\n  contents: read\n",
        "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
        'test "$(git rev-parse HEAD)" = "$expected"',
        'test -z "$(git status --porcelain)"',
    )
    for token, count in publisher_required:
        if publisher.count(token) != count:
            raise SystemExit("incident control publisher source drift: " + token)
    for token in independent_required:
        if token not in independent:
            raise SystemExit("incident control independent source drift: " + token)
    if blob(publisher) != REVIEWED_PUBLISHER or blob(independent) != REVIEWED_INDEPENDENT:
        raise SystemExit("incident control complete Git blob source drift")
    if ("Path('/tmp/incident-control-exercise.log').read_text" in publisher or
        "Path('/tmp/incident-control-validation.log').read_text" in publisher or
        "path.parent.mkdir(parents=True, exist_ok=True)" in publisher):
        raise SystemExit("incident control raw diagnostic or unchecked parent regression")


def inline_writers(publisher: str) -> tuple[str, str]:
    markers = (
        "          EXERCISE_EXIT_CODE=\"$code\" python - <<'PY'\n",
        "          VALIDATION_EXIT_CODE=\"$code\" python - <<'PY'\n",
    )
    if any(publisher.count(marker) != 1 for marker in markers):
        raise SystemExit("incident control inline diagnostic writers missing/ambiguous")
    scripts = []
    for marker in markers:
        start = publisher.index(marker) + len(marker)
        end = publisher.index("\n          PY\n", start)
        lines = publisher[start:end].splitlines()
        if not lines or any(line and not line.startswith("          ") for line in lines):
            raise SystemExit("incident control inline writer indentation drift")
        scripts.append("\n".join(line[10:] if line else "" for line in lines) + "\n")
    return scripts[0], scripts[1]


def run_writer(code: str, root: Path, success: bool, fault: str = "") -> None:
    injection = """
import os
if os.environ.get('INJECT_FAULT') == 'replace':
    def fail_replace(*args, **kwargs):
        raise OSError('synthetic replace failure')
    os.replace = fail_replace
if os.environ.get('INJECT_FAULT') == 'fsync':
    def fail_fsync(*args, **kwargs):
        raise OSError('synthetic fsync failure')
    os.fsync = fail_fsync
"""
    env = dict(os.environ, SOURCE_SHA="a" * 40, EXERCISE_EXIT_CODE="0",
               VALIDATION_EXIT_CODE="0", INJECT_FAULT=fault)
    result = subprocess.run([sys.executable, "-c", injection + code],
                            cwd=root, env=env, capture_output=True, text=True,
                            timeout=10, check=False)
    if (result.returncode == 0) != success:
        raise SystemExit("incident control diagnostic runtime exit drift: " + (fault or "path"))


def diagnostic_runtime(publisher: str) -> None:
    first, second = inline_writers(publisher)
    with tempfile.TemporaryDirectory(prefix="incident-control-diagnostic-") as tmp:
        root = Path(tmp)
        parent = root / "docs/fixtures/memory-os-operability"
        parent.mkdir(parents=True)
        path = parent / "incident-control-exercise-diagnostic.last.json"
        leftovers = lambda: list(parent.glob("." + path.name + ".*.tmp"))

        run_writer(first, root, True)
        value = json.loads(path.read_text(encoding="utf-8"))
        if (value.get("output") != "Incident control exercise completed; raw output withheld." or
            value.get("sourceCommitSha") != "a" * 40 or
            value.get("productionEvidence") is not False or
            value.get("humanTabletopCompleted") is not False or
            value.get("containsSecrets") is not False or leftovers()):
            raise SystemExit("incident control first diagnostic output drift")
        path.chmod(0o640)
        run_writer(first, root, True)
        if stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise SystemExit("incident control first writer mode drift")
        run_writer(second, root, True)
        value = json.loads(path.read_text(encoding="utf-8"))
        if (value.get("validationResult") != "PASS" or
            value.get("output") != "Incident control exercise and validation completed; raw output withheld." or
            stat.S_IMODE(path.stat().st_mode) != 0o640 or leftovers()):
            raise SystemExit("incident control second diagnostic output/mode drift")

        original = path.read_bytes()
        for writer in (first, second):
            for fault in ("replace", "fsync"):
                run_writer(writer, root, False, fault)
                if (path.read_bytes() != original or
                    stat.S_IMODE(path.stat().st_mode) != 0o640 or leftovers()):
                    raise SystemExit("incident control atomic failure changed prior bytes/mode/temp")

        external = root / "external-canary"
        external.write_bytes(b"external\n")
        path.unlink()
        path.symlink_to(external)
        for writer in (first, second):
            run_writer(writer, root, False)
        if external.read_bytes() != b"external\n" or leftovers():
            raise SystemExit("incident control followed target symlink")
        path.unlink()

        outside = root / "outside"
        outside.mkdir()
        (outside / path.name).write_bytes(b"outside\n")
        old_parent = root / "old-parent"
        parent.rename(old_parent)
        parent.symlink_to(outside, target_is_directory=True)
        for writer in (first, second):
            run_writer(writer, root, False)
        if (outside / path.name).read_bytes() != b"outside\n":
            raise SystemExit("incident control followed parent symlink")
        parent.unlink()
        old_parent.rename(parent)

        shutil.rmtree(parent)
        for writer in (first, second):
            run_writer(writer, root, False)
        if parent.exists():
            raise SystemExit("incident control created missing parent")
        parent.mkdir()
        path.mkdir()
        for writer in (first, second):
            run_writer(writer, root, False)
        if not path.is_dir() or leftovers():
            raise SystemExit("incident control accepted nonregular target")
    print("PASS: incident control two-writer diagnostic redaction/atomic/symlink runtime (15 cases)")


def predicate_runtime(independent: str) -> None:
    for cmd in (PR_BASE, PUSH_REF, SHA_FORMAT):
        if independent.count(cmd) != 1:
            raise SystemExit("incident control source predicate missing/ambiguous")
    for cmd, key, value, allow in (
        (PR_BASE, "GITHUB_BASE_REF", "so", True),
        (PR_BASE, "GITHUB_BASE_REF", "main", False),
        (PR_BASE, "GITHUB_BASE_REF", "", False),
        (PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
        (PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
        (PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
    ):
        r = subprocess.run(["bash", "-e", "-c", cmd],
                           env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                           capture_output=True, check=False)
        if (r.returncode == 0) != allow:
            raise SystemExit("incident control branch/base runtime drift")
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                         ("A" * 40, False), ("g" * 40, False), ("", False)):
        r = subprocess.run(["bash", "-e", "-c", SHA_FORMAT],
                           env=dict(os.environ, expected=value), capture_output=True, check=False)
        if (r.returncode == 0) != allow:
            raise SystemExit("incident control SHA runtime drift")
    print("PASS: incident control branch/base (6) and SHA (6) runtime cases")


def mutation_negatives(publisher: str, independent: str) -> None:
    p_cases = (
        ("raw exercise", "'Incident control exercise completed; raw output withheld.'", "Path('/tmp/incident-control-exercise.log').read_text()"),
        ("raw validation", "'Incident control exercise and validation completed; raw output withheld.'", "Path('/tmp/incident-control-validation.log').read_text()"),
        ("symlink", "if candidate.is_symlink():", "if False:"),
        ("missing parent", "if not target.parent.is_dir():", "if False:"),
        ("regular", "if target.exists() and not target.is_file():", "if False:"),
        ("mode", "os.fchmod(fd, existing_mode)", "pass"),
        ("fsync", "os.fsync(handle.fileno())", "pass"),
        ("atomic", "os.replace(temporary, target)", "target.write_text(text)"),
        ("cleanup", "temporary.unlink()", "pass"),
        ("guarded read", "guarded_target(path).read_text(encoding='utf-8')", "path.read_text(encoding='utf-8')"),
    )
    i_cases = (
        ("PR base", PR_BASE, "true"), ("push branch", PUSH_REF, "true"),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("self trigger", '      - "' + SELF + '"', ""),
        ("publisher trigger", '      - "' + PUBLISHER + '"', ""),
        ("root write", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("job scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", "    if: always()"),
    )
    for name, original, cases in (("publisher", publisher, p_cases), ("independent", independent, i_cases)):
        for label, old, new in cases:
            if old not in original:
                raise SystemExit("incident control mutation fixture missing: " + name + "/" + label)
            altered = original.replace(old, new, 1)
            if altered == original:
                raise SystemExit("incident control mutation fixture unchanged: " + name + "/" + label)
            try:
                validate(altered, independent) if name == "publisher" else validate(publisher, altered)
            except SystemExit:
                continue
            raise SystemExit("incident control accepted mutation: " + name + "/" + label)
    print("PASS: incident control publisher (10) and independent (10) source mutations")


def main() -> int:
    publisher, independent = source(PUBLISHER), source(INDEPENDENT)
    validate(publisher, independent)
    predicate_runtime(independent)
    mutation_negatives(publisher, independent)
    diagnostic_runtime(publisher)
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
