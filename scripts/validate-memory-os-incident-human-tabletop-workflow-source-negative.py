#!/usr/bin/env python3
"""Independent, read-only source and runtime fault proof for human-tabletop diagnostics."""
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
PUBLISHER = ".github/workflows/incident-human-tabletop-evidence.yml"
INDEPENDENT = ".github/workflows/incident-human-tabletop-workflow-source-negative.yml"
SELF = "scripts/validate-memory-os-incident-human-tabletop-workflow-source-negative.py"
REVIEWED_PUBLISHER = "a24f87fa0ccfcdf6b3861ef13ba0e8d2c4a335e9"
REVIEWED_INDEPENDENT = "5c1c180b5cee387956819255b75f293f9bb50f90"

PUBLISHER_PR_TRIGGER_PATHS = (
    ".github/workflows/incident-human-tabletop-evidence.yml",
    "contracts/operations/requests/incident-human-tabletop-evidence-foundation.v1.json",
    "contracts/operations/incident-human-tabletop-evidence-contract.v1.json",
    "docs/evidence/incident-tabletops/*.json",
    "scripts/register-memory-os-incident-human-tabletop.py",
    "scripts/validate-memory-os-incident-human-tabletop-writer-authority-negative.py",
    "scripts/validate-memory-os-incident-human-tabletops.py",
    "scripts/reconcile-memory-os-incident-human-tabletops.py",
    "scripts/validate-memory-os-incident-human-tabletop-source-negative.py",
    "scripts/validate-memory-os-incident-tabletop.py",
    "scripts/validate-memory-os-incident-response.py",
    "scripts/validate-memory-os-operability.py",
)
PUBLISHER_PUSH_TRIGGER_PATHS = (
    ".github/workflows/incident-human-tabletop-evidence.yml",
    "contracts/operations/requests/incident-human-tabletop-evidence-foundation.v1.json",
    "contracts/operations/incident-human-tabletop-evidence-contract.v1.json",
    "docs/evidence/incident-tabletops/*.json",
    "scripts/register-memory-os-incident-human-tabletop.py",
    "scripts/validate-memory-os-incident-human-tabletop-writer-authority-negative.py",
    "scripts/validate-memory-os-incident-human-tabletops.py",
    "scripts/reconcile-memory-os-incident-human-tabletops.py",
    "scripts/validate-memory-os-incident-human-tabletop-source-negative.py",
    "scripts/validate-memory-os-incident-tabletop.py",
    "scripts/validate-memory-os-incident-response.py",
    "scripts/validate-memory-os-operability.py",
)
INDEPENDENT_PR_TRIGGER_PATHS = (
    ".github/workflows/incident-human-tabletop-evidence.yml",
    ".github/workflows/incident-human-tabletop-workflow-source-negative.yml",
    "scripts/validate-memory-os-incident-human-tabletop-workflow-source-negative.py",
)
INDEPENDENT_PUSH_TRIGGER_PATHS = (
    ".github/workflows/incident-human-tabletop-evidence.yml",
    ".github/workflows/incident-human-tabletop-workflow-source-negative.yml",
    "scripts/validate-memory-os-incident-human-tabletop-workflow-source-negative.py",
)
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'



