#!/usr/bin/env python3
"""Independent full-source and runtime negative guard for inventory PR validation."""
from __future__ import annotations
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PR = ".github/workflows/operability-admission-inventory-pr.yml"
GUARD = ".github/workflows/operability-admission-inventory-pr-source-negative.yml"
SELF = "scripts/validate-memory-os-operability-admission-inventory-pr-source-negative.py"
PR_BLOB = "def6b2891a2c6f6ccda57dece11190ceb19b3cbf"
GUARD_BLOB = "457095582ad5f5c2be7c63f0124a4e1721b78c3d"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
D = chr(36)
BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
EVENT = 'test "' + D + '{GITHUB_EVENT_NAME:-}" = "pull_request"'
SHA = '[[ "' + D + 'expected" =~ ^[0-9a-f]{40}' + D + ' ]]'
HEAD = 'test "$(git rev-parse HEAD)" = "$expected"'


PR_TRIGGER_PATHS = tuple([".github/workflows/operability-admission-inventory-pr.yml",".github/workflows/operability-admission-inventory-pr-source-negative.yml","scripts/validate-memory-os-operability-admission-inventory-pr-source-negative.py",".github/workflows/operability-admission-inventory.yml","contracts/operations/**","docs/evidence/backup-restore/**","docs/evidence/recovery-objectives/approvals/**","docs/evidence/sustained-soak/**","docs/fixtures/memory-os-operability/**","docs/runbooks/memory-os-production-equivalent-backup-restore-drill.md","scripts/generate-memory-os-operability-admission-inventory.py","scripts/validate-memory-os-operability-admission-inventory*.py","scripts/memory_os_backup_restore_blockers.py","scripts/memory_os_environment_generation_eligibility.py","scripts/register-memory-os-backup-restore-*.py","scripts/register-memory-os-recovery-objectives.py","scripts/register-memory-os-production-equivalent-environment-generation.py","scripts/validate-memory-os-production-equivalent-environment-generation.py","scripts/reconcile-memory-os-backup-restore-*.py","scripts/reconcile-memory-os-backup-non-resurrection-authority.py","scripts/validate-memory-os-backup-restore-*.py","scripts/validate-memory-os-recovery-objectives*.py","scripts/validate-memory-os-sustained-*.py"])
GUARD_TRIGGER_PATHS = tuple([".github/workflows/operability-admission-inventory-pr.yml",".github/workflows/operability-admission-inventory-pr-source-negative.yml","scripts/validate-memory-os-operability-admission-inventory-pr-source-negative.py"])



