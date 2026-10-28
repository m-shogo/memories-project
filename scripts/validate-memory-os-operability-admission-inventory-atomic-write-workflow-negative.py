#!/usr/bin/env python3
"""Independent complete-source and runtime admission for atomic-write inventory CI."""
from __future__ import annotations
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ".github/workflows/operability-admission-inventory-atomic-write-negative.yml"
GUARD = ".github/workflows/operability-admission-inventory-atomic-write-source-negative.yml"
REPLACEMENT = ".github/workflows/operability-admission-inventory-atomic-replacement-negative.yml"
SELF = "scripts/validate-memory-os-operability-admission-inventory-atomic-write-workflow-negative.py"
MAIN_BLOB = "7e6bf84e53d7406eb345e0835d1d7f346474dc89"
GUARD_BLOB = "1019c867d110e5fc15950d6c74dd17d6f6c3c5ec"
REPLACEMENT_BLOB = "8cf7a9b2c6e01b8a911a9ea96fee56ed51c8b6d8"
D = chr(36)
BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
SHA = '[[ "' + D + 'expected" =~ ^[0-9a-f]{40}$ ]]'
HEAD = 'test "$(git rev-parse HEAD)" = "$expected"'
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"

def read(path: str) -> str:
    target = ROOT / path
    try:
        if target.is_symlink() or not target.is_file():
            raise ValueError("not a regular source file")
        if target.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
            raise ValueError("source path escapes repository")
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeError, RuntimeError, ValueError) as exc:
        raise SystemExit("atomic-write CI source unavailable: " + path) from exc

