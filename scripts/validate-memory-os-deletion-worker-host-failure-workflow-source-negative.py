#!/usr/bin/env python3
"""Independent, read-only source and runtime fault proof for deletion-host-failure diagnostics."""
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
PUBLISHER = ".github/workflows/deletion-worker-host-failure-admission.yml"
INDEPENDENT = ".github/workflows/deletion-worker-host-failure-source-negative.yml"
PERMISSION = ".github/workflows/deletion-worker-host-failure-permission-negative.yml"
PERMISSION_VALIDATOR = "scripts/validate-memory-os-deletion-worker-host-failure-permission-negative.py"
SELF = "scripts/validate-memory-os-deletion-worker-host-failure-workflow-source-negative.py"
REVIEWED_PUBLISHER = "01f3c5116119e5bc49b6b4431196dce39795be99"
REVIEWED_INDEPENDENT = "22a3ded0b234c3b01cdcd4986d09825059d03c1a"
RECONCILER = "scripts/reconcile-memory-os-deletion-worker-host-failure.py"
RECONCILE_NEGATIVE = "scripts/validate-memory-os-deletion-worker-host-failure-reconcile-negative.py"
REVIEWED_RECONCILER = "18914a55fae994551dd58d7fb89ed9aa617ca7c9"
REVIEWED_RECONCILE_NEGATIVE = "89400e99f33b6dbaaf5c9487a17cfc37834e11af"
REVIEWED_PERMISSION = "c2549cdc7a939dcaa7c91720724e61d31ee9d685"
REVIEWED_PERMISSION_VALIDATOR = "f145162df13bb60d64ae457cc86f4ca59e1a8d2e"
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
        raise SystemExit("deletion-host-failure source missing/substituted: " + relative) from exc


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()



def validate_yaml_root_permission(publisher: str, independent: str, permission: str) -> None:
    """Pin all three reviewed host-failure CI YAML roots and read-only permission leaves."""
    for label, value, roots in (
        ("publisher", publisher, ["name: Deletion Worker Host Failure Admission",
                                  "on:", "permissions:", "concurrency:", "jobs:"]),
        ("independent", independent, ["name: Deletion Worker Host Failure Source Negative",
                                      "on:", "permissions:", "jobs:"]),
        ("permission", permission, ["name: Deletion Host Failure Permission Negative",
                                    "on:", "permissions:", "concurrency:", "jobs:"]),
    ):
        actual = [line for line in value.splitlines()
                  if line.strip() and not line[0].isspace()
                  and not line.lstrip().startswith("#")]
        if actual != roots:
            raise SystemExit("host-failure " + label + " root YAML key shadow drift")
        if value.count("\npermissions:\n") != 1:
            raise SystemExit("host-failure " + label + " permission boundary drift")
        leaves = []
        for line in value.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                leaves.append(line)
        if leaves != ["  contents: read"]:
            raise SystemExit("host-failure " + label + " permission leaf shadow drift")