def validate_trigger_reachability(
    pr: str, guard: str, *,
    pr_paths: tuple[str, ...] | None = None,
    guard_paths: tuple[str, ...] | None = None,
) -> None:
    """Keep the publisher PR-only and independent PR/push trigger matrices exact."""
    pub = PR_TRIGGER_PATHS if pr_paths is None else pr_paths
    ind = GUARD_TRIGGER_PATHS if guard_paths is None else guard_paths
    if (len(pub) != len(PR_TRIGGER_PATHS) or len(ind) != len(GUARD_TRIGGER_PATHS) or
        len(set(pub)) != len(pub) or len(set(ind)) != len(ind)):
        raise SystemExit("inventory PR event trigger inventory shortened/duplicated")
    pub_lines = "".join('      - "' + path + '"\n' for path in pub)
    ind_lines = "".join('      - "' + path + '"\n' for path in ind)
    expected_pub = (
        "name: Operability Admission Inventory PR\n\non:\n"
        "  pull_request:\n    branches:\n      - so\n    paths:\n" + pub_lines
    )
    expected_guard = (
        "name: Operability Admission Inventory PR Source Negative\n\non:\n"
        "  pull_request:\n    branches: [so]\n    paths:\n" + ind_lines +
        "  push:\n    branches: [so]\n    paths:\n" + ind_lines
    )
    for label, value, expected in (("publisher", pr, expected_pub),
                                   ("independent", guard, expected_guard)):
        if value.count("\npermissions:\n") != 1:
            raise SystemExit("inventory PR " + label + " permissions boundary drift")
        if value.split("\npermissions:\n", 1)[0] != expected:
            raise SystemExit("inventory PR " + label + " exact trigger event drift")
        # Exact event-prefix checks alone miss a later valid YAML root key
        # shadowing on, permissions or jobs after the reviewed boundary.
        expected_roots = (
            ["name: Operability Admission Inventory PR", "on:", "permissions:",
             "concurrency:", "jobs:"]
            if label == "publisher" else
            ["name: Operability Admission Inventory PR Source Negative", "on:",
             "permissions:", "jobs:"]
        )
        observed_roots = [
            row for row in value.splitlines()
            if row.strip() and not row[0].isspace()
            and not row.lstrip().startswith("#")
        ]
        if observed_roots != expected_roots:
            raise SystemExit("inventory PR " + label + " root YAML key shadow drift")
        # Both reviewed workflows require read-only root permissions.
        # YAML quoted/spaced leaf keys may shadow a visible contents: read.
        permission_lines = value.split("\npermissions:\n", 1)[1].splitlines()
        permission_rows = []
        for row in permission_lines:
            if row.strip() and not row[0].isspace():
                break
            if row.strip() and not row.lstrip().startswith("#"):
                permission_rows.append(row)
        if permission_rows != ["  contents: read"]:
            raise SystemExit("inventory PR " + label + " permission leaf shadow drift")



def validate_job_authority(pr: str, guard: str) -> None:
    """Require reviewed PR-only and independent job identities and read-only scopes."""
    reviewed = (
        ("publisher", pr, "validate",
         "github.event_name == 'pull_request' && github.base_ref == 'so'", 10),
        ("independent", guard, "source-admission",
         "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", 5),
    )
    for label, value, name, condition, timeout in reviewed:
        if value.count("\njobs:\n") != 1:
            raise SystemExit("inventory PR " + label + " job mapping shadow drift")
        body = value.split("\njobs:\n", 1)[1]
        headers = [
            line for line in body.splitlines()
            if line.startswith("  ") and len(line) > 2 and line[2] != " "
            and not line.lstrip().startswith("#")
        ]
        if headers != ["  " + name + ":"]:
            raise SystemExit("inventory PR " + label + " job mapping shadow drift")
        lines = body.splitlines()[1:]
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
            raise SystemExit("inventory PR " + label + " job key shadow drift")
        start = lines.index("    permissions:")
        leaves = []
        for line in lines[start + 1:]:
            if line.startswith("    ") and len(line) > 4 and line[4] != " ":
                break
            if line.strip() and not line.lstrip().startswith("#"):
                leaves.append(line)
        if leaves != ["      contents: read"]:
            raise SystemExit("inventory PR " + label + " job permission leaf shadow drift")


