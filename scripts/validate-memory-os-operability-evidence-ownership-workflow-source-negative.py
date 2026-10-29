#!/usr/bin/env python3
"""Independent, read-only source and runtime fault proof for ownership diagnostics."""
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
PUBLISHER = ".github/workflows/operability-evidence-ownership.yml"
INDEPENDENT = ".github/workflows/operability-evidence-ownership-source-negative.yml"
SELF = "scripts/validate-memory-os-operability-evidence-ownership-workflow-source-negative.py"
REVIEWED_PUBLISHER = "3df9af1129f03fbbdce6cc95bdd3adb4dc434802"
REVIEWED_INDEPENDENT = "a842efd4b4224eb5bdb7a57981294ff501c18c76"

PUBLISHER_PUSH_TRIGGER_PATHS = (
    ".github/workflows/operability-evidence-ownership.yml",
    "contracts/operations/requests/operability-evidence-ownership.v1.json",
    "contracts/operations/operability-evidence-ownership-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "scripts/validate-memory-os-operability-evidence-ownership.py",
    "scripts/reconcile-memory-os-operability-evidence-ownership.py",
    "scripts/validate-memory-os-operability-evidence-ownership-reconcile-negative.py",
    "scripts/validate-memory-os-operability.py",
)
INDEPENDENT_PR_TRIGGER_PATHS = (
    ".github/workflows/operability-evidence-ownership.yml",
    ".github/workflows/operability-evidence-ownership-source-negative.yml",
    "scripts/validate-memory-os-operability-evidence-ownership-workflow-source-negative.py",
)
INDEPENDENT_PUSH_TRIGGER_PATHS = (
    ".github/workflows/operability-evidence-ownership.yml",
    ".github/workflows/operability-evidence-ownership-source-negative.yml",
    "scripts/validate-memory-os-operability-evidence-ownership-workflow-source-negative.py",
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
    """Pin push-only ownership publisher and PR/push independent CI paths."""
    expected_push = PUBLISHER_PUSH_TRIGGER_PATHS if publisher else INDEPENDENT_PUSH_TRIGGER_PATHS
    expected_pr = () if publisher else INDEPENDENT_PR_TRIGGER_PATHS
    approved_push = expected_push if push_paths is None else push_paths
    approved_pr = expected_pr if pr_paths is None else pr_paths
    for label, actual, expected in (("PR", approved_pr, expected_pr), ("push", approved_push, expected_push)):
        if len(actual) != len(expected) or len(set(actual)) != len(expected):
            raise SystemExit("ownership CI " + label + " trigger inventory shortened or duplicated")
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    end = "  workflow_dispatch:\n" if publisher else "\npermissions:\n"
    if value.count(push) != 1 or value.count(end) != 1:
        raise SystemExit("ownership CI trigger marker drift")
    if publisher:
        if "  pull_request:" in value or not (value.index(push) < value.index(end)):
            raise SystemExit("ownership publisher must remain push-only")
        events = (("push", push, end, approved_push),)
    else:
        if value.count(pr) != 1 or not (value.index(pr) < value.index(push) < value.index(end)):
            raise SystemExit("ownership independent CI event marker/order drift")
        events = (("PR", pr, push, approved_pr), ("push", push, end, approved_push))
    for label, start, stop, approved_paths in events:
        block = value.split(start, 1)[1].split(stop, 1)[0]
        actual = tuple(line for line in block.splitlines()
                       if line.strip() and not line.lstrip().startswith("#"))
        approved = tuple('      - "' + path + '"' for path in approved_paths)
        if actual != approved:
            raise SystemExit("ownership CI " + label + " exact trigger path drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    """Prove all single-event omissions, additions and shortened inventories."""
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    for label, value, is_publisher, events in (
        ("publisher", publisher, True, (("push", push, "  workflow_dispatch:\n", PUBLISHER_PUSH_TRIGGER_PATHS),)),
        ("independent", independent, False, (
            ("PR", pr, push, INDEPENDENT_PR_TRIGGER_PATHS),
            ("push", push, "\npermissions:\n", INDEPENDENT_PUSH_TRIGGER_PATHS),
        )),
    ):
        for event, start, stop, paths in events:
            start_index = value.index(start) + len(start)
            end_index = value.index(stop, start_index)
            block = value[start_index:end_index]
            for path in paths:
                token = '      - "' + path + '"\n'
                if block.count(token) != 1:
                    raise SystemExit("ownership CI mutation anchor drift: " + path)
                mutated = value[:start_index] + block.replace(token, "", 1) + value[end_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("ownership CI accepted missing " + label + " " + event + " trigger: " + path)
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
                    raise SystemExit("ownership CI accepted " + label + " " + event + " " + name)
            try:
                validate_trigger_reachability(
                    value, publisher=is_publisher,
                    pr_paths=paths[:-1] if event == "PR" else None,
                    push_paths=paths[:-1] if event == "push" else None,
                )
            except SystemExit:
                pass
            else:
                raise SystemExit("ownership CI accepted shortened " + label + " " + event + " inventory")
    print("PASS: ownership CI event triggers (14 removals; 12 additions; 3 shortened inventory negatives)")


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit("ownership source missing/substituted: " + relative) from exc


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate(publisher: str, independent: str) -> None:
    validate_job_authority(publisher, independent)
    publisher_required = (
        "on:\n  push:\n    branches:\n      - so\n",
        "  workflow_dispatch:\n",
        "permissions:\n  contents: write\n",
        '          echo "Ownership validation completed; raw validator output withheld."\n',
        "'output': 'Ownership validation failed; raw validator output withheld.',",
        "if candidate.is_symlink():", "if not path.parent.is_dir():",
        "path.parent.resolve(strict=True).relative_to(repo)",
        "if path.exists() and not path.is_file():",
        "os.fchmod(fd, mode)", "os.fsync(handle.fileno())",
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
        validate_yaml_authority(content, label)
        for token in required:
            if token not in content:
                raise SystemExit("ownership " + label + " missing source: " + token)
        if blob(content) != digest:
            raise SystemExit("ownership " + label + " complete Git blob drift")
    if '          cat "$log"\n' in publisher or "text[-12000:]" in publisher:
        raise SystemExit("ownership raw log disclosure")
    if "path.parent.mkdir(parents=True, exist_ok=True)" in publisher:
        raise SystemExit("ownership diagnostic creates unchecked parent")



def validate_job_authority(publisher: str, independent: str) -> None:
    """Pin push-only inherited-write and independent explicit-read job scopes."""
    reviewed = (
        ("publisher", publisher, (
            "validate", None, None, 8,
        )),
        ("independent", independent, (
            "source-admission",
            "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
            "read", 5,
        )),
    )
    for kind, content, (name, condition, scope, timeout) in reviewed:
        prefix = "ownership " + kind + " "
        if content.count("\njobs:\n") != 1:
            raise SystemExit(prefix + "job mapping shadow drift")
        body = content.split("\njobs:\n", 1)[1]
        actual = [
            line for line in body.splitlines()
            if line.startswith("  ") and len(line) > 2 and line[2] != " "
            and not line.lstrip().startswith("#")
        ]
        if actual != ["  " + name + ":"]:
            raise SystemExit(prefix + "job mapping shadow drift")
        keys = [
            line for line in body.splitlines()
            if line.startswith("    ") and len(line) > 4 and line[4] != " "
            and not line.lstrip().startswith("#")
        ]
        expected = (
            ["    runs-on: ubuntu-latest", "    timeout-minutes: " + str(timeout), "    steps:"]
            if condition is None else
            ["    if: " + condition, "    permissions:", "    runs-on: ubuntu-latest",
             "    timeout-minutes: " + str(timeout), "    steps:"]
        )
        if keys != expected:
            raise SystemExit(prefix + "job key shadow drift")
        if scope is not None:
            lines = body.splitlines()
            leaves: list[str] = []
            for line in lines[lines.index("    permissions:") + 1:]:
                if line.startswith("    ") and len(line) > 4 and line[4] != " ":
                    break
                if line.strip() and not line.lstrip().startswith("#"):
                    leaves.append(line)
            if leaves != ["      contents: " + scope]:
                raise SystemExit(prefix + "job permission leaf shadow drift")


def prove_job_authority_negatives(publisher: str, independent: str) -> None:
    """Reject 21 exact-diagnostic nested job mutations without a blob-only verdict."""
    validate_job_authority(publisher, independent)
    count = 0
    reviewed = (
        ("publisher", publisher, independent, "validate", None, None, 8, True),
        ("independent", independent, publisher, "source-admission",
         "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
         "read", 5, False),
    )
    for kind, content, other, name, condition, scope, timeout, is_publisher in reviewed:
        header = "  " + name + ":\n"
        if content.count(header) != 1:
            raise SystemExit("ownership " + kind + " job fixture header drift")

        def in_job(before: str, after: str) -> str:
            prefix, suffix = content.split(header, 1)
            if before not in suffix:
                raise SystemExit("ownership " + kind + " job fixture anchor drift: " + before[:35])
            return prefix + header + suffix.replace(before, after, 1)

        runner = "    runs-on: ubuntu-latest\n"
        timeout_anchor = "    timeout-minutes: " + str(timeout) + "\n"
        steps = "    steps:\n"
        cases = [
            ("duplicate mapping", content + "\n" + header + "    runs-on: ubuntu-latest\n",
             "job mapping shadow drift"),
            ("quoted mapping", content.replace(header, "  '" + name + "':\n", 1),
             "job mapping shadow drift"),
            ("spaced mapping", content.replace(header, "  " + name + " :\n", 1),
             "job mapping shadow drift"),
            ("runner shadow", in_job(runner, runner + "    runs-on : ubuntu-latest\n"),
             "job key shadow drift"),
            ("timeout shadow", in_job(timeout_anchor, timeout_anchor + "    timeout-minutes : 1\n"),
             "job key shadow drift"),
            ("steps shadow", in_job(steps, "    steps : []\n" + steps),
             "job key shadow drift"),
            ("continuation override", in_job(steps, "    continue-on-error: true\n" + steps),
             "job key shadow drift"),
        ]
        if condition is None:
            cases.extend([
                ("unexpected condition", in_job(runner, "    if: true\n" + runner),
                 "job key shadow drift"),
                ("unexpected job permission", in_job(runner, "    permissions:\n      contents: write\n" + runner),
                 "job key shadow drift"),
            ])
        else:
            condition_anchor = "    if: " + condition + "\n"
            permission = "    permissions:\n      contents: " + scope + "\n"
            cases.extend([
                ("condition shadow", in_job(condition_anchor, condition_anchor + "    if : true\n"),
                 "job key shadow drift"),
                ("permission shadow", in_job(permission, permission + "    permissions :\n      contents: write\n"),
                 "job key shadow drift"),
                ("direct permission change", in_job(permission, permission.replace("contents: read", "contents: write")),
                 "job permission leaf shadow drift"),
                ("spaced permission leaf", in_job(permission, permission + "      contents : write\n"),
                 "job permission leaf shadow drift"),
                ("quoted permission leaf", in_job(permission, permission + "      'contents': write\n"),
                 "job permission leaf shadow drift"),
            ])
        for mutation, changed, diagnostic in cases:
            if changed == content:
                raise SystemExit("ownership " + kind + " unchanged job fixture: " + mutation)
            try:
                if is_publisher:
                    validate_job_authority(changed, other)
                else:
                    validate_job_authority(other, changed)
            except SystemExit as exc:
                expected = "ownership " + kind + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("ownership " + kind + " wrong job diagnostic: "
                                     + mutation + ": " + str(exc)) from exc
            else:
                raise SystemExit("ownership " + kind + " accepted job shadow: " + mutation)
            count += 1
    if count != 21:
        raise SystemExit("ownership nested job negative inventory drift")
    print("PASS: ownership publisher/independent job authority (21 exact-diagnostic negatives)")


def validate_yaml_authority(content: str, kind: str) -> None:
    """Pin effective YAML event/root/permission authority for ownership publisher and CI."""
    if kind == "publisher":
        name = "name: Operability Evidence Ownership"
        events = ["  push:", "  workflow_dispatch:"]
        roots = [name, "on:", "permissions:", "concurrency:", "jobs:"]
        permission = "  contents: write"
    elif kind == "independent":
        name = "name: Operability Evidence Ownership Source Negative"
        events = ["  pull_request:", "  push:"]
        roots = [name, "on:", "permissions:", "jobs:"]
        permission = "  contents: read"
    else:
        raise SystemExit("ownership unknown YAML authority kind")
    prefix = "ownership " + kind + " "
    if (content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1
            or not content.startswith(name + "\n\non:\n")):
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
    if permission_rows != [permission]:
        raise SystemExit(prefix + "permission leaf shadow drift")


def prove_yaml_authority_negatives(publisher: str, independent: str) -> None:
    """Require exact semantic diagnostics for both ownership workflow authorities."""
    count = 0
    for kind, content, permission, alternate in (
        ("publisher", publisher, "write", "read"),
        ("independent", independent, "read", "write"),
    ):
        validate_yaml_authority(content, kind)
        event = content.replace("on:\n", "on:\n  issues:\n", 1)
        if event == content:
            raise SystemExit("ownership " + kind + " event fixture anchor drift")
        cases = [("extra event", event, "event topology drift")]
        for label, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: " + alternate + "\n"),
            ("quoted permissions", "'permissions':\n  contents: " + alternate + "\n"),
            ("spaced jobs", "jobs : {}\n"),
            ("quoted jobs", "'jobs': {}\n"),
        ):
            cases.append((label, content.rstrip("\n") + "\n" + suffix,
                          "root YAML key shadow drift"))
        marker = "\npermissions:\n  contents: " + permission + "\n"
        if content.count(marker) != 1:
            raise SystemExit("ownership " + kind + " permission fixture anchor drift")
        for label, leaf in (
            ("spaced contents", "  contents : " + alternate + "\n"),
            ("quoted contents", "  'contents': " + alternate + "\n"),
        ):
            cases.append((label, content.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        if len(cases) != 9:
            raise SystemExit("ownership " + kind + " YAML fixture count drift")
        for label, mutated, diagnostic in cases:
            if mutated == content:
                raise SystemExit("ownership " + kind + " unchanged YAML fixture: " + label)
            try:
                validate_yaml_authority(mutated, kind)
            except SystemExit as exc:
                expected = "ownership " + kind + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("ownership " + kind + " wrong YAML diagnostic: "
                                     + label + ": " + str(exc)) from exc
            else:
                raise SystemExit("ownership " + kind + " accepted YAML mutation: " + label)
            count += 1
    if count != 18:
        raise SystemExit("ownership YAML negative population drift")
    print("PASS: ownership publisher/independent YAML event/root/permission authority (18 exact-diagnostic negatives)")


def inline_writer(publisher: str) -> str:
    marker = "          python - <<'PY'\n"
    if publisher.count(marker) != 1:
        raise SystemExit("ownership diagnostic inline writer ambiguous")
    start = publisher.index(marker) + len(marker)
    end = publisher.index("\n          PY\n", start)
    lines = publisher[start:end].splitlines()
    if not lines or any(not line.startswith("          ") for line in lines):
        raise SystemExit("ownership diagnostic inline writer indentation drift")
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
    env = dict(os.environ, SOURCE_SHA="a" * 40, OWNERSHIP_EXIT_CODE="1", INJECT_FAULT=fault)
    result = subprocess.run([sys.executable, "-c", injection + code],
                            cwd=root, env=env, capture_output=True, text=True,
                            timeout=10, check=False)
    if (result.returncode == 0) != success:
        raise SystemExit("ownership diagnostic runtime exit drift: " + (fault or "path"))


def runtime(publisher: str) -> None:
    code = inline_writer(publisher)
    with tempfile.TemporaryDirectory(prefix="ownership-diagnostic-negative-") as tmp:
        root = Path(tmp)
        parent = root / "docs/fixtures/memory-os-operability"
        parent.mkdir(parents=True)
        path = parent / "operability-evidence-ownership-diagnostic.last.json"
        leftovers = lambda: list(parent.glob("." + path.name + ".*.tmp"))
        run_writer(code, root, True)
        value = json.loads(path.read_text(encoding="utf-8"))
        if (value.get("sourceCommitSha") != "a" * 40 or
            value.get("output") != "Ownership validation failed; raw validator output withheld." or
            value.get("containsSecrets") is not False or
            value.get("productionEvidence") is not False or
            value.get("productionReady") is not False or leftovers()):
            raise SystemExit("ownership diagnostic positive/redaction drift")
        path.chmod(0o640)
        run_writer(code, root, True)
        if stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise SystemExit("ownership diagnostic mode drift")
        original = path.read_bytes()
        for fault in ("replace", "fsync"):
            run_writer(code, root, False, fault)
            if path.read_bytes() != original or stat.S_IMODE(path.stat().st_mode) != 0o640 or leftovers():
                raise SystemExit("ownership diagnostic fault changed prior bytes/mode/temp")
        external = root / "external-canary"
        external.write_text("external\n", encoding="utf-8")
        path.unlink()
        path.symlink_to(external)
        run_writer(code, root, False)
        if external.read_text(encoding="utf-8") != "external\n" or leftovers():
            raise SystemExit("ownership diagnostic followed target symlink")
        path.unlink()
        outside = root / "outside"
        outside.mkdir()
        (outside / path.name).write_text("outside\n", encoding="utf-8")
        old_parent = root / "old-parent"
        parent.rename(old_parent)
        parent.symlink_to(outside, target_is_directory=True)
        run_writer(code, root, False)
        if (outside / path.name).read_text(encoding="utf-8") != "outside\n":
            raise SystemExit("ownership diagnostic followed parent symlink")
        parent.unlink()
        old_parent.rename(parent)
        shutil.rmtree(parent)
        run_writer(code, root, False)
        if parent.exists():
            raise SystemExit("ownership diagnostic created missing parent")
        parent.mkdir()
        path.mkdir()
        run_writer(code, root, False)
        if not path.is_dir() or leftovers():
            raise SystemExit("ownership diagnostic accepted nonregular target")
    print("PASS: ownership diagnostic redaction/atomic/symlink runtime (8 cases)")


def source_negatives(publisher: str, independent: str) -> None:
    p_cases = (
        ('raw CI log', '          echo "Ownership validation completed; raw validator output withheld."\n', '          cat "$log"\n'),
        ("raw diagnostic", "'output': 'Ownership validation failed; raw validator output withheld.',", "'output': text[-12000:],"),
        ("symlink", "if candidate.is_symlink():", "if False:"),
        ("missing parent", "if not path.parent.is_dir():", "if False:"),
        ("escape", "path.parent.resolve(strict=True).relative_to(repo)", "path.parent.resolve(strict=True)"),
        ("regular", "if path.exists() and not path.is_file():", "if False:"),
        ("mode", "os.fchmod(fd, mode)", "pass"),
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
                raise SystemExit("ownership negative fixture missing: " + name + "/" + label)
            altered = original.replace(old, new, 1)
            if altered == original:
                raise SystemExit("ownership negative fixture unchanged: " + name + "/" + label)
            try:
                validate(altered, independent) if name == "publisher" else validate(publisher, altered)
            except SystemExit:
                continue
            raise SystemExit("ownership accepted mutation: " + name + "/" + label)
    print("PASS: ownership publisher (10) and independent (10) source mutations")


def predicate_runtime(independent: str) -> None:
    for command in (PR_BASE, PUSH_REF, SHA_FORMAT):
        if independent.count(command) != 1:
            raise SystemExit("ownership runtime predicate missing/ambiguous")
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
            raise SystemExit("ownership runtime branch/base predicate drift")
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                         ("A" * 40, False), ("g" * 40, False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", SHA_FORMAT],
                                env=dict(os.environ, expected=value), capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("ownership runtime SHA predicate drift")
    print("PASS: ownership branch/base (6) and SHA (6) runtime cases")


def validate_concurrency_authority(publisher: str) -> None:
    """Bind reviewed operability evidence ownership serialization policy."""
    marker = "\nconcurrency:\n"
    end = "\njobs:\n"
    expected = "  group: operability-evidence-ownership-so\n  cancel-in-progress: false\n"
    if publisher.count(marker) != 1 or publisher.count(end) != 1:
        raise SystemExit("ownership publisher concurrency scope drift")
    actual = publisher.split(marker, 1)[1].split(end, 1)[0]
    if actual != expected:
        raise SystemExit("ownership publisher concurrency scope drift")


def prove_concurrency_authority_negatives(publisher: str) -> None:
    """Reject unsafe cancellation and YAML shadowing of ownership admission."""
    validate_concurrency_authority(publisher)
    group = "  group: operability-evidence-ownership-so\n"
    original = group + "  cancel-in-progress: false\n"
    cases = (
        ("global group", "  group: operability-evidence-ownership-global\n  cancel-in-progress: false\n"),
        ("cancel enabled", original.replace("false", "true")),
        ("duplicate group", original + "  group: unreviewed-global\n"),
        ("duplicate cancellation", original + "  cancel-in-progress: true\n"),
        ("spaced group", original + "  group : unreviewed-global\n"),
        ("quoted group", original + "  'group': unreviewed-global\n"),
        ("spaced cancellation", original + "  cancel-in-progress : true\n"),
        ("quoted cancellation", original + "  'cancel-in-progress': true\n"),
        ("unreviewed leaf", original + "  max-parallel: 10\n"),
        ("removed cancellation", group),
    )
    if publisher.count(original) != 1:
        raise SystemExit("ownership concurrency fixture anchor drift")
    for name, block in cases:
        changed = publisher.replace(original, block, 1)
        if changed == publisher:
            raise SystemExit("ownership unchanged concurrency fixture: " + name)
        try:
            validate_concurrency_authority(changed)
        except SystemExit as exc:
            if str(exc) != "ownership publisher concurrency scope drift":
                raise SystemExit("ownership wrong concurrency diagnostic: " + name + ": " + str(exc)) from exc
        else:
            raise SystemExit("ownership accepted concurrency mutation: " + name)
    print("PASS: ownership publisher concurrency serialization (10 exact-diagnostic negatives)")


def main() -> int:
    publisher, independent = source(PUBLISHER), source(INDEPENDENT)
    validate(publisher, independent)
    prove_yaml_authority_negatives(publisher, independent)
    prove_job_authority_negatives(publisher, independent)
    prove_concurrency_authority_negatives(publisher)
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