def yaml_root_permission_negatives(publisher: str, independent: str, permission: str) -> None:
    """Prove eighteen exact-diagnostic root and permission shadows across three workflows."""
    validate_yaml_root_permission(publisher, independent, permission)
    originals = [publisher, independent, permission]
    count = 0
    for index, label in enumerate(("publisher", "independent", "permission")):
        value = originals[index]
        cases = [
            (mutation, value + "\n" + suffix, "root YAML key shadow drift")
            for mutation, suffix in (
                ("spaced on", "on :\n  issues:\n"),
                ("quoted on", "'on':\n  issues:\n"),
                ("spaced jobs", "jobs : {}\n"),
                ("quoted jobs", "'jobs': {}\n"),
            )
        ]
        marker = "\npermissions:\n  contents: read\n"
        if value.count(marker) != 1:
            raise SystemExit("host-failure " + label + " permission fixture anchor drift")
        for mutation, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((mutation, value.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        for mutation, changed, diagnostic in cases:
            if changed == value:
                raise SystemExit("host-failure unchanged YAML fixture: " + label + " " + mutation)
            mutated = list(originals)
            mutated[index] = changed
            try:
                validate_yaml_root_permission(*mutated)
            except SystemExit as exc:
                expected = "host-failure " + label + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("host-failure wrong YAML diagnostic: "
                                     + label + " " + mutation + ": " + str(exc)) from exc
            else:
                raise SystemExit("host-failure accepted YAML shadow: " + label + " " + mutation)
            count += 1
    if count != 18:
        raise SystemExit("host-failure YAML negative inventory drift")
    print("PASS: host-failure triple-workflow root/permission YAML authority (18 exact-diagnostic negatives)")


def validate(publisher: str, independent: str) -> None:
    publisher_required = (
        "  pull_request:\n    branches:\n      - so\n",
        "  push:\n    branches:\n      - so\n",
        "  workflow_dispatch:\n",
        "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "          persist-credentials: false\n",
        "          persist-credentials: true\n",
        "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'",
        'test "${GITHUB_BASE_REF:-}" = "so"',
        'test "${GITHUB_REF:-}" = "refs/heads/so"',
        '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]',
        '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]',
        "permissions:\n  contents: read\n", "      contents: write\n",
        '          echo "Deletion host-failure validation completed; raw validator output withheld."\n',
        "'output': 'Deletion host-failure validation failed; raw validator output withheld.',",
        "if candidate.is_symlink():", "if not path.parent.is_dir():",
        "path.parent.resolve(strict=True).relative_to(repo)",
        "if path.exists() and not path.is_file():",
        "os.fchmod(fd, mode)", "os.fsync(handle.fileno())",
        "os.replace(temp_name, path)", "os.unlink(temp_name)",
    )
    independent_required = (
        "  pull_request:\n    branches:\n      - so\n",
        "  push:\n    branches:\n      - so\n",
        '      - "' + PUBLISHER + '"', '      - "' + INDEPENDENT + '"',
        '      - "' + SELF + '"', '      - "' + PERMISSION + '"',
        '      - "' + PERMISSION_VALIDATOR + '"', CHECKOUT, SETUP,
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
                raise SystemExit("deletion-host-failure " + label + " missing source: " + token)
        if blob(content) != digest:
            raise SystemExit("deletion-host-failure " + label + " complete Git blob drift")
    if '          cat "$log"\n' in publisher or "text[-12000:]" in publisher:
        raise SystemExit("deletion-host-failure raw log disclosure")
    if "path.parent.mkdir(parents=True, exist_ok=True)" in publisher:
        raise SystemExit("deletion-host-failure diagnostic creates unchecked parent")


PUBLISHER_PR_PATHS = (
    ".github/workflows/deletion-worker-host-failure-admission.yml",
    "contracts/operations/deletion-worker-host-failure-contract.v1.json",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "contracts/operations/production-operability-status.json",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/validate-memory-os-deletion-worker-host-failure.py",
    "scripts/validate-memory-os-deletion-worker-host-failure-generation-negative.py",
    "scripts/validate-memory-os-deletion-worker-host-failure-reconcile-negative.py",
    "scripts/reconcile-memory-os-deletion-worker-host-failure.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
)

PUBLISHER_PUSH_PATHS = (
    ".github/workflows/deletion-worker-host-failure-admission.yml",
    "contracts/operations/deletion-worker-host-failure-contract.v1.json",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "contracts/operations/production-operability-status.json",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/validate-memory-os-deletion-worker-host-failure.py",
    "scripts/validate-memory-os-deletion-worker-host-failure-generation-negative.py",
    "scripts/validate-memory-os-deletion-worker-host-failure-reconcile-negative.py",
    "scripts/reconcile-memory-os-deletion-worker-host-failure.py",
    "scripts/validate-memory-os-load.py",
    "scripts/validate-memory-os-operability.py",
)

INDEPENDENT_PR_PATHS = (
    ".github/workflows/deletion-worker-host-failure-admission.yml",
    ".github/workflows/deletion-worker-host-failure-permission-negative.yml",
    ".github/workflows/deletion-worker-host-failure-source-negative.yml",
    "scripts/validate-memory-os-deletion-worker-host-failure-permission-negative.py",
    "scripts/validate-memory-os-deletion-worker-host-failure-workflow-source-negative.py",
    "scripts/reconcile-memory-os-deletion-worker-host-failure.py",
    "scripts/validate-memory-os-deletion-worker-host-failure-reconcile-negative.py",
)

INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/deletion-worker-host-failure-admission.yml",
    ".github/workflows/deletion-worker-host-failure-permission-negative.yml",
    ".github/workflows/deletion-worker-host-failure-source-negative.yml",
    "scripts/validate-memory-os-deletion-worker-host-failure-permission-negative.py",
    "scripts/validate-memory-os-deletion-worker-host-failure-workflow-source-negative.py",
    "scripts/reconcile-memory-os-deletion-worker-host-failure.py",
    "scripts/validate-memory-os-deletion-worker-host-failure-reconcile-negative.py",
)


def trigger_event(event: str, paths: tuple[str, ...]) -> str:
    return ("  " + event + ":\n    branches:\n      - so\n    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("deletion-host-failure trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (trigger_event("pull_request", publisher_pr)
                          + trigger_event("push", publisher_push)
                          + "  workflow_dispatch:\n")
    expected_independent = (trigger_event("pull_request", independent_pr)
                            + trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if trigger_header(content) != expected:
            raise SystemExit("deletion-host-failure " + label
                             + " exact event trigger inventory drift")


def replace_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("deletion-host-failure trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("deletion-host-failure accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", PUBLISHER_PR_PATHS),
        ("publisher", "push", PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", INDEPENDENT_PR_PATHS),
        ("independent", "push", INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = trigger_header(original)
        block = trigger_event(event, paths)
        if header.count(block) != 1:
            raise SystemExit("deletion-host-failure trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_trigger_header(
                original, header, header.replace(block, trigger_event(event, shorter), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", PUBLISHER_PR_PATHS),
        ("publisher_push", PUBLISHER_PUSH_PATHS),
        ("independent_pr", INDEPENDENT_PR_PATHS),
        ("independent_push", INDEPENDENT_PUSH_PATHS),
    ):
        try:
            validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("deletion-host-failure accepted shortened trigger inventory")

    p_header, i_header = trigger_header(publisher), trigger_header(independent)
    topology = (
        (replace_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: deletion-host-failure exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")


def validate_permission(content: str) -> None:
    required = (
        "  pull_request:\n    branches:\n      - so\n",
        "  push:\n    branches:\n      - so\n",
        "  workflow_dispatch:\n",
        "permissions:\n  contents: read\n",
        "    if: github.event_name == 'pull_request' || ((github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so')",
        "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "          persist-credentials: false\n",
        'test "${GITHUB_BASE_REF:-}" = "so"',
        'test "${GITHUB_REF:-}" = "refs/heads/so"',
        '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]',
        "          python scripts/validate-memory-os-deletion-worker-host-failure-permission-negative.py",
    )
    for token in required:
        if token not in content:
            raise SystemExit("deletion-host-failure permission CI source missing: " + token)
    if blob(content) != REVIEWED_PERMISSION:
        raise SystemExit("deletion-host-failure permission CI complete Git blob drift")


def validate_permission_validator(content: str) -> None:
    required = (
        "pull requests must target so",
        "both checkouts must be immutable",
        "both Python setups must be immutable",
        "PR checkout must not persist credentials",
        "PR base identity missing",
        "PR head SHA format missing",
        "publication job must be scoped to so push/dispatch",
        "writer event identity missing",
        "writer branch identity missing",
        "writer SHA format missing",
        "physical host failure evidence fabricated: false",
    )
    for token in required:
        if token not in content:
            raise SystemExit("deletion-host-failure permission validator missing guard: " + token)
    if blob(content) != REVIEWED_PERMISSION_VALIDATOR:
        raise SystemExit("deletion-host-failure permission validator complete Git blob drift")


def permission_validator_negatives(content: str) -> None:
    cases = (
        ("PR base guard", "pull requests must target so", "PR base ignored"),
        ("checkout pin guard", "both checkouts must be immutable", "checkout floating"),
        ("setup pin guard", "both Python setups must be immutable", "setup floating"),
        ("PR credentials guard", "PR checkout must not persist credentials", "PR credentials allowed"),
        ("writer event guard", "writer event identity missing", "writer event ignored"),
        ("writer SHA guard", "writer SHA format missing", "writer SHA ignored"),
        ("host-failure evidence guard", "physical host failure evidence fabricated: false", "physical host evidence accepted"),
    )
    for label, old, new in cases:
        if old not in content:
            raise SystemExit("deletion-host-failure permission validator fixture missing: " + label)
        altered = content.replace(old, new, 1)
        if altered == content:
            raise SystemExit("deletion-host-failure permission validator fixture unchanged: " + label)
        try:
            validate_permission_validator(altered)
        except SystemExit:
            continue
        raise SystemExit("deletion-host-failure permission validator accepted mutation: " + label)
    print("PASS: deletion-host-failure permission validator source mutations (7 cases)")


def permission_negatives(content: str) -> None:
    cases = (
        ("PR base", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n    paths:\n"),
        ("job scope", "    if: github.event_name == 'pull_request' || ((github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so')", "    if: always()"),
        ("checkout pin", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "uses: actions/checkout@v4"),
        ("setup pin", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "uses: actions/setup-python@v5"),
        ("credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR base identity", 'test "${GITHUB_BASE_REF:-}" = "so"', "true"),
        ("writer ref identity", 'test "${GITHUB_REF:-}" = "refs/heads/so"', "true"),
        ("SHA identity", '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]', 'test -n "$expected"'),
        ("permission", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("self validator", "          python scripts/validate-memory-os-deletion-worker-host-failure-permission-negative.py", "          true"),
    )
    for label, old, new in cases:
        if old not in content:
            raise SystemExit("deletion-host-failure permission negative fixture missing: " + label)
        altered = content.replace(old, new, 1)
        if altered == content:
            raise SystemExit("deletion-host-failure permission negative fixture unchanged: " + label)
        try:
            validate_permission(altered)
        except SystemExit:
            continue
        raise SystemExit("deletion-host-failure permission accepted mutation: " + label)
    print("PASS: deletion-host-failure permission workflow source mutations (10 cases)")


def permission_runtime(content: str) -> None:
    marker = "      - name: Require exact clean source\n"
    if content.count(marker) != 1:
        raise SystemExit("deletion-host-failure permission runtime step ambiguous")
    start = content.index("        run: |\n", content.index(marker)) + len("        run: |\n")
    end = content.index("\n      - uses:", start)
    lines = content[start:end].splitlines()
    if not lines or any(line and not line.startswith("          ") for line in lines):
        raise SystemExit("deletion-host-failure permission runtime indentation drift")
    command = "\n".join(line[10:] if line else "" for line in lines) + "\n"
    a = "a" * 40
    with tempfile.TemporaryDirectory(prefix="deletion-host-permission-runtime-") as tmp:
        root = Path(tmp)
        git = root / "git"
        git.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then\n"
            "  printf '" + a + "\\n'\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi\n"
            "exit 1\n", encoding="utf-8",
        )
        git.chmod(0o755)
        cases = (
            ("pull_request", "so", "", a, a, True),
            ("pull_request", "main", "", a, a, False),
            ("pull_request", "so", "", "A" * 40, a, False),
            ("pull_request", "so", "", "b" * 40, a, False),
            ("pull_request", "so", "", "", a, False),
            ("push", "", "refs/heads/so", a, a, True),
            ("push", "", "refs/heads/main", a, a, False),
            ("push", "", "refs/heads/so", a, "A" * 40, False),
            ("push", "", "refs/heads/so", a, "a" * 39, False),
            ("workflow_dispatch", "", "refs/heads/so", a, a, True),
            ("workflow_dispatch", "", "refs/heads/main", a, a, False),
            ("schedule", "", "refs/heads/so", a, a, False),
        )
        for event, base, ref, pr_sha, sha, allowed in cases:
            env = dict(os.environ, PATH=str(root) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                       GITHUB_EVENT_NAME=event, GITHUB_BASE_REF=base, GITHUB_REF=ref,
                       PR_HEAD_SHA=pr_sha, GITHUB_SHA=sha)
            result = subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", command],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
            if (result.returncode == 0) != allowed:
                raise SystemExit("deletion-host-failure permission event/base/ref/SHA runtime drift: " + event)
    print("PASS: deletion-host-failure permission exact-source shell runtime (12 cases)")


def inline_writer(publisher: str) -> str:
    marker = "          python - <<'PY'\n"
    if publisher.count(marker) != 1:
        raise SystemExit("deletion-host-failure diagnostic inline writer ambiguous")
    start = publisher.index(marker) + len(marker)
    end = publisher.index("\n          PY\n", start)
    lines = publisher[start:end].splitlines()
    if not lines or any(not line.startswith("          ") for line in lines):
        raise SystemExit("deletion-host-failure diagnostic inline writer indentation drift")
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
    bindir = root / "bin"
    bindir.mkdir(exist_ok=True)
    fake_git = bindir / "git"
    fake_git.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then\n"
        "  printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\\n'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n", encoding="utf-8",
    )
    fake_git.chmod(0o755)
    env = dict(os.environ, SOURCE_SHA="a" * 40, ADMISSION_EXIT_CODE="1", INJECT_FAULT=fault,
               PATH=str(bindir) + ":" + os.environ.get("PATH", "/usr/bin:/bin"))
    result = subprocess.run([sys.executable, "-c", injection + code],
                            cwd=root, env=env, capture_output=True, text=True,
                            timeout=10, check=False)
    if (result.returncode == 0) != success:
        raise SystemExit("deletion-host-failure diagnostic runtime exit drift: " + (fault or "path"))


def runtime(publisher: str) -> None:
    code = inline_writer(publisher)
    with tempfile.TemporaryDirectory(prefix="deletion-host-failure-diagnostic-negative-") as tmp:
        root = Path(tmp)
        parent = root / "docs/fixtures/memory-os-operability"
        parent.mkdir(parents=True)
        path = parent / "deletion-worker-host-failure-admission-diagnostic.last.json"
        leftovers = lambda: list(parent.glob("." + path.name + ".*.tmp"))
        run_writer(code, root, True)
        value = json.loads(path.read_text(encoding="utf-8"))
        if (value.get("sourceCommitSha") != "a" * 40 or
            value.get("output") != "Deletion host-failure validation failed; raw validator output withheld." or
            value.get("containsSecrets") is not False or
            value.get("productionEvidence") is not False or
            value.get("productionReady") is not False or leftovers()):
            raise SystemExit("deletion-host-failure diagnostic positive/redaction drift")
        path.chmod(0o640)
        run_writer(code, root, True)
        if stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise SystemExit("deletion-host-failure diagnostic mode drift")
        original = path.read_bytes()
        for fault in ("replace", "fsync"):
            run_writer(code, root, False, fault)
            if path.read_bytes() != original or stat.S_IMODE(path.stat().st_mode) != 0o640 or leftovers():
                raise SystemExit("deletion-host-failure diagnostic fault changed prior bytes/mode/temp")
        external = root / "external-canary"
        external.write_text("external\n", encoding="utf-8")
        path.unlink()
        path.symlink_to(external)
        run_writer(code, root, False)
        if external.read_text(encoding="utf-8") != "external\n" or leftovers():
            raise SystemExit("deletion-host-failure diagnostic followed target symlink")
        path.unlink()
        outside = root / "outside"
        outside.mkdir()
        (outside / path.name).write_text("outside\n", encoding="utf-8")
        old_parent = root / "old-parent"
        parent.rename(old_parent)
        parent.symlink_to(outside, target_is_directory=True)
        run_writer(code, root, False)
        if (outside / path.name).read_text(encoding="utf-8") != "outside\n":
            raise SystemExit("deletion-host-failure diagnostic followed parent symlink")
        parent.unlink()
        old_parent.rename(parent)
        shutil.rmtree(parent)
        run_writer(code, root, False)
        if parent.exists():
            raise SystemExit("deletion-host-failure diagnostic created missing parent")
        parent.mkdir()
        path.mkdir()
        run_writer(code, root, False)
        if not path.is_dir() or leftovers():
            raise SystemExit("deletion-host-failure diagnostic accepted nonregular target")
    print("PASS: deletion-host-failure diagnostic redaction/atomic/symlink runtime (8 cases)")


def source_negatives(publisher: str, independent: str) -> None:
    p_cases = (
        ('raw CI log', '          echo "Deletion host-failure validation completed; raw validator output withheld."\n', '          cat "$log"\n'),
        ("raw diagnostic", "'output': 'Deletion host-failure validation failed; raw validator output withheld.',", "'output': text[-12000:],"),
        ("symlink", "if candidate.is_symlink():", "if False:"),
        ("missing parent", "if not path.parent.is_dir():", "if False:"),
        ("escape", "path.parent.resolve(strict=True).relative_to(repo)", "path.parent.resolve(strict=True)"),
        ("regular", "if path.exists() and not path.is_file():", "if False:"),
        ("mode", "os.fchmod(fd, mode)", "pass"),
        ("fsync", "os.fsync(handle.fileno())", "pass"),
        ("atomic", "os.replace(temp_name, path)", "path.write_bytes(payload)"),
        ("cleanup", "os.unlink(temp_name)", "pass"),
        ("PR base scope", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n    paths:\n"),
        ("floating checkout", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "uses: actions/checkout@v4"),
        ("floating setup", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "uses: actions/setup-python@v5"),
        ("PR credential", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("writer event scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "    if: github.event_name != 'pull_request'"),
        ("writer ref", 'test "${GITHUB_REF:-}" = "refs/heads/so"', "true"),
        ("writer SHA", '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]', 'test -n "$GITHUB_SHA"'),
    )
    i_cases = (
        ("PR base", PR_BASE, "true"), ("push branch", PUSH_REF, "true"),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("self trigger", '      - "' + SELF + '"', ""),
        ("publisher trigger", '      - "' + PUBLISHER + '"', ""),
        ("permission trigger", '      - "' + PERMISSION + '"', ""),
        ("permission validator trigger", '      - "' + PERMISSION_VALIDATOR + '"', ""),
        ("root write", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("job scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", "    if: always()"),
    )
    for name, original, cases in (("publisher", publisher, p_cases), ("independent", independent, i_cases)):
        for label, old, new in cases:
            if old not in original:
                raise SystemExit("deletion-host-failure negative fixture missing: " + name + "/" + label)
            altered = original.replace(old, new, 1)
            if altered == original:
                raise SystemExit("deletion-host-failure negative fixture unchanged: " + name + "/" + label)
            try:
                validate(altered, independent) if name == "publisher" else validate(publisher, altered)
            except SystemExit:
                continue
            raise SystemExit("deletion-host-failure accepted mutation: " + name + "/" + label)
    print("PASS: deletion-host-failure publisher (17) and independent (12) source mutations")


def predicate_runtime(independent: str) -> None:
    for command in (PR_BASE, PUSH_REF, SHA_FORMAT):
        if independent.count(command) != 1:
            raise SystemExit("deletion-host-failure runtime predicate missing/ambiguous")
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
            raise SystemExit("deletion-host-failure runtime branch/base predicate drift")
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                         ("A" * 40, False), ("g" * 40, False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", SHA_FORMAT],
                                env=dict(os.environ, expected=value), capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("deletion-host-failure runtime SHA predicate drift")
    print("PASS: deletion-host-failure branch/base (6) and SHA (6) runtime cases")


def reconcile_runtime() -> None:
    # Existing reconciler negatives write canonical contract/status; never execute in the source checkout.
    fixtures = (
        RECONCILER, RECONCILE_NEGATIVE,
        "contracts/operations/deletion-worker-host-failure-contract.v1.json",
        "contracts/operations/production-operability-status.json",
        "contracts/operations/load-test-scenario-contract.v1.json",
        PUBLISHER,
        "scripts/validate-memory-os-deletion-worker-host-failure.py",
        "scripts/validate-memory-os-load.py",
        "scripts/validate-memory-os-operability.py",
    )
    with tempfile.TemporaryDirectory(prefix="host-failure-reconcile-disposable-") as tmp:
        root = Path(tmp)
        for relative in fixtures:
            source(relative)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        result = subprocess.run([sys.executable, str(root / RECONCILE_NEGATIVE)],
                                cwd=root, capture_output=True, text=True, timeout=90, check=False)
        if result.returncode != 0 or "eight atomic path/mode/rollback cases" not in result.stdout:
            raise SystemExit("host-failure disposable reconcile negative failed; raw output withheld")
    print("PASS: host-failure source-bound disposable reconcile and atomic rollback negatives")


def main() -> int:
    publisher, independent = source(PUBLISHER), source(INDEPENDENT)
    if blob(source(RECONCILER)) != REVIEWED_RECONCILER or blob(source(RECONCILE_NEGATIVE)) != REVIEWED_RECONCILE_NEGATIVE:
        raise SystemExit("host-failure reconciler/negative complete Git blob unreviewed")
    if independent.count(RECONCILER) != 2 or independent.count(RECONCILE_NEGATIVE) != 2:
        raise SystemExit("host-failure reconcile negative PR/push trigger reachability drift")
    permission = source(PERMISSION)
    permission_validator = source(PERMISSION_VALIDATOR)
    validate(publisher, independent)
    validate_yaml_root_permission(publisher, independent, permission)
    yaml_root_permission_negatives(publisher, independent, permission)
    validate_trigger_matrix(publisher, independent)
    trigger_matrix_negatives(publisher, independent)
    validate_permission(permission)
    validate_permission_validator(permission_validator)
    permission_validator_negatives(permission_validator)
    permission_negatives(permission)
    permission_runtime(permission)
    predicate_runtime(independent)
    source_negatives(publisher, independent)
    runtime(publisher)
    reconcile_runtime()
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
