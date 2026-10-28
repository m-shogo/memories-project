#!/usr/bin/env python3
"""Read-only exact-source and runtime negative proof for release compatibility pair CI."""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/release-compatibility-pair.yml"
INDEPENDENT = ".github/workflows/release-compatibility-pair-source-negative.yml"
SELF = "scripts/validate-memory-os-release-compatibility-pair-workflow-source-negative.py"
PUBLISHER_SHA = "465bf1631f47ce832c8f4c515e4ef7c749abaf24"
INDEPENDENT_SHA = "c0b6309857e7f2c818dee23e1bb01a9f497ec872"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
PR_SHA = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA = '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("release pair CI source guard: " + message)


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


RELEASE_PAIR_PUBLISHER_PR_PATHS = (
    ".github/workflows/release-compatibility-pair.yml",
    ".github/workflows/release-compatibility-pair-source-negative.yml",
    "scripts/validate-memory-os-release-compatibility-pair-workflow-source-negative.py",
    "contracts/operations/release-baseline-registry-contract.v1.json",
    "contracts/operations/release-baseline-registry.v1.json",
    "contracts/operations/release-compatibility-pair-contract.v1.json",
    "contracts/operations/release-compatibility-pair-registry.v1.json",
    "contracts/operations/version-compatibility-execution-evidence.v1.json",
    "contracts/operations/compatibility-admission-gaps.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/evidence/release-compatibility-pairs/reviews/**",
    "scripts/register-memory-os-release-baseline.py",
    "scripts/register-memory-os-release-compatibility-pair.py",
    "scripts/validate-memory-os-release-compatibility-pair.py",
    "scripts/validate-memory-os-release-compatibility-pair-negative.py",
    "scripts/validate-memory-os-release-compatibility-pair-reconcile-negative.py",
    "scripts/validate-memory-os-release-compatibility-pair-independent-review.py",
    "scripts/validate-memory-os-release-compatibility-pair-independent-review-negative.py",
    "scripts/reconcile-memory-os-release-compatibility-pair.py",
    "scripts/validate-memory-os-version-compatibility-execution-evidence.py",
    "scripts/validate-memory-os-operability.py",
)

RELEASE_PAIR_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/release-compatibility-pair.yml",
    ".github/workflows/release-compatibility-pair-source-negative.yml",
    "scripts/validate-memory-os-release-compatibility-pair-workflow-source-negative.py",
    "contracts/operations/release-baseline-registry-contract.v1.json",
    "contracts/operations/release-baseline-registry.v1.json",
    "contracts/operations/release-compatibility-pair-contract.v1.json",
    "contracts/operations/release-compatibility-pair-registry.v1.json",
    "contracts/operations/version-compatibility-execution-evidence.v1.json",
    "contracts/operations/compatibility-admission-gaps.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/evidence/release-compatibility-pairs/reviews/**",
    "scripts/register-memory-os-release-baseline.py",
    "scripts/register-memory-os-release-compatibility-pair.py",
    "scripts/validate-memory-os-release-compatibility-pair.py",
    "scripts/validate-memory-os-release-compatibility-pair-negative.py",
    "scripts/validate-memory-os-release-compatibility-pair-reconcile-negative.py",
    "scripts/validate-memory-os-release-compatibility-pair-independent-review.py",
    "scripts/validate-memory-os-release-compatibility-pair-independent-review-negative.py",
    "scripts/reconcile-memory-os-release-compatibility-pair.py",
    "scripts/validate-memory-os-version-compatibility-execution-evidence.py",
    "scripts/validate-memory-os-operability.py",
)

RELEASE_PAIR_INDEPENDENT_PR_PATHS = (
    ".github/workflows/release-compatibility-pair.yml",
    ".github/workflows/release-compatibility-pair-source-negative.yml",
    "scripts/validate-memory-os-release-compatibility-pair-workflow-source-negative.py",
)

RELEASE_PAIR_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/release-compatibility-pair.yml",
    ".github/workflows/release-compatibility-pair-source-negative.yml",
    "scripts/validate-memory-os-release-compatibility-pair-workflow-source-negative.py",
)

