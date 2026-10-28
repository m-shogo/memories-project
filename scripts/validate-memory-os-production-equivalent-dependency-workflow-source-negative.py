#!/usr/bin/env python3
"""Read-only exact-source and runtime negative proof for release compatibility pair CI."""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/production-equivalent-dependency-contract.yml"
INDEPENDENT = ".github/workflows/production-equivalent-dependency-source-negative.yml"
SELF = "scripts/validate-memory-os-production-equivalent-dependency-workflow-source-negative.py"

PUBLISHER_TRIGGER_PATHS = (
    ".github/workflows/production-equivalent-dependency-contract.yml",
    ".github/workflows/production-equivalent-dependency-source-negative.yml",
    "scripts/validate-memory-os-production-equivalent-dependency-workflow-source-negative.py",
    "contracts/operations/production-equivalent-dependency-contract.v1.json",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "scripts/validate-memory-os-production-equivalent-dependencies.py",
    "scripts/reconcile-memory-os-production-equivalent-foundation.py",
    "scripts/validate-memory-os-production-equivalent-foundation-reconcile-negative.py",
    "scripts/validate-memory-os-load-evidence-index.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
)
INDEPENDENT_TRIGGER_PATHS = (
    ".github/workflows/production-equivalent-dependency-contract.yml",
    ".github/workflows/production-equivalent-dependency-source-negative.yml",
    "scripts/validate-memory-os-production-equivalent-dependency-workflow-source-negative.py",
)
PUBLISHER_SHA = "912aa3fb3a05daac88561fb375f23784d73a5b9c"
INDEPENDENT_SHA = "40621309545bc57e4729e9539d490837cadab707"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
PR_SHA = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA = '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("production-equivalent dependency CI source guard: " + message)


def read(path: str) -> str:
    file = ROOT / path
    require(file.is_file() and not file.is_symlink(), "missing or symlinked source: " + path)
    require(file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() == path,
            "source escaped root: " + path)
    return file.read_text(encoding="utf-8")


def check_source(
    name: str, source: str, expected: str, required: tuple[tuple[str, int], ...], *,
    check_blob: bool = True,
) -> None:
    for token, count in required:
        require(source.count(token) == count, name + " required source inventory drift: " + token[:55])
    for forbidden in ("pull_request_target:", "secrets.", "actions/checkout@v4", "actions/setup-python@v5"):
        require(forbidden not in source, name + " unreviewed source")
    data = source.encode("utf-8")
    digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    if check_blob:
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



