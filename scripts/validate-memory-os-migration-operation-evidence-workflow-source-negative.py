#!/usr/bin/env python3
"""Read-only exact-source and runtime negative proof for migration operation evidence CI."""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/migration-operation-evidence.yml"
INDEPENDENT = ".github/workflows/migration-operation-evidence-source-negative.yml"
SELF = "scripts/validate-memory-os-migration-operation-evidence-workflow-source-negative.py"
PUBLISHER_SHA = "fae2ea025d19fa8fce0b319a6392d67f368247fa"
INDEPENDENT_SHA = "a148fe425e74a2bab16973771b6137e95be20479"

PUBLISHER_TRIGGER_PATHS = (
    ".github/workflows/migration-operation-evidence.yml",
    ".github/workflows/migration-operation-evidence-source-negative.yml",
    "scripts/validate-memory-os-migration-operation-evidence-workflow-source-negative.py",
    "contracts/operations/migration-operation-evidence-contract.v1.json",
    "contracts/operations/migration-lifecycle-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "scripts/migration_operation_evidence_lib.py",
    "scripts/create-memory-os-migration-operation-evidence.py",
    "scripts/validate-memory-os-migration-operation-evidence.py",
    "scripts/validate-memory-os-migration-operation-library-authority-negative.py",
    "scripts/validate-memory-os-migration-operation-evidence-reconcile-negative.py",
    "scripts/validate-memory-os-migration-operation-reconcile-authority-negative.py",
    "scripts/reconcile-memory-os-migration-operation-evidence.py",
    "scripts/validate-memory-os-migration-lifecycle.py",
    "scripts/validate-memory-os-operability.py",
    "docs/evidence/migration-operations/**",
    "docs/fixtures/memory-os-operability/migration-operation-record.template.v1.json",
)
INDEPENDENT_TRIGGER_PATHS = (
    ".github/workflows/migration-operation-evidence.yml",
    ".github/workflows/migration-operation-evidence-source-negative.yml",
    "scripts/validate-memory-os-migration-operation-evidence-workflow-source-negative.py",
)
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
PR_SHA = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA = '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'



