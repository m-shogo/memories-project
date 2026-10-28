#!/usr/bin/env python3
"""Fail-closed release baseline publisher source, schedule and runtime negative proof."""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/release-baseline-registry.yml"
INDEPENDENT = ".github/workflows/release-baseline-registry-source-negative.yml"
SELF = "scripts/validate-memory-os-release-baseline-registry-workflow-source-negative.py"
PUBLISHER_SHA = "e14c1c779228404a75ee03a2d0ec6d4a598764c5"
INDEPENDENT_SHA = "7c3e469bc58787cdcfdf5abbac33869604101588"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') && github.ref == 'refs/heads/so'"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
PR_SHA = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA = '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'
WRITER_EVENT = '[[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" || "${GITHUB_EVENT_NAME:-}" == "schedule" ]]'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("release baseline CI source guard: " + message)


def read(path: str) -> str:
    file = ROOT / path
    require(file.is_file() and not file.is_symlink(), "missing or symlinked source: " + path)
    require(file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() == path,
            "source escaped root: " + path)
    return file.read_text(encoding="utf-8")


def check_source(name: str, source: str, expected: str, required: tuple[tuple[str, int], ...]) -> None:
    for token, count in required:
        require(source.count(token) == count, name + " source inventory drift: " + token[:60])
    for forbidden in ("pull_request_target:", "secrets.", "actions/checkout@v4", "actions/setup-python@v5"):
        require(forbidden not in source, name + " unreviewed source")
    data = source.encode("utf-8")
    digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    require(digest == expected, name + " complete source drift")


PUBLISHER_REQUIRED = (
    ("  pull_request:\n    branches:\n      - so\n", 1),
    ("  push:\n    branches:\n      - so\n", 1),
    ('  schedule:\n    - cron: "23 3 * * 2"\n', 1),
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
    (WRITER_EVENT, 1),
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


RELEASE_BASELINE_PUBLISHER_PR_PATHS = (
    ".github/workflows/release-baseline-registry.yml",
    ".github/workflows/release-baseline-registry-source-negative.yml",
    "scripts/validate-memory-os-release-baseline-registry-workflow-source-negative.py",
    "contracts/operations/release-baseline-registry-contract.v1.json",
    "contracts/operations/release-baseline-registry.v1.json",
    "docs/evidence/releases/README.md",
    "scripts/register-memory-os-release-baseline.py",
    "scripts/validate-memory-os-release-baseline-writer-authority-negative.py",
    "scripts/validate-memory-os-release-baseline-registry.py",
    "scripts/validate-memory-os-release-baseline-registry-negative.py",
    "scripts/validate-memory-os-release-baseline-evidence-binding.py",
    "scripts/validate-memory-os-release-baseline-evidence-binding-negative.py",
    "scripts/validate-memory-os-release-baseline-reconcile-authority-negative.py",
    "scripts/reconcile-memory-os-release-baseline-registry.py",
    "scripts/validate-memory-os-version-compatibility.py",
    "scripts/validate-memory-os-operability.py",
)

RELEASE_BASELINE_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/release-baseline-registry.yml",
    ".github/workflows/release-baseline-registry-source-negative.yml",
    "scripts/validate-memory-os-release-baseline-registry-workflow-source-negative.py",
    "contracts/operations/release-baseline-registry-contract.v1.json",
    "contracts/operations/release-baseline-registry.v1.json",
    "docs/evidence/releases/README.md",
    "scripts/register-memory-os-release-baseline.py",
    "scripts/validate-memory-os-release-baseline-writer-authority-negative.py",
    "scripts/validate-memory-os-release-baseline-registry.py",
    "scripts/validate-memory-os-release-baseline-registry-negative.py",
    "scripts/validate-memory-os-release-baseline-evidence-binding.py",
    "scripts/validate-memory-os-release-baseline-evidence-binding-negative.py",
    "scripts/validate-memory-os-release-baseline-reconcile-authority-negative.py",
    "scripts/reconcile-memory-os-release-baseline-registry.py",
    "scripts/validate-memory-os-version-compatibility.py",
    "scripts/validate-memory-os-operability.py",
)

RELEASE_BASELINE_INDEPENDENT_PR_PATHS = (
    ".github/workflows/release-baseline-registry.yml",
    ".github/workflows/release-baseline-registry-source-negative.yml",
    "scripts/validate-memory-os-release-baseline-registry-workflow-source-negative.py",
)

RELEASE_BASELINE_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/release-baseline-registry.yml",
    ".github/workflows/release-baseline-registry-source-negative.yml",
    "scripts/validate-memory-os-release-baseline-registry-workflow-source-negative.py",
)