def validate_trigger_reachability(
    content: str, kind: str, *, trigger_paths: tuple[str, ...] | None = None
) -> None:
    """Enforce both reviewed event path inventories independently of complete Git blob SHA."""
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    if kind == "publisher":
        canonical = PUBLISHER_TRIGGER_PATHS
        end_marker = "  workflow_dispatch:\n"
    elif kind == "independent":
        canonical = INDEPENDENT_TRIGGER_PATHS
        end_marker = "\npermissions:\n"
    else:
        raise SystemExit("production-equivalent dependency unknown trigger kind")
    if trigger_paths is None:
        trigger_paths = canonical
    require(len(trigger_paths) == len(canonical) and len(set(trigger_paths)) == len(canonical),
            kind + " trigger inventory shortened or duplicated")
    for marker in (pr_marker, push_marker, end_marker):
        require(content.count(marker) == 1, kind + " trigger event marker drift")
    if kind == "publisher":
        push = content.split(push_marker, 1)[1].split(pr_marker, 1)[0]
        pr = content.split(pr_marker, 1)[1].split(end_marker, 1)[0]
    else:
        pr = content.split(pr_marker, 1)[1].split(push_marker, 1)[0]
        push = content.split(push_marker, 1)[1].split(end_marker, 1)[0]
    approved = tuple('      - "' + path + '"' for path in trigger_paths)
    for event, block in (("pull_request", pr), ("push", push)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        require(actual == approved, kind + " " + event + " exact trigger inventory drift")
    # Publisher intentionally reviews push before PR; independent CI reviews
    # PR before push. Bind each exact event order and effective YAML authority.
    paths_block = "".join('      - "' + path + '"\n' for path in trigger_paths)
    expected_events = (
        push_marker + paths_block + pr_marker + paths_block + "  workflow_dispatch:\n"
        if kind == "publisher" else
        pr_marker + paths_block + push_marker + paths_block
    )
    expected_header = (
        ("name: Production Equivalent Dependency Contract" if kind == "publisher"
         else "name: Production Equivalent Dependency Source Negative")
        + "\n\non:\n" + expected_events
    )
    if (content.count("\npermissions:\n") != 1
            or content.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("production-equivalent dependency " + kind + " exact event header drift")
    observed_roots = [
        row for row in content.splitlines()
        if row.strip() and not row[0].isspace()
        and not row.lstrip().startswith("#")
    ]
    expected_roots = [
        ("name: Production Equivalent Dependency Contract" if kind == "publisher"
         else "name: Production Equivalent Dependency Source Negative"),
        "on:", "permissions:", "jobs:",
    ]
    if observed_roots != expected_roots:
        raise SystemExit("production-equivalent dependency " + kind + " root YAML key shadow drift")
    permission_lines = content.split("\npermissions:\n", 1)[1].splitlines()
    permission_rows = []
    for row in permission_lines:
        if row.strip() and not row[0].isspace():
            break
        if row.strip() and not row.lstrip().startswith("#"):
            permission_rows.append(row)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("production-equivalent dependency " + kind + " permission leaf shadow drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for kind, content, paths in (
        ("publisher", publisher, PUBLISHER_TRIGGER_PATHS),
        ("independent", independent, INDEPENDENT_TRIGGER_PATHS),
    ):
        validate_trigger_reachability(content, kind)
        for event in ("pull_request", "push"):
            marker = pr_marker if event == "pull_request" else push_marker
            for path in paths:
                token = '      - "' + path + '"\n'
                require(content.count(token) == 2, kind + " mutation anchor drift: " + path)
                prefix, suffix = content.split(marker, 1)
                mutated = prefix + marker + suffix.replace(token, "", 1)
                try:
                    validate_trigger_reachability(mutated, kind)
                except SystemExit:
                    continue
                raise SystemExit("production-equivalent dependency " + kind + " accepted missing " + event + " trigger: " + path)
            for label, injected in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                require(content.count(marker) == 1, kind + " addition marker drift: " + event)
                mutated = content.replace(marker, marker + injected, 1)
                require(mutated != content, kind + " addition fixture unchanged")
                try:
                    validate_trigger_reachability(mutated, kind)
                except SystemExit:
                    continue
                raise SystemExit("production-equivalent dependency " + kind + " accepted " + event + " addition: " + label)
        try:
            validate_trigger_reachability(content, kind, trigger_paths=paths[:-1])
        except SystemExit:
            pass
        else:
            raise SystemExit("production-equivalent dependency " + kind + " shortened inventory accepted")
    # All PR/push path inventories remain unchanged in these fixtures.
    for kind, content in (("publisher", publisher), ("independent", independent)):
        extra_event = content.replace("on:\n", "on:\n  issues:\n", 1)
        if extra_event == content:
            raise SystemExit("production-equivalent dependency event negative anchor drift: " + kind)
        try:
            validate_trigger_reachability(extra_event, kind)
        except SystemExit as exc:
            expected = "production-equivalent dependency " + kind + " exact event header drift"
            if str(exc) != expected:
                raise SystemExit(
                    "production-equivalent dependency event rejected for wrong reason: "
                    + kind + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("production-equivalent dependency accepted extra event: " + kind)
        for name, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: write\n"),
            ("spaced jobs", "jobs : {}\n"),
        ):
            try:
                validate_trigger_reachability(content + "\n" + suffix, kind)
            except SystemExit as exc:
                expected = "production-equivalent dependency " + kind + " root YAML key shadow drift"
                if str(exc) != expected:
                    raise SystemExit(
                        "production-equivalent dependency root rejected for wrong reason: "
                        + kind + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit(
                    "production-equivalent dependency accepted root shadow: " + kind + " " + name
                )
        anchor = "permissions:\n  contents: read\n"
        if content.count(anchor) != 1:
            raise SystemExit("production-equivalent dependency permission negative anchor drift: " + kind)
        for name, extra in (
            ("spaced", "  contents : write\n"),
            ("quoted", "  'contents': write\n"),
        ):
            mutated = content.replace(anchor, anchor + extra, 1)
            try:
                validate_trigger_reachability(mutated, kind)
            except SystemExit as exc:
                expected = "production-equivalent dependency " + kind + " permission leaf shadow drift"
                if str(exc) != expected:
                    raise SystemExit(
                        "production-equivalent dependency permission rejected for wrong reason: "
                        + kind + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit(
                    "production-equivalent dependency accepted permission shadow: " + kind + " " + name
                )
    print("PASS: production-equivalent dependency CI semantic YAML negatives "
          "(2 extra-event, 8 root, 4 permission exact-diagnostic cases)")
    print("PASS: production-equivalent dependency CI event-specific triggers (30 removals; 16 additions; 2 shortened inventory negatives)")


def validate(
    publisher: str, independent: str, *,
    check_publisher_blob: bool = True, check_independent_blob: bool = True,
) -> None:
    validate_trigger_reachability(publisher, "publisher")
    validate_trigger_reachability(independent, "independent")
    check_source("publisher", publisher, PUBLISHER_SHA, PUBLISHER_REQUIRED,
                 check_blob=check_publisher_blob)
    check_source("independent", independent, INDEPENDENT_SHA, INDEPENDENT_REQUIRED,
                 check_blob=check_independent_blob)


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
        ("publisher unreviewed Action", True, "      - name: Capture exact authority source\n",
         "      - uses: unreviewed/action@v1\n      - name: Capture exact authority source\n"),
        ("publisher unreviewed shell", True, "      - name: Capture exact authority source\n",
         "      - run: echo unreviewed\n      - name: Capture exact authority source\n"),
        ("independent unreviewed Action", False, "      - name: Prove publisher and independent source boundary\n",
         "      - uses: unreviewed/action@v1\n      - name: Prove publisher and independent source boundary\n"),
        ("independent unreviewed shell", False, "      - name: Prove publisher and independent source boundary\n",
         "      - run: echo unreviewed\n      - name: Prove publisher and independent source boundary\n"),
    )
    digest_only = {
        "publisher unreviewed Action", "publisher unreviewed shell",
        "independent unreviewed Action", "independent unreviewed shell",
    }
    semantic_count = 0
    digest_count = 0
    for label, publisher_case, before, after in cases:
        original = publisher if publisher_case else independent
        required = PUBLISHER_REQUIRED if publisher_case else INDEPENDENT_REQUIRED
        require(before in original, "mutation anchor missing: " + label)
        changed = original.replace(before, after, 1)
        require(changed != original, "mutation unchanged: " + label)
        semantic = any(changed.count(token) != original.count(token)
                       for token, _ in required)
        require(semantic == (label not in digest_only),
                "semantic/digest source negative classification drift: " + label)
        semantic_count += int(semantic)
        digest_count += int(not semantic)
        try:
            if publisher_case:
                validate(changed, independent, check_publisher_blob=not semantic)
            else:
                validate(publisher, changed, check_independent_blob=not semantic)
        except SystemExit:
            continue
        raise SystemExit("production-equivalent dependency source negative accepted: " + label)
    require((semantic_count, digest_count) == (14, 4),
            "production-equivalent dependency source negative coverage drift")
    print("PASS: production-equivalent dependency CI source negatives (14 semantic; 4 blob-only)")


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
    print("PASS: production-equivalent dependency branch/SHA runtime (18 cases)")



def validate_job_authority(publisher: str, independent: str) -> None:
    """Pin effective job mappings, scope and job keys before blob-only checks."""
    reviewed = (
        ("publisher", publisher, (
            ("validate-pr", "github.event_name == 'pull_request'", "read", 8),
            ("validate-and-publish",
             "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
             "write", 8),
        )),
        ("independent", independent, (
            ("source-negative",
             "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
             "read", 5),
        )),
    )
    for label, content, jobs in reviewed:
        prefix = "production-equivalent dependency " + label + " "
        if content.count("\njobs:\n") != 1:
            raise SystemExit(prefix + "job mapping shadow drift")
        body = content.split("\njobs:\n", 1)[1]
        sections: dict[str, list[str]] = {}
        current: str | None = None
        actual: list[str] = []
        for line in body.splitlines():
            if (line.startswith("  ") and len(line) > 2 and line[2] != " "
                    and not line.lstrip().startswith("#")):
                current = line
                actual.append(line)
                sections[current] = []
            elif current is not None:
                sections[current].append(line)
        expected = ["  " + name + ":" for name, _, _, _ in jobs]
        if actual != expected:
            raise SystemExit(prefix + "job mapping shadow drift")
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
                raise SystemExit(prefix + name + " job key shadow drift")
            leaves: list[str] = []
            for line in lines[lines.index("    permissions:") + 1:]:
                if line.startswith("    ") and len(line) > 4 and line[4] != " ":
                    break
                if line.strip() and not line.lstrip().startswith("#"):
                    leaves.append(line)
            if leaves != ["      contents: " + scope]:
                raise SystemExit(prefix + name + " job permission leaf shadow drift")


def prove_job_authority_negatives(publisher: str, independent: str) -> None:
    """Exercise 36 exact-diagnostic nested YAML mutations, not just blob mismatch."""
    validate_job_authority(publisher, independent)
    count = 0
    reviewed = (
        ("publisher", publisher, independent, (
            ("validate-pr", "github.event_name == 'pull_request'", "read", 8),
            ("validate-and-publish",
             "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
             "write", 8),
        ), True),
        ("independent", independent, publisher, (
            ("source-negative",
             "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
             "read", 5),
        ), False),
    )
    for label, content, other, jobs, is_publisher in reviewed:
        for name, condition, scope, timeout in jobs:
            header = "  " + name + ":\n"
            if content.count(header) != 1:
                raise SystemExit("production-equivalent dependency job fixture header drift: " + label + " " + name)

            def in_job(before: str, after: str) -> str:
                prefix, suffix = content.split(header, 1)
                if before not in suffix:
                    raise SystemExit("production-equivalent dependency job fixture anchor drift: " + name)
                return prefix + header + suffix.replace(before, after, 1)

            condition_anchor = "    if: " + condition + "\n"
            permission = "    permissions:\n      contents: " + scope + "\n"
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
                ("condition shadow", in_job(condition_anchor, condition_anchor + "    if : true\n"),
                 name + " job key shadow drift"),
                ("permission shadow", in_job(permission, permission + "    permissions :\n      contents: write\n"),
                 name + " job key shadow drift"),
                ("runner shadow", in_job(runner, runner + "    runs-on : ubuntu-latest\n"),
                 name + " job key shadow drift"),
                ("timeout shadow", in_job(timeout_anchor, timeout_anchor + "    timeout-minutes : 1\n"),
                 name + " job key shadow drift"),
                ("steps shadow", in_job(steps, "    steps : []\n" + steps),
                 name + " job key shadow drift"),
                ("continuation override", in_job(steps, "    continue-on-error: true\n" + steps),
                 name + " job key shadow drift"),
                ("direct permission change", in_job(permission, permission.replace(
                    "contents: " + scope, "contents: " + ("read" if scope == "write" else "write"))),
                 name + " job permission leaf shadow drift"),
                ("spaced permission leaf", in_job(permission, permission + "      contents : write\n"),
                 name + " job permission leaf shadow drift"),
                ("quoted permission leaf", in_job(permission, permission + "      'contents': write\n"),
                 name + " job permission leaf shadow drift"),
            ]
            for mutation, changed, diagnostic in cases:
                if changed == content:
                    raise SystemExit("production-equivalent dependency unchanged job fixture: " + mutation)
                try:
                    if is_publisher:
                        validate_job_authority(changed, other)
                    else:
                        validate_job_authority(other, changed)
                except SystemExit as exc:
                    expected = "production-equivalent dependency " + label + " " + diagnostic
                    if str(exc) != expected:
                        raise SystemExit("production-equivalent dependency wrong job diagnostic: "
                                         + label + " " + name + " " + mutation + ": " + str(exc)) from exc
                else:
                    raise SystemExit("production-equivalent dependency accepted job shadow: "
                                     + label + " " + name + " " + mutation)
                count += 1
    if count != 36:
        raise SystemExit("production-equivalent dependency job negative inventory drift")
    print("PASS: production-equivalent dependency publisher/independent job authority (36 exact-diagnostic negatives)")


def main() -> int:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    validate(publisher, independent)
    prove_job_authority_negatives(publisher, independent)
    prove_trigger_reachability_negatives(publisher, independent)
    negative_proofs(publisher, independent)
    runtime_proofs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