def validate_trigger_reachability(
    value: str, *, publisher: bool,
    pr_paths: tuple[str, ...] | None = None,
    push_paths: tuple[str, ...] | None = None,
) -> None:
    """Preserve tabletop publisher PR paths-only and independent PR branch restriction."""
    expected_pr = PUBLISHER_PR_TRIGGER_PATHS if publisher else INDEPENDENT_PR_TRIGGER_PATHS
    expected_push = PUBLISHER_PUSH_TRIGGER_PATHS if publisher else INDEPENDENT_PUSH_TRIGGER_PATHS
    approved_pr = expected_pr if pr_paths is None else pr_paths
    approved_push = expected_push if push_paths is None else push_paths
    for label, actual, expected in (("PR", approved_pr, expected_pr), ("push", approved_push, expected_push)):
        if len(actual) != len(expected) or len(set(actual)) != len(expected):
            raise SystemExit("human-tabletop CI " + label + " trigger inventory shortened or duplicated")
    pr = "  pull_request:\n    paths:\n" if publisher else "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    end = "  workflow_dispatch:\n" if publisher else "\npermissions:\n"
    if any(value.count(marker) != 1 for marker in (pr, push, end)):
        raise SystemExit("human-tabletop CI event marker drift")
    if not (value.index(pr) < value.index(push) < value.index(end)):
        raise SystemExit("human-tabletop CI event order drift")
    for event, start, stop, approved_paths in (
        ("PR", pr, push, approved_pr), ("push", push, end, approved_push)
    ):
        block = value.split(start, 1)[1].split(stop, 1)[0]
        actual = tuple(line for line in block.splitlines()
                       if line.strip() and not line.lstrip().startswith("#"))
        approved = tuple('      - "' + path + '"' for path in approved_paths)
        if actual != approved:
            raise SystemExit("human-tabletop CI " + event + " exact trigger path drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    """Prove every event omission, quoted/unquoted addition and shortened inventory."""
    pub_pr = "  pull_request:\n    paths:\n"
    ind_pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    for label, value, is_publisher, pr_paths, push_paths in (
        ("publisher", publisher, True, PUBLISHER_PR_TRIGGER_PATHS, PUBLISHER_PUSH_TRIGGER_PATHS),
        ("independent", independent, False, INDEPENDENT_PR_TRIGGER_PATHS, INDEPENDENT_PUSH_TRIGGER_PATHS),
    ):
        pr = pub_pr if is_publisher else ind_pr
        end = "  workflow_dispatch:\n" if is_publisher else "\npermissions:\n"
        for event, start, stop, paths in (
            ("PR", pr, push, pr_paths), ("push", push, end, push_paths)
        ):
            start_index = value.index(start) + len(start)
            end_index = value.index(stop, start_index)
            block = value[start_index:end_index]
            for path in paths:
                token = '      - "' + path + '"\n'
                if block.count(token) != 1:
                    raise SystemExit("human-tabletop CI mutation anchor drift: " + path)
                mutated = value[:start_index] + block.replace(token, "", 1) + value[end_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("human-tabletop CI accepted missing " + label + " " + event + " trigger: " + path)
            for name, injection in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                mutated = value[:start_index] + injection + value[start_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("human-tabletop CI accepted " + label + " " + event + " " + name)
        for event in ("PR", "push"):
            try:
                validate_trigger_reachability(
                    value, publisher=is_publisher,
                    pr_paths=pr_paths[:-1] if event == "PR" else pr_paths,
                    push_paths=push_paths[:-1] if event == "push" else push_paths,
                )
            except SystemExit:
                pass
            else:
                raise SystemExit("human-tabletop CI accepted shortened " + label + " " + event + " inventory")
    print("PASS: human-tabletop CI event triggers (30 removals; 16 additions; 4 shortened inventory negatives)")


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit("human-tabletop source missing/substituted: " + relative) from exc


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate(publisher: str, independent: str) -> None:
    publisher_required = (
        "  push:\n    branches:\n      - so\n",
        "  workflow_dispatch:\n",
        "permissions:\n  contents: read\n", "      contents: write\n",
        '          echo "Human tabletop validation completed; raw validator output withheld."\n',
        "'output': 'Human tabletop validation failed; raw validator output withheld.',",
        "if candidate.is_symlink():", "if not path.parent.is_dir():",
        "path.parent.resolve(strict=True).relative_to(repo)",
        "if path.exists() and not path.is_file():",
        "os.fchmod(fd, existing_mode)", "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)", "os.unlink(tmp_name)",
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
    for label, content, required, digest in (
        ("publisher", publisher, publisher_required, REVIEWED_PUBLISHER),
        ("independent", independent, independent_required, REVIEWED_INDEPENDENT),
    ):
        for token in required:
            if token not in content:
                raise SystemExit("human-tabletop " + label + " missing source: " + token)
        if blob(content) != digest:
            raise SystemExit("human-tabletop " + label + " complete Git blob drift")
    if '          cat "$log"\n' in publisher or "text[-12000:]" in publisher:
        raise SystemExit("human-tabletop raw log disclosure")
    if "path.parent.mkdir(parents=True, exist_ok=True)" in publisher:
        raise SystemExit("human-tabletop diagnostic creates unchecked parent")


def inline_writer(publisher: str) -> str:
    marker = "          python - <<'PY'\n"
    if publisher.count(marker) != 1:
        raise SystemExit("human-tabletop diagnostic inline writer ambiguous")
    start = publisher.index(marker) + len(marker)
    end = publisher.index("\n          PY\n", start)
    lines = publisher[start:end].splitlines()
    if not lines or any(not line.startswith("          ") for line in lines):
        raise SystemExit("human-tabletop diagnostic inline writer indentation drift")
    return "\n".join(line[10:] for line in lines) + "\n"


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
    env = dict(os.environ, SOURCE_SHA="a" * 40, TABLETOP_EXIT_CODE="1", INJECT_FAULT=fault)
    result = subprocess.run([sys.executable, "-c", injection + code],
                            cwd=root, env=env, capture_output=True, text=True,
                            timeout=10, check=False)
    if (result.returncode == 0) != success:
        raise SystemExit("human-tabletop diagnostic runtime exit drift: " + (fault or "path"))


def runtime(publisher: str) -> None:
    code = inline_writer(publisher)
    with tempfile.TemporaryDirectory(prefix="human-tabletop-diagnostic-negative-") as tmp:
        root = Path(tmp)
        parent = root / "docs/fixtures/memory-os-operability"
        parent.mkdir(parents=True)
        path = parent / "incident-human-tabletop-diagnostic.last.json"
        leftovers = lambda: list(parent.glob("." + path.name + ".*.tmp"))
        run_writer(code, root, True)
        value = json.loads(path.read_text(encoding="utf-8"))
        if (value.get("sourceCommitSha") != "a" * 40 or
            value.get("output") != "Human tabletop validation failed; raw validator output withheld." or
            value.get("containsSecrets") is not False or
            value.get("productionEvidence") is not False or
            value.get("productionReady") is not False or leftovers()):
            raise SystemExit("human-tabletop diagnostic positive/redaction drift")
        path.chmod(0o640)
        run_writer(code, root, True)
        if stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise SystemExit("human-tabletop diagnostic mode drift")
        original = path.read_bytes()
        for fault in ("replace", "fsync"):
            run_writer(code, root, False, fault)
            if path.read_bytes() != original or stat.S_IMODE(path.stat().st_mode) != 0o640 or leftovers():
                raise SystemExit("human-tabletop diagnostic fault changed prior bytes/mode/temp")
        external = root / "external-canary"
        external.write_text("external\n", encoding="utf-8")
        path.unlink()
        path.symlink_to(external)
        run_writer(code, root, False)
        if external.read_text(encoding="utf-8") != "external\n" or leftovers():
            raise SystemExit("human-tabletop diagnostic followed target symlink")
        path.unlink()
        outside = root / "outside"
        outside.mkdir()
        (outside / path.name).write_text("outside\n", encoding="utf-8")
        old_parent = root / "old-parent"
        parent.rename(old_parent)
        parent.symlink_to(outside, target_is_directory=True)
        run_writer(code, root, False)
        if (outside / path.name).read_text(encoding="utf-8") != "outside\n":
            raise SystemExit("human-tabletop diagnostic followed parent symlink")
        parent.unlink()
        old_parent.rename(parent)
        shutil.rmtree(parent)
        run_writer(code, root, False)
        if parent.exists():
            raise SystemExit("human-tabletop diagnostic created missing parent")
        parent.mkdir()
        path.mkdir()
        run_writer(code, root, False)
        if not path.is_dir() or leftovers():
            raise SystemExit("human-tabletop diagnostic accepted nonregular target")
    print("PASS: human-tabletop diagnostic redaction/atomic/symlink runtime (8 cases)")


def source_negatives(publisher: str, independent: str) -> None:
    p_cases = (
        ('raw CI log', '          echo "Human tabletop validation completed; raw validator output withheld."\n', '          cat "$log"\n'),
        ("raw diagnostic", "'output': 'Human tabletop validation failed; raw validator output withheld.',", "'output': text[-12000:],"),
        ("symlink", "if candidate.is_symlink():", "if False:"),
        ("missing parent", "if not path.parent.is_dir():", "if False:"),
        ("escape", "path.parent.resolve(strict=True).relative_to(repo)", "path.parent.resolve(strict=True)"),
        ("regular", "if path.exists() and not path.is_file():", "if False:"),
        ("mode", "os.fchmod(fd, existing_mode)", "pass"),
        ("fsync", "os.fsync(handle.fileno())", "pass"),
        ("atomic", "os.replace(tmp_name, path)", "path.write_bytes(payload)"),
        ("cleanup", "os.unlink(tmp_name)", "pass"),
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
                raise SystemExit("human-tabletop negative fixture missing: " + name + "/" + label)
            altered = original.replace(old, new, 1)
            if altered == original:
                raise SystemExit("human-tabletop negative fixture unchanged: " + name + "/" + label)
            try:
                validate(altered, independent) if name == "publisher" else validate(publisher, altered)
            except SystemExit:
                continue
            raise SystemExit("human-tabletop accepted mutation: " + name + "/" + label)
    print("PASS: human-tabletop publisher (10) and independent (10) source mutations")


def predicate_runtime(independent: str) -> None:
    for command in (PR_BASE, PUSH_REF, SHA_FORMAT):
        if independent.count(command) != 1:
            raise SystemExit("human-tabletop runtime predicate missing/ambiguous")
    for command, key, value, allow in (
        (PR_BASE, "GITHUB_BASE_REF", "so", True),
        (PR_BASE, "GITHUB_BASE_REF", "main", False),
        (PR_BASE, "GITHUB_BASE_REF", "", False),
        (PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
        (PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
        (PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
    ):
        result = subprocess.run(["bash", "-e", "-c", command],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("human-tabletop runtime branch/base predicate drift")
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                         ("A" * 40, False), ("g" * 40, False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", SHA_FORMAT],
                                env=dict(os.environ, expected=value), capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("human-tabletop runtime SHA predicate drift")
    print("PASS: human-tabletop branch/base (6) and SHA (6) runtime cases")


def main() -> int:
    publisher, independent = source(PUBLISHER), source(INDEPENDENT)
    validate(publisher, independent)
    validate_trigger_reachability(publisher, publisher=True)
    validate_trigger_reachability(independent, publisher=False)
    prove_trigger_reachability_negatives(publisher, independent)
    predicate_runtime(independent)
    source_negatives(publisher, independent)
    runtime(publisher)
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
