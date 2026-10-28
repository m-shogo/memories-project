#!/usr/bin/env python3
"""Read-only exact-source, runtime and diagnostic privacy proof for migration evidence CI."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/migration-evidence-registry.yml"
INDEPENDENT = ".github/workflows/migration-evidence-registry-source-negative.yml"
SELF = "scripts/validate-memory-os-migration-evidence-registry-workflow-source-negative.py"
PUBLISHER_SHA = "7770a3774201a492d18b90ed96f7feadfcd82788"
INDEPENDENT_SHA = "878f920daaa183087dceb1dc8c24dde0b47e2180"

PUBLISHER_TRIGGER_PATHS = (
    ".github/workflows/migration-evidence-registry.yml",
    ".github/workflows/migration-evidence-registry-source-negative.yml",
    "scripts/validate-memory-os-migration-evidence-registry-workflow-source-negative.py",
    "contracts/operations/migration-evidence-registry-contract.v1.json",
    "contracts/operations/migration-evidence-registry.v1.json",
    "contracts/operations/migration-lifecycle-contract.v1.json",
    "contracts/operations/local-migration-recovery-artifact-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "contracts/operations/production-operability-status.json",
    "docs/evidence/migrations/recovery/**",
    "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
    "scripts/memory_os_migration_recovery_point.py",
    "scripts/run-memory-os-local-migration-recovery-artifact.sh",
    "scripts/validate-memory-os-local-migration-recovery-artifact.py",
    "scripts/validate-memory-os-local-migration-recovery-artifact-reconcile-negative.py",
    "scripts/reconcile-memory-os-local-migration-recovery-artifact.py",
    "scripts/reconcile-memory-os-migration-recovery-result-orphans.py",
    "scripts/register-memory-os-migration-rehearsal-evidence.py",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/validate-memory-os-migration-evidence-registry.py",
    "scripts/validate-memory-os-migration-evidence-registry-append-negative.py",
    "scripts/validate-memory-os-migration-evidence-registry-reconcile-authority-negative.py",
    "scripts/reconcile-memory-os-migration-evidence-registry.py",
    "scripts/validate-memory-os-migration-lifecycle.py",
    "scripts/validate-memory-os-operability.py",
)
INDEPENDENT_TRIGGER_PATHS = (
    ".github/workflows/migration-evidence-registry.yml",
    ".github/workflows/migration-evidence-registry-source-negative.yml",
    "scripts/validate-memory-os-migration-evidence-registry-workflow-source-negative.py",
    "scripts/validate-memory-os-migration-evidence-registry-reconcile-authority-negative.py",
    "scripts/reconcile-memory-os-migration-evidence-registry.py",
)
AUTHORITY_NEGATIVE = "scripts/validate-memory-os-migration-evidence-registry-reconcile-authority-negative.py"
AUTHORITY_NEGATIVE_SHA = "e7a730b30064e069efc969a1b7e9715725911815"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
PR_SHA = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA = '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'
CLONE_CHECKOUT = 'git -C "$sandbox/repo" checkout --quiet --detach "$(git rev-parse HEAD)"'
CLONE_CLEAN = '            test -z "$(git status --porcelain)"'



def validate_trigger_reachability(
    source: str, *, publisher: bool, trigger_paths: tuple[str, ...] | None = None
) -> None:
    """Pin complete reviewed PR/push paths without relying on a changed Git blob."""
    expected = PUBLISHER_TRIGGER_PATHS if publisher else INDEPENDENT_TRIGGER_PATHS
    paths = expected if trigger_paths is None else trigger_paths
    if len(paths) != len(expected) or len(set(paths)) != len(expected):
        raise SystemExit("migration evidence CI trigger inventory shortened or duplicated")
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    end = "  workflow_dispatch:\n" if publisher else "\npermissions:\n"
    if any(source.count(marker) != 1 for marker in (pr, push, end)):
        raise SystemExit("migration evidence CI event marker drift")
    if not (source.index(pr) < source.index(push) < source.index(end)):
        raise SystemExit("migration evidence CI event ordering drift")
    for event, start, stop in (("pull_request", pr, push), ("push", push, end)):
        block = source.split(start, 1)[1].split(stop, 1)[0]
        actual = tuple(line for line in block.splitlines()
                       if line.strip() and not line.lstrip().startswith("#"))
        approved = tuple('      - "' + path + '"' for path in paths)
        if actual != approved:
            raise SystemExit("migration evidence CI " + event + " exact trigger inventory drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    """Prove every event omission, extra/duplicate and shortened inventory."""
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    for label, source, paths, is_publisher in (
        ("publisher", publisher, PUBLISHER_TRIGGER_PATHS, True),
        ("independent", independent, INDEPENDENT_TRIGGER_PATHS, False),
    ):
        end = "  workflow_dispatch:\n" if is_publisher else "\npermissions:\n"
        for event, start, stop in (("pull_request", pr, push), ("push", push, end)):
            start_index = source.index(start) + len(start)
            end_index = source.index(stop, start_index)
            block = source[start_index:end_index]
            for path in paths:
                token = '      - "' + path + '"\n'
                if block.count(token) != 1:
                    raise SystemExit("migration evidence CI mutation anchor drift: " + path)
                mutated = source[:start_index] + block.replace(token, "", 1) + source[end_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("migration evidence CI accepted missing " + label + " " + event + " trigger: " + path)
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
                    raise SystemExit("migration evidence CI accepted " + label + " " + event + " " + name)
        try:
            validate_trigger_reachability(source, publisher=is_publisher, trigger_paths=paths[:-1])
        except SystemExit:
            pass
        else:
            raise SystemExit("migration evidence CI accepted shortened " + label + " inventory")
    print("PASS: migration evidence CI event triggers (68 removals; 16 additions; 2 shortened inventory negatives)")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("migration evidence CI source guard: " + message)


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
    ("'output': 'REDACTED: migration evidence registry failed; raw output withheld'", 1),
    ("raw validator log suppressed", 1),
    ('cat "$log"', 0),
    ("text[-12000:]", 0),
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
    ('      - "' + AUTHORITY_NEGATIVE + '"\n', 2),
    ('      - "' + "scripts/reconcile-memory-os-migration-evidence-registry.py" + '"\n', 2),
    ("python " + AUTHORITY_NEGATIVE, 1),
    ("git clone --quiet --no-hardlinks --no-checkout .", 1),
    (CLONE_CHECKOUT, 1),
    (CLONE_CLEAN, 1),
    ("permissions:\n  contents: read\n", 1),
    ("      contents: read\n", 1),
)


def validate(publisher: str, independent: str, authority_negative: str | None = None) -> None:
    check_source("publisher", publisher, PUBLISHER_SHA, PUBLISHER_REQUIRED)
    check_source("independent", independent, INDEPENDENT_SHA, INDEPENDENT_REQUIRED)
    validate_trigger_reachability(publisher, publisher=True)
    validate_trigger_reachability(independent, publisher=False)
    validate_yaml_authority(publisher, 'publisher')
    validate_yaml_authority(independent, 'independent')
    check_source("lifecycle negative", read(AUTHORITY_NEGATIVE) if authority_negative is None else authority_negative,
                 AUTHORITY_NEGATIVE_SHA, ())


def validate_yaml_authority(content: str, kind: str) -> None:
    """Bind reviewed migration evidence YAML event/root/permission semantics without blob-only reliance."""
    if kind == "publisher":
        name = "name: Migration Evidence Registry"
        events = ["  pull_request:", "  push:", "  workflow_dispatch:"]
        roots = [name, "on:", "permissions:", "concurrency:", "jobs:"]
    elif kind == "independent":
        name = "name: Migration Evidence Registry Source Negative"
        events = ["  pull_request:", "  push:"]
        roots = [name, "on:", "permissions:", "jobs:"]
    else:
        raise SystemExit("migration evidence unknown YAML authority kind")
    prefix = "migration evidence " + kind + " "
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
    body = content.split("\n" + "jobs:\n", 1)[1]
    if kind == "publisher":
        jobs = (
            ("validate-pr", "    if: github.event_name == 'pull_request'", "read", 8),
            ("reconcile", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "write", 8),
        )
    else:
        jobs = (
            ("source-negative", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", "read", 5),
        )
    headers = [
        row for row in body.splitlines()
        if row.startswith("  ") and not row.startswith("   ")
        and row.strip() and not row.lstrip().startswith("#")
    ]
    if headers != ["  " + job[0] + ":" for job in jobs]:
        raise SystemExit(prefix + "job mapping shadow drift")
    for index, (job, condition, scope, timeout) in enumerate(jobs):
        section = body.split("  " + job + ":\n", 1)[1]
        if index + 1 < len(jobs):
            section = section.split("  " + jobs[index + 1][0] + ":\n", 1)[0]
        keys = [
            row for row in section.splitlines()
            if row.startswith("    ") and not row.startswith("     ")
            and row.strip() and not row.lstrip().startswith("#")
        ]
        if keys != [
            condition, "    permissions:", "    runs-on: ubuntu-latest",
            "    timeout-minutes: " + str(timeout), "    steps:",
        ]:
            raise SystemExit(prefix + "job key/permission shadow drift")
        marker = "    permissions:\n"
        if (section.count(marker) != 1
                or section.split(marker, 1)[1].split("    runs-on: ubuntu-latest\n", 1)[0]
                != "      contents: " + scope + "\n"):
            raise SystemExit(prefix + "job permission scope drift")


def prove_yaml_authority_negatives(publisher: str, independent: str) -> None:
    """Require intended diagnostics for publisher and independent CI shadow mutations."""
    count = 0
    for kind, content in (("publisher", publisher), ("independent", independent)):
        validate_yaml_authority(content, kind)
        event = content.replace("on:\n", "on:\n  issues:\n", 1)
        if event == content:
            raise SystemExit("migration evidence " + kind + " event fixture anchor drift")
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
            raise SystemExit("migration evidence " + kind + " permission fixture anchor drift")
        for label, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((label, content.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        jobs = (
            (("validate-pr", "    if: github.event_name == 'pull_request'", "read"),
             ("reconcile", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "write"))
            if kind == "publisher" else
            (("source-negative", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", "read"),)
        )
        for job, condition, scope in jobs:
            job_anchor = "  " + job + ":\n"
            if content.count(job_anchor) != 1:
                raise SystemExit("migration evidence " + kind + " job fixture anchor drift: " + job)
            for label, suffix in (
                ("duplicate job", "  " + job + ": {}\n"),
                ("spaced job", "  " + job + " : {}\n"),
                ("quoted job", "  '" + job + "': {}\n"),
            ):
                cases.append((job + " " + label, content.rstrip("\n") + "\n" + suffix,
                              "job mapping shadow drift"))
            prefix, section = content.split(job_anchor, 1)
            runs_on = "    runs-on: ubuntu-latest\n"
            if runs_on not in section:
                raise SystemExit("migration evidence " + kind + " runs-on fixture anchor drift: " + job)
            for label, leaf in (
                ("job permission", "    permissions:\n      contents: write\n"),
                ("spaced job permission", "    permissions :\n      contents: write\n"),
                ("quoted job permission", "    'permissions':\n      contents: write\n"),
            ):
                cases.append((job + " " + label,
                              prefix + job_anchor + section.replace(runs_on, runs_on + leaf, 1),
                              "job key/permission shadow drift"))
            permission = "    permissions:\n      contents: " + scope + "\n"
            if permission not in section:
                raise SystemExit("migration evidence " + kind + " scope fixture anchor drift: " + job)
            alternate = "write" if scope == "read" else "read"
            cases.append((job + " direct scope", prefix + job_anchor + section.replace(
                permission, "    permissions:\n      contents: " + alternate + "\n", 1),
                "job permission scope drift"))
            for label, leaf in (
                ("spaced contents", "      contents : write\n"),
                ("quoted contents", "      'contents': write\n"),
            ):
                cases.append((job + " " + label, prefix + job_anchor + section.replace(
                    permission, permission + leaf, 1), "job permission scope drift"))
            if condition + "\n" not in section:
                raise SystemExit("migration evidence " + kind + " event fixture anchor drift: " + job)
            cases.append((job + " event bypass", prefix + job_anchor + section.replace(
                condition + "\n", "    if: true\n", 1),
                "job key/permission shadow drift"))
        if len(cases) != (29 if kind == "publisher" else 19):
            raise SystemExit("migration evidence " + kind + " YAML fixture count drift")
        for label, mutated, diagnostic in cases:
            if mutated == content:
                raise SystemExit("migration evidence " + kind + " unchanged YAML fixture: " + label)
            try:
                validate_yaml_authority(mutated, kind)
            except SystemExit as exc:
                expected = "migration evidence " + kind + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("migration evidence " + kind + " wrong YAML diagnostic: "
                                     + label + ": " + str(exc)) from exc
            else:
                raise SystemExit("migration evidence " + kind + " accepted YAML mutation: " + label)
            count += 1
    if count != 48:
        raise SystemExit("migration evidence YAML negative population drift")
    print("PASS: migration evidence publisher/independent YAML event/root/job/permission authority (48 exact-diagnostic negatives)")


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
        ("publisher redaction", True, "'output': 'REDACTED: migration evidence registry failed; raw output withheld'", "'output': text[-12000:]"),
        ("publisher log suppression", True, "raw validator log suppressed", "raw validator log exposed"),
        ("independent PR base", False, PR_BASE, "true"),
        ("independent writer ref", False, WRITER_REF, "true"),
        ("independent SHA", False, PR_SHA, 'test -n "$expected"'),
        ("independent checkout pin", False, CHECKOUT, "uses: actions/checkout@v4"),
        ("independent setup pin", False, SETUP, "uses: actions/setup-python@v5"),
        ("independent event scope", False, "  push:\n    branches:\n      - so\n", "  workflow_dispatch:\n"),
        ("independent digest-only drift", False, "\n", "\n# unauthorized independent source drift\n"),
        ("independent credentials", False, "persist-credentials: false", "persist-credentials: true"),
        ("independent self guard", False, "python " + SELF, "echo skip"),
        ("independent lifecycle guard", False, "python " + AUTHORITY_NEGATIVE, "echo skip"),
        ("independent isolated clone", False, "git clone --quiet --no-hardlinks --no-checkout .", "echo skip"),
        ("independent clone exact HEAD", False, CLONE_CHECKOUT, 'git -C "$sandbox/repo" checkout --quiet so'),
        ("independent clone inner clean", False, CLONE_CLEAN, "            true"),
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
            require(reason.startswith("migration evidence CI source guard: ") and expected in reason,
                    "negative rejected for wrong reason: " + label + ": " + reason)
            continue
        raise SystemExit("migration evidence source negative accepted: " + label)
    suite = read(AUTHORITY_NEGATIVE)
    require("def prove_stronger_lifecycle_authority_cannot_be_downgraded" in suite,
            "lifecycle downgrade negative entrypoint missing")
    try:
        validate(publisher, independent, suite.replace(
            "def prove_stronger_lifecycle_authority_cannot_be_downgraded",
            "def disabled_stronger_lifecycle_authority_cannot_be_downgraded", 1))
    except SystemExit as exc:
        require("lifecycle negative complete Git blob drift" in str(exc),
                "lifecycle suite mutation rejected for wrong reason: " + str(exc))
    else:
        raise SystemExit("migration evidence source negative accepted: lifecycle suite digest drift")
    print("PASS: migration evidence CI source negatives (27 cases)")


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
    print("PASS: migration evidence branch/SHA runtime (18 cases)")


def require_diagnostic_payload(raw: str) -> None:
    """Reject secret-bearing or promotion-shaped diagnostic JSON."""
    require("CANARY_DO_NOT_PERSIST_MIGRATION_EVIDENCE" not in raw,
            "migration evidence diagnostic persisted sensitive canary")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit("migration evidence CI source guard: diagnostic invalid JSON") from exc
    require(isinstance(value, dict), "migration evidence diagnostic root must be object")
    require(set(value) == {
        "schemaVersion", "workflow", "result", "exitCode", "sourceCommitSha",
        "output", "containsSecrets", "productionEvidence", "productionReady",
    }, "migration evidence diagnostic field inventory drift")
    require(value.get("schemaVersion") == "memory-os-validator-diagnostic.v1",
            "migration evidence diagnostic schema drift")
    require(value.get("workflow") == "migration-evidence-registry" and value.get("result") == "FAIL",
            "migration evidence diagnostic identity drift")
    require(value.get("sourceCommitSha") == "e" * 40 and value.get("exitCode") == 23,
            "migration evidence diagnostic source/exit drift")
    require(value.get("output") == "REDACTED: migration evidence registry failed; raw output withheld",
            "migration evidence diagnostic raw output not redacted")
    require(value.get("containsSecrets") is False and value.get("productionEvidence") is False
            and value.get("productionReady") is False,
            "migration evidence diagnostic asserted secrets/evidence/readiness")


def diagnostic_runtime(publisher: str) -> None:
    """Execute the actual reviewed inline writer with a canary in an isolated directory."""
    marker = "      - name: Record privacy-safe diagnostic\n"
    require(publisher.count(marker) == 1, "migration evidence diagnostic step not unique")
    section = publisher.split(marker, 1)[1]
    start, end = "          python - <<'PY'\n", "          PY\n"
    require(section.count(start) == 1 and section.count(end) >= 1,
            "migration evidence inline diagnostic writer not unique")
    inline = section.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    marker_text = "'REDACTED: migration evidence registry failed; raw output withheld'"
    require(script.count(marker_text) == 1, "migration evidence diagnostic marker not unique")
    require(script.count("'productionReady': False") == 1, "migration evidence diagnostic readiness guard not unique")
    with tempfile.TemporaryDirectory(prefix="migration-evidence-diagnostic-proof-") as temp:
        root = Path(temp)
        env = os.environ.copy()
        env.update({"SOURCE_COMMIT_SHA": "e" * 40, "MIGRATION_EXIT_CODE": "23",
                    "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_MIGRATION_EVIDENCE"})
        variants = (
            ("reviewed", script, True, None),
            ("secrets flag promotion", script.replace("'containsSecrets': False", "'containsSecrets': True", 1),
             False, "asserted secrets/evidence/readiness"),
            ("evidence flag promotion", script.replace("'productionEvidence': False", "'productionEvidence': True", 1),
             False, "asserted secrets/evidence/readiness"),
            ("schema version", script.replace("'schemaVersion': 'memory-os-validator-diagnostic.v1'",
                 "'schemaVersion': 'unreviewed.v1'", 1), False, "diagnostic schema drift"),
            ("workflow identity", script.replace("'workflow': 'migration-evidence-registry'",
                 "'workflow': 'unreviewed-writer'", 1), False, "diagnostic identity drift"),
            ("result identity", script.replace("'result': 'FAIL'", "'result': 'PASS'", 1),
             False, "diagnostic identity drift"),
            ("source identity", script.replace("'sourceCommitSha': os.environ['SOURCE_COMMIT_SHA']",
                 "'sourceCommitSha': '0' * 40", 1), False, "diagnostic source/exit drift"),
            ("exit code identity", script.replace("'exitCode': int(os.environ['MIGRATION_EXIT_CODE'])",
                 "'exitCode': 0", 1), False, "diagnostic source/exit drift"),
            ("output redaction", script.replace(marker_text, "'unreviewed output'", 1),
             False, "raw output not redacted"),
            ("raw canary", script.replace(marker_text, "os.environ['SENSITIVE_CANARY']", 1),
             False, "persisted sensitive canary"),
            ("readiness promotion", script.replace("'productionReady': False", "'productionReady': True", 1),
             False, "asserted secrets/evidence/readiness"),
            ("unreviewed traffic", script.replace("'productionReady': False,",
                "'productionReady': False,\n    'productionTraffic': True,", 1),
             False, "diagnostic field inventory drift"),
            ("unreviewed credentials", script.replace("'productionReady': False,",
                "'productionReady': False,\n    'productionCredentials': True,", 1),
             False, "diagnostic field inventory drift"),
            ("unreviewed raw field", script.replace("'productionReady': False,",
                "'productionReady': False,\n    'rawSql': 'SELECT 1',", 1),
             False, "diagnostic field inventory drift"),
            ("array root", script.replace("json.dump(value, handle, indent=2)",
                "json.dump([value], handle, indent=2)", 1),
             False, "diagnostic root must be object"),
            ("scalar root", script.replace("json.dump(value, handle, indent=2)",
                "json.dump('not-an-object', handle, indent=2)", 1),
             False, "diagnostic root must be object"),
            ("invalid JSON", script.replace("json.dump(value, handle, indent=2)",
                "handle.write('{invalid json')", 1),
             False, "diagnostic invalid JSON"),
        )
        for name, program, allowed, expected_failure in variants:
            directory = root / name.replace(" ", "-")
            directory.mkdir()
            result = subprocess.run([sys.executable, "-c", program], cwd=directory, env=env,
                                    capture_output=True, text=True, timeout=15, check=False)
            require(result.returncode == 0, "migration evidence diagnostic writer failed in isolation: " + name)
            require("CANARY_DO_NOT_PERSIST_MIGRATION_EVIDENCE" not in result.stdout + result.stderr,
                    "migration evidence diagnostic leaked canary to process output")
            path = directory / "docs/fixtures/memory-os-operability/migration-evidence-registry-diagnostic.last.json"
            require(path.is_file() and not path.is_symlink(), "migration evidence diagnostic output missing")
            raw = path.read_text(encoding="utf-8")
            try:
                require_diagnostic_payload(raw)
            except SystemExit as exc:
                require(not allowed, "migration evidence reviewed diagnostic rejected")
                require(expected_failure is not None and expected_failure in str(exc),
                        "migration evidence diagnostic rejected for wrong reason: " + name + ": " + str(exc))
            else:
                require(allowed, "migration evidence diagnostic accepted unsafe mutation: " + name)
    print("PASS: migration evidence actual diagnostic writer (1 positive, 16 negative runtime cases)")



def diagnostic_atomic_runtime(publisher: str) -> None:
    """Execute the reviewed writer against preexisting modes and injected atomic failures."""
    marker = "      - name: Record privacy-safe diagnostic\n"
    require(publisher.count(marker) == 1, "migration evidence diagnostic atomic step not unique")
    section = publisher.split(marker, 1)[1]
    start, end = "          python - <<'PY'\n", "          PY\n"
    require(section.count(start) == 1 and section.count(end) >= 1,
            "migration evidence atomic writer extraction drift")
    script = "\n".join(line[10:] for line in section.split(start, 1)[1].split(end, 1)[0].splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="migration-evidence-diagnostic-atomic-") as temp:
        directory = Path(temp)
        path = directory / "docs/fixtures/memory-os-operability/migration-evidence-registry-diagnostic.last.json"
        path.parent.mkdir(parents=True)
        original = b'{"previous": "preserve-on-failure"}\n'
        env = os.environ.copy()
        env.update({"SOURCE_COMMIT_SHA": "e" * 40, "MIGRATION_EXIT_CODE": "23"})
        def reset() -> None:
            path.write_bytes(original)
            path.chmod(0o640)
        def check_mode_and_cleanup(label: str) -> None:
            require(stat.S_IMODE(path.stat().st_mode) == 0o640,
                    "migration evidence diagnostic mode drift: " + label)
            require(not list(path.parent.glob(".migration-evidence-registry-diagnostic.*.tmp")),
                    "migration evidence diagnostic temporary file remained: " + label)
        def execute(program: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([sys.executable, "-c", program], cwd=directory, env=env,
                                  capture_output=True, text=True, timeout=15, check=False)
        reset()
        positive = execute(script)
        require(positive.returncode == 0, "migration evidence diagnostic atomic positive failed")
        require_diagnostic_payload(path.read_text(encoding="utf-8"))
        check_mode_and_cleanup("successful replacement")
        failures = (
            ("replace", "def fail_replace(*_args):\n    raise OSError('synthetic migration diagnostic replace failure')\nos.replace = fail_replace\n"),
            ("fsync", "def fail_fsync(*_args):\n    raise OSError('synthetic migration diagnostic fsync failure')\nos.fsync = fail_fsync\n"),
        )
        for label, injection in failures:
            reset()
            outcome = execute("import os\n" + injection + script)
            require(outcome.returncode != 0 and "synthetic migration diagnostic " + label + " failure" in outcome.stderr,
                    "migration evidence diagnostic did not reach intended atomic failure: " + label)
            require(path.read_bytes() == original,
                    "migration evidence diagnostic failure mutated existing bytes: " + label)
            check_mode_and_cleanup(label)
        reset()
        outside = directory / "external-diagnostic-canary"
        outside.write_bytes(original)
        path.unlink()
        path.symlink_to(outside)
        symlink_result = execute(script)
        require(symlink_result.returncode != 0 and "target must not be a symlink" in symlink_result.stderr,
                "migration evidence diagnostic accepted symlinked output")
        require(path.is_symlink() and outside.read_bytes() == original,
                "migration evidence diagnostic followed or replaced symlinked output")
        require(not list(path.parent.glob(".migration-evidence-registry-diagnostic.*.tmp")),
                "migration evidence diagnostic left temporary file after symlink rejection")
    print("PASS: migration evidence diagnostic atomic runtime (mode, replace, fsync, symlink)")


def main() -> int:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    validate(publisher, independent)
    prove_yaml_authority_negatives(publisher, independent)
    prove_trigger_reachability_negatives(publisher, independent)
    negative_proofs(publisher, independent)
    runtime_proofs()
    diagnostic_runtime(publisher)
    diagnostic_atomic_runtime(publisher)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