def prove_job_authority_negatives(pr: str, guard: str) -> None:
    """Prove 24 exact-diagnostic nested job and permission shadow cases."""
    validate_job_authority(pr, guard)
    count = 0
    for label, value, other, name, condition, timeout, is_publisher in (
        ("publisher", pr, guard, "validate",
         "github.event_name == 'pull_request' && github.base_ref == 'so'", 10, True),
        ("independent", guard, pr, "source-admission",
         "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", 5, False),
    ):
        header = "  " + name + ":\n"
        if value.count(header) != 1:
            raise SystemExit("inventory PR job fixture header drift: " + label)

        def in_job(old: str, new: str) -> str:
            prefix, suffix = value.split(header, 1)
            if old not in suffix:
                raise SystemExit("inventory PR job fixture anchor missing: " + label)
            return prefix + header + suffix.replace(old, new, 1)

        condition_anchor = "    if: " + condition + "\n"
        permission = "    permissions:\n      contents: read\n"
        runner = "    runs-on: ubuntu-latest\n"
        timeout_anchor = "    timeout-minutes: " + str(timeout) + "\n"
        steps = "    steps:\n"
        cases = [
            ("duplicate mapping", value + "\n" + header + "    runs-on: ubuntu-latest\n", "job mapping shadow drift"),
            ("quoted mapping", value.replace(header, "  '" + name + "':\n", 1), "job mapping shadow drift"),
            ("spaced mapping", value.replace(header, "  " + name + " :\n", 1), "job mapping shadow drift"),
            ("condition shadow", in_job(condition_anchor, condition_anchor + "    if : true\n"), "job key shadow drift"),
            ("permission shadow", in_job(permission, permission + "    permissions :\n      contents: write\n"), "job key shadow drift"),
            ("runner shadow", in_job(runner, runner + "    runs-on : ubuntu-latest\n"), "job key shadow drift"),
            ("timeout shadow", in_job(timeout_anchor, timeout_anchor + "    timeout-minutes : 1\n"), "job key shadow drift"),
            ("steps shadow", in_job(steps, "    steps : []\n" + steps), "job key shadow drift"),
            ("continuation override", in_job(steps, "    continue-on-error: true\n" + steps), "job key shadow drift"),
            ("direct permission change", in_job(permission, permission.replace("contents: read", "contents: write")), "job permission leaf shadow drift"),
            ("spaced permission leaf", in_job(permission, permission + "      contents : write\n"), "job permission leaf shadow drift"),
            ("quoted permission leaf", in_job(permission, permission + "      'contents': write\n"), "job permission leaf shadow drift"),
        ]
        for mutation, changed, diagnostic in cases:
            if changed == value:
                raise SystemExit("inventory PR unchanged job fixture: " + label + " " + mutation)
            try:
                if is_publisher:
                    validate_job_authority(changed, other)
                else:
                    validate_job_authority(other, changed)
            except SystemExit as exc:
                expected = "inventory PR " + label + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("inventory PR wrong job diagnostic: " + label + " " + mutation + ": " + str(exc)) from exc
            else:
                raise SystemExit("inventory PR accepted job shadow: " + label + " " + mutation)
            count += 1
    if count != 24:
        raise SystemExit("inventory PR job negative inventory drift")
    print("PASS: inventory PR publisher/independent job authority (24 exact-diagnostic negatives)")


