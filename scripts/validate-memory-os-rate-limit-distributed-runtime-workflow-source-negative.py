#!/usr/bin/env python3
"""Independent, read-only source and runtime fault proof for distributed-rate-limit diagnostics."""
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
PUBLISHER = ".github/workflows/rate-limit-distributed-runtime-admission.yml"
INDEPENDENT = ".github/workflows/rate-limit-distributed-runtime-source-negative.yml"
SELF = "scripts/validate-memory-os-rate-limit-distributed-runtime-workflow-source-negative.py"
REVIEWED_PUBLISHER = "239b456fe90714b4e6bf9d535c92fd38b6e0134d"
REVIEWED_INDEPENDENT = "b66b4476536e1560ce6b0ed5c4f878961af0a296"
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
        raise SystemExit("distributed-rate-limit source missing/substituted: " + relative) from exc


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


RATE_LIMIT_PUBLISHER_PR_PATHS = (
    ".github/workflows/rate-limit-distributed-runtime-admission.yml",
    "contracts/operations/requests/rate-limit-distributed-runtime-foundation.v1.json",
    "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json",
    "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
    "contracts/operations/rate-limit-policy-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "docs/evidence/rate-limit-distributed-runtime/independent-reviews/**",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/register-memory-os-rate-limit-distributed-runtime.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-writer-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-registry-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-evidence-binding-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-generation-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-operations.py",
    "scripts/validate-memory-os-rate-limit.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/reconcile-memory-os-rate-limit-distributed-runtime.py",
)

RATE_LIMIT_PUBLISHER_PUSH_PATHS = (
    ".github/workflows/rate-limit-distributed-runtime-admission.yml",
    "contracts/operations/requests/rate-limit-distributed-runtime-foundation.v1.json",
    "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json",
    "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
    "contracts/operations/rate-limit-policy-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "docs/evidence/rate-limit-distributed-runtime/independent-reviews/**",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/register-memory-os-rate-limit-distributed-runtime.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-writer-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-registry-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-evidence-binding-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-generation-authority-negative.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-reconcile-negative.py",
    "scripts/validate-memory-os-rate-limit-operations.py",
    "scripts/validate-memory-os-rate-limit.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/reconcile-memory-os-rate-limit-distributed-runtime.py",
)

RATE_LIMIT_INDEPENDENT_PR_PATHS = (
    ".github/workflows/rate-limit-distributed-runtime-admission.yml",
    ".github/workflows/rate-limit-distributed-runtime-source-negative.yml",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-workflow-source-negative.py",
)

RATE_LIMIT_INDEPENDENT_PUSH_PATHS = (
    ".github/workflows/rate-limit-distributed-runtime-admission.yml",
    ".github/workflows/rate-limit-distributed-runtime-source-negative.yml",
    "scripts/validate-memory-os-rate-limit-distributed-runtime-workflow-source-negative.py",
)

def rate_limit_trigger_event(event: str, paths: tuple[str, ...], branch: bool = True) -> str:
    return ("  " + event + ":\n" + ("    branches:\n      - so\n" if branch else "") + "    paths:\n"
            + "".join('      - "' + path + '"\n' for path in paths))


def rate_limit_trigger_header(content: str) -> str:
    # Exact, ordered event header: reject unknown, unquoted, duplicate and
    # unexpected event paths instead of depending only on a Git blob digest.
    if content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1:
        raise SystemExit("rate-limit distributed trigger section ambiguous")
    return content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]


def rate_limit_validate_trigger_matrix(
    publisher: str, independent: str,
    publisher_pr: tuple[str, ...] = RATE_LIMIT_PUBLISHER_PR_PATHS,
    publisher_push: tuple[str, ...] = RATE_LIMIT_PUBLISHER_PUSH_PATHS,
    independent_pr: tuple[str, ...] = RATE_LIMIT_INDEPENDENT_PR_PATHS,
    independent_push: tuple[str, ...] = RATE_LIMIT_INDEPENDENT_PUSH_PATHS,
) -> None:
    expected_publisher = (rate_limit_trigger_event("pull_request", publisher_pr, False)
                          + rate_limit_trigger_event("push", publisher_push)
                          + "  workflow_dispatch:\n")
    expected_independent = (rate_limit_trigger_event("pull_request", independent_pr)
                            + rate_limit_trigger_event("push", independent_push))
    for label, content, expected in (
        ("publisher", publisher, expected_publisher),
        ("independent", independent, expected_independent),
    ):
        if rate_limit_trigger_header(content) != expected:
            raise SystemExit("rate-limit distributed " + label
                             + " exact event trigger inventory drift")


def replace_rate_limit_trigger_header(content: str, original: str, replacement: str) -> str:
    old = "\non:\n" + original + "\npermissions:\n"
    if content.count(old) != 1 or original == replacement:
        raise SystemExit("rate-limit distributed trigger negative fixture unreachable")
    return content.replace(old, "\non:\n" + replacement + "\npermissions:\n", 1)


def rate_limit_trigger_matrix_negatives(publisher: str, independent: str) -> None:
    def must_reject(p: str, i: str) -> None:
        try:
            rate_limit_validate_trigger_matrix(p, i)
        except SystemExit:
            return
        raise SystemExit("rate-limit distributed accepted event trigger mutation")

    omissions = additions = 0
    cases = (
        ("publisher", "pull_request", RATE_LIMIT_PUBLISHER_PR_PATHS),
        ("publisher", "push", RATE_LIMIT_PUBLISHER_PUSH_PATHS),
        ("independent", "pull_request", RATE_LIMIT_INDEPENDENT_PR_PATHS),
        ("independent", "push", RATE_LIMIT_INDEPENDENT_PUSH_PATHS),
    )
    for label, event, paths in cases:
        original = publisher if label == "publisher" else independent
        header = rate_limit_trigger_header(original)
        block = rate_limit_trigger_event(event, paths, not (label == "publisher" and event == "pull_request"))
        if header.count(block) != 1:
            raise SystemExit("rate-limit distributed trigger event fixture ambiguous")
        for index in range(len(paths)):
            shorter = paths[:index] + paths[index + 1:]
            mutated = replace_rate_limit_trigger_header(
                original, header, header.replace(block, rate_limit_trigger_event(event, shorter, not (label == "publisher" and event == "pull_request")), 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            omissions += 1
        first = '      - "' + paths[0] + '"\n'
        for addition in (
            '      - "unreviewed/**"\n', '      - unreviewed/**\n',
            first, '      - ' + paths[0] + '\n',
        ):
            mutated_block = block.replace(first, first + addition, 1)
            mutated = replace_rate_limit_trigger_header(
                original, header, header.replace(block, mutated_block, 1))
            must_reject(mutated, independent) if label == "publisher" else must_reject(publisher, mutated)
            additions += 1

    shortened = 0
    for field, paths in (
        ("publisher_pr", RATE_LIMIT_PUBLISHER_PR_PATHS),
        ("publisher_push", RATE_LIMIT_PUBLISHER_PUSH_PATHS),
        ("independent_pr", RATE_LIMIT_INDEPENDENT_PR_PATHS),
        ("independent_push", RATE_LIMIT_INDEPENDENT_PUSH_PATHS),
    ):
        try:
            rate_limit_validate_trigger_matrix(publisher, independent, **{field: paths[:-1]})
        except SystemExit:
            shortened += 1
        else:
            raise SystemExit("rate-limit distributed accepted shortened trigger inventory")

    p_header, i_header = rate_limit_trigger_header(publisher), rate_limit_trigger_header(independent)
    topology = (
        (replace_rate_limit_trigger_header(
            publisher, p_header, p_header.replace("  pull_request:\n    paths:\n", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1)), independent),
        (replace_rate_limit_trigger_header(
            publisher, p_header, p_header.replace("  workflow_dispatch:\n", "", 1)), independent),
        (replace_rate_limit_trigger_header(
            publisher, p_header, p_header.replace(
                "  workflow_dispatch:\n",
                "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)), independent),
        (publisher, replace_rate_limit_trigger_header(
            independent, i_header, i_header + "  workflow_dispatch:\n")),
    )
    for p, i in topology:
        must_reject(p, i)
    print("PASS: rate-limit distributed exact trigger matrix: "
          + str(omissions) + " omissions, " + str(additions)
          + " additions/duplicates, " + str(shortened)
          + " shortened inventories, " + str(len(topology)) + " event topology negatives")



def validate_yaml_root_permission(publisher: str, independent: str) -> None:
    """Pin reviewed root YAML mapping and read-only permission leaves."""
    for label, value, roots in (
        ("publisher", publisher, ["name: Rate Limit Distributed Runtime Admission",
                                  "on:", "permissions:", "concurrency:", "jobs:"]),
        ("independent", independent, ["name: Rate Limit Distributed Runtime Source Negative",
                                      "on:", "permissions:", "jobs:"]),
    ):
        actual = [line for line in value.splitlines()
                  if line.strip() and not line[0].isspace()
                  and not line.lstrip().startswith("#")]
        if actual != roots:
            raise SystemExit("distributed-rate-limit " + label + " root YAML key shadow drift")
        if value.count("\npermissions:\n") != 1:
            raise SystemExit("distributed-rate-limit " + label + " permission boundary drift")
        leaves = []
        for line in value.split("\npermissions:\n", 1)[1].splitlines():
            if line.strip() and not line[0].isspace():
                break
            if line.strip() and not line.lstrip().startswith("#"):
                leaves.append(line)
        if leaves != ["  contents: read"]:
            raise SystemExit("distributed-rate-limit " + label + " permission leaf shadow drift")


def yaml_root_permission_negatives(publisher: str, independent: str) -> None:
    """Prove twelve exact-diagnostic YAML root and permission shadow mutations."""
    validate_yaml_root_permission(publisher, independent)
    count = 0
    for label, value, other, is_publisher in (
        ("publisher", publisher, independent, True),
        ("independent", independent, publisher, False),
    ):
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
            raise SystemExit("distributed-rate-limit " + label + " permission fixture anchor drift")
        for mutation, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((mutation, value.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        for mutation, changed, diagnostic in cases:
            if changed == value:
                raise SystemExit("distributed-rate-limit unchanged YAML fixture: " + mutation)
            try:
                if is_publisher:
                    validate_yaml_root_permission(changed, other)
                else:
                    validate_yaml_root_permission(other, changed)
            except SystemExit as exc:
                expected = "distributed-rate-limit " + label + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("distributed-rate-limit wrong YAML diagnostic: "
                                     + label + " " + mutation + ": " + str(exc)) from exc
            else:
                raise SystemExit("distributed-rate-limit accepted YAML shadow: " + label + " " + mutation)
            count += 1
    if count != 12:
        raise SystemExit("distributed-rate-limit YAML negative inventory drift")
    print("PASS: distributed-rate-limit root/permission YAML authority (12 exact-diagnostic negatives)")


def validate(publisher: str, independent: str) -> None:
    publisher_required = (
        "  push:\n    branches:\n      - so\n",
        "  workflow_dispatch:\n",
        "permissions:\n  contents: read\n", "      contents: write\n",
        '          echo "Distributed rate limit validation completed; raw validator output withheld."\n',
        "'output': 'Distributed rate limit validation failed; raw validator output withheld.',",
        "if candidate.is_symlink():", "if not path.parent.is_dir():",
        "path.parent.resolve(strict=True).relative_to(repo)",
        "if path.exists() and not path.is_file():",
        "os.fchmod(handle.fileno(), mode)", "os.fsync(handle.fileno())",
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
                raise SystemExit("distributed-rate-limit " + label + " missing source: " + token)
        if blob(content) != digest:
            raise SystemExit("distributed-rate-limit " + label + " complete Git blob drift")
    if '          cat "$log"\n' in publisher or "text[-12000:]" in publisher:
        raise SystemExit("distributed-rate-limit raw log disclosure")
    if "path.parent.mkdir(parents=True, exist_ok=True)" in publisher:
        raise SystemExit("distributed-rate-limit diagnostic creates unchecked parent")


def inline_writer(publisher: str) -> str:
    marker = "          python - <<'PY'\n"
    if publisher.count(marker) != 1:
        raise SystemExit("distributed-rate-limit diagnostic inline writer ambiguous")
    start = publisher.index(marker) + len(marker)
    end = publisher.index("\n          PY\n", start)
    lines = publisher[start:end].splitlines()
    if not lines or any(not line.startswith("          ") for line in lines):
        raise SystemExit("distributed-rate-limit diagnostic inline writer indentation drift")
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
    env = dict(os.environ, SOURCE_SHA="a" * 40, RUNTIME_EXIT_CODE="1", INJECT_FAULT=fault)
    result = subprocess.run([sys.executable, "-c", injection + code],
                            cwd=root, env=env, capture_output=True, text=True,
                            timeout=10, check=False)
    if (result.returncode == 0) != success:
        raise SystemExit("distributed-rate-limit diagnostic runtime exit drift: " + (fault or "path"))


def runtime(publisher: str) -> None:
    code = inline_writer(publisher)
    with tempfile.TemporaryDirectory(prefix="distributed-rate-limit-diagnostic-negative-") as tmp:
        root = Path(tmp)
        parent = root / "docs/fixtures/memory-os-operability"
        parent.mkdir(parents=True)
        path = parent / "rate-limit-distributed-runtime-diagnostic.last.json"
        leftovers = lambda: list(parent.glob("." + path.name + ".*.tmp"))
        run_writer(code, root, True)
        value = json.loads(path.read_text(encoding="utf-8"))
        if (value.get("sourceCommitSha") != "a" * 40 or
            value.get("output") != "Distributed rate limit validation failed; raw validator output withheld." or
            value.get("containsSecrets") is not False or
            value.get("productionEvidence") is not False or
            value.get("productionReady") is not False or leftovers()):
            raise SystemExit("distributed-rate-limit diagnostic positive/redaction drift")
        path.chmod(0o640)
        run_writer(code, root, True)
        if stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise SystemExit("distributed-rate-limit diagnostic mode drift")
        original = path.read_bytes()
        for fault in ("replace", "fsync"):
            run_writer(code, root, False, fault)
            if path.read_bytes() != original or stat.S_IMODE(path.stat().st_mode) != 0o640 or leftovers():
                raise SystemExit("distributed-rate-limit diagnostic fault changed prior bytes/mode/temp")
        external = root / "external-canary"
        external.write_text("external\n", encoding="utf-8")
        path.unlink()
        path.symlink_to(external)
        run_writer(code, root, False)
        if external.read_text(encoding="utf-8") != "external\n" or leftovers():
            raise SystemExit("distributed-rate-limit diagnostic followed target symlink")
        path.unlink()
        outside = root / "outside"
        outside.mkdir()
        (outside / path.name).write_text("outside\n", encoding="utf-8")
        old_parent = root / "old-parent"
        parent.rename(old_parent)
        parent.symlink_to(outside, target_is_directory=True)
        run_writer(code, root, False)
        if (outside / path.name).read_text(encoding="utf-8") != "outside\n":
            raise SystemExit("distributed-rate-limit diagnostic followed parent symlink")
        parent.unlink()
        old_parent.rename(parent)
        shutil.rmtree(parent)
        run_writer(code, root, False)
        if parent.exists():
            raise SystemExit("distributed-rate-limit diagnostic created missing parent")
        parent.mkdir()
        path.mkdir()
        run_writer(code, root, False)
        if not path.is_dir() or leftovers():
            raise SystemExit("distributed-rate-limit diagnostic accepted nonregular target")
    print("PASS: distributed-rate-limit diagnostic redaction/atomic/symlink runtime (8 cases)")


def source_negatives(publisher: str, independent: str) -> None:
    p_cases = (
        ('raw CI log', '          echo "Distributed rate limit validation completed; raw validator output withheld."\n', '          cat "$log"\n'),
        ("raw diagnostic", "'output': 'Distributed rate limit validation failed; raw validator output withheld.',", "'output': text[-12000:],"),
        ("symlink", "if candidate.is_symlink():", "if False:"),
        ("missing parent", "if not path.parent.is_dir():", "if False:"),
        ("escape", "path.parent.resolve(strict=True).relative_to(repo)", "path.parent.resolve(strict=True)"),
        ("regular", "if path.exists() and not path.is_file():", "if False:"),
        ("mode", "os.fchmod(handle.fileno(), mode)", "pass"),
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
                raise SystemExit("distributed-rate-limit negative fixture missing: " + name + "/" + label)
            altered = original.replace(old, new, 1)
            if altered == original:
                raise SystemExit("distributed-rate-limit negative fixture unchanged: " + name + "/" + label)
            try:
                validate(altered, independent) if name == "publisher" else validate(publisher, altered)
            except SystemExit:
                continue
            raise SystemExit("distributed-rate-limit accepted mutation: " + name + "/" + label)
    print("PASS: distributed-rate-limit publisher (10) and independent (10) source mutations")


def predicate_runtime(independent: str) -> None:
    for command in (PR_BASE, PUSH_REF, SHA_FORMAT):
        if independent.count(command) != 1:
            raise SystemExit("distributed-rate-limit runtime predicate missing/ambiguous")
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
            raise SystemExit("distributed-rate-limit runtime branch/base predicate drift")
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                         ("A" * 40, False), ("g" * 40, False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", SHA_FORMAT],
                                env=dict(os.environ, expected=value), capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("distributed-rate-limit runtime SHA predicate drift")
    print("PASS: distributed-rate-limit branch/base (6) and SHA (6) runtime cases")


def main() -> int:
    publisher, independent = source(PUBLISHER), source(INDEPENDENT)
    validate(publisher, independent)
    rate_limit_validate_trigger_matrix(publisher, independent)
    rate_limit_trigger_matrix_negatives(publisher, independent)
    validate_yaml_root_permission(publisher, independent)
    yaml_root_permission_negatives(publisher, independent)
    predicate_runtime(independent)
    source_negatives(publisher, independent)
    runtime(publisher)
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
