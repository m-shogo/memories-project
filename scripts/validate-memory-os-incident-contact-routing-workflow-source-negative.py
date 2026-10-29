#!/usr/bin/env python3
"""Independent, read-only source and runtime fault proof for contact-routing diagnostics."""
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
PUBLISHER = ".github/workflows/incident-contact-routing-admission.yml"
INDEPENDENT = ".github/workflows/incident-contact-routing-source-negative.yml"
SELF = "scripts/validate-memory-os-incident-contact-routing-workflow-source-negative.py"
REVIEWED_PUBLISHER = "df3ecb650747f2d2686b2cd9fbeb5737e4975522"
REVIEWED_INDEPENDENT = "2946cdfb8b9c006bb58a83de866e2ba495e550b5"

PUBLISHER_PR_TRIGGER_PATHS = (
    ".github/workflows/incident-contact-routing-admission.yml",
    "contracts/operations/requests/incident-contact-routing-foundation.v1.json",
    "contracts/operations/incident-contact-routing-admission-contract.v1.json",
    "contracts/operations/incident-contact-routing-admission-registry.v1.json",
    "contracts/operations/observability-stack-deployment-contract.v1.json",
    "contracts/operations/observability-stack-deployment-registry.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "docs/evidence/incident-contact-routing/independent-reviews/**",
    "docs/evidence/observability-stack/independent-reviews/**",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/register-memory-os-observability-stack-deployment.py",
    "scripts/register-memory-os-incident-contact-routing.py",
    "scripts/validate-memory-os-incident-contact-routing-writer-authority-negative.py",
    "scripts/validate-memory-os-incident-contact-routing.py",
    "scripts/reconcile-memory-os-incident-contact-routing.py",
    "scripts/validate-memory-os-incident-contact-routing-reconcile-negative.py",
    "scripts/validate-memory-os-incident-contact-routing-generation-authority-negative.py",
    "scripts/validate-memory-os-incident-response.py",
    "scripts/validate-memory-os-operability.py",
)
PUBLISHER_PUSH_TRIGGER_PATHS = (
    ".github/workflows/incident-contact-routing-admission.yml",
    "contracts/operations/requests/incident-contact-routing-foundation.v1.json",
    "contracts/operations/incident-contact-routing-admission-contract.v1.json",
    "contracts/operations/incident-contact-routing-admission-registry.v1.json",
    "contracts/operations/observability-stack-deployment-contract.v1.json",
    "contracts/operations/observability-stack-deployment-registry.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "docs/evidence/incident-contact-routing/independent-reviews/**",
    "docs/evidence/observability-stack/independent-reviews/**",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/register-memory-os-observability-stack-deployment.py",
    "scripts/register-memory-os-incident-contact-routing.py",
    "scripts/validate-memory-os-incident-contact-routing-writer-authority-negative.py",
    "scripts/validate-memory-os-incident-contact-routing.py",
    "scripts/reconcile-memory-os-incident-contact-routing.py",
    "scripts/validate-memory-os-incident-contact-routing-reconcile-negative.py",
    "scripts/validate-memory-os-incident-contact-routing-generation-authority-negative.py",
    "scripts/validate-memory-os-incident-response.py",
    "scripts/validate-memory-os-operability.py",
)
INDEPENDENT_PR_TRIGGER_PATHS = (
    ".github/workflows/incident-contact-routing-admission.yml",
    ".github/workflows/incident-contact-routing-source-negative.yml",
    "scripts/validate-memory-os-incident-contact-routing-workflow-source-negative.py",
)
INDEPENDENT_PUSH_TRIGGER_PATHS = (
    ".github/workflows/incident-contact-routing-admission.yml",
    ".github/workflows/incident-contact-routing-source-negative.yml",
    "scripts/validate-memory-os-incident-contact-routing-workflow-source-negative.py",
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
    """Preserve publisher PR paths-only and independent PR branch-restricted trigger topology."""
    expected_pr = PUBLISHER_PR_TRIGGER_PATHS if publisher else INDEPENDENT_PR_TRIGGER_PATHS
    expected_push = PUBLISHER_PUSH_TRIGGER_PATHS if publisher else INDEPENDENT_PUSH_TRIGGER_PATHS
    approved_pr = expected_pr if pr_paths is None else pr_paths
    approved_push = expected_push if push_paths is None else push_paths
    for label, actual, expected in (("PR", approved_pr, expected_pr), ("push", approved_push, expected_push)):
        if len(actual) != len(expected) or len(set(actual)) != len(expected):
            raise SystemExit("contact-routing CI " + label + " trigger inventory shortened or duplicated")
    pr = "  pull_request:\n    paths:\n" if publisher else "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    end = "  workflow_dispatch:\n" if publisher else "\npermissions:\n"
    if any(value.count(marker) != 1 for marker in (pr, push, end)):
        raise SystemExit("contact-routing CI event marker drift")
    if not (value.index(pr) < value.index(push) < value.index(end)):
        raise SystemExit("contact-routing CI event order drift")
    for event, start, stop, approved_paths in (
        ("PR", pr, push, approved_pr), ("push", push, end, approved_push)
    ):
        block = value.split(start, 1)[1].split(stop, 1)[0]
        actual = tuple(line for line in block.splitlines()
                       if line.strip() and not line.lstrip().startswith("#"))
        approved = tuple('      - "' + path + '"' for path in approved_paths)
        if actual != approved:
            raise SystemExit("contact-routing CI " + event + " exact trigger path drift")
    # Bind the exclusive full event header and effective YAML root mapping,
    # not just individual PR/push path blocks.
    expected_header = (
        ("name: Incident Contact Routing Admission" if publisher
         else "name: Incident Contact Routing Source Negative")
        + "\n\non:\n"
        + pr + "".join('      - "' + path + '"\n' for path in approved_pr)
        + push + "".join('      - "' + path + '"\n' for path in approved_push)
        + ("  workflow_dispatch:\n" if publisher else "")
    )
    if (value.count("\npermissions:\n") != 1
            or value.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("contact-routing CI exact event header drift")
    expected_roots = (
        ["name: Incident Contact Routing Admission", "on:", "permissions:",
         "concurrency:", "jobs:"]
        if publisher else
        ["name: Incident Contact Routing Source Negative", "on:",
         "permissions:", "jobs:"]
    )
    observed_roots = [
        row for row in value.splitlines()
        if row.strip() and not row[0].isspace()
        and not row.lstrip().startswith("#")
    ]
    if observed_roots != expected_roots:
        raise SystemExit("contact-routing CI root YAML key shadow drift")
    # Both workflow-level permission scopes are read-only; reject YAML
    # quoted or whitespace-colon contents leaf shadows.
    permission_lines = value.split("\npermissions:\n", 1)[1].splitlines()
    permission_rows = []
    for row in permission_lines:
        if row.strip() and not row[0].isspace():
            break
        if row.strip() and not row.lstrip().startswith("#"):
            permission_rows.append(row)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("contact-routing CI permission leaf shadow drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    """Prove every event omission, quoted/unquoted addition and shortened inventory."""
    pub_pr = "  pull_request:\n    paths:\n"
    ind_pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    for label, value, is_publisher, pr_paths, push_paths in (
        ("publisher", publisher, True, PUBLISHER_PR_TRIGGER_PATHS, PUBLISHER_PUSH_TRIGGER_PATHS),
        ("independent", independent, False, INDEPENDENT_PR_TRIGGER_PATHS, INDEPENDENT_PUSH_TRIGGER_PATHS),
    ):
        pr = pub_pr if is_publisher else ind_pr
        end = "  workflow_dispatch:\n" if is_publisher else "\npermissions:\n"
        for event, start, stop, paths in (
            ("PR", pr, push, pr_paths), ("push", push, end, push_paths)
        ):
            start_index = value.index(start) + len(start)
            end_index = value.index(stop, start_index)
            block = value[start_index:end_index]
            for path in paths:
                token = '      - "' + path + '"\n'
                if block.count(token) != 1:
                    raise SystemExit("contact-routing CI mutation anchor drift: " + path)
                mutated = value[:start_index] + block.replace(token, "", 1) + value[end_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("contact-routing CI accepted missing " + label + " " + event + " trigger: " + path)
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
                    raise SystemExit("contact-routing CI accepted " + label + " " + event + " " + name)
        for event in ("PR", "push"):
            try:
                validate_trigger_reachability(
                    value, publisher=is_publisher,
                    pr_paths=pr_paths[:-1] if event == "PR" else pr_paths,
                    push_paths=push_paths[:-1] if event == "push" else push_paths,
                )
            except SystemExit:
                pass
            else:
                raise SystemExit("contact-routing CI accepted shortened " + label + " " + event + " inventory")
    # Additional events before the PR block preserve both reviewed path
    # inventories and must fail the exact full-header guard.
    for label, original, is_publisher in (
        ("publisher", publisher, True),
        ("independent", independent, False),
    ):
        mutated = original.replace("on:\n", "on:\n  issues:\n", 1)
        if mutated == original:
            raise SystemExit("contact-routing CI header negative anchor drift: " + label)
        try:
            validate_trigger_reachability(mutated, publisher=is_publisher)
        except SystemExit as exc:
            if str(exc) != "contact-routing CI exact event header drift":
                raise SystemExit(
                    "contact-routing CI header rejected for wrong reason: "
                    + label + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("contact-routing CI accepted extra event: " + label)
    root_shadows = (
        ("spaced on", "on :\n  issues:\n"),
        ("quoted on", "'on':\n  issues:\n"),
        ("spaced permissions", "permissions :\n  contents: write\n"),
        ("spaced jobs", "jobs : {}\n"),
    )
    root_negative_count = 0
    for label, original, is_publisher in (
        ("publisher", publisher, True),
        ("independent", independent, False),
    ):
        for name, suffix in root_shadows:
            try:
                validate_trigger_reachability(original + suffix, publisher=is_publisher)
            except SystemExit as exc:
                if str(exc) != "contact-routing CI root YAML key shadow drift":
                    raise SystemExit(
                        "contact-routing CI root shadow rejected for wrong reason: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit("contact-routing CI accepted root shadow: " + label + " " + name)
            root_negative_count += 1
    if root_negative_count != 8:
        raise SystemExit("contact-routing CI root shadow fixture count drift")
    permission_negative_count = 0
    for label, original, is_publisher in (
        ("publisher", publisher, True),
        ("independent", independent, False),
    ):
        anchor = "permissions:\n  contents: read\n"
        if original.count(anchor) != 1:
            raise SystemExit("contact-routing CI permission negative anchor drift: " + label)
        for name, extra in (
            ("spaced", "  contents : write\n"),
            ("quoted", "  'contents': write\n"),
        ):
            mutated = original.replace(anchor, anchor + extra, 1)
            try:
                validate_trigger_reachability(mutated, publisher=is_publisher)
            except SystemExit as exc:
                if str(exc) != "contact-routing CI permission leaf shadow drift":
                    raise SystemExit(
                        "contact-routing CI permission shadow rejected for wrong reason: "
                        + label + " " + name + ": " + str(exc)
                    ) from exc
            else:
                raise SystemExit(
                    "contact-routing CI accepted permission leaf shadow: " + label + " " + name
                )
            permission_negative_count += 1
    if permission_negative_count != 4:
        raise SystemExit("contact-routing CI permission leaf fixture count drift")
    print("PASS: contact-routing CI semantic YAML negatives "
          "(2 extra-event, 8 root, 4 permission exact-diagnostic cases)")
    print("PASS: contact-routing CI event triggers (52 removals; 16 additions; 4 shortened inventory negatives)")


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit("contact-routing source missing/substituted: " + relative) from exc


def blob(content: str) -> str:
    data = content.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate(publisher: str, independent: str) -> None:
    validate_job_authority(publisher, independent)
    publisher_required = (
        "  push:\n    branches:\n      - so\n",
        "  workflow_dispatch:\n",
        "permissions:\n  contents: read\n", "      contents: write\n",
        '          echo "Contact routing validation completed; raw validator output withheld."\n',
        "'output': 'Contact routing validation failed; raw validator output withheld.',",
        "if candidate.is_symlink():", "if not path.parent.is_dir():",
        "path.parent.resolve(strict=True).relative_to(repo)",
        "if path.exists() and not path.is_file():",
        "os.fchmod(fd, existing_mode)", "os.fsync(handle.fileno())",
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
                raise SystemExit("contact-routing " + label + " missing source: " + token)
        if blob(content) != digest:
            raise SystemExit("contact-routing " + label + " complete Git blob drift")
    if '          cat "$log"\n' in publisher or "text[-12000:]" in publisher:
        raise SystemExit("contact-routing raw log disclosure")
    if "path.parent.mkdir(parents=True, exist_ok=True)" in publisher:
        raise SystemExit("contact-routing diagnostic creates unchecked parent")


def inline_writer(publisher: str) -> str:
    marker = "          python - <<'PY'\n"
    if publisher.count(marker) != 1:
        raise SystemExit("contact-routing diagnostic inline writer ambiguous")
    start = publisher.index(marker) + len(marker)
    end = publisher.index("\n          PY\n", start)
    lines = publisher[start:end].splitlines()
    if not lines or any(not line.startswith("          ") for line in lines):
        raise SystemExit("contact-routing diagnostic inline writer indentation drift")
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
    env = dict(os.environ, SOURCE_SHA="a" * 40, ROUTING_EXIT_CODE="1", INJECT_FAULT=fault)
    result = subprocess.run([sys.executable, "-c", injection + code],
                            cwd=root, env=env, capture_output=True, text=True,
                            timeout=10, check=False)
    if (result.returncode == 0) != success:
        raise SystemExit("contact-routing diagnostic runtime exit drift: " + (fault or "path"))


def runtime(publisher: str) -> None:
    code = inline_writer(publisher)
    with tempfile.TemporaryDirectory(prefix="contact-routing-diagnostic-negative-") as tmp:
        root = Path(tmp)
        parent = root / "docs/fixtures/memory-os-operability"
        parent.mkdir(parents=True)
        path = parent / "incident-contact-routing-diagnostic.last.json"
        leftovers = lambda: list(parent.glob("." + path.name + ".*.tmp"))
        run_writer(code, root, True)
        value = json.loads(path.read_text(encoding="utf-8"))
        if (value.get("sourceCommitSha") != "a" * 40 or
            value.get("output") != "Contact routing validation failed; raw validator output withheld." or
            value.get("containsSecrets") is not False or
            value.get("productionEvidence") is not False or
            value.get("productionReady") is not False or leftovers()):
            raise SystemExit("contact-routing diagnostic positive/redaction drift")
        path.chmod(0o640)
        run_writer(code, root, True)
        if stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise SystemExit("contact-routing diagnostic mode drift")
        original = path.read_bytes()
        for fault in ("replace", "fsync"):
            run_writer(code, root, False, fault)
            if path.read_bytes() != original or stat.S_IMODE(path.stat().st_mode) != 0o640 or leftovers():
                raise SystemExit("contact-routing diagnostic fault changed prior bytes/mode/temp")
        external = root / "external-canary"
        external.write_text("external\n", encoding="utf-8")
        path.unlink()
        path.symlink_to(external)
        run_writer(code, root, False)
        if external.read_text(encoding="utf-8") != "external\n" or leftovers():
            raise SystemExit("contact-routing diagnostic followed target symlink")
        path.unlink()
        outside = root / "outside"
        outside.mkdir()
        (outside / path.name).write_text("outside\n", encoding="utf-8")
        old_parent = root / "old-parent"
        parent.rename(old_parent)
        parent.symlink_to(outside, target_is_directory=True)
        run_writer(code, root, False)
        if (outside / path.name).read_text(encoding="utf-8") != "outside\n":
            raise SystemExit("contact-routing diagnostic followed parent symlink")
        parent.unlink()
        old_parent.rename(parent)
        shutil.rmtree(parent)
        run_writer(code, root, False)
        if parent.exists():
            raise SystemExit("contact-routing diagnostic created missing parent")
        parent.mkdir()
        path.mkdir()
        run_writer(code, root, False)
        if not path.is_dir() or leftovers():
            raise SystemExit("contact-routing diagnostic accepted nonregular target")
    print("PASS: contact-routing diagnostic redaction/atomic/symlink runtime (8 cases)")


def source_negatives(publisher: str, independent: str) -> None:
    p_cases = (
        ('raw CI log', '          echo "Contact routing validation completed; raw validator output withheld."\n', '          cat "$log"\n'),
        ("raw diagnostic", "'output': 'Contact routing validation failed; raw validator output withheld.',", "'output': text[-12000:],"),
        ("symlink", "if candidate.is_symlink():", "if False:"),
        ("missing parent", "if not path.parent.is_dir():", "if False:"),
        ("escape", "path.parent.resolve(strict=True).relative_to(repo)", "path.parent.resolve(strict=True)"),
        ("regular", "if path.exists() and not path.is_file():", "if False:"),
        ("mode", "os.fchmod(fd, existing_mode)", "pass"),
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
                raise SystemExit("contact-routing negative fixture missing: " + name + "/" + label)
            altered = original.replace(old, new, 1)
            if altered == original:
                raise SystemExit("contact-routing negative fixture unchanged: " + name + "/" + label)
            try:
                validate(altered, independent) if name == "publisher" else validate(publisher, altered)
            except SystemExit:
                continue
            raise SystemExit("contact-routing accepted mutation: " + name + "/" + label)
    print("PASS: contact-routing publisher (10) and independent (10) source mutations")


def predicate_runtime(independent: str) -> None:
    for command in (PR_BASE, PUSH_REF, SHA_FORMAT):
        if independent.count(command) != 1:
            raise SystemExit("contact-routing runtime predicate missing/ambiguous")
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
            raise SystemExit("contact-routing runtime branch/base predicate drift")
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                         ("A" * 40, False), ("g" * 40, False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", SHA_FORMAT],
                                env=dict(os.environ, expected=value), capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("contact-routing runtime SHA predicate drift")
    print("PASS: contact-routing branch/base (6) and SHA (6) runtime cases")


def validate_job_authority(publisher: str, independent: str) -> None:
    """Pin effective job mappings, scope and job keys before blob-only checks."""
    reviewed = (
        ("publisher", publisher, (
            ("validate-pr", "github.event_name == 'pull_request'", "read", 8),
            ("validate-and-publish",
             "github.event_name != 'pull_request'",
             "write", 8),
        )),
        ("independent", independent, (
            ("source-admission",
             "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
             "read", 5),
        )),
    )
    for label, content, jobs in reviewed:
        prefix = "contact-routing CI " + label + " "
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
             "github.event_name != 'pull_request'",
             "write", 8),
        ), True),
        ("independent", independent, publisher, (
            ("source-admission",
             "github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
             "read", 5),
        ), False),
    )
    for label, content, other, jobs, is_publisher in reviewed:
        for name, condition, scope, timeout in jobs:
            header = "  " + name + ":\n"
            if content.count(header) != 1:
                raise SystemExit("contact-routing CI job fixture header drift: " + label + " " + name)

            def in_job(before: str, after: str) -> str:
                prefix, suffix = content.split(header, 1)
                if before not in suffix:
                    raise SystemExit("contact-routing CI job fixture anchor drift: " + name)
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
                    raise SystemExit("contact-routing CI unchanged job fixture: " + mutation)
                try:
                    if is_publisher:
                        validate_job_authority(changed, other)
                    else:
                        validate_job_authority(other, changed)
                except SystemExit as exc:
                    expected = "contact-routing CI " + label + " " + diagnostic
                    if str(exc) != expected:
                        raise SystemExit("contact-routing CI wrong job diagnostic: "
                                         + label + " " + name + " " + mutation + ": " + str(exc)) from exc
                else:
                    raise SystemExit("contact-routing CI accepted job shadow: "
                                     + label + " " + name + " " + mutation)
                count += 1
    if count != 36:
        raise SystemExit("contact-routing CI job negative inventory drift")
    print("PASS: contact-routing CI publisher/independent job authority (36 exact-diagnostic negatives)")


def validate_concurrency_authority(publisher: str) -> None:
    """Bind reviewed incident contact-routing admission serialization."""
    marker = "\nconcurrency:\n"
    end = "\njobs:\n"
    group = "  group: incident-contact-routing-admission-" + chr(36) + "{{ github.event.pull_request.number || 'so' }}\n"
    expected = group + "  cancel-in-progress: false\n"
    if publisher.count(marker) != 1 or publisher.count(end) != 1:
        raise SystemExit("contact-routing publisher concurrency scope drift")
    actual = publisher.split(marker, 1)[1].split(end, 1)[0]
    if actual != expected:
        raise SystemExit("contact-routing publisher concurrency scope drift")


def prove_concurrency_authority_negatives(publisher: str) -> None:
    """Reject unsafe cancellation and group shadows in contact routing."""
    validate_concurrency_authority(publisher)
    group = "  group: incident-contact-routing-admission-" + chr(36) + "{{ github.event.pull_request.number || 'so' }}\n"
    original = group + "  cancel-in-progress: false\n"
    cases = (
        ("global group", "  group: incident-contact-routing-admission-global\n  cancel-in-progress: false\n"),
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
        raise SystemExit("contact-routing concurrency fixture anchor drift")
    for name, block in cases:
        changed = publisher.replace(original, block, 1)
        if changed == publisher:
            raise SystemExit("contact-routing unchanged concurrency fixture: " + name)
        try:
            validate_concurrency_authority(changed)
        except SystemExit as exc:
            if str(exc) != "contact-routing publisher concurrency scope drift":
                raise SystemExit("contact-routing wrong concurrency diagnostic: " + name + ": " + str(exc)) from exc
        else:
            raise SystemExit("contact-routing accepted concurrency mutation: " + name)
    print("PASS: contact-routing publisher concurrency serialization (10 exact-diagnostic negatives)")


def main() -> int:
    publisher, independent = source(PUBLISHER), source(INDEPENDENT)
    validate(publisher, independent)
    validate_trigger_reachability(publisher, publisher=True)
    validate_trigger_reachability(independent, publisher=False)
    prove_trigger_reachability_negatives(publisher, independent)
    prove_job_authority_negatives(publisher, independent)
    prove_concurrency_authority_negatives(publisher)
    predicate_runtime(independent)
    source_negatives(publisher, independent)
    runtime(publisher)
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