def trigger_negatives(pr: str, guard: str) -> None:
    """Prove all reviewed event paths, unquoted extras, truncation and event topology."""
    cases = (
        ("publisher PR", pr, "  pull_request:\n    branches:\n      - so\n    paths:\n",
         "\npermissions:\n", PR_TRIGGER_PATHS, True),
        ("independent PR", guard, "  pull_request:\n    branches: [so]\n    paths:\n",
         "  push:\n", GUARD_TRIGGER_PATHS, False),
        ("independent push", guard, "  push:\n    branches: [so]\n    paths:\n",
         "\npermissions:\n", GUARD_TRIGGER_PATHS, False),
    )
    omitted = added = 0
    for label, value, start, stop, paths, is_publisher in cases:
        if value.count(start) != 1 or value.count(stop) != 1:
            raise SystemExit("inventory PR trigger negative event anchor drift: " + label)
        begin = value.index(start) + len(start)
        end = value.index(stop, begin)
        block = value[begin:end]
        mutations = []
        for path in paths:
            token = '      - "' + path + '"\n'
            if block.count(token) != 1:
                raise SystemExit("inventory PR trigger omission fixture drift: " + path)
            mutations.append(("omission " + path, block.replace(token, "", 1), True))
        mutations.extend((
            ("quoted extra", block + '      - "unreviewed/**"\n', False),
            ("quoted duplicate", block + '      - "' + paths[0] + '"\n', False),
            ("unquoted extra", block + "      - unreviewed/**\n", False),
            ("unquoted duplicate", block + "      - " + paths[0] + "\n", False),
        ))
        for name, changed, is_omission in mutations:
            mutated = value[:begin] + changed + value[end:]
            if mutated == value:
                raise SystemExit("inventory PR unchanged negative: " + name)
            try:
                if is_publisher:
                    validate_trigger_reachability(mutated, guard)
                else:
                    validate_trigger_reachability(pr, mutated)
            except SystemExit:
                pass
            else:
                raise SystemExit("inventory PR accepted " + label + " " + name)
            omitted += int(is_omission)
            added += int(not is_omission)
    for label, kwargs in (
        ("publisher", {"pr_paths": PR_TRIGGER_PATHS[:-1]}),
        ("independent", {"guard_paths": GUARD_TRIGGER_PATHS[:-1]}),
    ):
        try:
            validate_trigger_reachability(pr, guard, **kwargs)
        except SystemExit:
            pass
        else:
            raise SystemExit("inventory PR accepted shortened " + label + " inventory")
    for label, mutated, is_publisher in (
        ("publisher push event", pr.replace(
            "\npermissions:\n", "  push:\n    branches: [so]\n\npermissions:\n", 1), True),
        ("publisher dispatch event", pr.replace(
            "\npermissions:\n", "  workflow_dispatch:\n\npermissions:\n", 1), True),
        ("independent dispatch event", guard.replace(
            "\npermissions:\n", "  workflow_dispatch:\n\npermissions:\n", 1), False),
    ):
        try:
            if is_publisher:
                validate_trigger_reachability(mutated, guard)
            else:
                validate_trigger_reachability(pr, mutated)
        except SystemExit:
            pass
        else:
            raise SystemExit("inventory PR accepted event topology mutation: " + label)
    # The reviewed event prefix stays byte-for-byte intact in these
    # mutations: only the root YAML shadow guard can reject them here.
    root_shadows = (
        ("spaced on", "on :\n  workflow_dispatch:\n"),
        ("quoted on", "'on':\n  workflow_dispatch:\n"),
        ("spaced permissions", "permissions :\n  contents: write\n"),
        ("spaced jobs", "jobs : {}\n"),
    )
    root_negative_count = 0
    for label, original, is_publisher in (
        ("publisher", pr, True),
        ("independent", guard, False),
    ):
        for name, suffix in root_shadows:
            mutated = original + suffix
            try:
                if is_publisher:
                    validate_trigger_reachability(mutated, guard)
                else:
                    validate_trigger_reachability(pr, mutated)
            except SystemExit as exc:
                expected = "inventory PR " + label + " root YAML key shadow drift"
                if str(exc) != expected:
                    raise SystemExit(
                        "inventory PR root shadow rejected for wrong reason: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit(
                    "inventory PR accepted root YAML shadow: " + label + " " + name
                )
            root_negative_count += 1
    if root_negative_count != 8:
        raise SystemExit("inventory PR root shadow fixture count drift")
    permission_negative_count = 0
    for label, original, is_publisher in (
        ("publisher", pr, True),
        ("independent", guard, False),
    ):
        anchor = "permissions:\n  contents: read\n"
        if original.count(anchor) != 1:
            raise SystemExit("inventory PR permission negative anchor drift: " + label)
        for name, extra in (
            ("spaced", "  contents : write\n"),
            ("quoted", "  'contents': write\n"),
        ):
            mutated = original.replace(anchor, anchor + extra, 1)
            try:
                if is_publisher:
                    validate_trigger_reachability(mutated, guard)
                else:
                    validate_trigger_reachability(pr, mutated)
            except SystemExit as exc:
                expected = "inventory PR " + label + " permission leaf shadow drift"
                if str(exc) != expected:
                    raise SystemExit(
                        "inventory PR permission shadow rejected for wrong reason: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit(
                    "inventory PR accepted permission leaf shadow: " + label + " " + name
                )
            permission_negative_count += 1
    if permission_negative_count != 4:
        raise SystemExit("inventory PR permission leaf fixture count drift")
    print("PASS: inventory PR permission leaf shadows (4 exact-diagnostic negatives)")
    if (omitted, added) != (29, 12):
        raise SystemExit("inventory PR event trigger negative population drift")
    print("PASS: inventory PR exact event triggers (29 omissions; 12 additions; "
          "2 shortened inventories; 3 event topology; 8 root shadow negatives)")


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not a regular file")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped repository")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        raise SystemExit("inventory PR source unavailable: " + relative) from exc


