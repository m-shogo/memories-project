#!/usr/bin/env python3
"""Fail-closed source/permission admission for derived operability inventory writer."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/operability-admission-inventory.yml"
INDEPENDENT = ".github/workflows/operability-admission-inventory-source-negative.yml"
SELF = "scripts/validate-memory-os-operability-admission-inventory-workflow-negative.py"
REVIEWED_PUBLISHER = "1792edd78dc74c49d22e50145a4b1dc41b61bb24"
REVIEWED_INDEPENDENT = "1cc32e55bcfca0d8d1d2be6f4d4222260a327123"
D = chr(36)
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
PUBLISHER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
CAPTURE = "      - name: Capture exact inventory source\n"
MAIN_REQUIRED = (
    ("push branch", "  push:\n    branches:\n      - so\n    paths:\n", 1),
    ("dispatch", "  workflow_dispatch:\n", 1),
    ("script trigger", '      - "' + SELF + '"\n', 1),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 1),
    ("checkout SHA", CHECKOUT, 1),
    ("setup SHA", SETUP, 1),
    ("writer credentials", "          persist-credentials: true\n", 1),
    ("writer branch", PUSH_REF, 1),
    ("writer event", EVENT, 1),
    ("SHA format", SHA_FORMAT, 1),
    ("publisher scope", PUBLISHER_SCOPE, 1),
    ("writer self execution", "\n          python " + SELF + "\n", 1),
    ("retry self execution", "\n            python " + SELF + "\n", 1),
    ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', 1),
    ("writer SHA source", 'expected="' + D + '{GITHUB_SHA:-}"', 1),
    ("latest reset", "            git reset --hard origin/so\n", 1),
    ("capture step", CAPTURE, 1),
    ("root read token", "permissions:\n  contents: read\n", 1),
    ("writer write token", "      contents: write\n", 1),
    ("bounded retry job budget", "    timeout-minutes: 20\n", 1),
)
INDEPENDENT_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("self trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("script trigger", '      - "' + SELF + '"\n', 2),
    ("checkout SHA", CHECKOUT, 1),
    ("setup SHA", SETUP, 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR base", PR_BASE, 1),
    ("push branch", PUSH_REF, 1),
    ("SHA format", SHA_FORMAT, 1),
    ("self execution", "          python " + SELF + "\n", 1),
    ("read token", "  contents: read\n", 2),
    ("event scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
)


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if not path.is_file() or path.is_symlink():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        raise SystemExit("operability inventory CI source missing or substituted: " + relative) from exc


def validate(publisher: str, independent: str) -> None:
    for name, content, required, digest in (
        ("publisher", publisher, MAIN_REQUIRED, REVIEWED_PUBLISHER),
        ("independent", independent, INDEPENDENT_REQUIRED, REVIEWED_INDEPENDENT),
    ):
        validate_yaml_authority(content, name)
        for label, token, count in required:
            if content.count(token) != count:
                raise SystemExit("operability inventory " + name + " source drift: " + label)
        data = content.encode("utf-8")
        blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        if hashlib.sha1(blob).hexdigest() != digest:
            raise SystemExit("operability inventory " + name + " complete source drift")
    validate_concurrency_authority(publisher)



def validate_concurrency_authority(publisher: str) -> None:
    """Pin the reviewed noncancelling derived inventory publisher group."""
    marker = "\nconcurrency:\n"
    end = "\njobs:\n"
    expected = "  group: operability-admission-inventory-so\n  cancel-in-progress: false\n"
    if (publisher.count(marker) != 1 or publisher.count(end) != 1
            or publisher.split(marker, 1)[1].split(end, 1)[0] != expected):
        raise SystemExit("operability inventory publisher concurrency scope drift")


def prove_concurrency_authority_negatives(publisher: str) -> None:
    """Ten exact-diagnostic negatives for inventory serialization and cancellation."""
    validate_concurrency_authority(publisher)
    original = "  group: operability-admission-inventory-so\n  cancel-in-progress: false\n"
    cases = (
        ("global group", "  group: operability-admission-inventory-global\n"
         "  cancel-in-progress: false\n"),
        ("cancellation enabled", original.replace("false", "true")),
        ("duplicate group", original + "  group: unreviewed-global\n"),
        ("duplicate cancellation", original + "  cancel-in-progress: true\n"),
        ("spaced group", original + "  group : unreviewed-global\n"),
        ("quoted group", original + "  'group': unreviewed-global\n"),
        ("spaced cancellation", original + "  cancel-in-progress : true\n"),
        ("quoted cancellation", original + "  'cancel-in-progress': true\n"),
        ("unreviewed leaf", original + "  max-parallel: 100\n"),
        ("removed cancellation", original.replace("  cancel-in-progress: false\n", "")),
    )
    if publisher.count(original) != 1:
        raise SystemExit("operability inventory concurrency fixture anchor drift")
    for name, replacement in cases:
        changed = publisher.replace(original, replacement, 1)
        if changed == publisher:
            raise SystemExit("operability inventory unchanged concurrency fixture: " + name)
        try:
            validate_concurrency_authority(changed)
        except SystemExit as exc:
            if str(exc) != "operability inventory publisher concurrency scope drift":
                raise SystemExit(
                    "operability inventory wrong concurrency diagnostic: " + name + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("operability inventory accepted concurrency mutation: " + name)
    print("PASS: operability inventory publisher concurrency (10 exact-diagnostic negatives)")


def validate_yaml_authority(content: str, kind: str) -> None:
    """Reject effective YAML event/root/permission shadows without relying on blob identity."""
    if kind == "publisher":
        expected_name = "name: Operability Admission Inventory"
        events = ["  push:", "  workflow_dispatch:"]
        roots = [expected_name, "on:", "permissions:", "concurrency:", "jobs:"]
    elif kind == "independent":
        expected_name = "name: Operability Admission Inventory Source Negative"
        events = ["  pull_request:", "  push:"]
        roots = [expected_name, "on:", "permissions:", "jobs:"]
    else:
        raise SystemExit("operability inventory unknown YAML authority kind")
    prefix = "operability inventory " + kind + " "
    if (content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1
            or not content.startswith(expected_name + "\n\non:\n")):
        raise SystemExit(prefix + "event header drift")
    event_block = content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    event_keys = [
        line for line in event_block.splitlines()
        if line.startswith("  ") and not line.startswith("    ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if event_keys != events:
        raise SystemExit(prefix + "event topology drift")
    root_keys = [
        line for line in content.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if root_keys != roots:
        raise SystemExit(prefix + "root YAML key shadow drift")
    permission_rows = []
    for line in content.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            permission_rows.append(line)
    if permission_rows != ["  contents: read"]:
        raise SystemExit(prefix + "permission leaf shadow drift")
    jobs = {
        "publisher": (
            "generate",
            "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
            "write", 20,
        ),
        "independent": (
            "source-admission",
            "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
            "read", 5,
        ),
    }
    job, condition, scope, timeout = jobs[kind]
    body = content.split("\njobs:\n", 1)[1]
    job_rows = [
        line for line in body.splitlines()
        if line.startswith("  ") and not line.startswith("   ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_rows != ["  " + job + ":"]:
        raise SystemExit(prefix + "job mapping shadow drift")
    job_keys = [
        line for line in body.splitlines()
        if line.startswith("    ") and not line.startswith("     ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_keys != [
        condition, "    permissions:", "    runs-on: ubuntu-latest",
        "    timeout-minutes: " + str(timeout), "    steps:",
    ]:
        raise SystemExit(prefix + "job key/permission shadow drift")
    block = body.split("  " + job + ":\n", 1)[1]
    marker = "    permissions:\n"
    if (block.count(marker) != 1
            or block.split(marker, 1)[1].split("    runs-on: ubuntu-latest\n", 1)[0]
            != "      contents: " + scope + "\n"):
        raise SystemExit(prefix + "job permission scope drift")


def prove_yaml_authority_negatives(publisher: str, independent: str) -> None:
    """Pin intended diagnostics for both publisher and independent CI shadow fixtures."""
    count = 0
    for kind, content in (("publisher", publisher), ("independent", independent)):
        validate_yaml_authority(content, kind)
        event = content.replace("on:\n", "on:\n  issues:\n", 1)
        if event == content:
            raise SystemExit("operability inventory " + kind + " event fixture anchor drift")
        cases = [("extra event", event, "event topology drift")]
        for label, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: write\n"),
            ("quoted permissions", "'permissions':\n  contents: write\n"),
            ("spaced jobs", "jobs : {}\n"),
            ("quoted jobs", "'jobs': {}\n"),
        ):
            cases.append((label, content.rstrip("\n") + "\n" + suffix,
                          "root YAML key shadow drift"))
        marker = "\npermissions:\n  contents: read\n"
        if content.count(marker) != 1:
            raise SystemExit("operability inventory " + kind + " permission fixture anchor drift")
        for label, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((label, content.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        jobs = {
            "publisher": (
                "generate",
                "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
                "write",
            ),
            "independent": (
                "source-admission",
                "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
                "read",
            ),
        }
        job, condition, scope = jobs[kind]
        for label, suffix in (
            ("duplicate job", "  " + job + ": {}\n"),
            ("spaced job", "  " + job + " : {}\n"),
            ("quoted job", "  '" + job + "': {}\n"),
        ):
            cases.append((label, content.rstrip("\n") + "\n" + suffix,
                          "job mapping shadow drift"))
        runs_on = "    runs-on: ubuntu-latest\n"
        permission = "    permissions:\n      contents: " + scope + "\n"
        if (content.count(runs_on) != 1 or content.count(permission) != 1
                or content.count(condition + "\n") != 1):
            raise SystemExit("operability inventory " + kind + " job fixture anchor drift")
        for label, leaf in (
            ("job permission", "    permissions:\n      contents: write\n"),
            ("spaced job permission", "    permissions :\n      contents: write\n"),
            ("quoted job permission", "    'permissions':\n      contents: write\n"),
            ("job timeout shadow", "    timeout-minutes : 0\n"),
            ("job continuation shadow", "    continue-on-error: true\n"),
        ):
            cases.append((label, content.replace(runs_on, runs_on + leaf, 1),
                          "job key/permission shadow drift"))
        cases.append(("job event bypass", content.replace(condition + "\n", "    if: true\n", 1),
                      "job key/permission shadow drift"))
        alternate = "read" if scope == "write" else "write"
        for label, replacement in (
            ("direct scope drift", "    permissions:\n      contents: " + alternate + "\n"),
            ("spaced contents", permission + "      contents : write\n"),
            ("quoted contents", permission + "      'contents': write\n"),
        ):
            cases.append((label, content.replace(permission, replacement, 1),
                          "job permission scope drift"))
        if len(cases) != 21:
            raise SystemExit("operability inventory " + kind + " YAML fixture count drift")
        for label, mutated, diagnostic in cases:
            if mutated == content:
                raise SystemExit("operability inventory " + kind + " unchanged YAML fixture: " + label)
            try:
                validate_yaml_authority(mutated, kind)
            except SystemExit as exc:
                expected = "operability inventory " + kind + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("operability inventory " + kind + " wrong YAML diagnostic: "
                                     + label + ": " + str(exc)) from exc
            else:
                raise SystemExit("operability inventory " + kind + " accepted YAML mutation: " + label)
            count += 1
    if count != 42:
        raise SystemExit("operability inventory YAML negative population drift")
    print("PASS: operability inventory publisher/independent YAML event/root/permission authority (42 exact-diagnostic negatives)")


def runtime(publisher: str, independent: str) -> None:
    for name, content, cases in (
        ("publisher", publisher, (
            ("push so", PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
            ("push main", PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
            ("push tag", PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
        )),
        ("independent", independent, (
            ("PR so", PR_BASE, "GITHUB_BASE_REF", "so", True),
            ("PR main", PR_BASE, "GITHUB_BASE_REF", "main", False),
            ("PR absent", PR_BASE, "GITHUB_BASE_REF", "", False),
            ("push so", PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
            ("push main", PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
            ("push tag", PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
        )),
    ):
        for label, command, key, value, allow in cases:
            if content.count(command) != 1:
                raise SystemExit("operability inventory " + name + " runtime command missing: " + label)
            result = subprocess.run(["bash", "-e", "-c", command],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                    capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("operability inventory " + name + " runtime branch drift: " + label)
    for event, allow in (("push", True), ("workflow_dispatch", True), ("pull_request", False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", EVENT],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event},
                                capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("operability inventory writer event runtime drift: " + event)
    print("PASS: operability inventory writer/independent branch runtime (9 cases), writer event runtime (4 cases)")


def negatives(publisher: str, independent: str) -> None:
    publisher_cases = (
        ("push target", "  push:\n    branches:\n      - so\n", "  push:\n"),
        ("dispatch", "  workflow_dispatch:\n", ""),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("writer credentials", "          persist-credentials: true\n", ""),
        ("writer branch", PUSH_REF, ""),
        ("writer event", EVENT, ""),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("broad publisher scope", PUBLISHER_SCOPE, "    if: always()\n"),
        ("writer self guard", "\n          python " + SELF + "\n", ""),
        ("retry self guard", "\n            python " + SELF + "\n", ""),
        ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', "true"),
        ("writer SHA source", 'expected="' + D + '{GITHUB_SHA:-}"', 'expected="$PR_HEAD_SHA"'),
        ("latest reset", "            git reset --hard origin/so\n", ""),
        ("root write token", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("writer token removed", "      contents: write\n", "      contents: read\n"),
        ("insufficient retry budget", "    timeout-minutes: 20\n", "    timeout-minutes: 10\n"),
        ("capture step removed", CAPTURE, ""),
        ("unreviewed Action", CAPTURE, "      - uses: unreviewed/action@v1\n" + CAPTURE),
        ("unreviewed shell", CAPTURE, "      - run: echo unreviewed\n" + CAPTURE),
    )
    independent_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("self trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("persist credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR base", PR_BASE, ""),
        ("push branch", PUSH_REF, ""),
        ("event scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", "    if: always()\n"),
        ("self execution", "          python " + SELF + "\n", ""),
        ("injected Action", "      - name: Prove inventory source admission\n", "      - uses: unreviewed/action@v1\n      - name: Prove inventory source admission\n"),
        ("injected shell", "      - name: Prove inventory source admission\n", "      - run: echo unreviewed\n      - name: Prove inventory source admission\n"),
    )
    for target, cases in (("publisher", publisher_cases), ("independent", independent_cases)):
        for label, old, new in cases:
            original = publisher if target == "publisher" else independent
            if old not in original:
                raise SystemExit("operability inventory negative fixture missing: " + target + " " + label)
            mutated = original.replace(old, new, 1)
            if mutated == original:
                raise SystemExit("operability inventory negative fixture unchanged: " + target + " " + label)
            try:
                validate(mutated, independent) if target == "publisher" else validate(publisher, mutated)
            except SystemExit:
                continue
            raise SystemExit("operability inventory accepted source mutation: " + target + " " + label)
    print(f"PASS: operability inventory publisher source admission ({len(publisher_cases)} negatives), independent source admission ({len(independent_cases)} negatives)")



def diagnostic_script(publisher: str) -> str:
    marker = "          python - <<'PY'\n"
    if publisher.count(marker) != 1:
        raise SystemExit("inventory diagnostic inline writer missing or ambiguous")
    begin = publisher.index(marker) + len(marker)
    end = publisher.index("\n          PY\n", begin)
    lines = publisher[begin:end].splitlines()
    if not lines or any(not line.startswith("          ") for line in lines):
        raise SystemExit("inventory diagnostic inline writer indentation drift")
    return "\n".join(line[10:] for line in lines) + "\n"


def validate_diagnostic_source(publisher: str) -> str:
    if '          cat "$log"\n' in publisher or "text[-12000:]" in publisher:
        raise SystemExit("inventory diagnostic raw log disclosure")
    script = diagnostic_script(publisher)
    required = (
        "'output': 'Inventory validation failed; raw validator output withheld.',",
        "if candidate.is_symlink():",
        "if not path.parent.is_dir():",
        "path.parent.resolve(strict=True).relative_to(repo)",
        "if path.exists() and not path.is_file():",
        "os.fchmod(fd, mode)",
        "os.fsync(handle.fileno())",
        "os.replace(temp_name, path)",
        "os.unlink(temp_name)",
    )
    for token in required:
        if script.count(token) != 1:
            raise SystemExit("inventory diagnostic missing runtime guard: " + token)
    if "/tmp/operability-admission-inventory.log" in script:
        raise SystemExit("inventory diagnostic reads untrusted raw log")
    return script


def diagnostic_runtime(publisher: str) -> None:
    import json
    import stat
    import sys
    import tempfile
    script = validate_diagnostic_source(publisher)
    guard = "              if candidate.is_symlink():\n"
    if publisher.count(guard) != 1:
        raise SystemExit("inventory diagnostic symlink guard ambiguous")
    try:
        validate_diagnostic_source(publisher.replace(guard, "", 1))
    except SystemExit as exc:
        if "if candidate.is_symlink():" not in str(exc):
            raise SystemExit("inventory diagnostic symlink negative wrong rejection") from exc
    else:
        raise SystemExit("inventory diagnostic accepted removed symlink guard")

    with tempfile.TemporaryDirectory(prefix="inventory-diagnostic-") as directory:
        root = Path(directory)
        parent = root / "docs/fixtures/memory-os-operability"
        parent.mkdir(parents=True)
        path = parent / "operability-admission-inventory-diagnostic.last.json"
        env = dict(os.environ, SOURCE_SHA="a" * 40, INVENTORY_EXIT_CODE="1")
        def run(source: str):
            return subprocess.run([sys.executable, "-c", source], cwd=root, env=env,
                                  capture_output=True, text=True, check=False, timeout=15)
        positive = run(script)
        if positive.returncode != 0:
            raise SystemExit("inventory diagnostic positive writer failed: " + positive.stderr[-600:])
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("output") != "Inventory validation failed; raw validator output withheld.":
            raise SystemExit("inventory diagnostic failed redaction")
        if value.get("productionReady") is not False or value.get("productionEvidence") is not False:
            raise SystemExit("inventory diagnostic claimed production authority")
        path.chmod(0o640)
        positive = run(script)
        if positive.returncode != 0 or stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise SystemExit("inventory diagnostic failed mode preservation")
        previous = path.read_bytes()
        for label, anchor in (("replace", "os.replace(temp_name, path)"),
                              ("fsync", "os.fsync(handle.fileno())")):
            if script.count(anchor) != 1:
                raise SystemExit("inventory diagnostic fault anchor drift: " + label)
            fault = script.replace(anchor, "raise OSError('synthetic inventory " + label + " failure')", 1)
            result = run(fault)
            if result.returncode == 0 or "synthetic inventory " + label + " failure" not in result.stderr:
                raise SystemExit("inventory diagnostic fault not reached: " + label)
            if path.read_bytes() != previous or stat.S_IMODE(path.stat().st_mode) != 0o640:
                raise SystemExit("inventory diagnostic rollback changed bytes or mode: " + label)
            if list(parent.glob(".operability-admission-inventory-diagnostic.last.json.*.tmp")):
                raise SystemExit("inventory diagnostic leaked temporary file: " + label)
        outside = root / "outside-canary"
        outside.write_bytes(b"OUTSIDE_CANARY")
        path.unlink()
        path.symlink_to(outside)
        result = run(script)
        if result.returncode == 0 or "must not be a symlink" not in result.stderr:
            raise SystemExit("inventory diagnostic followed target symlink")
        if outside.read_bytes() != b"OUTSIDE_CANARY" or not path.is_symlink():
            raise SystemExit("inventory diagnostic altered external canary")
        path.unlink()
        parent.rmdir()
        outside_parent = root / "outside-parent"
        outside_parent.mkdir()
        parent.symlink_to(outside_parent, target_is_directory=True)
        result = run(script)
        if result.returncode == 0 or "must not be a symlink" not in result.stderr:
            raise SystemExit("inventory diagnostic followed parent symlink")
        if list(outside_parent.iterdir()):
            raise SystemExit("inventory diagnostic wrote outside repository fixture")
        parent.unlink()
        result = run(script)
        if result.returncode == 0 or "parent missing" not in result.stderr or parent.exists():
            raise SystemExit("inventory diagnostic created missing parent")
    print("PASS: inventory diagnostic redaction, symlink containment and atomic rollback (7 cases)")


def main() -> int:
    publisher = source(PUBLISHER)
    independent = source(INDEPENDENT)
    validate(publisher, independent)
    prove_yaml_authority_negatives(publisher, independent)
    prove_concurrency_authority_negatives(publisher)
    diagnostic_runtime(publisher)
    runtime(publisher, independent)
    negatives(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