def release_baseline_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def release_baseline_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("release-baseline trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def release_baseline_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = RELEASE_BASELINE_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = RELEASE_BASELINE_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = RELEASE_BASELINE_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = RELEASE_BASELINE_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (release_baseline_trigger_event("pull_request", publisher_pr)
                          + release_baseline_trigger_event("push", publisher_push)
                          + '  schedule:\n    - cron: "23 3 * * 2"\n'
                          + "  workflow_dispatch:\n")
    expected_independent = (release_baseline_trigger_event("pull_request", independent_pr)
                            + release_baseline_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if release_baseline_trigger_header(content) != expected:
            raise SystemExit("release-baseline " + label
                             + " exact event trigger inventory drift")


def replace_release_baseline_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("release-baseline trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def release_baseline_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            release_baseline_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("release-baseline accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", RELEASE_BASELINE_PUBLISHER_PR_PATHS),
        ("publisher", "push", RELEASE_BASELINE_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", RELEASE_BASELINE_INDEPENDENT_PR_PATHS),
        ("independent", "push", RELEASE_BASELINE_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = release_baseline_trigger_header(original)
        block = release_baseline_trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("release-baseline trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_release_baseline_trigger_header(
                original, header, header.replace(block, release_baseline_trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_release_baseline_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", RELEASE_BASELINE_PUBLISHER_PR_PATHS),
        ("publisher_push", RELEASE_BASELINE_PUBLISHER_PUSH_PATHS),
        ("independent_pr", RELEASE_BASELINE_INDEPENDENT_PR_PATHS),
        ("independent_push", RELEASE_BASELINE_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            release_baseline_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("release-baseline accepted shortened trigger inventory")

    p_header, i_header = release_baseline_trigger_header(publisher), release_baseline_trigger_header(independent)
    topology = (
        (replace_release_baseline_trigger_header(
            publisher, p_header, p_header.replace("23 3 * * 2", "0 0 * * *", 1)), independent),
        (replace_release_baseline_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_release_baseline_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_release_baseline_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: release-baseline exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")


def validate(publisher: str, independent: str) -> None:
    validate_job_authority(publisher, independent)
    check_source("publisher", publisher, PUBLISHER_SHA, PUBLISHER_REQUIRED)
    check_source("independent", independent, INDEPENDENT_SHA, INDEPENDENT_REQUIRED)
    validate_yaml_root_permission_authority(publisher, 'publisher')
    validate_yaml_root_permission_authority(independent, 'independent')


def validate_yaml_root_permission_authority(content: str, kind: str) -> None:
    """Pin effective YAML root and read-only permission mapping separately from exact event matrix."""
    if kind == "publisher":
        name = "name: Release Baseline Registry"
        roots = [name, "on:", "permissions:", "concurrency:", "jobs:"]
    elif kind == "independent":
        name = "name: Release Baseline Registry Source Negative"
        roots = [name, "on:", "permissions:", "jobs:"]
    else:
        raise SystemExit("release baseline unknown YAML authority kind")
    prefix = "release baseline " + kind + " "
    if (content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1
            or not content.startswith(name + "\n\non:\n")):
        raise SystemExit(prefix + "root YAML header drift")
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


def prove_yaml_root_permission_negatives(publisher: str, independent: str) -> None:
    """Exact-diagnostic negatives complement existing exact PR/push/schedule event matrix."""
    count = 0
    for kind, content in (("publisher", publisher), ("independent", independent)):
        validate_yaml_root_permission_authority(content, kind)
        cases = []
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
            raise SystemExit("release baseline " + kind + " permission fixture anchor drift")
        for label, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((label, content.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        if len(cases) != 8:
            raise SystemExit("release baseline " + kind + " YAML fixture count drift")
        for label, mutated, diagnostic in cases:
            if mutated == content:
                raise SystemExit("release baseline " + kind + " unchanged YAML fixture: " + label)
            try:
                validate_yaml_root_permission_authority(mutated, kind)
            except SystemExit as exc:
                expected = "release baseline " + kind + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("release baseline " + kind + " wrong YAML diagnostic: "
                                     + label + ": " + str(exc)) from exc
            else:
                raise SystemExit("release baseline " + kind + " accepted YAML mutation: " + label)
            count += 1
    if count != 16:
        raise SystemExit("release baseline YAML negative population drift")
    print("PASS: release baseline publisher/independent YAML root/permission authority (16 exact-diagnostic negatives)")



def validate_job_authority(publisher: str, independent: str) -> None:
    """Pin release publisher PR/write jobs and independent read-only CI job."""
    reviewed = (
        ("publisher", publisher, (
            ("validate-pr", "github.event_name == 'pull_request'", "read", 10),
            ("validate-and-publish", "(github.event_name == 'push' || github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') && github.ref == 'refs/heads/so'", "write", 10),
        )),
        ("independent", independent, (
            ("source-negative", "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", "read", 5),
        )),
    )
    for label, value, jobs in reviewed:
        if value.count("\njobs:\n") != 1:
            raise SystemExit("release baseline " + label + " job mapping shadow drift")
        body = value.split("\njobs:\n", 1)[1]
        sections: dict[str, list[str]] = {}
        current: str | None = None
        actual = []
        for line in body.splitlines():
            if (line.startswith("  ") and len(line) > 2 and line[2] != " "
                    and not line.lstrip().startswith("#")):
                current = line
                actual.append(line)
                sections[current] = []
            elif current is not None:
                sections[current].append(line)
        expected_names = ["  " + name + ":" for name, _, _, _ in jobs]
        if actual != expected_names:
            raise SystemExit("release baseline " + label + " job mapping shadow drift")
        for name, condition, scope, timeout in jobs:
            lines = sections["  " + name + ":"]
            keys = [
                line for line in lines
                if line.startswith("    ") and len(line) > 4 and line[4] != " "
                and not line.lstrip().startswith("#")
            ]
            if keys != [
                "    if: " + condition,
                "    permissions:",
                "    runs-on: ubuntu-latest",
                "    timeout-minutes: " + str(timeout),
                "    steps:",
            ]:
                raise SystemExit("release baseline " + label + " " + name + " job key shadow drift")
            start = lines.index("    permissions:")
            leaves = []
            for line in lines[start + 1:]:
                if line.startswith("    ") and len(line) > 4 and line[4] != " ":
                    break
                if line.strip() and not line.lstrip().startswith("#"):
                    leaves.append(line)
            if leaves != ["      contents: " + scope]:
                raise SystemExit("release baseline " + label + " " + name + " job permission leaf shadow drift")


def prove_job_authority_negatives(publisher: str, independent: str) -> None:
    """Prove 36 exact-diagnostic release baseline nested YAML job mutations."""
    validate_job_authority(publisher, independent)
    count = 0
    for label, value, other, jobs, is_publisher in (
        ("publisher", publisher, independent, (
            ("validate-pr", "github.event_name == 'pull_request'", "read", 10),
            ("validate-and-publish", "(github.event_name == 'push' || github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') && github.ref == 'refs/heads/so'", "write", 10),
        ), True),
        ("independent", independent, publisher, (
            ("source-negative", "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", "read", 5),
        ), False),
    ):
        for name, condition, scope, timeout in jobs:
            header = "  " + name + ":\n"
            if value.count(header) != 1:
                raise SystemExit("release baseline job fixture header drift: " + label + " " + name)

            def in_job(old: str, new: str) -> str:
                prefix, suffix = value.split(header, 1)
                if old not in suffix:
                    raise SystemExit("release baseline job fixture anchor missing: " + name)
                return prefix + header + suffix.replace(old, new, 1)

            condition_anchor = "    if: " + condition + "\n"
            permission = "    permissions:\n      contents: " + scope + "\n"
            runner = "    runs-on: ubuntu-latest\n"
            timeout_anchor = "    timeout-minutes: " + str(timeout) + "\n"
            steps = "    steps:\n"
            cases = [
                ("duplicate mapping", value + "\n" + header + "    runs-on: ubuntu-latest\n", "job mapping shadow drift"),
                ("quoted mapping", value.replace(header, "  '" + name + "':\n", 1), "job mapping shadow drift"),
                ("spaced mapping", value.replace(header, "  " + name + " :\n", 1), "job mapping shadow drift"),
                ("condition shadow", in_job(condition_anchor, condition_anchor + "    if : true\n"), name + " job key shadow drift"),
                ("permission shadow", in_job(permission, permission + "    permissions :\n      contents: write\n"), name + " job key shadow drift"),
                ("runner shadow", in_job(runner, runner + "    runs-on : ubuntu-latest\n"), name + " job key shadow drift"),
                ("timeout shadow", in_job(timeout_anchor, timeout_anchor + "    timeout-minutes : 1\n"), name + " job key shadow drift"),
                ("steps shadow", in_job(steps, "    steps : []\n" + steps), name + " job key shadow drift"),
                ("continuation override", in_job(steps, "    continue-on-error: true\n" + steps), name + " job key shadow drift"),
                ("direct permission change", in_job(permission, permission.replace("contents: " + scope, "contents: " + ("read" if scope == "write" else "write"))), name + " job permission leaf shadow drift"),
                ("spaced permission leaf", in_job(permission, permission + "      contents : write\n"), name + " job permission leaf shadow drift"),
                ("quoted permission leaf", in_job(permission, permission + "      'contents': write\n"), name + " job permission leaf shadow drift"),
            ]
            for mutation, changed, diagnostic in cases:
                if changed == value:
                    raise SystemExit("release baseline unchanged job fixture: " + label + " " + mutation)
                try:
                    if is_publisher:
                        validate_job_authority(changed, other)
                    else:
                        validate_job_authority(other, changed)
                except SystemExit as exc:
                    expected = "release baseline " + label + " " + diagnostic
                    if str(exc) != expected:
                        raise SystemExit("release baseline wrong job diagnostic: " + label + " " + name + " " + mutation + ": " + str(exc)) from exc
                else:
                    raise SystemExit("release baseline accepted job shadow: " + label + " " + name + " " + mutation)
                count += 1
    if count != 36:
        raise SystemExit("release baseline job negative inventory drift")
    print("PASS: release baseline publisher/independent job authority (36 exact-diagnostic negatives)")


def negatives(publisher: str, independent: str) -> None:
    cases = (
        ("publisher PR target", True, "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher writer scope", True, WRITER_SCOPE, "    if: github.event_name != 'pull_request'"),
        ("publisher writer event", True, WRITER_EVENT, "true"),
        ("publisher PR base", True, PR_BASE, "true"),
        ("publisher writer ref", True, WRITER_REF, "true"),
        ("publisher PR SHA", True, PR_SHA, 'test -n "$expected"'),
        ("publisher writer SHA", True, WRITER_SHA, 'test -n "$GITHUB_SHA"'),
        ("publisher checkout pin", True, CHECKOUT, "uses: actions/checkout@v4"),
        ("publisher credentials", True, "persist-credentials: false", "persist-credentials: true"),
        ("publisher self guard", True, "python " + SELF, "echo skip"),
        ("independent PR target", False, "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("independent ref", False, WRITER_REF, "true"),
        ("independent PR base", False, PR_BASE, "true"),
        ("independent SHA", False, PR_SHA, 'test -n "$expected"'),
        ("independent checkout", False, CHECKOUT, "uses: actions/checkout@v4"),
        ("independent self guard", False, "python " + SELF, "echo skip"),
    )
    for label, publisher_case, before, after in cases:
        original = publisher if publisher_case else independent
        require(before in original, "missing mutation anchor: " + label)
        changed = original.replace(before, after, 1)
        require(changed != original, "unchanged mutation: " + label)
        try:
            validate(changed, independent) if publisher_case else validate(publisher, changed)
        except SystemExit:
            continue
        raise SystemExit("release baseline source mutation accepted: " + label)
    print("PASS: release baseline source negatives (16 cases)")


def runtime() -> None:
    for script, key, value, allowed in (
        (PR_BASE, "GITHUB_BASE_REF", "so", True),
        (PR_BASE, "GITHUB_BASE_REF", "main", False),
        (WRITER_REF, "GITHUB_REF", "refs/heads/so", True),
        (WRITER_REF, "GITHUB_REF", "refs/heads/main", False),
        (WRITER_EVENT, "GITHUB_EVENT_NAME", "push", True),
        (WRITER_EVENT, "GITHUB_EVENT_NAME", "workflow_dispatch", True),
        (WRITER_EVENT, "GITHUB_EVENT_NAME", "schedule", True),
        (WRITER_EVENT, "GITHUB_EVENT_NAME", "pull_request", False),
        (WRITER_EVENT, "GITHUB_EVENT_NAME", "unexpected", False),
    ):
        result = subprocess.run(["bash", "-e", "-c", script],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                capture_output=True, check=False)
        require((result.returncode == 0) == allowed, "release baseline branch/event runtime drift")
    for predicate, variable in ((PR_SHA, "expected"), (WRITER_SHA, "GITHUB_SHA")):
        for value, allowed in (("a" * 40, True), ("0" * 40, True), ("A" * 40, False),
                               ("g" * 40, False), ("a" * 39, False), ("a" * 41, False), ("", False)):
            result = subprocess.run(["bash", "-e", "-c", predicate],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), variable: value},
                                    capture_output=True, check=False)
            require((result.returncode == 0) == allowed, "release baseline SHA runtime drift")
    print("PASS: release baseline branch/event/SHA runtime (23 cases)")


def main() -> int:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    validate(publisher, independent)
    prove_yaml_root_permission_negatives(publisher, independent)
    prove_job_authority_negatives(publisher, independent)
    release_baseline_validate_trigger_matrix(publisher, independent)
    release_baseline_trigger_matrix_negatives(publisher, independent)
    negatives(publisher, independent)
    runtime()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