def validate_trigger_reachability(
    source: str, *, publisher: bool, trigger_paths: tuple[str, ...] | None = None
) -> None:
    """Pin every reviewed PR/push path independently of the full Git blob."""
    expected = PUBLISHER_TRIGGER_PATHS if publisher else INDEPENDENT_TRIGGER_PATHS
    paths = expected if trigger_paths is None else trigger_paths
    if len(paths) != len(expected) or len(set(paths)) != len(expected):
        raise SystemExit("migration operation CI trigger inventory shortened or duplicated")
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    end = "  workflow_dispatch:\n" if publisher else "\npermissions:\n"
    first, second = (push, pr) if publisher else (pr, push)
    if any(source.count(marker) != 1 for marker in (first, second, end)):
        raise SystemExit("migration operation CI trigger marker drift")
    if not (source.index(first) < source.index(second) < source.index(end)):
        raise SystemExit("migration operation CI event ordering drift")
    for event, start, stop in (("first", first, second), ("second", second, end)):
        block = source.split(start, 1)[1].split(stop, 1)[0]
        actual = tuple(line for line in block.splitlines()
                       if line.strip() and not line.lstrip().startswith("#"))
        approved = tuple('      - "' + path + '"' for path in paths)
        if actual != approved:
            raise SystemExit("migration operation CI " + event + " exact trigger inventory drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    """Prove every single-event omission, quoted/unquoted addition and inventory truncation."""
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    for label, source, paths, is_publisher in (
        ("publisher", publisher, PUBLISHER_TRIGGER_PATHS, True),
        ("independent", independent, INDEPENDENT_TRIGGER_PATHS, False),
    ):
        first, second = (push, pr) if is_publisher else (pr, push)
        end = "  workflow_dispatch:\n" if is_publisher else "\npermissions:\n"
        for event, start, stop in (("first", first, second), ("second", second, end)):
            start_index = source.index(start) + len(start)
            end_index = source.index(stop, start_index)
            block = source[start_index:end_index]
            for path in paths:
                token = '      - "' + path + '"\n'
                if block.count(token) != 1:
                    raise SystemExit("migration operation CI mutation anchor drift: " + path)
                mutated = source[:start_index] + block.replace(token, "", 1) + source[end_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("migration operation CI accepted missing " + label + " " + event + " trigger: " + path)
            for name, injection in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                mutated = source[:start_index] + injection + source[start_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("migration operation CI accepted " + label + " " + event + " " + name)
        try:
            validate_trigger_reachability(source, publisher=is_publisher, trigger_paths=paths[:-1])
        except SystemExit:
            pass
        else:
            raise SystemExit("migration operation CI accepted shortened " + label + " inventory")
    print("PASS: migration operation CI event triggers (40 removals; 16 additions; 2 shortened inventory negatives)")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("migration operation CI source guard: " + message)


def read(path: str) -> str:
    file = ROOT / path
    require(file.is_file() and not file.is_symlink(), "missing or symlinked source: " + path)
    require(file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() == path,
            "source escaped root: " + path)
    return file.read_text(encoding="utf-8")


def check_source(name: str, source: str, expected: str, required: tuple[tuple[str, int], ...]) -> None:
    for token, count in required:
        require(source.count(token) == count, name + " required source inventory drift: " + token[:55])
    for forbidden in ("pull_request_target:", "secrets.", "actions/checkout@v4", "actions/setup-python@v5"):
        require(forbidden not in source, name + " unreviewed source")
    data = source.encode("utf-8")
    digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    require(digest == expected, name + " complete Git blob drift")


PUBLISHER_REQUIRED = (
    ("  pull_request:\n    branches:\n      - so\n", 1),
    ("  push:\n    branches:\n      - so\n", 1),
    ("  workflow_dispatch:\n", 1),
    ('      - "' + PUBLISHER + '"\n', 2),
    ('      - "' + INDEPENDENT + '"\n', 2),
    ('      - "' + SELF + '"\n', 2),
    (CHECKOUT, 2),
    (SETUP, 2),
    ("persist-credentials: false", 1),
    ("persist-credentials: true", 1),
    (WRITER_SCOPE, 1),
    (PR_BASE, 1),
    (WRITER_REF, 1),
    (PR_SHA, 1),
    (WRITER_SHA, 1),
    ("python " + SELF, 2),
    ("permissions:\n  contents: read\n", 1),
    ("      contents: write\n", 1),
    ("      contents: read\n", 1),
)
INDEPENDENT_REQUIRED = (
    ("  pull_request:\n    branches:\n      - so\n", 1),
    ("  push:\n    branches:\n      - so\n", 1),
    ('      - "' + PUBLISHER + '"\n', 2),
    ('      - "' + INDEPENDENT + '"\n', 2),
    ('      - "' + SELF + '"\n', 2),
    (CHECKOUT, 1),
    (SETUP, 1),
    ("persist-credentials: false", 1),
    (PR_BASE, 1),
    (WRITER_REF, 1),
    (PR_SHA, 1),
    ("python " + SELF, 1),
    ("permissions:\n  contents: read\n", 1),
    ("      contents: read\n", 1),
)


def validate(publisher: str, independent: str) -> None:
    check_source("publisher", publisher, PUBLISHER_SHA, PUBLISHER_REQUIRED)
    check_source("independent", independent, INDEPENDENT_SHA, INDEPENDENT_REQUIRED)
    validate_trigger_reachability(publisher, publisher=True)
    validate_trigger_reachability(independent, publisher=False)
    validate_yaml_authority(publisher, 'publisher')
    validate_yaml_authority(independent, 'independent')


def validate_yaml_authority(content: str, kind: str) -> None:
    """Independently bind effective YAML event, root and read-only permission semantics."""
    if kind == "publisher":
        name = "name: Migration Operation Evidence"
        events = ["  push:", "  pull_request:", "  workflow_dispatch:"]
        roots = [name, "on:", "permissions:", "concurrency:", "jobs:"]
    elif kind == "independent":
        name = "name: Migration Operation Evidence Source Negative"
        events = ["  pull_request:", "  push:"]
        roots = [name, "on:", "permissions:", "jobs:"]
    else:
        raise SystemExit("migration operation unknown YAML authority kind")
    prefix = "migration operation " + kind + " "
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
    if permission_rows != ["  contents: read"]:
        raise SystemExit(prefix + "permission leaf shadow drift")


def prove_yaml_authority_negatives(publisher: str, independent: str) -> None:
    """Require exact semantic diagnostics for publisher and independent CI shadows."""
    count = 0
    for kind, content in (("publisher", publisher), ("independent", independent)):
        validate_yaml_authority(content, kind)
        event = content.replace("on:\n", "on:\n  issues:\n", 1)
        if event == content:
            raise SystemExit("migration operation " + kind + " event fixture anchor drift")
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
            raise SystemExit("migration operation " + kind + " permission fixture anchor drift")
        for label, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((label, content.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        if len(cases) != 9:
            raise SystemExit("migration operation " + kind + " YAML fixture count drift")
        for label, mutated, diagnostic in cases:
            if mutated == content:
                raise SystemExit("migration operation " + kind + " unchanged YAML fixture: " + label)
            try:
                validate_yaml_authority(mutated, kind)
            except SystemExit as exc:
                expected = "migration operation " + kind + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("migration operation " + kind + " wrong YAML diagnostic: "
                                     + label + ": " + str(exc)) from exc
            else:
                raise SystemExit("migration operation " + kind + " accepted YAML mutation: " + label)
            count += 1
    if count != 18:
        raise SystemExit("migration operation YAML negative population drift")
    print("PASS: migration operation publisher/independent YAML event/root/permission authority (18 exact-diagnostic negatives)")


def negative_proofs(publisher: str, independent: str) -> None:
    cases = (
        ("publisher PR base", True, PR_BASE, "true"),
        ("publisher writer ref", True, WRITER_REF, "true"),
        ("publisher writer scope", True, WRITER_SCOPE, "    if: always()"),
        ("publisher PR SHA", True, PR_SHA, 'test -n "$expected"'),
        ("publisher writer SHA", True, WRITER_SHA, 'test -n "$GITHUB_SHA"'),
        ("publisher checkout pin", True, CHECKOUT, "uses: actions/checkout@v4"),
        ("publisher setup pin", True, SETUP, "uses: actions/setup-python@v5"),
        ("publisher event scope", True, "  workflow_dispatch:\n", "  pull_request_target:\n"),
        ("publisher digest-only drift", True, "\n", "\n# unauthorized publisher source drift\n"),
        ("publisher credentials", True, "persist-credentials: false", "persist-credentials: true"),
        ("publisher self guard", True, "python " + SELF, "echo skip"),
        ("independent PR base", False, PR_BASE, "true"),
        ("independent writer ref", False, WRITER_REF, "true"),
        ("independent SHA", False, PR_SHA, 'test -n "$expected"'),
        ("independent checkout pin", False, CHECKOUT, "uses: actions/checkout@v4"),
        ("independent setup pin", False, SETUP, "uses: actions/setup-python@v5"),
        ("independent event scope", False, "  push:\n    branches:\n      - so\n", "  workflow_dispatch:\n"),
        ("independent digest-only drift", False, "\n", "\n# unauthorized independent source drift\n"),
        ("independent credentials", False, "persist-credentials: false", "persist-credentials: true"),
        ("independent self guard", False, "python " + SELF, "echo skip"),
    )
    for label, publisher_case, before, after in cases:
        original = publisher if publisher_case else independent
        require(before in original, "mutation anchor missing: " + label)
        changed = original.replace(before, after, 1)
        require(changed != original, "mutation unchanged: " + label)
        try:
            validate(changed, independent) if publisher_case else validate(publisher, changed)
        except SystemExit as exc:
            expected = ("complete Git blob drift" if "digest-only" in label
                        else "required source inventory drift")
            reason = str(exc)
            require(reason.startswith("migration operation CI source guard: ")
                    and expected in reason,
                    "negative rejected for wrong reason: " + label + ": " + reason)
            continue
        raise SystemExit("migration operation source negative accepted: " + label)
    print(f"PASS: migration operation CI source negatives ({len(cases)} cases)")


def runtime_proofs() -> None:
    for label, script, key, value, expected in (
        ("PR so", PR_BASE, "GITHUB_BASE_REF", "so", True),
        ("PR main", PR_BASE, "GITHUB_BASE_REF", "main", False),
        ("writer so", WRITER_REF, "GITHUB_REF", "refs/heads/so", True),
        ("writer main", WRITER_REF, "GITHUB_REF", "refs/heads/main", False),
    ):
        result = subprocess.run(["bash", "-e", "-c", script],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                capture_output=True, check=False)
        require((result.returncode == 0) == expected, "runtime branch drift: " + label)
    for predicate, variable in ((PR_SHA, "expected"), (WRITER_SHA, "GITHUB_SHA")):
        for value, allowed in (("a" * 40, True), ("0" * 40, True), ("A" * 40, False),
                               ("g" * 40, False), ("a" * 39, False), ("a" * 41, False), ("", False)):
            result = subprocess.run(["bash", "-e", "-c", predicate],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), variable: value},
                                    capture_output=True, check=False)
            require((result.returncode == 0) == allowed, "runtime SHA drift")
    print("PASS: migration operation branch/SHA runtime (18 cases)")


def main() -> int:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    validate(publisher, independent)
    prove_yaml_authority_negatives(publisher, independent)
    prove_trigger_reachability_negatives(publisher, independent)
    negative_proofs(publisher, independent)
    runtime_proofs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