def validate(main: str, guard: str) -> None:
    common = ((CHECKOUT, 1), (SETUP, 1), (BASE, 1), (REF, 1), (SHA, 1),
              (HEAD, 1), ("          persist-credentials: false\n", 1),
              ("          python " + SELF + "\n", 1),
              ('          test -z "$(git status --porcelain)"\n', 2),
              ("    permissions:\n      contents: read\n", 1))
    main_checks = common + (
        ("  pull_request:\n    branches: [so]\n", 1),
        ("  push:\n    branches:\n      - so\n", 1),
        ("  workflow_dispatch:\n", 1),
        ("  contents: read\n", 2),
        ("      - \"" + GUARD + "\"\n", 2),
        ("      - \"" + SELF + "\"\n", 2),
        ("          PR_HEAD_SHA: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
        ("          ref: " + D + "{{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
        ("    if: github.event_name == 'pull_request' || ((github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so')\n", 1),
    )
    guard_checks = common + (
        ("  pull_request:\n    branches: [so]\n", 1),
        ("  push:\n    branches: [so]\n", 1),
        ("  contents: read\n", 2),
        ("      - \"" + MAIN + "\"\n", 2),
        ("      - \"" + REPLACEMENT + "\"\n", 2),
        ("      - \"" + GUARD + "\"\n", 2),
        ("      - \"" + SELF + "\"\n", 2),
        ("          PR_HEAD_SHA: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
        ("          ref: " + D + "{{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
        ("    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    )
    for label, content, expected_blob, checks in (
        ("atomic publisher", main, MAIN_BLOB, main_checks),
        ("atomic independent", guard, GUARD_BLOB, guard_checks),
    ):
        validate_yaml_authority(content, 'publisher' if label == 'atomic publisher' else 'independent')
        for token, count in checks:
            if content.count(token) != count:
                raise SystemExit(label + " anchor drift: " + repr(token[:75]))
        payload = content.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != expected_blob:
            raise SystemExit(label + " complete source drift")

def validate_yaml_authority(content: str, kind: str) -> None:
    """Pin effective event/root/read-only permission YAML semantics for three atomic CI sources."""
    if kind == "publisher":
        name = "name: Operability Admission Inventory Atomic Write Negative"
        events = ["  push:", "  pull_request:", "  workflow_dispatch:"]
    elif kind == "independent":
        name = "name: Operability Admission Inventory Atomic Write Source Negative"
        events = ["  pull_request:", "  push:"]
    elif kind == "replacement":
        name = "name: Operability Admission Inventory Atomic Replacement Negative"
        events = ["  pull_request:", "  push:"]
    else:
        raise SystemExit("atomic unknown YAML authority kind")
    prefix = "atomic " + kind + " "
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
    roots = [
        line for line in content.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [name, "on:", "permissions:", "jobs:"]:
        raise SystemExit(prefix + "root YAML key shadow drift")
    permission_rows = []
    for line in content.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            permission_rows.append(line)
    if permission_rows != ["  contents: read"]:
        raise SystemExit(prefix + "permission leaf shadow drift")


def prove_yaml_authority_negatives(main: str, guard: str, replacement: str) -> None:
    """Require intended semantic diagnostics for all three atomic CI source authorities."""
    count = 0
    for kind, content in (("publisher", main), ("independent", guard),
                          ("replacement", replacement)):
        validate_yaml_authority(content, kind)
        event = content.replace("on:\n", "on:\n  issues:\n", 1)
        if event == content:
            raise SystemExit("atomic " + kind + " event fixture anchor drift")
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
            raise SystemExit("atomic " + kind + " permission fixture anchor drift")
        for label, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((label, content.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        if len(cases) != 9:
            raise SystemExit("atomic " + kind + " YAML fixture count drift")
        for label, mutated, diagnostic in cases:
            if mutated == content:
                raise SystemExit("atomic " + kind + " unchanged YAML fixture: " + label)
            try:
                validate_yaml_authority(mutated, kind)
            except SystemExit as exc:
                expected = "atomic " + kind + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("atomic " + kind + " wrong YAML diagnostic: "
                                     + label + ": " + str(exc)) from exc
            else:
                raise SystemExit("atomic " + kind + " accepted YAML mutation: " + label)
            count += 1
    if count != 27:
        raise SystemExit("atomic YAML negative population drift")
    print("PASS: atomic publisher/independent/replacement YAML event/root/permission authority (27 exact-diagnostic negatives)")


def runtime(main: str, guard: str) -> None:
    for label, source in (("publisher", main), ("independent", guard)):
        for token in (BASE, REF, SHA, HEAD):
            if source.count(token) != 1:
                raise SystemExit("atomic runtime predicate unreachable: " + label)
        for key, command, values in (
            ("GITHUB_BASE_REF", BASE, (("so", True), ("main", False), ("", False))),
            ("GITHUB_REF", REF, (("refs/heads/so", True), ("refs/heads/main", False), ("refs/tags/v1", False), ("", False))),
        ):
            for value, allowed in values:
                p = subprocess.run(["bash", "-e", "-c", command], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}, capture_output=True, check=False)
                if (p.returncode == 0) != allowed:
                    raise SystemExit("atomic branch predicate drift: " + label + " " + key)
        for value, allowed in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False), ("A" * 40, False), ("g" * 40, False), ("", False), ("$(echo bypass)", False)):
            script = 'expected="' + D + '{PROBE_SHA:-}"\n' + SHA
            p = subprocess.run(["bash", "-e", "-c", script], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}, capture_output=True, check=False)
            if (p.returncode == 0) != allowed:
                raise SystemExit("atomic SHA predicate drift: " + label)
    print("PASS: atomic source runtime branch (14) and SHA (14) cases")

def negatives(main: str, guard: str) -> None:
    cases = (
        ("main", CHECKOUT, "uses: actions/checkout@v4"),
        ("main", SETUP, "uses: actions/setup-python@v5"),
        ("main", BASE, "true"),
        ("main", REF, "true"),
        ("main", SHA, 'test -n "$expected"'),
        ("main", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("main", "  workflow_dispatch:\n", ""),
        ("main", "  pull_request:\n    branches: [so]\n", "  pull_request:\n"),
        ("main", "          python " + SELF + "\n", "          true\n"),
        ("main", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("guard", CHECKOUT, "uses: actions/checkout@v4"),
        ("guard", SETUP, "uses: actions/setup-python@v5"),
        ("guard", BASE, "true"),
        ("guard", REF, "true"),
        ("guard", SHA, 'test -n "$expected"'),
        ("guard", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("guard", "  pull_request:\n    branches: [so]\n", "  pull_request:\n"),
        ("guard", "          python " + SELF + "\n", "          true\n"),
        ("guard", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("guard", '          PR_HEAD_SHA: ' + D + '{{ github.event.pull_request.head.sha }}\n', '          PR_HEAD_SHA: ' + D + '{{ github.sha }}\n'),
    )
    for label, old, new in cases:
        source = main if label == "main" else guard
        if source.count(old) != 1:
            raise SystemExit("atomic negative fixture ambiguous: " + label + " " + old[:60])
        mutated = source.replace(old, new, 1)
        if mutated == source:
            raise SystemExit("atomic negative unchanged: " + label)
        try:
            validate(mutated, guard) if label == "main" else validate(main, mutated)
        except SystemExit:
            continue
        raise SystemExit("atomic source accepted negative: " + label)
    print("PASS: atomic source 20 negative mutations")


def validate_replacement(source: str) -> None:
    validate_yaml_authority(source, 'replacement')
    checks = (
        (CHECKOUT, 1), (SETUP, 1), (BASE, 1), (REF, 1), (SHA, 1), (HEAD, 1),
        ("          persist-credentials: false\n", 1),
        ("  pull_request:\n    branches:\n      - so\n", 1),
        ("  push:\n    branches:\n      - so\n", 1),
        ("  contents: read\n", 2),
        ("          PR_HEAD_SHA: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
        ("          ref: " + D + "{{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
        ("    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
        ('          test -z "$(git status --porcelain)"\n', 2),
    )
    for token, count in checks:
        if source.count(token) != count:
            raise SystemExit("atomic replacement source anchor drift: " + repr(token[:75]))
    payload = source.encode("utf-8")
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if hashlib.sha1(git_blob).hexdigest() != REPLACEMENT_BLOB:
        raise SystemExit("atomic replacement complete source drift")

def runtime_replacement(source: str) -> None:
    for token in (BASE, REF, SHA, HEAD):
        if source.count(token) != 1:
            raise SystemExit("atomic replacement runtime predicate unreachable")
    for key, command, values in (
        ("GITHUB_BASE_REF", BASE, (("so", True), ("main", False), ("", False))),
        ("GITHUB_REF", REF, (("refs/heads/so", True), ("refs/heads/main", False), ("refs/tags/v1", False), ("", False))),
    ):
        for value, allowed in values:
            p = subprocess.run(["bash", "-e", "-c", command], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}, capture_output=True, check=False)
            if (p.returncode == 0) != allowed:
                raise SystemExit("atomic replacement branch predicate drift: " + key)
    for value, allowed in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False), ("A" * 40, False), ("g" * 40, False), ("", False), ("$(echo bypass)", False)):
        script = 'expected="' + D + '{PROBE_SHA:-}"\n' + SHA
        p = subprocess.run(["bash", "-e", "-c", script], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}, capture_output=True, check=False)
        if (p.returncode == 0) != allowed:
            raise SystemExit("atomic replacement SHA predicate drift")
    print("PASS: atomic replacement source runtime branch (7) and SHA (7) cases")

def negatives_replacement(source: str) -> None:
    cases = (
        (CHECKOUT, "uses: actions/checkout@v4"),
        (SETUP, "uses: actions/setup-python@v5"),
        (BASE, "true"),
        (REF, "true"),
        (SHA, 'test -n "$expected"'),
        ("          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ('          PR_HEAD_SHA: ' + D + '{{ github.event.pull_request.head.sha }}\n', '          PR_HEAD_SHA: ' + D + '{{ github.sha }}\n'),
        ("    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", "    if: always()\n"),
    )
    for old, new in cases:
        if source.count(old) != 1:
            raise SystemExit("atomic replacement negative fixture ambiguous: " + old[:65])
        mutated = source.replace(old, new, 1)
        try:
            validate_replacement(mutated)
        except SystemExit:
            continue
        raise SystemExit("atomic replacement accepted source mutation")
    print("PASS: atomic replacement 10 negative source mutations")

def main() -> int:
    main_source, guard_source = read(MAIN), read(GUARD)
    replacement_source = read(REPLACEMENT)
    validate(main_source, guard_source)
    validate_replacement(replacement_source)
    prove_yaml_authority_negatives(main_source, guard_source, replacement_source)
    runtime(main_source, guard_source)
    runtime_replacement(replacement_source)
    negatives(main_source, guard_source)
    negatives_replacement(replacement_source)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