def validate(pr: str, guard: str) -> None:
    validate_trigger_reachability(pr, guard)
    validate_job_authority(pr, guard)
    validate_pr_concurrency_authority(pr)
    checks = (
        ("PR", pr, PR_BLOB, (
            (CHECKOUT, 1), (SETUP, 1), ("  pull_request:\n    branches:\n      - so\n", 1),
            ("    if: github.event_name == 'pull_request' && github.base_ref == 'so'\n", 1),
            ("permissions:\n  contents: read\n", 1), ("    permissions:\n      contents: read\n", 1),
            ("          persist-credentials: false\n", 1),
            ("          ref: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
            ("          PR_HEAD_SHA: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
            (EVENT, 1), (BASE, 1), (SHA, 1), (HEAD, 1),
            ("          python " + SELF + "\n", 1),
            ('          test -z "$(git status --porcelain)"\n', 2),
            ('      - "' + GUARD + '"\n', 1),
            ('      - "' + SELF + '"\n', 1),
        )),
        ("independent", guard, GUARD_BLOB, (
            (CHECKOUT, 1), (SETUP, 1), ("  pull_request:\n    branches: [so]\n", 1),
            ("  push:\n    branches: [so]\n", 1),
            ("permissions:\n  contents: read\n", 1), ("    permissions:\n      contents: read\n", 1),
            ("          persist-credentials: false\n", 1),
            ("          ref: " + D + "{{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
            ("          PR_HEAD_SHA: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
            (BASE, 1), (SHA, 1), (HEAD, 1),
            ('test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"', 1),
            ("    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
            ("          python " + SELF + "\n", 1),
            ('      - "' + PR + '"\n', 2), ('      - "' + GUARD + '"\n', 2), ('      - "' + SELF + '"\n', 2),
            ('          test -z "$(git status --porcelain)"\n', 2),
        )),
    )
    for label, content, expected, anchors in checks:
        for token, count in anchors:
            if content.count(token) != count:
                raise SystemExit("inventory PR " + label + " anchor drift: " + repr(token[:80]))
        data = content.encode("utf-8")
        blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        if hashlib.sha1(blob).hexdigest() != expected:
            raise SystemExit("inventory PR " + label + " complete source drift")


def runtime() -> None:
    cases = (
        (EVENT, "GITHUB_EVENT_NAME", (("pull_request", True), ("push", False), ("", False))),
        (BASE, "GITHUB_BASE_REF", (("so", True), ("main", False), ("", False))),
    )
    for command, key, values in cases:
        for value, allow in values:
            result = subprocess.run(["bash", "-e", "-c", command],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                    capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("inventory PR runtime event/base drift: " + key + " " + value)
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                         ("A" * 40, False), ("g" * 40, False), ("", False)):
        command = 'expected="' + D + '{PROBE_SHA:-}"\n' + SHA
        result = subprocess.run(["bash", "-e", "-c", command],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value},
                                capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("inventory PR runtime SHA drift: " + value)
    print("PASS: inventory PR runtime event/base (6) and SHA (6) cases")


def negatives(pr: str, guard: str) -> None:
    cases = (
        ("PR", CHECKOUT, "uses: actions/checkout@v4"),
        ("PR", SETUP, "uses: actions/setup-python@v5"),
        ("PR", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("PR", EVENT, "true"), ("PR", BASE, "true"),
        ("PR", SHA, 'test -n "$expected"'),
        ("PR", HEAD, "true"),
        ("PR", "          python " + SELF + "\n", "          true\n"),
        ("PR", "    if: github.event_name == 'pull_request' && github.base_ref == 'so'\n", "    if: always()\n"),
        ("PR", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("independent", CHECKOUT, "uses: actions/checkout@v4"),
        ("independent", SETUP, "uses: actions/setup-python@v5"),
        ("independent", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("independent", "  pull_request:\n    branches: [so]\n", "  pull_request:\n"),
        ("independent", BASE, "true"), ("independent", SHA, 'test -n "$expected"'),
        ("independent", HEAD, "true"),
        ("independent", "          python " + SELF + "\n", "          true\n"),
        ("independent", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
    )
    for label, old, new in cases:
        original = pr if label == "PR" else guard
        if original.count(old) != 1:
            raise SystemExit("inventory PR negative fixture ambiguous: " + label + " " + old[:60])
        mutated = original.replace(old, new, 1)
        try:
            validate(mutated, guard) if label == "PR" else validate(pr, mutated)
        except SystemExit:
            continue
        raise SystemExit("inventory PR accepted source mutation: " + label)
    print("PASS: inventory PR source negative mutations (20 cases)")


def validate_pr_concurrency_authority(source: str) -> None:
    """Pin the reviewed PR-only inventory cancellation policy separately from its blob."""
    marker = "\nconcurrency:\n"
    end = "\njobs:\n"
    group = ("  group: operability-admission-inventory-pr-"
             + chr(36) + "{{ github.event.pull_request.number }}\n")
    expected = group + "  cancel-in-progress: true\n"
    if source.count(marker) != 1 or source.count(end) != 1:
        raise SystemExit("inventory PR concurrency scope drift")
    if source.split(marker, 1)[1].split(end, 1)[0] != expected:
        raise SystemExit("inventory PR concurrency scope drift")


def prove_pr_concurrency_authority_negatives(source: str) -> None:
    """Reject ten YAML-equivalent PR concurrency mutations by exact diagnostic."""
    validate_pr_concurrency_authority(source)
    group = ("  group: operability-admission-inventory-pr-"
             + chr(36) + "{{ github.event.pull_request.number }}\n")
    original = group + "  cancel-in-progress: true\n"
    cases = (
        ("global group", "  group: operability-admission-inventory-pr-global\n  cancel-in-progress: true\n"),
        ("cancel disabled", original.replace("true", "false")),
        ("duplicate group", original + "  group: unreviewed-global\n"),
        ("duplicate cancellation", original + "  cancel-in-progress: false\n"),
        ("spaced group", original + "  group : unreviewed-global\n"),
        ("quoted group", original + "  'group': unreviewed-global\n"),
        ("spaced cancellation", original + "  cancel-in-progress : false\n"),
        ("quoted cancellation", original + "  'cancel-in-progress': false\n"),
        ("unreviewed leaf", original + "  max-parallel: 10\n"),
        ("removed cancellation", group),
    )
    if source.count(original) != 1 or len(cases) != 10:
        raise SystemExit("inventory PR concurrency fixture anchor drift")
    for label, replacement in cases:
        mutated = source.replace(original, replacement, 1)
        if mutated == source:
            raise SystemExit("inventory PR inert concurrency fixture: " + label)
        try:
            validate_pr_concurrency_authority(mutated)
        except SystemExit as exc:
            if str(exc) != "inventory PR concurrency scope drift":
                raise SystemExit("inventory PR wrong concurrency diagnostic: " + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("inventory PR accepted concurrency mutation: " + label)
    print("PASS: inventory PR concurrency scope (10 exact-diagnostic negatives)")


def main() -> int:
    pr, guard = source(PR), source(GUARD)
    validate(pr, guard)
    trigger_negatives(pr, guard)
    prove_job_authority_negatives(pr, guard)
    runtime()
    prove_pr_concurrency_authority_negatives(pr)
    negatives(pr, guard)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