def release_pair_trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def release_pair_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("release-compatibility-pair trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def release_pair_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = RELEASE_PAIR_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = RELEASE_PAIR_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = RELEASE_PAIR_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = RELEASE_PAIR_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (release_pair_trigger_event("pull_request", publisher_pr)
                          + release_pair_trigger_event("push", publisher_push)
                          + "  workflow_dispatch:\n")
    expected_independent = (release_pair_trigger_event("pull_request", independent_pr)
                            + release_pair_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if release_pair_trigger_header(content) != expected:
            raise SystemExit("release-compatibility-pair " + label
                             + " exact event trigger inventory drift")
    release_pair_validate_yaml_root_permissions(publisher, independent)



def release_pair_validate_yaml_root_permissions(publisher: str, independent: str) -> None:
    """Reject effective YAML mapping shadows independently of the reviewed blob."""
    for label, content, expected_roots in (
        ("publisher", publisher, [
            "name: Release Compatibility Pair", "on:", "permissions:",
            "concurrency:", "jobs:",
        ]),
        ("independent", independent, [
            "name: Release Compatibility Pair Source Negative", "on:",
            "permissions:", "jobs:",
        ]),
    ):
        roots = [
            line for line in content.splitlines()
            if line.strip() and not line[0].isspace()
            and not line.lstrip().startswith("#")
        ]
        if roots != expected_roots:
            raise SystemExit("release-compatibility-pair " + label
                             + " root YAML key shadow drift")
        if content.count("\npermissions:\n") != 1:
            raise SystemExit("release-compatibility-pair " + label
                             + " permission leaf shadow drift")
        permission_rows = []
        for line in content.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                permission_rows.append(line)
        if permission_rows != ["  contents: read"]:
            raise SystemExit("release-compatibility-pair " + label
                             + " permission leaf shadow drift")


def release_pair_yaml_shadow_negatives(publisher: str, independent: str) -> None:
    total = 0
    for label, content in (("publisher", publisher), ("independent", independent)):
        cases = []
        for name, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: write\n"),
            ("spaced jobs", "jobs : {}\n"),
        ):
            cases.append((name, content + "\n" + suffix, "root YAML key shadow drift"))
        anchor = "permissions:\n  contents: read\n"
        if content.count(anchor) != 1:
            raise SystemExit("release-compatibility-pair " + label
                             + " permission mutation anchor drift")
        for name, extra in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((name, content.replace(anchor, anchor + extra, 1),
                          "permission leaf shadow drift"))
        for name, altered, diagnostic in cases:
            if altered == content:
                raise SystemExit("release-compatibility-pair YAML fixture unchanged: " + name)
            try:
                if label == "publisher":
                    release_pair_validate_trigger_matrix(altered, independent)
                else:
                    release_pair_validate_trigger_matrix(publisher, altered)
            except SystemExit as exc:
                expected = "release-compatibility-pair " + label + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit(
                        "release-compatibility-pair YAML wrong diagnostic: "
                        + label + "/" + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit("release-compatibility-pair accepted YAML shadow: "
                                 + label + "/" + name)
            total += 1
    if total != 12:
        raise SystemExit("release-compatibility-pair YAML fixture count drift")
    print("PASS: release pair publisher/independent YAML root/permission (12 exact-diagnostic negatives)")


def replace_release_pair_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("release-compatibility-pair trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def release_pair_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            release_pair_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("release-compatibility-pair accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", RELEASE_PAIR_PUBLISHER_PR_PATHS),
        ("publisher", "push", RELEASE_PAIR_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", RELEASE_PAIR_INDEPENDENT_PR_PATHS),
        ("independent", "push", RELEASE_PAIR_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = release_pair_trigger_header(original)
        block = release_pair_trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("release-compatibility-pair trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_release_pair_trigger_header(
                original, header, header.replace(block, release_pair_trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_release_pair_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", RELEASE_PAIR_PUBLISHER_PR_PATHS),
        ("publisher_push", RELEASE_PAIR_PUBLISHER_PUSH_PATHS),
        ("independent_pr", RELEASE_PAIR_INDEPENDENT_PR_PATHS),
        ("independent_push", RELEASE_PAIR_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            release_pair_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("release-compatibility-pair accepted shortened trigger inventory")

    p_header, i_header = release_pair_trigger_header(publisher), release_pair_trigger_header(independent)
    topology = (
        (replace_release_pair_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_release_pair_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_release_pair_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: release-compatibility-pair exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")


def validate(publisher: str, independent: str) -> None:
    check_source("publisher", publisher, PUBLISHER_SHA, PUBLISHER_REQUIRED)
    check_source("independent", independent, INDEPENDENT_SHA, INDEPENDENT_REQUIRED)


def negative_proofs(publisher: str, independent: str) -> None:
    cases = (
        ("publisher PR base", True, PR_BASE, "true"),
        ("publisher writer ref", True, WRITER_REF, "true"),
        ("publisher writer scope", True, WRITER_SCOPE, "    if: always()"),
        ("publisher PR SHA", True, PR_SHA, 'test -n "$expected"'),
        ("publisher writer SHA", True, WRITER_SHA, 'test -n "$GITHUB_SHA"'),
        ("publisher checkout pin", True, CHECKOUT, "uses: actions/checkout@v4"),
        ("publisher credentials", True, "persist-credentials: false", "persist-credentials: true"),
        ("publisher self guard", True, "python " + SELF, "echo skip"),
        ("independent PR base", False, PR_BASE, "true"),
        ("independent writer ref", False, WRITER_REF, "true"),
        ("independent SHA", False, PR_SHA, 'test -n "$expected"'),
        ("independent checkout pin", False, CHECKOUT, "uses: actions/checkout@v4"),
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
        except SystemExit:
            continue
        raise SystemExit("release pair source negative accepted: " + label)
    print("PASS: release pair CI source negatives (14 cases)")


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
    print("PASS: release pair branch/SHA runtime (18 cases)")


def main() -> int:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    validate(publisher, independent)
    release_pair_validate_trigger_matrix(publisher, independent)
    release_pair_trigger_matrix_negatives(publisher, independent)
    release_pair_yaml_shadow_negatives(publisher, independent)
    negative_proofs(publisher, independent)
    runtime_proofs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
